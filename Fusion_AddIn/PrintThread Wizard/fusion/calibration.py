"""Generate an isolated calibration component inside the command transaction."""
from uuid import uuid4
import adsk.core
import adsk.fusion
from ..core.iso_metric import ISO_FLANK_ANGLE, radial_thread_depth
from ..core.thread_parameters import ThreadParameters
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
    for index, (label, gap, x) in enumerate(series.specimens()):
        sketch = component.sketches.add(component.xYConstructionPlane)
        sketch.name = label
        center = adsk.core.Point3D.create(x, 0, 0)
        circles = sketch.sketchCurves.sketchCircles
        circles.addByCenterRadius(center, series.diameter / 2)
        if index:
            circles.addByCenterRadius(center, series.diameter / 2 + series.wall)
        profile = next(sketch.profiles.item(i) for i in range(sketch.profiles.count)
                       if sketch.profiles.item(i).profileLoops.count == (2 if index else 1))
        feature = component.features.extrudeFeatures.addSimple(
            profile, adsk.core.ValueInput.createByReal(series.length),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        body = feature.bodies.item(0)
        face = next(body.faces.item(i) for i in range(body.faces.count)
                    if adsk.core.Cylinder.cast(body.faces.item(i).geometry)
                    and abs(adsk.core.Cylinder.cast(body.faces.item(i).geometry).radius
                            - series.diameter / 2) < 1e-6)
        external = analyze_cylinder(face).is_external
        if external != (index == 0):
            raise ValueError(tr('cal_invalid'))
        result = create_thread(ThreadParameters(
            face, (), ISO_FLANK_ANGLE, radial_thread_depth(series.pitch, external),
            series.pitch, 0.0, tolerance=gap, handedness=series.handedness,
            clearance_distribution='internal'), creation_occurrence=occurrence,
            calculation_mode='iso_metric')
        for i in range(result.bodies.count):
            result_body = result.bodies.item(i)
            result_body.name = label
            result_body.attributes.add('PrintThreadWizard', 'calibration', label)
        sketch.isVisible = False
