from ..localization import translate as tr

import math
from dataclasses import replace

import adsk.core
import adsk.fusion

from ..core.thread_parameters import ThreadParameters
from .thread_records import capture_record, attach_record
from .chamfer import capture_chamfer_ends, create_revolved_chamfers
from .face_analysis import (
    CylinderGeometry,
    analyze_cylinder,
)


PROFILE_OVERLAP = 0.01  # 0,1 mm in Fusion-internen Zentimetern
HELIX_OVERRUN_TURNS = 1.0


def thread_section(cylinder, parameters, chamfer_ends=None):
    """Resolve the chosen physical end before any model changes."""
    if chamfer_ends is None:
        chamfer_ends = capture_chamfer_ends(cylinder, parameters.chamfer_edges)
    physical = _trim_reference_from_selected_circles(cylinder, chamfer_ends)
    if parameters.full_length:
        return physical
    if parameters.start_edge is None:
        raise ValueError(tr('start_edge_required'))
    start_end = capture_chamfer_ends(cylinder, (parameters.start_edge,))[0]
    low, high = parameters.axial_range(physical.length, from_end=not start_end.is_start)
    for end in chamfer_ends:
        if (end.is_start and low > 1e-7) or (not end.is_start and high < physical.length - 1e-7):
            raise ValueError(tr('chamfer_outside_range'))
        axial_size = ((parameters.thread_depth + parameters.chamfer_extra)
                      * math.tan(parameters.flank_angle / 2) + 0.01)
        if axial_size > high - low:
            raise ValueError(tr('chamfer_outside_range'))
    return replace(physical,
                   axis_start=_translated_point(physical.axis_start, physical.axis, low),
                   axis_end=_translated_point(physical.axis_start, physical.axis, high),
                   length=high - low)


def create_thread(parameters: ThreadParameters, creation_occurrence=None, calculation_mode='free',
                  group_timeline=True):
    errors = parameters.validation_errors()
    if errors:
        raise ValueError('\n'.join(errors))

    cylinder = analyze_cylinder(parameters.face)
    record = capture_record(parameters, calculation_mode, creation_occurrence)
    chamfer_ends = capture_chamfer_ends(cylinder, parameters.chamfer_edges)
    trim_reference = thread_section(cylinder, parameters, chamfer_ends)
    timeline = cylinder.component.parentDesign.timeline
    timeline_start = timeline.count
    parameter_sketch = _create_parameter_note_sketch(cylinder, parameters)
    tolerance_feature = None
    try:
        radial_offset = parameters.tolerance_radius_offset(cylinder.is_external)
        cylinder, tolerance_feature = _apply_radial_tolerance(
            cylinder, trim_reference, radial_offset
        )
        trim_reference = replace(
            trim_reference, body=cylinder.body, radius=cylinder.radius
        )
        chamfer_ends = tuple(
            replace(chamfer_end, radius=chamfer_end.radius + radial_offset)
            for chamfer_end in chamfer_ends
        )
        if parameters.sharp_profile_depth >= cylinder.radius:
            raise ValueError(tr('depth_radius'))
    except Exception:
        _delete_if_valid(tolerance_feature)
        _delete_if_valid(parameter_sketch)
        raise

    helix_feature = None
    profile_plane = None
    profile_sketch = None
    try:
        cylinder = _extend_helix(cylinder, trim_reference, parameters.pitch)

        helix_feature, helix_edge, guide_face = _create_persistent_helix(
            cylinder, parameters
        )
        profile_plane = _create_profile_plane(cylinder.component, helix_edge, creation_occurrence)
        profile = _create_cut_profile(profile_plane, cylinder, parameters)
        profile_sketch = profile.parentSketch
        sweep = _create_thread_sweep(cylinder, profile, helix_edge, guide_face,
                                     bounded_external=not parameters.full_length,
                                     creation_occurrence=creation_occurrence)
        result_feature = (
            sweep
            if cylinder.is_external and parameters.full_length
            else _trim_and_combine_thread(
                cylinder,
                sweep,
                trim_reference.axis_start,
                trim_reference.axis_end,
            )
        )
        target_body = (
            result_feature.bodies.item(0)
            if result_feature.bodies.count
            else cylinder.body
        )
        chamfer_feature = create_revolved_chamfers(
            trim_reference,
            target_body,
            chamfer_ends,
            parameters.thread_depth,
            parameters.flank_angle,
            parameters.chamfer_extra,
        )
        _name_and_hide_helpers(helix_feature, profile_plane, profile_sketch)
        attach_record(record, parameter_sketch, chamfer_feature or result_feature)
        if group_timeline:
            _group_timeline_entries(timeline, timeline_start)
        return chamfer_feature or result_feature
    except Exception:
        _delete_if_valid(profile_sketch)
        _delete_if_valid(profile_plane)
        _delete_if_valid(helix_feature)
        _delete_if_valid(tolerance_feature)
        _delete_if_valid(parameter_sketch)
        raise


