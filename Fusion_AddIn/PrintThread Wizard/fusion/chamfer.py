from dataclasses import dataclass
import math

import adsk.core
import adsk.fusion


CHAMFER_CUT_OVERLAP = 0.01  # 0,1 mm in Fusion-internen Zentimetern


@dataclass(frozen=True)
class ChamferEnd:
    center: adsk.core.Point3D
    radius: float
    is_start: bool


def capture_chamfer_ends(cylinder, selected_edges):
    """Speichert Kreisgeometrie, bevor Gewindefeatures die Kanten verändern."""
    result = []
    for selected_edge in selected_edges:
        edge = adsk.fusion.BRepEdge.cast(selected_edge)
        if edge is None:
            raise ValueError('Eine ausgewählte Fasen-Kante ist ungültig.')
        native_edge = getattr(edge, 'nativeObject', None)
        if native_edge:
            edge = native_edge
        if edge.body != cylinder.body:
            raise ValueError('Alle Fasen-Kanten müssen zum ausgewählten Zylinderkörper gehören.')

        circle = adsk.core.Circle3D.cast(edge.geometry)
        if circle is None:
            raise ValueError('Für die Rotationsfase müssen kreisförmige Kanten ausgewählt werden.')
        position = cylinder.axis_start.vectorTo(circle.center).dotProduct(cylinder.axis)
        result.append(ChamferEnd(circle.center.copy(), circle.radius, position <= cylinder.length / 2))
    return tuple(result)


def create_revolved_chamfers(
    cylinder, target_body, chamfer_ends, distance, flank_angle
):
    """Schneidet die Fasen nach dem Gewinde als rotierte Dreiecksprofile."""
    if not chamfer_ends:
        return None

    component = cylinder.component
    helper_sketch = None
    plane = None
    sketch = None
    try:
        helper_sketch = component.sketches.add(component.xYConstructionPlane)
        helper_sketch.name = 'PrintThread Wizard – Fasenebene Hilfspunkte'
        helper_sketch.is3D = True
        points = helper_sketch.sketchPoints
        axis_start = points.add(cylinder.axis_start)
        axis_end = points.add(cylinder.axis_end)
        radial_point = points.add(
            _translated_point(cylinder.axis_start, cylinder.radial, 1.0)
        )

        plane_input = component.constructionPlanes.createInput()
        if not plane_input.setByThreePoints(axis_start, axis_end, radial_point):
            raise RuntimeError('Die Ebene für die Rotationsfase konnte nicht definiert werden.')
        plane = component.constructionPlanes.add(plane_input)
        plane.name = 'PrintThread Wizard – Fasenebene'

        sketch = component.sketches.add(plane)
        sketch.name = 'PrintThread Wizard – Fasenprofile'
        lines = sketch.sketchCurves.sketchLines
        axis_line = lines.addByTwoPoints(
            sketch.modelToSketchSpace(cylinder.axis_start),
            sketch.modelToSketchSpace(cylinder.axis_end),
        )
        axis_line.isConstruction = True

        # An beiden Gewindearten wird Material zwischen Nenndurchmesser und
        # Kerndurchmesser entfernt. Beim Außengewinde liegt die axiale Spitze
        # am Nenndurchmesser, beim Innengewinde am Kerndurchmesser. Andernfalls
        # wird beim Innengewinde die komplementäre Hälfte des Dreiecks entfernt.
        for chamfer_end in chamfer_ends:
            inward = cylinder.axis.copy()
            if not chamfer_end.is_start:
                inward.scaleBy(-1)
            # Der Fasenkörper reicht bei Innen- und Außengewinden geringfügig
            # über den Gewindegrund hinaus. So entstehen an der tangentialen
            # Berührung mit dem letzten Gewindegang keine Restflächen.
            cut_overlap = CHAMFER_CUT_OVERLAP
            axial_distance = distance * math.tan(flank_angle / 2) + cut_overlap
            corner = _translated_point(
                chamfer_end.center, cylinder.radial, chamfer_end.radius
            )
            radial_point = _translated_point(
                chamfer_end.center,
                cylinder.radial,
                chamfer_end.radius - distance - cut_overlap,
            )
            axial_point = (
                corner.copy()
                if cylinder.is_external
                else radial_point.copy()
            )
            axial_offset = inward.copy()
            axial_offset.scaleBy(axial_distance)
            axial_point.translateBy(axial_offset)

            corner_2d = sketch.modelToSketchSpace(corner)
            radial_2d = sketch.modelToSketchSpace(radial_point)
            axial_2d = sketch.modelToSketchSpace(axial_point)
            first = lines.addByTwoPoints(corner_2d, radial_2d)
            second = lines.addByTwoPoints(first.endSketchPoint, axial_2d)
            lines.addByTwoPoints(second.endSketchPoint, first.startSketchPoint)

        if sketch.profiles.count != len(chamfer_ends):
            raise RuntimeError('Die Dreiecksprofile der Rotationsfase sind nicht geschlossen.')

        profiles = adsk.core.ObjectCollection.create()
        for index in range(sketch.profiles.count):
            profiles.add(sketch.profiles.item(index))

        revolves = component.features.revolveFeatures
        revolve_input = revolves.createInput(
            profiles, axis_line, adsk.fusion.FeatureOperations.CutFeatureOperation
        )
        revolve_input.setAngleExtent(
            False, adsk.core.ValueInput.createByReal(2 * math.pi)
        )
        revolve_input.participantBodies = [target_body]
        revolve = revolves.add(revolve_input)
        if revolve is None:
            raise RuntimeError(
                'Die rotierte Fase konnte nicht vom Gewindekörper abgezogen werden.'
            )
        revolve.name = 'PrintThread Wizard – Gewindefasen'

        helper_sketch.isLightBulbOn = False
        plane.isLightBulbOn = False
        sketch.isLightBulbOn = False
        return revolve
    except Exception:
        _delete_if_valid(sketch)
        _delete_if_valid(plane)
        _delete_if_valid(helper_sketch)
        raise


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
