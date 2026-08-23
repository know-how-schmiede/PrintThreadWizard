import math
from dataclasses import replace

import adsk.core
import adsk.fusion

from ..core.thread_parameters import ThreadParameters
from .chamfer import create_thread_end_chamfer
from .face_analysis import (
    CylinderGeometry,
    analyze_cylinder,
    find_updated_cylinder,
)


PROFILE_OVERLAP = 0.01  # 0,1 mm in Fusion-internen Zentimetern
END_CLEARANCE = 1e-5


def create_thread(parameters: ThreadParameters):
    errors = parameters.validation_errors()
    if errors:
        raise ValueError('\n'.join(errors))

    cylinder = analyze_cylinder(parameters.face)
    if parameters.sharp_profile_depth >= cylinder.radius:
        raise ValueError('Die Gewindetiefe muss kleiner als der Zylinderradius sein.')

    chamfer_feature = None
    helix_feature = None
    profile_plane = None
    profile_sketch = None
    try:
        chamfer_feature = create_thread_end_chamfer(
            cylinder.component,
            cylinder.body,
            parameters.chamfer_edges,
            parameters.thread_depth,
        )
        if chamfer_feature:
            updated_body = (
                chamfer_feature.bodies.item(0)
                if chamfer_feature.bodies.count
                else cylinder.body
            )
            cylinder = find_updated_cylinder(cylinder, updated_body)

        cylinder = _limit_internal_thread_to_end_faces(cylinder, parameters)
        helix_feature, helix_edge = _create_persistent_helix(cylinder, parameters.pitch)
        profile_plane = _create_profile_plane(cylinder.component, helix_edge)
        profile = _create_cut_profile(profile_plane, cylinder, parameters)
        profile_sketch = profile.parentSketch
        sweep = _create_thread_sweep(cylinder, profile, helix_edge)
        _name_and_hide_helpers(helix_feature, profile_plane, profile_sketch)
        return sweep
    except Exception:
        _delete_if_valid(profile_sketch)
        _delete_if_valid(profile_plane)
        _delete_if_valid(helix_feature)
        _delete_if_valid(chamfer_feature)
        raise


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

    base_feature = cylinder.component.features.baseFeatures.add()
    base_feature.name = 'PrintThread Wizard – Helix'
    base_feature.startEdit()
    try:
        cylinder.component.bRepBodies.add(temporary_wire, base_feature)
    finally:
        base_feature.finishEdit()

    if base_feature.bodies.count == 0 or base_feature.bodies.item(0).edges.count == 0:
        _delete_if_valid(base_feature)
        raise RuntimeError('Die Helix konnte nicht in das Modell übernommen werden.')
    return base_feature, base_feature.bodies.item(0).edges.item(0)


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


def _limit_internal_thread_to_end_faces(
    cylinder: CylinderGeometry, parameters: ThreadParameters
) -> CylinderGeometry:
    """Verkürzt den Join-Pfad um die axiale Ausdehnung des Profils."""
    if cylinder.is_external:
        return cylinder

    base_direction = _profile_base_direction(cylinder, parameters.pitch)
    effective_depth = parameters.sharp_profile_depth + PROFILE_OVERLAP
    half_width = effective_depth * math.tan(parameters.flank_angle / 2)
    axial_margin = abs(base_direction.dotProduct(cylinder.axis)) * half_width
    axial_margin += END_CLEARANCE
    if 2 * axial_margin >= cylinder.length:
        raise ValueError('Die Zylinderfläche ist für das Innengewindeprofil zu kurz.')

    return replace(
        cylinder,
        axis_start=_translated_point(cylinder.axis_start, cylinder.axis, axial_margin),
        axis_end=_translated_point(cylinder.axis_end, cylinder.axis, -axial_margin),
        length=cylinder.length - 2 * axial_margin,
    )


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


def _create_thread_sweep(cylinder, profile, helix_edge):
    path = adsk.fusion.Path.create(
        helix_edge, adsk.fusion.ChainedCurveOptions.noChainedCurves
    )
    if path is None:
        raise RuntimeError('Aus der Helix konnte kein Sweep-Pfad erzeugt werden.')

    sweeps = cylinder.component.features.sweepFeatures
    operation = (
        adsk.fusion.FeatureOperations.CutFeatureOperation
        if cylinder.is_external
        else adsk.fusion.FeatureOperations.JoinFeatureOperation
    )
    sweep_input = sweeps.createInput(
        profile, path, operation
    )
    # Die Zylinderfläche definiert den radialen Bezug des Profils über die
    # gesamte Helix. Ohne Führungsfläche kann Fusion den Profilrahmen entlang
    # des räumlichen Pfads verdrehen, sodass der Schnitt den Körper nur noch
    # abschnittsweise überlappt.
    sweep_input.guideSurfaces = [cylinder.face]
    sweep_input.isChainSelection = False
    sweep_input.participantBodies = [cylinder.body]
    sweep = sweeps.add(sweep_input)
    if sweep is None:
        raise RuntimeError('Der Gewinde-Sweep konnte nicht erzeugt werden.')
    thread_type = 'Außengewinde' if cylinder.is_external else 'Innengewinde'
    sweep.name = f'PrintThread Wizard – {thread_type}'
    return sweep


def create_external_thread(parameters: ThreadParameters):
    """Kompatibilitätsalias; die Flächenart wird inzwischen automatisch erkannt."""
    return create_thread(parameters)


def _name_and_hide_helpers(helix_feature, profile_plane, profile_sketch):
    for index in range(helix_feature.bodies.count):
        helix_feature.bodies.item(index).isVisible = False
    profile_plane.isLightBulbOn = False
    profile_sketch.isLightBulbOn = False


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