def _create_parameter_note_sketch(cylinder, parameters):
    component = cylinder.component
    units = component.parentDesign.unitsManager
    length_units = units.defaultLengthUnits
    radial_offset = parameters.tolerance_radius_offset(cylinder.is_external)
    major_value = (cylinder.radius + radial_offset) * 2
    pitch_value = major_value - parameters.thread_depth
    minor_value = major_value - 2 * parameters.thread_depth
    thread_type = tr('external_thread') if cylinder.is_external else tr('internal_thread')

    def length(value):
        return units.formatInternalValue(value, length_units, True)

    angle = units.formatInternalValue(parameters.flank_angle, 'deg', True)
    bore_value = '–' if cylinder.is_external else length(minor_value)
    section = thread_section(cylinder, parameters)

    def point_text(point):
        return ', '.join(length(value) for value in (point.x, point.y, point.z))

    fields = (
        ('thread_type', thread_type),
        ('thread_direction', tr('right_hand' if parameters.handedness == 'right' else 'left_hand')),
        ('full_length', tr('yes') if parameters.full_length else tr('no')),
        ('start_edge', tr('full_length') if parameters.full_length else point_text(
            capture_chamfer_ends(cylinder, (parameters.start_edge,))[0].center)),
        ('start_offset', length(0.0 if parameters.full_length else parameters.start_offset)),
        ('thread_length', length(cylinder.length if parameters.full_length else parameters.thread_length)),
        ('section_start', point_text(section.axis_start)),
        ('section_end', point_text(section.axis_end)),
        ('nominal_diameter', length(cylinder.radius * 2)),
        ('pitch', length(parameters.pitch)),
        ('profile_angle', angle),
        ('thread_depth', length(parameters.thread_depth)),
        ('fillet_radius', length(parameters.fillet_radius)),
        ('tolerance', length(parameters.tolerance)),
        ('clearance_distribution', tr('distribution_' + parameters.clearance_distribution)),
        ('major_diameter', length(major_value)),
        ('pitch_diameter', length(pitch_value)),
        ('minor_diameter', length(minor_value)),
        ('tap_drill', bore_value),
        ('chamfer_edges', len(parameters.chamfer_edges)),
    )
    text = 'PrintThread Wizard – ' + tr('parameters') + '\n'
    text += '\n'.join(f'{tr(key)}: {value}' for key, value in fields)
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = (
        f"PrintThread Wizard – {tr('parameters')} – {thread_type} – "
        f'd {length(major_value)} – P {length(parameters.pitch)}'
    )
    texts = sketch.sketchTexts
    expression = "'" + text.replace("'", "''") + "'"
    text_input = texts.createInput3(
        expression, adsk.core.ValueInput.createByReal(0.35)
    )
    text_input.setAsMultiLine(
        adsk.core.Point3D.create(0, 0, 0),
        adsk.core.Point3D.create(14, 7, 0),
        adsk.core.HorizontalAlignments.LeftHorizontalAlignment,
        adsk.core.VerticalAlignments.TopVerticalAlignment,
        0,
    )
    if texts.add(text_input) is None:
        _delete_if_valid(sketch)
        raise RuntimeError(tr('note_failed'))
    sketch.isLightBulbOn = False
    return sketch


