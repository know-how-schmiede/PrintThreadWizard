import math

import adsk.core
import adsk.fusion

from ..core.thread_parameters import ThreadParameters
from .chamfer import create_thread_end_chamfer
from .face_analysis import (
    CylinderGeometry,
    analyze_external_cylinder,
    find_updated_external_cylinder,
)


PROFILE_OVERLAP = 0.01  # 0,1 mm in Fusion-internen Zentimetern


def create_external_thread(parameters: ThreadParameters):
    errors = parameters.validation_errors()
    if errors:
        raise ValueError('\n'.join(errors))

    cylinder = analyze_external_cylinder(parameters.face)
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
            cylinder = find_updated_external_cylinder(cylinder, updated_body)

        helix_feature, helix_edge = _create_persistent_helix(cylinder, parameters.pitch)
        profile_plane = _create_profile_plane(cylinder.component, helix_edge)
        profile = _create_cut_profile(profile_plane, cylinder, parameters)
        profile_sketch = profile.parentSketch
        sweep = _create_cut_sweep(cylinder, profile, helix_edge)
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

    tangent = cylinder.axis.crossProduct(cylinder.radial)
    tangent.scaleBy(2 * math.pi * cylinder.radius / parameters.pitch)
    tangent.add(cylinder.axis)
    tangent.normalize()
    base_direction = tangent.crossProduct(cylinder.radial)
    if not base_direction.normalize():
        raise RuntimeError('Die Richtung des Gewindeprofils konnte nicht ermittelt werden.')

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


def _create_cut_sweep(cylinder, profile, helix_edge):
    path = adsk.fusion.Path.create(
        helix_edge, adsk.fusion.ChainedCurveOptions.noChainedCurves
    )
    if path is None:
        raise RuntimeError('Aus der Helix konnte kein Sweep-Pfad erzeugt werden.')

    sweeps = cylinder.component.features.sweepFeatures
    sweep_input = sweeps.createInput(
        profile, path, adsk.fusion.FeatureOperations.CutFeatureOperation
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
    sweep.name = 'PrintThread Wizard – Außengewinde'
    return sweep


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
