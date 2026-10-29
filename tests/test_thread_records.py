"""M6a metadata and read-only resolution boundaries; no simulated B-Rep."""
import copy
from dataclasses import replace
import importlib
import json
import math
import types
import unittest
from unittest.mock import Mock, patch
from test_localization import parameters

records = importlib.import_module('printthread_test.core.thread_records')
fusion_records = importlib.import_module('printthread_test.fusion.thread_records')
probe_module = importlib.import_module('printthread_test.fusion.thread_reference_probe')
trial_module = importlib.import_module('printthread_test.fusion.thread_rebuild_trial')
edits = importlib.import_module('printthread_test.core.thread_edits')


class ThreadRecordTests(unittest.TestCase):
    def test_changed_trial_preserves_saved_parameters_and_free_profile(self):
        original = self.p
        changed = edits.apply_trial_changes(original, 'free', {'pitch': .3, 'tolerance': .04}, True)
        self.assertEqual(original.pitch, .2)
        self.assertEqual(original.tolerance, .023)
        self.assertEqual(changed.pitch, .3)
        self.assertEqual(changed.tolerance, .04)
        self.assertEqual(changed.thread_depth, original.thread_depth)
        self.assertEqual(changed.handedness, original.handedness)

    def test_metric_pitch_change_recalculates_inside_and_outside_depth(self):
        outside = edits.apply_trial_changes(self.p, 'iso_metric', {'pitch': .3}, True)
        inside = edits.apply_trial_changes(self.p, 'iso_metric', {'pitch': .3}, False)
        self.assertAlmostEqual(outside.thread_depth, .18403035)
        self.assertAlmostEqual(inside.thread_depth, .1623798)
        self.assertEqual(outside.flank_angle, math.pi / 3)

    def test_length_trial_changes_keep_start_reference_and_validate_values(self):
        changed = edits.apply_trial_changes(self.p, 'free', {'start_offset': .3, 'thread_length': 1}, True)
        self.assertIs(changed.start_edge, self.p.start_edge)
        self.assertEqual(changed.axial_range(4), (.3, 1.3))
        with self.assertRaises(ValueError):
            edits.validate_trial_changes({'thread_length': 1}, True)
        for changes in ({'pitch': 0}, {'pitch': float('nan')}, {'tolerance': -1},
                        {'tolerance': True}, {'thread_length': float('inf')}, {'face': object()}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                edits.validate_trial_changes(changes, False)

    def test_modified_trial_values_reach_generator_without_changing_record(self):
        import sys
        design, group, events = self.probe_design()
        build = Mock()
        record = self.record()
        before = records.encode_record(record)
        classification = types.ModuleType('printthread_test.fusion.face_analysis')
        classification.analyze_cylinder = lambda _: types.SimpleNamespace(is_external=True)
        with patch.dict(sys.modules, {'printthread_test.fusion.face_analysis': classification}):
            trial_module.run_rebuild_trial(design, record, Mock(return_value=[]), build,
                              changes={'pitch': .3, 'tolerance': .04, 'thread_length': 1})
        p = build.call_args.args[0]
        self.assertEqual(p.pitch, .3)
        self.assertEqual(p.tolerance, .04)
        self.assertEqual(p.thread_length, 1)
        self.assertEqual(records.encode_record(record), before)
        self.assertFalse(build.call_args.kwargs['group_timeline'])

    def test_trial_rebuild_uses_original_settings_without_grouping_future_features(self):
        design, group, events = self.probe_design()
        build = Mock()
        trial_module.run_rebuild_trial(design, self.record(), Mock(return_value=[]), build)
        build.assert_called_once()
        self.assertEqual(build.call_args.args[0].pitch, .2)
        self.assertEqual(build.call_args.args[0].handedness, 'left')
        self.assertEqual(build.call_args.kwargs['calculation_mode'], 'iso_metric')
        self.assertFalse(build.call_args.kwargs['group_timeline'])
        self.assertTrue(group.isCollapsed)
        self.assertNotIn('restore-end', events)

    def test_trial_rebuild_propagates_failure_for_whole_command_rollback(self):
        design, group, events = self.probe_design()
        with self.assertRaisesRegex(RuntimeError, 'trial sweep failed'):
            trial_module.run_rebuild_trial(design, self.record(), Mock(return_value=[]),
                                           Mock(side_effect=RuntimeError('trial sweep failed')))
        self.assertTrue(group.isCollapsed)
        self.assertNotIn('restore-end', events)

    def test_trial_validation_failure_does_not_start_geometry(self):
        design, group, events = self.probe_design()
        build = Mock()
        with self.assertRaisesRegex(ValueError, 'invalid section'):
            trial_module.run_rebuild_trial(design, self.record(), Mock(return_value=['invalid section']), build)
        build.assert_not_called()

    def test_successful_trial_execute_always_requests_transaction_rollback(self):
        import ast
        from test_localization import ADDIN
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_execute')
        handler.args.args[0].annotation = None
        trial = Mock()
        ns = dict(thread_preview=Mock(), _record_probe_enabled=lambda _: True,
                  _record_rebuild_trial_enabled=lambda _: True,
                  record_inspector=types.SimpleNamespace(selected_record=lambda _: self.record(), trial_changes=lambda _: None),
                  run_rebuild_trial=trial, _validation_errors=Mock(), create_thread=Mock(),
                  app=types.SimpleNamespace(activeProduct='design'), futil=Mock(),
                  adsk=types.SimpleNamespace(fusion=types.SimpleNamespace(Design=types.SimpleNamespace(cast=lambda d: d))),
                  tr=lambda key: key)
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<trial-execute>', 'exec'), ns)
        args = types.SimpleNamespace(command=types.SimpleNamespace(commandInputs=None), executeFailed=False)
        ns['command_execute'](args)
        trial.assert_called_once()
        self.assertTrue(args.executeFailed)
        self.assertEqual(args.executeFailedMessage, 'trial_rolled_back')

    def test_unresolved_component_uses_unique_body_owner_in_probe(self):
        design, group, events = self.probe_design()
        lookup = design.findEntityByToken
        owner = types.SimpleNamespace(isValid=True)
        body = types.SimpleNamespace(isValid=True, nativeObject=None, parentComponent=owner)
        def resolve(token):
            if token == 'comp':
                return []
            if token == 'body':
                return [body]
            return lookup(token)
        design.findEntityByToken = resolve
        validator = Mock(return_value=[])
        result = probe_module.probe_original_references(design, self.record(), validator)
        self.assertTrue(result['ready'])
        validator.assert_called_once()
        self.assertEqual(design.timeline.markerPosition, 12)
        self.assertTrue(group.isCollapsed)

    def test_component_fallback_never_guesses_or_masks_ambiguity(self):
        root, child = object(), types.SimpleNamespace(isValid=True)
        body = types.SimpleNamespace(isValid=True, nativeObject=None, parentComponent=child)
        lookup = {'comp': [], 'body': [body]}
        design = types.SimpleNamespace(rootComponent=root, findEntityByToken=lambda token: lookup[token])
        self.assertEqual(fusion_records.resolve_reference(design, self.record(), 'component', 'comp'), [child])
        lookup['body'] = [body, body]
        self.assertEqual(fusion_records.resolve_reference(design, self.record(), 'component', 'comp'), [])
        lookup['comp'] = [child, child]
        lookup['body'] = [body]
        self.assertEqual(fusion_records.resolve_reference(design, self.record(), 'component', 'comp'), [child, child])

    def probe_design(self):
        timeline = types.SimpleNamespace(markerPosition=12, count=20)
        events = []
        def end():
            events.append('restore-end')
            timeline.markerPosition = 20
            return True
        timeline.moveToEnd = end
        group = types.SimpleNamespace(isCollapsed=True, parentGroup=None)
        def roll(before):
            self.assertFalse(group.isCollapsed)
            self.assertTrue(before)
            events.append('roll-before')
            timeline.markerPosition = 2
            return True
        feature = types.SimpleNamespace(isValid=True, timelineObject=types.SimpleNamespace(
                  parentGroup=group, rollTo=roll))
        entity = types.SimpleNamespace(isValid=True, nativeObject=None)
        def lookup(token):
            if token == 'first':
                return [feature]
            self.assertEqual(timeline.markerPosition, 2)
            return [entity]
        return types.SimpleNamespace(timeline=timeline, findEntityByToken=lookup), group, events

    def test_original_reference_probe_restores_marker_and_collapsed_group(self):
        design, group, events = self.probe_design()
        validator = Mock(return_value=[])
        result = probe_module.probe_original_references(design, self.record(), validator)
        self.assertTrue(result['ready'])
        self.assertTrue(group.isCollapsed)
        self.assertEqual(design.timeline.markerPosition, 12)
        self.assertEqual(events, ['roll-before', 'restore-end'])
        validator.assert_called_once()
        self.assertEqual(validator.call_args.args[0].start_offset, .2)

    def test_original_reference_probe_restores_after_validation_exception(self):
        design, group, events = self.probe_design()
        with self.assertRaisesRegex(RuntimeError, 'injected validation failure'):
            probe_module.probe_original_references(design, self.record(),
                              Mock(side_effect=RuntimeError('injected validation failure')))
        self.assertEqual(design.timeline.markerPosition, 12)
        self.assertTrue(group.isCollapsed)

    def test_probe_rejects_ambiguous_reference_without_using_first_match(self):
        design, group, events = self.probe_design()
        lookup = design.findEntityByToken
        design.findEntityByToken = lambda token: lookup(token) * (2 if token == 'face' else 1)
        validator = Mock()
        result = probe_module.probe_original_references(design, self.record(), validator)
        self.assertFalse(result['ready'])
        validator.assert_not_called()
        self.assertEqual(design.timeline.markerPosition, 12)
        self.assertTrue(group.isCollapsed)

    def test_probe_reports_failed_roll_and_still_restores(self):
        design, group, events = self.probe_design()
        feature = design.findEntityByToken('first')[0]
        feature.timelineObject.rollTo = lambda before: False
        with self.assertRaises(ValueError):
            probe_module.probe_original_references(design, self.record(), Mock())
        self.assertEqual(design.timeline.markerPosition, 12)
        self.assertTrue(group.isCollapsed)

    def test_probe_execute_does_not_create_threads(self):
        import ast
        import traceback
        from test_localization import ADDIN
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_execute')
        handler.args.args[0].annotation = None
        create = Mock()
        probe = Mock(return_value=dict(ready=True, references=[], errors=[]))
        ns = dict(_record_rebuild_trial_enabled=lambda _: False, thread_preview=Mock(), _record_probe_enabled=lambda _: True,
                  record_inspector=types.SimpleNamespace(selected_record=lambda _: self.record(), trial_changes=lambda _: None),
                  probe_original_references=probe, _validation_errors=Mock(), create_thread=create,
                  app=types.SimpleNamespace(activeProduct='design'), ui=Mock(),
                  adsk=types.SimpleNamespace(fusion=types.SimpleNamespace(Design=types.SimpleNamespace(cast=lambda d: d))),
                  tr=lambda key: key)
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<probe-execute>', 'exec'), ns)
        ns['command_execute'](types.SimpleNamespace(command=types.SimpleNamespace(commandInputs=None)))
        probe.assert_called_once()
        create.assert_not_called()
        ns['ui'].messageBox.assert_called_once()

    def setUp(self):
        self.p = parameters.ThreadParameters(object(), (), math.pi / 3, .06, .2, 0,
                     tolerance=.023, handedness='left', clearance_distribution='internal',
                     full_length=False, start_offset=.2, thread_length=1.5, start_edge=object())
        self.refs = dict(face='face', body='body', component='comp', occurrence='occ',
                         start_edge='edge', chamfer_edges=['chamfer'])

    def record(self):
        data = records.make_record(self.p, self.refs.copy(), 'iso_metric', '0.9.6')
        data['references'].update(first_feature='first', result_feature='last')
        return data

    def test_roundtrip_exact_parameters_without_live_entities(self):
        original = self.record()
        loaded = records.decode_record(records.encode_record(original))
        self.assertEqual(original, loaded)
        values = loaded['parameters']
        self.assertNotIn('face', values)
        self.assertNotIn('start_edge', values)
        self.assertNotIn('chamfer_edges', values)
        self.assertEqual(values['tolerance'], .023)
        self.assertEqual(values['start_offset'], .2)
        self.assertEqual(values['handedness'], 'left')
        self.assertEqual(values['clearance_distribution'], 'internal')
        self.assertEqual(loaded['calculation_mode'], 'iso_metric')
        rebuilt = parameters.ThreadParameters(object(), (), **values)
        self.assertEqual(rebuilt.axial_range(4), (.2, 1.7))

    def test_unknown_schema_and_bad_parameters_rejected_without_mutation(self):
        base = self.record()
        invalid = []
        for key, value in (('schema_version', 2), ('schema_version', True), ('calculation_mode', 'other')):
            bad = copy.deepcopy(base)
            bad[key] = value
            invalid.append(bad)
        for key, value in (('pitch', float('nan')), ('tolerance', True), ('thread_length', 0),
                           ('handedness', 'unknown')):
            bad = copy.deepcopy(base)
            bad['parameters'][key] = value
            invalid.append(bad)
        bad = copy.deepcopy(base)
        bad['references']['start_edge'] = None
        invalid.append(bad)
        for bad in invalid:
            snapshot = json.dumps(bad)
            with self.assertRaises(ValueError):
                records.decode_record(snapshot)
            self.assertEqual(json.dumps(bad), snapshot)

    def test_capture_before_topology_change_and_attach_document_attributes(self):
        body = types.SimpleNamespace(entityToken='body', parentComponent=types.SimpleNamespace(entityToken='comp'))
        face = types.SimpleNamespace(nativeObject=None, assemblyContext=None, entityToken='face', body=body)
        occurrence = types.SimpleNamespace(entityToken='calibration-occurrence')
        p = replace(self.p, face=face, start_edge=types.SimpleNamespace(entityToken='edge'), chamfer_edges=())
        record = fusion_records.capture_record(p, 'free', occurrence)
        face.entityToken = 'changed-after-cut'
        sketch = types.SimpleNamespace(entityToken='first', attributes=Mock())
        feature = types.SimpleNamespace(entityToken='last', attributes=Mock())
        fusion_records.attach_record(record, sketch, feature)
        saved = records.decode_record(sketch.attributes.add.call_args.args[2])
        self.assertEqual(saved['references']['face'], 'face')
        self.assertEqual(saved['references']['occurrence'], 'calibration-occurrence')
        feature.attributes.add.assert_called_once_with(records.GROUP, 'thread_id', saved['id'])

    def test_ambiguous_and_missing_references_do_not_select_first_entity(self):
        one = types.SimpleNamespace(isValid=True)
        lookup = {'comp': [one], 'body': [one], 'face': [one, one], 'occ': [],
                  'edge': [types.SimpleNamespace(isValid=False)], 'first': [one], 'last': [one], 'chamfer': []}
        design = types.SimpleNamespace(findEntityByToken=lambda token: lookup[token])
        result = fusion_records.inspect_references(design, self.record())
        states = {key: state for key, index, state in result}
        self.assertIn('ambiguous', states['face'])
        self.assertIn('unresolved', states['start_edge'])
        self.assertIn('uniquely', states['component'])

    def test_timeline_inspection_is_read_only_and_counts_later_entries(self):
        class Timeline:
            count = 15
            @property
            def markerPosition(self):
                return 15
            @markerPosition.setter
            def markerPosition(self, value):
                raise AssertionError('read-only inspector must not move history')
        first = types.SimpleNamespace(isValid=True, timelineObject=types.SimpleNamespace(index=2))
        last = types.SimpleNamespace(isValid=True, timelineObject=types.SimpleNamespace(index=10))
        design = types.SimpleNamespace(timeline=Timeline(),
                  findEntityByToken=lambda token: [first if token == 'first' else last])
        self.assertEqual(fusion_records.inspect_timeline(design, self.record()), dict(start=3, end=11, following=4))
        design.findEntityByToken = lambda token: []
        self.assertIsNone(fusion_records.inspect_timeline(design, self.record()))

    def test_corrupt_record_does_not_hide_other_records(self):
        good = types.SimpleNamespace(value=records.encode_record(self.record()), parent=types.SimpleNamespace(name='Good'))
        bad = types.SimpleNamespace(value='{"schema_version":99}', parent=types.SimpleNamespace(name='Unknown'))
        design = types.SimpleNamespace(findAttributes=lambda *args: [bad, good])
        results = fusion_records.list_records(design)
        self.assertEqual(len(results), 2)
        self.assertIsNotNone(results[0]['error'])
        self.assertIsNotNone(results[1]['record'])
