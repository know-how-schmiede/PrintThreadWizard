"""Engrave clearance into the safe solid part of a sample's top face."""
import adsk.core
import adsk.fusion
from ..core.calibration import clearance_label, rectangle_in_material
from ..localization import translate as tr


def engrave_clearance(component, occurrence, body, series, specimen):
    faces = []
    for index in range(body.faces.count):
        face = body.faces.item(index)
        plane = adsk.core.Plane.cast(face.geometry)
        if plane is None or abs(plane.origin.z - series.length) > 1e-6:
            continue
        ok, normal = face.evaluator.getNormalAtPoint(face.pointOnFace)
        if ok and normal.z > .999:
            faces.append(face)
    if not faces:
        raise ValueError(tr('cal_mark_failed'))
    face = max(faces, key=lambda item: item.area)
    sketch = component.sketches.add(face)
    sketch.name = specimen.label + ' - ' + tr('cal_engrave')
    center = sketch.modelToSketchSpace(adsk.core.Point3D.create(specimen.x, specimen.y, series.length))
    box, inner, outer = series.marking_rectangle(specimen.clearance, specimen.is_external)
    x0, y0, x1, y1 = box
    text_input = sketch.sketchTexts.createInput3(
        "'" + clearance_label(specimen.clearance) + "'", adsk.core.ValueInput.createByReal(series.text_height))
    text_input.fontName = 'Arial'
    if not text_input.setAsMultiLine(
            adsk.core.Point3D.create(center.x + x0, center.y + y0, 0),
            adsk.core.Point3D.create(center.x + x1, center.y + y1, 0),
            adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
            adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0):
        raise ValueError(tr('cal_mark_failed'))
    text = sketch.sketchTexts.add(text_input)
    if text is None:
        raise ValueError(tr('cal_mark_failed'))
    bounds = text.boundingBox
    actual = (bounds.minPoint.x - center.x, bounds.minPoint.y - center.y,
              bounds.maxPoint.x - center.x, bounds.maxPoint.y - center.y)
    if not rectangle_in_material(actual, inner, outer):
        raise ValueError(tr('cal_mark_invalid'))
    extrudes = component.features.extrudeFeatures
    cut = extrudes.createInput(text, adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut.creationOccurrence = occurrence
    distance = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(series.mark_depth))
    zero = sketch.sketchToModelSpace(adsk.core.Point3D.create(0, 0, 0))
    normal_point = sketch.sketchToModelSpace(adsk.core.Point3D.create(0, 0, 1))
    direction = (adsk.fusion.ExtentDirections.NegativeExtentDirection
                 if normal_point.z > zero.z else adsk.fusion.ExtentDirections.PositiveExtentDirection)
    if not cut.setOneSideExtent(distance, direction):
        raise ValueError(tr('cal_mark_failed'))
    cut.participantBodies = [body]
    feature = extrudes.add(cut)
    if feature is None or feature.bodies.count != 1:
        raise ValueError(tr('cal_mark_failed'))
    feature.name = specimen.label + ' - ' + tr('cal_engrave')
    sketch.isVisible = False
    return feature.bodies.item(0)