def _apply_radial_tolerance(cylinder, trim_reference, radial_offset):
    if abs(radial_offset) <= 1e-12:
        return cylinder, None

    adjusted_radius = cylinder.radius + radial_offset
    if adjusted_radius <= 0:
        raise ValueError(tr('tolerance_large'))

    temp_manager = adsk.fusion.TemporaryBRepManager.get()
    if cylinder.is_external:
        tool_body = temp_manager.createCylinderOrCone(
            trim_reference.axis_start,
            cylinder.radius + PROFILE_OVERLAP,
            trim_reference.axis_end,
            cylinder.radius + PROFILE_OVERLAP,
        )
        inner_body = temp_manager.createCylinderOrCone(
            trim_reference.axis_start,
            adjusted_radius,
            trim_reference.axis_end,
            adjusted_radius,
        )
        if tool_body is None or inner_body is None or not temp_manager.booleanOperation(
            tool_body, inner_body, adsk.fusion.BooleanTypes.DifferenceBooleanType
        ):
            raise RuntimeError(tr('tolerance_ring_missing'))
    else:
        tool_body = temp_manager.createCylinderOrCone(
            trim_reference.axis_start,
            adjusted_radius,
            trim_reference.axis_end,
            adjusted_radius,
        )
        if tool_body is None:
            raise RuntimeError(tr('tolerance_cylinder_missing'))

    base_feature = cylinder.component.features.baseFeatures.add()
    base_feature.name = "PrintThread Wizard – " + tr('tolerance_tool')
    base_feature.startEdit()
    try:
        cylinder.component.bRepBodies.add(tool_body, base_feature)
    finally:
        base_feature.finishEdit()
    if base_feature.bodies.count == 0:
        _delete_if_valid(base_feature)
        raise RuntimeError(tr('tolerance_tool_failed'))

    tools = adsk.core.ObjectCollection.create()
    tools.add(base_feature.bodies.item(0))
    combines = cylinder.component.features.combineFeatures
    combine_input = combines.createInput(cylinder.body, tools)
    combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    combine_input.isKeepToolBodies = False
    tolerance_cut = combines.add(combine_input)
    if tolerance_cut is None or tolerance_cut.bodies.count == 0:
        _delete_if_valid(base_feature)
        raise RuntimeError(tr('tolerance_cut_failed'))
    tolerance_cut.name = "PrintThread Wizard – " + tr('cylinder_tolerance')
    return replace(
        cylinder, body=tolerance_cut.bodies.item(0), radius=adjusted_radius
    ), tolerance_cut


