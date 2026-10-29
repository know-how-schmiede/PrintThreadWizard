"""Generate an isolated calibration component inside the command transaction."""
from uuid import uuid4
import adsk.core
import adsk.fusion
from ..core.iso_metric import ISO_FLANK_ANGLE, radial_thread_depth
from ..core.thread_parameters import ThreadParameters
from ..core.thread_records import pair_record_contexts
from .calibration_marking import engrave_clearance
from .thread_geometry import create_thread
from .face_analysis import analyze_cylinder
from ..localization import translate as tr


def create_calibration(design, series):
    series.validate()
    occurrence = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    component = occurrence.component
    component.name = 'PrintThread Calibration ' + uuid4().hex[:8]
    try:
        _create_specimens(component, occurrence, series)
    except Exception:
        # This component belongs exclusively to this command. Remove it even
        # before Fusion completes the executeFailed transaction rollback.
        if occurrence.isValid:
            occurrence.deleteMe()
        raise
    return occurrence


def _create_specimens(component, occurrence, series):
    specimens = series.specimens()
    for row in range(0, len(specimens), 2):
        pair = specimens[row:row + 2]
        # Create both blanks before either thread, preserving separate bodies.
        blanks = [_create_blank(component, series, specimen) for specimen in pair]
        contexts = pair_record_contexts()
        bodies = []
        for specimen, (body, sketch), context in zip(pair, blanks, contexts):
            face = next(body.faces.item(i) for i in range(body.faces.count)
                        if adsk.core.Cylinder.cast(body.faces.item(i).geometry)
                        and abs(adsk.core.Cylinder.cast(body.faces.item(i).geometry).radius
                                - series.diameter / 2) < 1e-6)
            external = analyze_cylinder(face).is_external
            if external != specimen.is_external:
                raise ValueError(tr('cal_invalid'))
            result = create_thread(ThreadParameters(
                face, (), ISO_FLANK_ANGLE, radial_thread_depth(series.pitch, external),
                series.pitch, 0.0, tolerance=specimen.clearance, handedness=series.handedness,
                clearance_distribution=series.clearance_distribution), creation_occurrence=occurrence,
                calculation_mode='iso_metric', record_context=context)
            if result.bodies.count != 1:
                raise ValueError(tr('cal_invalid'))
            bodies.append(result.bodies.item(0))
            sketch.isVisible = False
        for specimen, body in zip(pair, bodies):
            if series.engrave:
                body = engrave_clearance(component, occurrence, body, series, specimen)
            body.name = specimen.label
            body.attributes.add('PrintThreadWizard', 'calibration', specimen.label)


def _create_blank(component, series, specimen):
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = specimen.label
    center = adsk.core.Point3D.create(specimen.x, specimen.y, 0)
    circles = sketch.sketchCurves.sketchCircles
    circles.addByCenterRadius(center, series.diameter / 2)
    if not specimen.is_external:
        circles.addByCenterRadius(center, series.diameter / 2 + series.wall)
    profile = next(sketch.profiles.item(i) for i in range(sketch.profiles.count)
                   if sketch.profiles.item(i).profileLoops.count == (1 if specimen.is_external else 2))
    feature = component.features.extrudeFeatures.addSimple(
        profile, adsk.core.ValueInput.createByReal(series.length),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    return feature.bodies.item(0), sketch
