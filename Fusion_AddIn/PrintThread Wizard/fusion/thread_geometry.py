import math
from dataclasses import replace

import adsk.core
import adsk.fusion

from ..core.thread_parameters import ThreadParameters
from .chamfer import capture_chamfer_ends, create_revolved_chamfers
from .face_analysis import (
    CylinderGeometry,
    analyze_cylinder,
)


PROFILE_OVERLAP = 0.01  # 0,1 mm in Fusion-internen Zentimetern
HELIX_OVERRUN_TURNS = 1.0


def create_thread(parameters: ThreadParameters):
    errors = parameters.validation_errors()
    if errors:
        raise ValueError('\n'.join(errors))

    cylinder = analyze_cylinder(parameters.face)
    timeline = cylinder.component.parentDesign.timeline
    timeline_start = timeline.count
    parameter_sketch = _create_parameter_note_sketch(cylinder, parameters)
    tolerance_feature = None
    try:
        chamfer_ends = capture_chamfer_ends(cylinder, parameters.chamfer_edges)
        trim_reference = _trim_reference_from_selected_circles(cylinder, chamfer_ends)
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
            raise ValueError('Die Gewindetiefe muss kleiner als der Zylinderradius sein.')
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
            cylinder, parameters.pitch
        )
        profile_plane = _create_profile_plane(cylinder.component, helix_edge)
        profile = _create_cut_profile(profile_plane, cylinder, parameters)
        profile_sketch = profile.parentSketch
        sweep = _create_thread_sweep(cylinder, profile, helix_edge, guide_face)
        result_feature = (
            sweep
            if cylinder.is_external
            else _trim_and_join_internal_thread(
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
        )
        _name_and_hide_helpers(helix_feature, profile_plane, profile_sketch)
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
    thread_type = 'Außengewinde' if cylinder.is_external else 'Innengewinde'

    def length(value):
        return units.formatInternalValue(value, length_units, True)

    angle = units.formatInternalValue(parameters.flank_angle, 'deg', True)
    bore_value = '–' if cylinder.is_external else length(minor_value)
    text = (
        'PrintThread Wizard – Gewindeparameter\n'
        f'Gewindeart: {thread_type}\n'
        f'Nenndurchmesser: {length(cylinder.radius * 2)}\n'
        f'Gewindesteigung (P): {length(parameters.pitch)}\n'
        f'Profilwinkel (α): {angle}\n'
        f'Gewindetiefe (h): {length(parameters.thread_depth)}\n'
        f'Verrundungsradius (r): {length(parameters.fillet_radius)}\n'
        f'Toleranz: {length(parameters.tolerance)}\n'
        f'Außendurchmesser (d): {length(major_value)}\n'
        f'Teilkreisdurchmesser (d2): {length(pitch_value)}\n'
        f'Innendurchmesser (d1): {length(minor_value)}\n'
        f'Gewindebohrung (T): {bore_value}\n'
        f'Fasen-Kanten: {len(parameters.chamfer_edges)}'
    )
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = (
        f'PrintThread Wizard – Gewindeparameter – {thread_type} – '
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
        raise RuntimeError('Die Skizze mit den Gewindeparametern konnte nicht erstellt werden.')
    sketch.isLightBulbOn = False
    return sketch


def _apply_radial_tolerance(cylinder, trim_reference, radial_offset):
    if abs(radial_offset) <= 1e-12:
        return cylinder, None

    adjusted_radius = cylinder.radius + radial_offset
    if adjusted_radius <= 0:
        raise ValueError('Die Toleranz ist für diesen Zylinderdurchmesser zu groß.')

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
            raise RuntimeError('Der Toleranzring für das Außengewinde fehlt.')
    else:
        tool_body = temp_manager.createCylinderOrCone(
            trim_reference.axis_start,
            adjusted_radius,
            trim_reference.axis_end,
            adjusted_radius,
        )
        if tool_body is None:
            raise RuntimeError('Der Toleranzzylinder für das Innengewinde fehlt.')

    base_feature = cylinder.component.features.baseFeatures.add()
    base_feature.name = 'PrintThread Wizard – Toleranzwerkzeug'
    base_feature.startEdit()
    try:
        cylinder.component.bRepBodies.add(tool_body, base_feature)
    finally:
        base_feature.finishEdit()
    if base_feature.bodies.count == 0:
        _delete_if_valid(base_feature)
        raise RuntimeError('Das Toleranzwerkzeug konnte nicht übernommen werden.')

    tools = adsk.core.ObjectCollection.create()
    tools.add(base_feature.bodies.item(0))
    combines = cylinder.component.features.combineFeatures
    combine_input = combines.createInput(cylinder.body, tools)
    combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    combine_input.isKeepToolBodies = False
    tolerance_cut = combines.add(combine_input)
    if tolerance_cut is None or tolerance_cut.bodies.count == 0:
        _delete_if_valid(base_feature)
        raise RuntimeError('Die Toleranz konnte nicht auf die Zylinderfläche angewendet werden.')
    tolerance_cut.name = 'PrintThread Wizard – Zylindertoleranz'
    return replace(
        cylinder, body=tolerance_cut.bodies.item(0), radius=adjusted_radius
    ), tolerance_cut


def _create_persistent_helix(cylinder: CylinderGeometry, pitch: float):
    start_point = _translated_point(cylinder.axis_start, cylinder.radial, cylinder.radius)
    turns = cylinder.length / pitch
    if turns <= 0:
        raise ValueError('Aus Zylinderlänge und Steigung ergeben sich keine Windungen.')

    temp_manager = adsk.fusion.TemporaryBRepManager.get()
    temporary_wire = temp_manager.createHelixWire(
        cylinder.axis_start, cylinder.axis, start_point, pitch, turns, 0.0
    )
    if temporary_wire is None or temporary_wire.edges.count == 0:
        raise RuntimeError('Die exakte Helix konnte nicht erzeugt werden.')

    guide_solid = temp_manager.createCylinderOrCone(
        cylinder.axis_start,
        cylinder.radius,
        cylinder.axis_end,
        cylinder.radius,
    )
    if guide_solid is None:
        raise RuntimeError('Der verlängerte Führungszylinder konnte nicht erzeugt werden.')
    temporary_guide = None
    for index in range(guide_solid.faces.count):
        face = guide_solid.faces.item(index)
        if adsk.core.Cylinder.cast(face.geometry):
            temporary_guide = temp_manager.copy(face)
            break
    if temporary_guide is None:
        raise RuntimeError('Die verlängerte zylindrische Führungsfläche fehlt.')

    base_feature = cylinder.component.features.baseFeatures.add()
    base_feature.name = 'PrintThread Wizard – Helix'
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
            body.name = 'PrintThread Wizard – Helixpfad'
            helix_edge = body.edges.item(0)
        for face_index in range(body.faces.count):
            face = body.faces.item(face_index)
            if adsk.core.Cylinder.cast(face.geometry):
                body.name = 'PrintThread Wizard – Sweep-Führung'
                guide_face = face
                break
        body.isLightBulbOn = False
        body.isVisible = False

    if helix_edge is None or guide_face is None:
        _delete_if_valid(base_feature)
        raise RuntimeError('Helix oder Führungsfläche konnte nicht übernommen werden.')
    return base_feature, helix_edge, guide_face


def _create_profile_plane(component, helix_edge):
    plane_input = component.constructionPlanes.createInput()
    if not plane_input.setByDistanceOnPath(
        helix_edge, adsk.core.ValueInput.createByReal(0.0)
    ):
        raise RuntimeError('Die Profilebene konnte nicht definiert werden.')
    plane = component.constructionPlanes.add(plane_input)
    plane.name = 'PrintThread Wizard – Profilebene'
    return plane


def _create_cut_profile(plane, cylinder: CylinderGeometry, parameters: ThreadParameters):
    sketch = cylinder.component.sketches.add(plane)
    sketch.name = 'PrintThread Wizard – Schneidprofil'

    base_center = _translated_point(
        cylinder.axis_start, cylinder.radial, cylinder.radius + PROFILE_OVERLAP
    )
    apex = _translated_point(
        cylinder.axis_start,
        cylinder.radial,
        cylinder.radius - parameters.sharp_profile_depth,
    )

    base_direction = _profile_base_direction(cylinder, parameters.pitch)

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
            raise ValueError('Der Verrundungsradius kann am Gewindegrund nicht erzeugt werden.')

    if sketch.profiles.count != 1:
        raise RuntimeError('Das Schneidprofil ist nicht eindeutig geschlossen.')
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
        raise ValueError('Die ausgewählten Fasen-Kreise ergeben keine gültige Gewindelänge.')
    return replace(cylinder, axis_start=start, axis_end=end, length=length)


def _profile_base_direction(cylinder: CylinderGeometry, pitch: float):
    tangent = cylinder.axis.crossProduct(cylinder.radial)
    tangent.scaleBy(2 * math.pi * cylinder.radius / pitch)
    tangent.add(cylinder.axis)
    if not tangent.normalize():
        raise RuntimeError('Die Tangente der Helix konnte nicht ermittelt werden.')

    base_direction = tangent.crossProduct(cylinder.radial)
    if not base_direction.normalize():
        raise RuntimeError('Die Richtung des Gewindeprofils konnte nicht ermittelt werden.')
    return base_direction


def _create_thread_sweep(cylinder, profile, helix_edge, guide_face):
    path = adsk.fusion.Path.create(
        helix_edge, adsk.fusion.ChainedCurveOptions.noChainedCurves
    )
    if path is None:
        raise RuntimeError('Aus der Helix konnte kein Sweep-Pfad erzeugt werden.')

    sweeps = cylinder.component.features.sweepFeatures
    operation = (
        adsk.fusion.FeatureOperations.CutFeatureOperation
        if cylinder.is_external
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
    if cylinder.is_external:
        sweep_input.participantBodies = [cylinder.body]
    sweep = sweeps.add(sweep_input)
    if sweep is None:
        raise RuntimeError('Der Gewinde-Sweep konnte nicht erzeugt werden.')
    thread_type = 'Außengewinde' if cylinder.is_external else 'Innengewinde'
    sweep.name = f'PrintThread Wizard – {thread_type}'
    return sweep


def _trim_and_join_internal_thread(
    cylinder, sweep, trim_start, trim_end
):
    if sweep.bodies.count == 0:
        raise RuntimeError('Der Innengewinde-Sweep enthält keinen Körper.')

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
            raise RuntimeError('Der Innengewindekörper konnte nicht axial begrenzt werden.')
        trim_feature_result.name = 'PrintThread Wizard – Gewinde begrenzen'
        created_features.append(trim_feature_result)
        thread_body = trim_feature_result.bodies.item(0)

        tools = adsk.core.ObjectCollection.create()
        tools.add(thread_body)
        combine_input = combines.createInput(cylinder.body, tools)
        combine_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        combine_input.isKeepToolBodies = False
        combine = combines.add(combine_input)
        if combine is None:
            raise RuntimeError('Das beschnittene Innengewinde konnte nicht verbunden werden.')
        combine.name = 'PrintThread Wizard – Innengewinde'
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
        raise RuntimeError('Der Begrenzungskörper für das Innengewinde fehlt.')

    base_feature = component.features.baseFeatures.add()
    base_feature.name = 'PrintThread Wizard – axiale Begrenzung'
    base_feature.startEdit()
    try:
        component.bRepBodies.add(temporary_body, base_feature)
    finally:
        base_feature.finishEdit()
    if base_feature.bodies.count == 0:
        _delete_if_valid(base_feature)
        raise RuntimeError('Der Begrenzungskörper konnte nicht übernommen werden.')
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
            'Die erzeugten Features konnten nicht in der Konstruktionshistorie gruppiert werden.'
        )
    group.name = 'PrintThread Wizard – Gewinde'
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