def _create_persistent_helix(cylinder: CylinderGeometry, parameters: ThreadParameters):
    start_point = _translated_point(cylinder.axis_start, cylinder.radial, cylinder.radius)
    turns = parameters.helix_turns(cylinder.length)
    if cylinder.length <= 0:
        raise ValueError(tr('no_turns'))

    temp_manager = adsk.fusion.TemporaryBRepManager.get()
    helix_axis = cylinder.axis.copy()
    if parameters.handedness == 'left':
        # Reverse rotation while negative pitch preserves the original axial rise.
        # Negative turn counts are rejected by the Fusion kernel.
        helix_axis.scaleBy(-1)
    try:
        temporary_wire = temp_manager.createHelixWire(
            cylinder.axis_start, helix_axis, start_point, parameters.signed_pitch, turns, 0.0
        )
    except RuntimeError as error:
        raise RuntimeError(tr('helix_failed')) from error
    if temporary_wire is None or temporary_wire.edges.count == 0:
        raise RuntimeError(tr('helix_failed'))

    guide_solid = temp_manager.createCylinderOrCone(
        cylinder.axis_start,
        cylinder.radius,
        cylinder.axis_end,
        cylinder.radius,
    )
    if guide_solid is None:
        raise RuntimeError(tr('guide_failed'))
    temporary_guide = None
    for index in range(guide_solid.faces.count):
        face = guide_solid.faces.item(index)
        if adsk.core.Cylinder.cast(face.geometry):
            temporary_guide = temp_manager.copy(face)
            break
    if temporary_guide is None:
        raise RuntimeError(tr('guide_missing'))

    base_feature = cylinder.component.features.baseFeatures.add()
    base_feature.name = "PrintThread Wizard – " + tr('helix')
    base_feature.startEdit()
    try:
        cylinder.component.bRepBodies.add(temporary_wire, base_feature)
        cylinder.component.bRepBodies.add(temporary_guide, base_feature)
    finally:
        base_feature.finishEdit()

    helix_edge = None
    guide_face = None
    for body_index in range(base_feature.bodies.count):
        body = base_feature.bodies.item(body_index)
        if body.faces.count == 0 and body.edges.count:
            body.name = "PrintThread Wizard – " + tr('helix_path')
            helix_edge = body.edges.item(0)
        for face_index in range(body.faces.count):
            face = body.faces.item(face_index)
            if adsk.core.Cylinder.cast(face.geometry):
                body.name = "PrintThread Wizard – " + tr('sweep_guide')
                guide_face = face
                break
        body.isLightBulbOn = False
        body.isVisible = False

    if helix_edge is None or guide_face is None:
        _delete_if_valid(base_feature)
        raise RuntimeError(tr('helix_add_failed'))
    return base_feature, helix_edge, guide_face


def _create_profile_plane(component, helix_edge, creation_occurrence=None):
    # A native B-Rep edge has no assembly path outside the root component.
    # Supply the occurrence explicitly for the calibration component rather
    # than relying on whichever component happens to be active in the UI.
    if creation_occurrence is None:
        plane_input = component.constructionPlanes.createInput()
    else:
        plane_input = component.constructionPlanes.createInput(creation_occurrence)
        helix_edge = helix_edge.createForAssemblyContext(creation_occurrence)
    if not plane_input.setByDistanceOnPath(
        helix_edge, adsk.core.ValueInput.createByReal(0.0)
    ):
        raise RuntimeError(tr('profile_plane_failed'))
    plane = component.constructionPlanes.add(plane_input)
    plane.name = "PrintThread Wizard – " + tr('profile_plane')
    return plane


def _create_cut_profile(plane, cylinder: CylinderGeometry, parameters: ThreadParameters):
    sketch = cylinder.component.sketches.add(plane)
    sketch.name = "PrintThread Wizard – " + tr('cut_profile')

    base_center = _translated_point(
        cylinder.axis_start, cylinder.radial, cylinder.radius + PROFILE_OVERLAP
    )
    apex = _translated_point(
        cylinder.axis_start,
        cylinder.radial,
        cylinder.radius - parameters.sharp_profile_depth,
    )

    base_direction = _profile_base_direction(cylinder, parameters.signed_pitch)

    effective_depth = parameters.sharp_profile_depth + PROFILE_OVERLAP
    half_width = effective_depth * math.tan(parameters.flank_angle / 2)
    left = _translated_point(base_center, base_direction, half_width)
    right = _translated_point(base_center, base_direction, -half_width)

    left_2d = sketch.modelToSketchSpace(left)
    apex_2d = sketch.modelToSketchSpace(apex)
    right_2d = sketch.modelToSketchSpace(right)
    lines = sketch.sketchCurves.sketchLines
    left_flank = lines.addByTwoPoints(left_2d, apex_2d)
    right_flank = lines.addByTwoPoints(left_flank.endSketchPoint, right_2d)
    lines.addByTwoPoints(right_flank.endSketchPoint, left_flank.startSketchPoint)

    if parameters.fillet_radius > 0:
        arc = sketch.sketchCurves.sketchArcs.addFillet(
            left_flank,
            left_flank.endSketchPoint.geometry,
            right_flank,
            right_flank.startSketchPoint.geometry,
            parameters.fillet_radius,
        )
        if arc is None:
            raise ValueError(tr('fillet_failed'))

    if sketch.profiles.count != 1:
        raise RuntimeError(tr('profile_open'))
    return sketch.profiles.item(0)


