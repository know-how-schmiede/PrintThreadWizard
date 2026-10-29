"""Ownership and transaction boundaries for restricted M6 replacement."""
import ast
import importlib
import types
import unittest
from unittest.mock import Mock
from test_localization import ADDIN
import test_thread_records

module = importlib.import_module('printthread_test.fusion.thread_rebuild_trial')


class ThreadReplacementTests(unittest.TestCase):
    def test_edit_ok_validation_uses_record_without_new_face_selection(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_validate_input')
        handler.args.args[0].annotation = None
        design, record, features = self.fixture()
        status = types.SimpleNamespace(text='')
        ns = dict(_record_pair_edit_enabled=lambda _:False, pair_record_contexts=lambda: (None, None), _record_view_only=lambda _:False, active_command_inputs=None, _record_probe_enabled=lambda _: True,
                  _record_apply_edit_enabled=lambda _: True, _record_rebuild_trial_enabled=lambda _: False,
                  record_inspector=types.SimpleNamespace(selected_record=lambda _: record, trial_changes=lambda _: None),
                  _input_by_id=lambda *args: status, tr=lambda key: key)
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<edit-validation>', 'exec'), ns)
        args = types.SimpleNamespace(areInputsValid=False)
        ns['command_validate_input'](args)
        self.assertTrue(args.areInputsValid)
        del record['references']['owned_features']
        ns['command_validate_input'](args)
        self.assertFalse(args.areInputsValid)
        self.assertEqual(status.text, 'edit_ownership_missing')

    def test_grouping_stops_at_creation_marker_not_future_history(self):
        tree = ast.parse((ADDIN / 'fusion/thread_geometry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_group_timeline_entries')
        timeline = types.SimpleNamespace(count=100, markerPosition=8, timelineGroups=Mock())
        ns = dict(_record_pair_edit_enabled=lambda _:False, pair_record_contexts=lambda: (None, None), tr=lambda key: key)
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<group-range>', 'exec'), ns)
        ns['_group_timeline_entries'](timeline, 2)
        timeline.timelineGroups.add.assert_called_once_with(2, 7)

    def fixture(self):
        source = test_thread_records.ThreadRecordTests()
        source.setUp()
        record = source.record()
        record['references']['owned_features'] = ['first', 'middle', 'last']
        timeline = types.SimpleNamespace(count=5, markerPosition=5)
        group = types.SimpleNamespace(isCollapsed=True, parentGroup=None)
        def roll(before):
            timeline.markerPosition = 2
            return True
        features = {}
        for index, token in enumerate(('first', 'middle', 'last'), 2):
            features[token] = types.SimpleNamespace(isValid=True,
                timelineObject=types.SimpleNamespace(index=index, parentGroup=group, rollTo=roll),
                attributes=types.SimpleNamespace(itemByName=lambda *a: types.SimpleNamespace(value=record['id'])))
        entity = types.SimpleNamespace(isValid=True, nativeObject=None)
        design = types.SimpleNamespace(timeline=timeline,
                 findEntityByToken=lambda token: [features.get(token, entity)])
        def delete():
            timeline.count = timeline.markerPosition
            return True
        timeline.deleteAllAfterMarker = Mock(side_effect=delete)
        return design, record, features

    def test_exact_owned_suffix_can_be_replaced_and_new_build_is_grouped(self):
        design, record, features = self.fixture()
        build = Mock()
        module.run_rebuild_trial(design, record, Mock(return_value=[]), build, replace_original=True)
        design.timeline.deleteAllAfterMarker.assert_called_once()
        self.assertTrue(build.call_args.kwargs['group_timeline'])
        self.assertEqual(build.call_args.kwargs['record_context']['id'], record['id'])
        self.assertEqual(build.call_args.args[0].pitch, .2)

    def test_later_or_inserted_foreign_features_block_deletion(self):
        for kind in ('later', 'inserted'):
            design, record, features = self.fixture()
            design.timeline.count = 6
            design.timeline.markerPosition = 6
            if kind == 'inserted':
                features['last'].timelineObject.index = 5
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                module.run_rebuild_trial(design, record, Mock(return_value=[]), Mock(), replace_original=True)
            design.timeline.deleteAllAfterMarker.assert_not_called()

    def test_legacy_record_or_wrong_owner_blocks_deletion(self):
        for kind in ('legacy', 'wrong-owner'):
            design, record, features = self.fixture()
            if kind == 'legacy':
                del record['references']['owned_features']
            else:
                features['middle'].attributes.itemByName = lambda *a: types.SimpleNamespace(value='foreign')
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                module.run_rebuild_trial(design, record, Mock(return_value=[]), Mock(), replace_original=True)
            design.timeline.deleteAllAfterMarker.assert_not_called()

    def test_invalid_changes_block_deletion_and_build_failure_propagates(self):
        design, record, features = self.fixture()
        with self.assertRaisesRegex(ValueError, 'invalid parameters'):
            module.run_rebuild_trial(design, record, Mock(return_value=['invalid parameters']), Mock(), replace_original=True)
        design.timeline.deleteAllAfterMarker.assert_not_called()
        design, record, features = self.fixture()
        with self.assertRaisesRegex(RuntimeError, 'failed after removal'):
            module.run_rebuild_trial(design, record, Mock(return_value=[]),
                      Mock(side_effect=RuntimeError('failed after removal')), replace_original=True)

    def test_replace_execute_commits_success_and_requests_rollback_on_failure(self):
        import traceback
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_execute')
        handler.args.args[0].annotation = None
        build = Mock()
        ns = dict(_record_pair_edit_enabled=lambda _:False, pair_record_contexts=lambda: (None, None), _record_view_only=lambda _:False, thread_preview=Mock(), _record_probe_enabled=lambda _: True,
                  _record_apply_edit_enabled=lambda _: True,
                  record_inspector=types.SimpleNamespace(selected_record=lambda _: self.fixture()[1], trial_changes=lambda _: None),
                  _validation_errors=Mock(), create_thread=Mock(), run_rebuild_trial=build,
                  app=types.SimpleNamespace(activeProduct='design'), ui=Mock(), futil=Mock(),
                  tr=lambda key: key, traceback=traceback, CMD_NAME='test',
                  adsk=types.SimpleNamespace(fusion=types.SimpleNamespace(Design=types.SimpleNamespace(cast=lambda d:d)),
                       core=types.SimpleNamespace(LogLevels=types.SimpleNamespace(ErrorLogLevel=1))))
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<edit-execute>', 'exec'), ns)
        args = types.SimpleNamespace(command=types.SimpleNamespace(commandInputs=None), executeFailed=False)
        ns['command_execute'](args)
        self.assertFalse(args.executeFailed)
        self.assertTrue(build.call_args.kwargs['replace_original'])
        build.side_effect = RuntimeError('rebuild failed')
        ns['command_execute'](args)
        self.assertTrue(args.executeFailed)
        self.assertEqual(args.executeFailedMessage, 'rebuild failed')
