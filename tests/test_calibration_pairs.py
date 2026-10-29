"""0.9.7 pair layout, marking boundaries and engraving API checks."""
import ast
from dataclasses import replace
import importlib
import math
import types
import unittest
from unittest.mock import Mock
from test_localization import ADDIN

cal = importlib.import_module('printthread_test.core.calibration')


class CalibrationPairTests(unittest.TestCase):
    def test_generator_creates_two_members_per_gap_and_marks_both(self):
        records = importlib.import_module('printthread_test.core.thread_records')
        params = importlib.import_module('printthread_test.core.thread_parameters')
        tree = ast.parse((ADDIN / 'fusion/calibration.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_create_specimens')
        for engraved in (True, False):
            series = cal.CalibrationSeries(engrave=engraved)
            events = []
            def blank(component, series, specimen):
                events.append('blank')
                face = types.SimpleNamespace(geometry=types.SimpleNamespace(radius=series.diameter/2), external=specimen.is_external)
                return types.SimpleNamespace(faces=types.SimpleNamespace(count=1, item=lambda i:face)), types.SimpleNamespace(isVisible=True)
            def build(p, **kwargs):
                events.append('thread')
                body = types.SimpleNamespace(attributes=Mock(), name='')
                return types.SimpleNamespace(bodies=types.SimpleNamespace(count=1,item=lambda i:body))
            create = Mock(side_effect=build)
            mark = Mock(side_effect=lambda component,occurrence,body,series,specimen:body)
            ns = dict(_create_blank=blank, pair_record_contexts=records.pair_record_contexts,
                      analyze_cylinder=lambda face:types.SimpleNamespace(is_external=face.external),
                      create_thread=create, engrave_clearance=mark, ThreadParameters=params.ThreadParameters,
                      ISO_FLANK_ANGLE=math.pi/3, radial_thread_depth=lambda p, external:p*(.6134345 if external else .541266),
                      tr=lambda key:key, adsk=types.SimpleNamespace(core=types.SimpleNamespace(Cylinder=types.SimpleNamespace(cast=lambda g:g))))
            exec(compile(ast.Module(body=[handler],type_ignores=[]),'<series>', 'exec'),ns)
            ns['_create_specimens'](object(), object(), series)
            self.assertEqual(create.call_count, 10)
            self.assertEqual(mark.call_count, 10 if engraved else 0)
            self.assertEqual(events[:4], ['blank','blank','thread','thread'])
            for i in range(0, 10, 2):
                a, b = create.call_args_list[i:i+2]
                self.assertEqual(a.args[0].tolerance, b.args[0].tolerance)
                self.assertEqual(a.args[0].clearance_distribution, 'balanced')
                self.assertEqual(a.kwargs['record_context']['pair_id'], b.kwargs['record_context']['pair_id'])
                self.assertEqual(a.kwargs['record_context']['partner_id'], b.kwargs['record_context']['id'])

    def test_all_labels_distinct_and_pair_positions_do_not_overlap(self):
        series = cal.CalibrationSeries(clearances=(0, .01, .02))
        specimens = series.specimens()
        self.assertEqual(len(specimens), 6)
        self.assertEqual(cal.clearance_label(.015), '0.15')
        self.assertEqual(cal.clearance_label(0), '0.00')
        for index, first in enumerate(specimens):
            for second in specimens[index+1:]:
                self.assertGreater(math.hypot(first.x-second.x, first.y-second.y), series.diameter + 2*series.wall)
        for external in (True, False):
            labels = [cal.clearance_label(s.clearance) for s in specimens if s.is_external == external]
            self.assertEqual(len(labels), len(set(labels)))

    def test_marking_boxes_stay_outside_thread_surfaces(self):
        for distribution in ('balanced', 'internal', 'external'):
            series = cal.CalibrationSeries(clearance_distribution=distribution).validate()
            for sample in series.specimens():
                box, inner, outer = series.marking_rectangle(sample.clearance, sample.is_external)
                self.assertTrue(cal.rectangle_in_material(box, inner, outer))
                if sample.is_external:
                    self.assertEqual(inner, 0)
                    self.assertLess(outer, series.diameter / 2 - .12)
                else:
                    self.assertGreater(inner, series.diameter / 2)
                    self.assertLess(outer, series.diameter / 2 + series.wall)

    def test_invalid_marking_and_radius_limits_are_rejected(self):
        series = cal.CalibrationSeries()
        for changes in (dict(text_height=.8), dict(mark_depth=0), dict(mark_depth=.2),
                        dict(clearance_distribution='unknown'), dict(engrave='yes'),
                        dict(clearances=(.01, .01000000001))):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(series, **changes).validate()
        replace(series, engrave=False, text_height=.8).validate()
        # Full external correction may consume the thread core radius.
        with self.assertRaises(ValueError):
            replace(series, diameter=.4, pitch=.2, clearance_distribution='external',
                    clearances=(.1,), engrave=False).validate()

    def test_decimal_input_and_non_numeric_messages(self):
        self.assertEqual(cal.parse_clearances('0,10; 0.15; 0.20'), (.01, .015, .02))
        for value in ('', 'text', None):
            with self.assertRaises(ValueError):
                cal.parse_clearances(value)

    def test_engraving_cuts_only_target_body_and_checks_text_bounds(self):
        tree = ast.parse((ADDIN / 'fusion/calibration_marking.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'engrave_clearance')
        series = cal.CalibrationSeries()
        sample = series.specimens()[0]
        face = types.SimpleNamespace(geometry=types.SimpleNamespace(origin=types.SimpleNamespace(z=series.length)),
                   evaluator=types.SimpleNamespace(getNormalAtPoint=lambda p:(True,types.SimpleNamespace(z=1))),
                   pointOnFace=object(), area=5)
        body = types.SimpleNamespace(faces=types.SimpleNamespace(count=1, item=lambda i:face))
        text = types.SimpleNamespace(boundingBox=types.SimpleNamespace(
             minPoint=types.SimpleNamespace(x=-.2,y=-.06), maxPoint=types.SimpleNamespace(x=.2,y=.06)))
        sketch = Mock()
        sketch.modelToSketchSpace.return_value = types.SimpleNamespace(x=0,y=0)
        sketch.sketchTexts.add.return_value = text
        sketch.sketchToModelSpace.side_effect = lambda p:p
        component = Mock()
        component.sketches.add.return_value = sketch
        component.features.extrudeFeatures.add.return_value.bodies.count = 1
        def point(x,y,z): return types.SimpleNamespace(x=x,y=y,z=z)
        ns = dict(tr=lambda key:key, clearance_label=cal.clearance_label,
                  rectangle_in_material=cal.rectangle_in_material,
                  adsk=types.SimpleNamespace(core=types.SimpleNamespace(Plane=types.SimpleNamespace(cast=lambda p:p),
                     Point3D=types.SimpleNamespace(create=point), ValueInput=types.SimpleNamespace(createByReal=lambda v:v),
                     HorizontalAlignments=types.SimpleNamespace(CenterHorizontalAlignment=0),
                     VerticalAlignments=types.SimpleNamespace(MiddleVerticalAlignment=0)),
                     fusion=types.SimpleNamespace(FeatureOperations=types.SimpleNamespace(CutFeatureOperation='cut'),
                     DistanceExtentDefinition=types.SimpleNamespace(create=lambda v:v),
                     ExtentDirections=types.SimpleNamespace(NegativeExtentDirection='negative',PositiveExtentDirection='positive'))))
        exec(compile(ast.Module(body=[handler],type_ignores=[]),'<engraving>', 'exec'),ns)
        ns['engrave_clearance'](component, object(), body, series, sample)
        cut = component.features.extrudeFeatures.createInput.return_value
        self.assertEqual(cut.participantBodies, [body])
        cut.setOneSideExtent.assert_called_once_with(.03,'negative')
        component.features.extrudeFeatures.add.assert_called_once_with(cut)
        text.boundingBox.maxPoint.x = 5
        component.features.extrudeFeatures.add.reset_mock()
        with self.assertRaises(ValueError):
            ns['engrave_clearance'](component, object(), body, series, sample)
        component.features.extrudeFeatures.add.assert_not_called()