def _extend_helix(cylinder, trim_reference, pitch):
    overrun = pitch * HELIX_OVERRUN_TURNS
    return replace(
        cylinder,
        axis=trim_reference.axis,
        axis_start=_translated_point(
            trim_reference.axis_start, trim_reference.axis, -overrun
        ),
        axis_end=_translated_point(
            trim_reference.axis_end, trim_reference.axis, overrun
        ),
        length=trim_reference.length + 2 * overrun,
    )


def _trim_reference_from_selected_circles(cylinder, chamfer_ends):
    """Nutzt ausgewählte Kreiszentren als exakte axiale Bauteilgrenzen."""
    start = cylinder.axis_start
    end = cylinder.axis_end
    for chamfer_end in chamfer_ends:
        if chamfer_end.is_start:
            start = chamfer_end.center
        else:
            end = chamfer_end.center

    length = start.vectorTo(end).dotProduct(cylinder.axis)
    if length <= 0:
        raise ValueError(tr('trim_length_invalid'))
    return replace(cylinder, axis_start=start, axis_end=end, length=length)


def _profile_base_direction(cylinder: CylinderGeometry, pitch: float):
    tangent = cylinder.axis.crossProduct(cylinder.radial)
    tangent.scaleBy(2 * math.pi * cylinder.radius / pitch)
    tangent.add(cylinder.axis)
    if not tangent.normalize():
        raise RuntimeError(tr('tangent_missing'))

    base_direction = tangent.crossProduct(cylinder.radial)
    if not base_direction.normalize():
        raise RuntimeError(tr('profile_direction_missing'))
    return base_direction


