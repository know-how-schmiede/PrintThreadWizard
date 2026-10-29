"""Handedness editing and the compact record-action dialog."""
import ast
import math
import types
import unittest
from unittest.mock import Mock
from test_localization import ADDIN
import test_thread_records

edits = test_thread_records.edits


class RecordDialogTests(unittest.TestCase):
    def fixture(self):
        sample = test_thread_records.ThreadRecordTests()
        sample.setUp()
        return sample

    def test_handedness_changes_preserve_other_parameters_and_validate_enum(self):
        p = self.fixture().p
        for old, new in (('left', 'right'), ('right', 'left')):
            from dataclasses import replace
            original = replace(p, handedness=old)
            changed = edits.apply_trial_changes(original, 'free', {'handedness': new}, True)
            self.assertEqual(changed.handedness, new)
            self.assertEqual(changed.pitch, original.pitch)
            self.assertEqual(changed.thread_depth, original.thread_depth)
            self.assertEqual(original.handedness, old)
        for invalid in ('RIGHT', '', None, True, 0):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                edits.validate_trial_changes({'handedness': invalid}, False)

    def test_action_helpers_scope_to_record_tab_and_map_one_action(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        names = ('_record_probe_enabled', '_record_rebuild_trial_enabled', '_record_apply_edit_enabled', '_record_view_only', '_record_pair_edit_enabled')
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        tab = types.SimpleNamespace(isActive=True)
        action = types.SimpleNamespace(selectedItem=types.SimpleNamespace(index=0))
        ns = dict(_input_by_id=lambda inputs, key: tab if key == 'records_tab' else action)
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<actions>', 'exec'), ns)
        for index in range(5):
            action.selectedItem.index = index
            self.assertTrue(ns['_record_probe_enabled'](None))
            self.assertEqual(ns['_record_view_only'](None), index == 0)
            self.assertEqual(ns['_record_rebuild_trial_enabled'](None), index == 2)
            self.assertEqual(ns['_record_apply_edit_enabled'](None), index == 3)
            self.assertEqual(ns['_record_pair_edit_enabled'](None), index == 4)
        tab.isActive = False
        self.assertFalse(ns['_record_probe_enabled'](None))

    def test_view_only_closes_without_loading_or_creating_thread(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_execute')
        handler.args.args[0].annotation = None
        ns = dict(thread_preview=Mock(), _record_probe_enabled=lambda _:True,
                  _record_view_only=lambda _:True)
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<view-only>', 'exec'), ns)
        ns['command_execute'](types.SimpleNamespace(command=types.SimpleNamespace(commandInputs=None)))

    def test_dialog_reads_direction_and_partial_values_without_modify_checkbox(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/records_tab.py').read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        ns = dict(validate_trial_changes=edits.validate_trial_changes)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), '<record-dialog>', 'exec'), ns)
        inspector = ns['RecordInspector']()
        sample = self.fixture()
        inspector.selected_record = lambda _: sample.record()
        controls = {key: types.SimpleNamespace(value=value) for key, value in
                    (('trial_pitch', .3), ('trial_tolerance', .04), ('trial_start_offset', .2), ('trial_thread_length', 1))}
        controls['record_action'] = types.SimpleNamespace(selectedItem=types.SimpleNamespace(index=2))
        controls['trial_handedness'] = types.SimpleNamespace(selectedItem=types.SimpleNamespace(index=0))
        changes = inspector.trial_changes(controls.__getitem__)
        self.assertEqual(changes, dict(pitch=.3, tolerance=.04, start_offset=.2, thread_length=1, handedness='right'))
        controls['record_action'].selectedItem.index = 4
        self.assertEqual(inspector.trial_changes(controls.__getitem__), dict(pitch=.3, tolerance=.04, handedness='right'))
