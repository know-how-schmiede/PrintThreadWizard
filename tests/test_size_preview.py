"""M5 size data, schematic geometry and disposable graphics regressions."""
import ast
from dataclasses import replace
import importlib
import math
import types
import unittest
from unittest.mock import Mock
from test_localization import ADDIN, parameters

sizes = importlib.import_module('printthread_test.core.thread_sizes')
geometry = importlib.import_module('printthread_test.core.thread_preview')


class SizePreviewTests(unittest.TestCase):
    def test_input_updates_do_not_create_graphics_and_preview_does_not_replace_execute(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        update = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_update_assistance')
        preview = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_execute_preview')
        preview.args.args[0].annotation = None
        status = Mock()
        ns = dict(_input_by_id=Mock(), size_preview=types.SimpleNamespace(update_size_status=status))
        exec(compile(ast.Module(body=[update], type_ignores=[]), '<input-update>', 'exec'), ns)
        # Only UI text may be updated before the executePreview transaction.
        # No model/graphics globals exist in this namespace.
        ns['_update_assistance'](object())
        status.assert_called_once()
        draw = Mock()
        ns['_update_assistance'] = draw
        exec(compile(ast.Module(body=[preview], type_ignores=[]), '<execute-preview>', 'exec'), ns)
        inputs = object()
        args = types.SimpleNamespace(command=types.SimpleNamespace(commandInputs=inputs), isValidResult=True)
        ns['command_execute_preview'](args)
        draw.assert_called_once_with(inputs, draw_preview=True)
        self.assertFalse(args.isValidResult)
        created = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_created')
        self.assertTrue(any(isinstance(n, ast.Attribute) and n.attr == 'executePreview' for n in ast.walk(created)))

    def setUp(self):
        self.p = parameters.ThreadParameters(object(), (), math.pi / 3, .06, .2, 0)

    def test_verified_metric_examples_and_mm_conversion(self):
        options = sizes.size_options()
        for value in ((.6, .1, 'coarse'), (.8, .125, 'coarse'),
                      (.8, .1, 'fine'), (1.2, .175, 'coarse'),
                      (1.2, .125, 'fine'), (2.4, .2, 'fine')):
            self.assertIn(value, options)
        self.assertEqual(len(options), len(set(options)))
        self.assertNotIn((.6, .125, 'fine'), options)
        self.assertTrue(sizes.diameter_matches(.8, .8))
        self.assertTrue(sizes.diameter_matches(.801, .8))
        self.assertFalse(sizes.diameter_matches(.802, .8))
        for value in (0, -1, float('nan'), float('inf')):
            self.assertFalse(sizes.diameter_matches(value, .8))

    def test_preview_extent_profile_and_mirrored_direction(self):
        def lines(p):
            return geometry.preview_lines((0, 0, 2), (0, 0, 4), (1, 0, 0), 1, p)
        extent, right, profile = lines(self.p)
        left = lines(replace(self.p, handedness='left'))[1]
        self.assertEqual(extent[0], ((0, 0, 2), (0, 0, 4)))
        for segment in extent:
            for point in segment:
                self.assertGreaterEqual(point[2], 2)
                self.assertLessEqual(point[2], 4)
        # The quarter-turn sample is mirrored around the axial/radial plane.
        r, l = right[15][1], left[15][1]
        self.assertAlmostEqual(r[0], l[0])
        self.assertAlmostEqual(r[1], -l[1])
        self.assertAlmostEqual(r[2], 2.05)
        self.assertAlmostEqual(l[2], 2.05)
        self.assertAlmostEqual(profile[0][1][0], .94)
        self.assertEqual(len(profile), 3)

    def test_preview_cost_bounded_and_short_sections(self):
        for length in (.01, 1, 1000):
            sets = geometry.preview_lines((3, 4, 0), (3, 4, length), (1, 0, 0), 1, self.p)
            self.assertLessEqual(sum(map(len, sets)), 170)
            self.assertEqual(len(sets[1]), 66)
        self.assertEqual(geometry.preview_lines((0, 0, 0), (0, 0, .01), (1, 0, 0), 1, self.p)[2], [])

    def test_size_apply_changes_only_pitch_and_calculation_mode(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_input_changed')
        handler.args.args[0].annotation = None
        fields = {'pitch': types.SimpleNamespace(value=.2), 'calculation_mode': object()}
        select = Mock()
        ns = dict(loading_preset=False, active_command_inputs=object(),
                  size_preview=types.SimpleNamespace(selected_size=lambda _: (.8, .1, 'fine')),
                  _input_by_id=lambda inputs, key: fields[key], _select_dropdown_item=select,
                  ISO_MODE_NAME='ISO', _apply_calculation_mode=Mock(), _update_result_text=Mock())
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<size-apply>', 'exec'), ns)
        ns['command_input_changed'](types.SimpleNamespace(input=types.SimpleNamespace(id='apply_metric_size', value=True)))
        self.assertEqual(fields['pitch'].value, .1)
        select.assert_called_once_with(fields['calculation_mode'], 'ISO')
        self.assertFalse(ns['loading_preset'])

    def test_diameter_warning_includes_second_partner_without_resizing(self):
        from test_localization import loc
        tree = ast.parse((ADDIN / 'commands/commandDialog/size_preview.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'update_size_status')
        def field(radius):
            return types.SimpleNamespace(selectionCount=1,
                   selection=lambda i: types.SimpleNamespace(entity=types.SimpleNamespace(radius=radius)))
        fields = {'pair_mode': types.SimpleNamespace(value=True), 'target_face': field(.4),
                  'partner_face': field(.5), 'pitch': types.SimpleNamespace(value=.1),
                  'size_status': types.SimpleNamespace(text='')}
        ns = dict(selected_size=lambda _: (.8, .1, 'fine'), diameter_matches=sizes.diameter_matches,
                  analyze_cylinder=lambda face: face, tr=loc.translator('en'))
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<size-warning>', 'exec'), ns)
        ns['update_size_status'](fields.__getitem__)
        self.assertIn('10 mm differs from M8', fields['size_status'].text)
        self.assertEqual(fields['partner_face'].selection(0).entity.radius, .5)

    def test_dialog_destruction_removes_preview(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_destroy')
        handler.args.args[0].annotation = None
        preview = Mock()
        ns = dict(thread_preview=preview)
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<destroy>', 'exec'), ns)
        ns['command_destroy'](None)
        preview.clear.assert_called_once()

    def test_diameter_warning_includes_second_partner_without_resizing(self):
        from test_localization import loc
        tree = ast.parse((ADDIN / 'commands/commandDialog/size_preview.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'update_size_status')
        def field(radius):
            return types.SimpleNamespace(selectionCount=1,
                   selection=lambda i: types.SimpleNamespace(entity=types.SimpleNamespace(radius=radius)))
        fields = {'pair_mode': types.SimpleNamespace(value=True), 'target_face': field(.4),
                  'partner_face': field(.5), 'pitch': types.SimpleNamespace(value=.1),
                  'size_status': types.SimpleNamespace(text='')}
        ns = dict(selected_size=lambda _: (.8, .1, 'fine'), diameter_matches=sizes.diameter_matches,
                  analyze_cylinder=lambda face: face, tr=loc.translator('en'))
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<size-warning>', 'exec'), ns)
        ns['update_size_status'](fields.__getitem__)
        self.assertIn('10 mm differs from M8', fields['size_status'].text)
        self.assertEqual(fields['partner_face'].selection(0).entity.radius, .5)

    def test_dialog_destruction_removes_preview(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_destroy')
        handler.args.args[0].annotation = None
        preview = Mock()
        ns = dict(thread_preview=preview)
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<destroy>', 'exec'), ns)
        ns['command_destroy'](None)
        preview.clear.assert_called_once()

    def test_failed_preview_removes_all_groups_and_success_can_clear(self):
        tree = ast.parse((ADDIN / 'fusion/thread_preview.py').read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        created = []
        def group():
            result = Mock(isValid=True)
            created.append(result)
            return result
        design = types.SimpleNamespace(rootComponent=types.SimpleNamespace(
            customGraphicsGroups=types.SimpleNamespace(add=group)))
        point = types.SimpleNamespace(x=0, y=0, z=0)
        cylinder = types.SimpleNamespace(axis_start=point, axis_end=point, radial=point,
                                         radius=1, is_external=True)
        face = types.SimpleNamespace(assemblyContext=types.SimpleNamespace(transform2=object()))
        p = replace(self.p, face=face)
        coords = Mock(side_effect=RuntimeError('graphics failed'))
        ns = dict(analyze_cylinder=lambda _: cylinder, thread_section=lambda *a: cylinder,
                  preview_lines=lambda *a: ([((0, 0, 0), (0, 0, 1))], [], []),
                  adsk=types.SimpleNamespace(fusion=types.SimpleNamespace(
                       CustomGraphicsCoordinates=types.SimpleNamespace(create=coords),
                       CustomGraphicsShowThroughColorEffect=types.SimpleNamespace(create=lambda *a: None)),
                       core=types.SimpleNamespace(Color=types.SimpleNamespace(create=lambda *a: None))))
        exec(compile(ast.Module(body=[cls], type_ignores=[]), '<preview>', 'exec'), ns)
        preview = ns['ThreadPreview']()
        with self.assertRaisesRegex(RuntimeError, 'graphics failed'):
            preview.update(design, [p])
        created[0].deleteMe.assert_called_once()
        self.assertEqual(preview.groups, [])
        coords.side_effect = None
        preview.update(design, [p])
        self.assertIs(created[-1].transform, face.assemblyContext.transform2)
        self.assertFalse(created[-1].isSelectable)
        preview.clear()
        created[-1].deleteMe.assert_called_once()