def _create_thread_sweep(cylinder, profile, helix_edge, guide_face, bounded_external=False,
                         creation_occurrence=None):
    # Path.create resolves an assembly object path before the feature's owning
    # component is known. A native edge of the calibration subcomponent cannot
    # be resolved there; supply its occurrence proxy, as for the profile plane.
    path_edge = (helix_edge.createForAssemblyContext(creation_occurrence)
                 if creation_occurrence is not None else helix_edge)
    path = adsk.fusion.Path.create(
        path_edge, adsk.fusion.ChainedCurveOptions.noChainedCurves
    )
    if path is None:
        raise RuntimeError(tr('path_failed'))

    sweeps = cylinder.component.features.sweepFeatures
    operation = (
        adsk.fusion.FeatureOperations.CutFeatureOperation
        if cylinder.is_external and not bounded_external
        else adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    sweep_input = sweeps.createInput(
        profile, path, operation
    )
    # Die Zylinderfläche definiert den radialen Bezug des Profils über die
    # gesamte Helix. Ohne Führungsfläche kann Fusion den Profilrahmen entlang
    # des räumlichen Pfads verdrehen, sodass der Schnitt den Körper nur noch
    # abschnittsweise überlappt.
    sweep_input.guideSurfaces = [guide_face]
    sweep_input.isChainSelection = False
    if cylinder.is_external and not bounded_external:
        sweep_input.participantBodies = [cylinder.body]
    sweep = sweeps.add(sweep_input)
    if sweep is None:
        raise RuntimeError(tr('sweep_failed'))
    thread_type = tr('external_thread') if cylinder.is_external else tr('internal_thread')
    sweep.name = f'PrintThread Wizard – {thread_type}'
    return sweep


def _trim_and_combine_thread(
    cylinder, sweep, trim_start, trim_end
):
    if sweep.bodies.count == 0:
        raise RuntimeError(tr('internal_body_missing'))

    created_features = []
    try:
        thread_body = sweep.bodies.item(0)
        trim_feature, trim_body = _create_axial_trim_body(
            cylinder.component,
            trim_start,
            trim_end,
            cylinder.radius * 2,
        )
        created_features.append(trim_feature)

        trim_tools = adsk.core.ObjectCollection.create()
        trim_tools.add(trim_body)
        combines = cylinder.component.features.combineFeatures
        trim_input = combines.createInput(thread_body, trim_tools)
        trim_input.operation = adsk.fusion.FeatureOperations.IntersectFeatureOperation
        trim_input.isKeepToolBodies = False
        trim_feature_result = combines.add(trim_input)
        if trim_feature_result is None or trim_feature_result.bodies.count == 0:
            raise RuntimeError(tr('trim_failed'))
        trim_feature_result.name = "PrintThread Wizard – " + tr('trim_thread')
        created_features.append(trim_feature_result)
        tools = adsk.core.ObjectCollection.create()
        for index in range(trim_feature_result.bodies.count):
            tools.add(trim_feature_result.bodies.item(index))
        combine_input = combines.createInput(cylinder.body, tools)
        combine_input.operation = (
            adsk.fusion.FeatureOperations.CutFeatureOperation if cylinder.is_external
            else adsk.fusion.FeatureOperations.JoinFeatureOperation
        )
        combine_input.isKeepToolBodies = False
        combine = combines.add(combine_input)
        if combine is None:
            raise RuntimeError(tr('join_failed'))
        combine.name = "PrintThread Wizard – " + tr('external_thread' if cylinder.is_external else 'internal_thread')
        return combine
    except Exception:
        for feature in reversed(created_features):
            _delete_if_valid(feature)
        _delete_if_valid(sweep)
        raise


def _create_axial_trim_body(component, start_point, end_point, radius):
    temp_manager = adsk.fusion.TemporaryBRepManager.get()
    temporary_body = temp_manager.createCylinderOrCone(
        start_point, radius, end_point, radius
    )
    if temporary_body is None:
        raise RuntimeError(tr('trim_body_missing'))

    base_feature = component.features.baseFeatures.add()
    base_feature.name = "PrintThread Wizard – " + tr('axial_trim')
    base_feature.startEdit()
    try:
        component.bRepBodies.add(temporary_body, base_feature)
    finally:
        base_feature.finishEdit()
    if base_feature.bodies.count == 0:
        _delete_if_valid(base_feature)
        raise RuntimeError(tr('trim_add_failed'))
    return base_feature, base_feature.bodies.item(0)


def create_external_thread(parameters: ThreadParameters):
    """Kompatibilitätsalias; die Flächenart wird inzwischen automatisch erkannt."""
    return create_thread(parameters)


def _name_and_hide_helpers(helix_feature, profile_plane, profile_sketch):
    for index in range(helix_feature.bodies.count):
        body = helix_feature.bodies.item(index)
        body.isLightBulbOn = False
        body.isVisible = False
    profile_plane.isLightBulbOn = False
    profile_sketch.isLightBulbOn = False


def _group_timeline_entries(timeline, start_index):
    end_index = timeline.count - 1
    if end_index < start_index:
        return
    group = timeline.timelineGroups.add(start_index, end_index)
    if group is None:
        raise RuntimeError(
            tr('group_failed')
        )
    group.name = "PrintThread Wizard – " + tr('thread')
    group.isCollapsed = True


def _translated_point(point, direction, distance):
    result = point.copy()
    offset = direction.copy()
    offset.scaleBy(distance)
    result.translateBy(offset)
    return result


def _delete_if_valid(entity):
    try:
        if entity and entity.isValid:
            entity.deleteMe()
    except Exception:
        pass
