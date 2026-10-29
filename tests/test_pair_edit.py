"""Linked-pair identity and transaction boundaries without B-Rep simulation."""
import copy
import importlib
import types
import unittest
from unittest.mock import Mock
import test_thread_records

core = test_thread_records.records
module = importlib.import_module('printthread_test.fusion.thread_pair_edit')


class PairEditTests(unittest.TestCase):
    def test_pair_execute_requests_whole_rollback_after_second_failure(self):
        import ast
        import traceback
        from test_localization import ADDIN
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_execute')
        handler.args.args[0].annotation = None
        run = Mock(side_effect=RuntimeError('second partner failed'))
        ns = dict(thread_preview=Mock(), _record_probe_enabled=lambda _:True,
                  _record_view_only=lambda _:False, _record_pair_edit_enabled=lambda _:True,
                  record_inspector=types.SimpleNamespace(selected_record=lambda _:self.fixture()[1][0], trial_changes=lambda _:None),
                  replace_linked_pair=run, _validation_errors=Mock(), create_thread=Mock(),
                  analyze_cylinder=Mock(), validate_pair=Mock(), futil=Mock(), ui=Mock(),
                  app=types.SimpleNamespace(activeProduct='design'), traceback=traceback, CMD_NAME='test',
                  adsk=types.SimpleNamespace(fusion=types.SimpleNamespace(Design=types.SimpleNamespace(cast=lambda d:d)),
                       core=types.SimpleNamespace(LogLevels=types.SimpleNamespace(ErrorLogLevel=1))))
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<pair-execute>', 'exec'), ns)
        args = types.SimpleNamespace(command=types.SimpleNamespace(commandInputs=None), executeFailed=False)
        ns['command_execute'](args)
        self.assertTrue(args.executeFailed)
        self.assertEqual(args.executeFailedMessage, 'second partner failed')

    def fixture(self):
        sample = test_thread_records.ThreadRecordTests()
        sample.setUp()
        contexts = core.pair_record_contexts()
        records, entities, attributes = [], {}, []
        timeline = types.SimpleNamespace(count=8, markerPosition=8)
        class Group:
            parentGroup = None
            isCollapsed = True
        for n, context in enumerate(contexts):
            record = copy.deepcopy(sample.record())
            record.update(context)
            record['references'] = {key: f'{key}{n}' for key in ('face', 'body', 'component', 'first_feature', 'result_feature')}
            record['references'].update(occurrence=None, start_edge=f'edge{n}', chamfer_edges=[],
                owned_features=[f'first_feature{n}', f'middle{n}', f'result_feature{n}'])
            records.append(record)
            group = Group()
            for index, token in enumerate(record['references']['owned_features'], 2 + 3*n):
                def roll(before, index=index):
                    timeline.markerPosition = index
                    return True
                owner = types.SimpleNamespace(value=record['id'])
                entities[token] = types.SimpleNamespace(isValid=True, timelineObject=types.SimpleNamespace(
                    index=index, parentGroup=group, rollTo=roll),
                    attributes=types.SimpleNamespace(itemByName=lambda *a, owner=owner: owner))
            for key in ('face', 'body', 'component', 'start_edge'):
                token = record['references'][key]
                entities[token] = types.SimpleNamespace(isValid=True, nativeObject=None, label=token)
            attributes.append(types.SimpleNamespace(value=core.encode_record(record), parent=types.SimpleNamespace(name=f'P{n}')))
        def delete():
            timeline.count = timeline.markerPosition
            return True
        def end():
            timeline.markerPosition = timeline.count
            return True
        timeline.deleteAllAfterMarker = Mock(side_effect=delete)
        timeline.moveToEnd = end
        design = types.SimpleNamespace(timeline=timeline, findAttributes=lambda *a: attributes,
                     findEntityByToken=lambda token: [entities[token]] if token in entities else [])
        classify = lambda face: types.SimpleNamespace(is_external=face.label == 'face0', radius=1)
        return design, records, classify, attributes

    def test_pair_contexts_survive_serialization_and_link_both_directions(self):
        design, records, classify, attributes = self.fixture()
        for selected in records:
            pair = module.linked_pair(design, core.decode_record(core.encode_record(selected)))
            self.assertEqual(len(pair), 2)
            self.assertEqual(pair[0]['id'], pair[1]['partner_id'])
            self.assertEqual(pair[0]['pair_id'], pair[1]['pair_id'])

    def test_pair_rebuilds_both_with_shared_changes_and_stable_identity(self):
        design, records, classify, attributes = self.fixture()
        build = Mock()
        validate_pair = Mock()
        module.replace_linked_pair(design, records[1], dict(pitch=.3, tolerance=.04, handedness='right'),
                                   Mock(return_value=[]), build, classify, validate_pair)
        design.timeline.deleteAllAfterMarker.assert_called_once()
        self.assertEqual(build.call_count, 2)
        validate_pair.assert_called_once()
        for call, record in zip(build.call_args_list, records):
            self.assertEqual(call.args[0].handedness, 'right')
            self.assertEqual(call.args[0].pitch, .3)
            self.assertEqual(call.args[0].thread_length, record['parameters']['thread_length'])
            self.assertEqual(call.kwargs['record_context'], core.record_context(record))
        self.assertAlmostEqual(build.call_args_list[0].args[0].thread_depth, .18403035)
        self.assertAlmostEqual(build.call_args_list[1].args[0].thread_depth, .1623798)

    def test_second_failure_propagates_for_atomic_command_rollback(self):
        design, records, classify, attributes = self.fixture()
        build = Mock(side_effect=[object(), RuntimeError('second thread failed')])
        with self.assertRaisesRegex(RuntimeError, 'second thread failed'):
            module.replace_linked_pair(design, records[0], None, Mock(return_value=[]), build, classify, Mock())
        self.assertEqual(build.call_count, 2)

    def test_foreign_suffix_blocks_removal_and_restores_marker(self):
        design, records, classify, attributes = self.fixture()
        design.timeline.count = 9
        design.timeline.markerPosition = 9
        with self.assertRaises(ValueError):
            module.replace_linked_pair(design, records[0], None, Mock(return_value=[]), Mock(), classify, Mock())
        design.timeline.deleteAllAfterMarker.assert_not_called()
        self.assertEqual(design.timeline.markerPosition, 9)

    def test_legacy_or_broken_link_is_not_inferred(self):
        design, records, classify, attributes = self.fixture()
        for key in ('pair_id', 'partner_id'):
            bad = copy.deepcopy(records[0])
            del bad[key]
            with self.assertRaises(ValueError):
                module.linked_pair(design, bad)
        attributes.pop()
        with self.assertRaises(ValueError):
            module.linked_pair(design, records[0])
        design.timeline.deleteAllAfterMarker.assert_not_called()

    def test_invalid_shared_length_or_pair_geometry_blocks_removal(self):
        for changes, validator in (({'thread_length': 1}, Mock()),
                                   (None, Mock(side_effect=ValueError('pair invalid')))):
            design, records, classify, attributes = self.fixture()
            with self.assertRaises(ValueError):
                module.replace_linked_pair(design, records[0], changes, Mock(return_value=[]), Mock(), classify, validator)
            design.timeline.deleteAllAfterMarker.assert_not_called()
