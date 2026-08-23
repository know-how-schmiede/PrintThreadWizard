from dataclasses import dataclass

import adsk.core
import adsk.fusion


@dataclass(frozen=True)
class CylinderGeometry:
    face: adsk.fusion.BRepFace
    body: adsk.fusion.BRepBody
    component: adsk.fusion.Component
    axis_start: adsk.core.Point3D
    axis_end: adsk.core.Point3D
    axis: adsk.core.Vector3D
    radial: adsk.core.Vector3D
    radius: float
    length: float


def analyze_external_cylinder(selected_face) -> CylinderGeometry:
    face = adsk.fusion.BRepFace.cast(selected_face)
    if face is None:
        raise ValueError('Die Auswahl ist keine Fläche.')

    native_face = getattr(face, 'nativeObject', None)
    if native_face:
        face = native_face

    cylinder = adsk.core.Cylinder.cast(face.geometry)
    if cylinder is None:
        raise ValueError('Die ausgewählte Fläche ist keine Zylinderfläche.')

    body = face.body
    component = body.parentComponent if body else None
    if body is None or component is None:
        raise ValueError('Der Körper der Zylinderfläche konnte nicht ermittelt werden.')

    axis = cylinder.axis.copy()
    if not axis.normalize():
        raise ValueError('Die Zylinderachse ist ungültig.')

    radial = _radial_direction(face, cylinder.origin, axis)
    if radial is None:
        raise ValueError('Die radiale Richtung konnte nicht ermittelt werden.')

    normal_result = face.evaluator.getNormalAtPoint(face.pointOnFace)
    if not normal_result or not normal_result[0]:
        raise ValueError('Die Flächennormale konnte nicht ermittelt werden.')
    normal = normal_result[1]
    normal.normalize()
    if normal.dotProduct(radial) < 0:
        raise ValueError('Es muss eine äußere Zylinderfläche ausgewählt werden.')

    extent = _axis_extent(face, cylinder.origin, axis)
    if extent is None or extent[1] - extent[0] <= 1e-7:
        raise ValueError('Die Länge der Zylinderfläche konnte nicht ermittelt werden.')

    axis_start = _translated_point(cylinder.origin, axis, extent[0])
    axis_end = _translated_point(cylinder.origin, axis, extent[1])
    return CylinderGeometry(
        face=face,
        body=body,
        component=component,
        axis_start=axis_start,
        axis_end=axis_end,
        axis=axis,
        radial=radial,
        radius=cylinder.radius,
        length=extent[1] - extent[0],
    )


def _radial_direction(face, origin, axis):
    point = face.pointOnFace
    along_axis = origin.vectorTo(point).dotProduct(axis)
    axis_point = _translated_point(origin, axis, along_axis)
    radial = axis_point.vectorTo(point)
    return radial if radial.normalize() else None


def _axis_extent(face, origin, axis):
    values = []
    edges = face.edges
    for index in range(edges.count):
        center = getattr(edges.item(index).geometry, 'center', None)
        if center:
            values.append(origin.vectorTo(center).dotProduct(axis))

    if len(values) < 2:
        box = face.boundingBox
        for x in (box.minPoint.x, box.maxPoint.x):
            for y in (box.minPoint.y, box.maxPoint.y):
                for z in (box.minPoint.z, box.maxPoint.z):
                    point = adsk.core.Point3D.create(x, y, z)
                    values.append(origin.vectorTo(point).dotProduct(axis))

    return (min(values), max(values)) if values else None


def _translated_point(point, direction, distance):
    result = point.copy()
    offset = direction.copy()
    offset.scaleBy(distance)
    result.translateBy(offset)
    return result
