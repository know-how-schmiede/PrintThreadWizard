"""M0 regressions without Fusion."""
from dataclasses import replace, make_dataclass
import ast
import importlib
import json
import math
from pathlib import Path
import tempfile
import types
import traceback
import unittest
from unittest.mock import Mock, patch
from test_localization import parameters, presets, ADDIN

iso = importlib.import_module('printthread_test.core.iso_metric')

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.params = parameters.ThreadParameters(object(), (), math.pi / 3, .06, .2, 0, .02)
        self.settings = dict(calculation_mode='free', flank_angle_rad=math.pi / 3,
                             thread_depth_cm=.06, pitch_cm=.2, fillet_radius_cm=0)

    def test_radial_pair_clearance(self):
        for clearance in (0, .015, .02, .05):
            p = replace(self.params, tolerance=clearance)
            outside, inside = p.tolerance_radius_offset(True), p.tolerance_radius_offset(False)
            self.assertAlmostEqual(inside - outside, clearance)
            self.assertAlmostEqual(outside * 2, -clearance)
            self.assertAlmostEqual(inside * 2, clearance)

    def test_handedness_preserves_extent_and_reverses_rotation(self):
        self.assertEqual(self.params.handedness, 'right')
        for direction, axis_sign in (('right', 1), ('left', -1)):
            p = replace(self.params, handedness=direction)
            self.assertEqual(p.validation_errors(), [])
            self.assertAlmostEqual(p.helix_turns(2), 10)
            self.assertAlmostEqual(axis_sign * p.signed_pitch * p.helix_turns(2), 2)
            # At a quarter turn, identical rise but mirrored angular position.
            self.assertAlmostEqual(axis_sign * p.signed_pitch / 4, .05)
        self.assertTrue(replace(self.params, handedness='unknown').validation_errors())

    def test_partial_range_from_both_ends_in_centimeters(self):
        p = replace(self.params, full_length=False, start_offset=.2, thread_length=1.5)
        # A 40 mm cylinder, 2 mm offset and 15 mm length.
        self.assertEqual(p.axial_range(4), (.2, 1.7))
        self.assertEqual(p.axial_range(4, from_end=True), (2.3, 3.8))
        self.assertEqual(self.params.axial_range(4), (0, 4))
        self.assertEqual(self.params.axial_range(4, from_end=True), (0, 4))
        for direction in ('right', 'left'):
            self.assertEqual(replace(p, handedness=direction).axial_range(4), (.2, 1.7))

    def test_invalid_section_values_and_bounds(self):
        p = replace(self.params, full_length=False)
        for changes in (dict(start_offset=-.1), dict(thread_length=0),
                        dict(thread_length=-1), dict(start_offset=float('nan')),
                        dict(thread_length=float('inf')), dict(start_offset=3.5)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(p, **changes).axial_range(4)
        for available in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                p.axial_range(available)
        self.assertTrue(replace(p, full_length='false').validation_errors())

    def test_section_preset_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Path(directory) / 'storage.json'
            source = Path(directory) / 'transfer.json'
            with patch.object(presets, 'preset_file_path', return_value=storage):
                settings = dict(self.settings, full_length=False, start_offset_cm=.2, thread_length_cm=1.5)
                saved = presets.save_thread_preset('15 mm', '', settings)
                presets.export_thread_presets(str(source))
                presets.delete_thread_preset(saved['id'])
                presets.import_thread_presets(str(source))
                self.assertEqual(presets.load_thread_presets()[0]['settings'], settings)
                original = storage.read_bytes()
                for key, value in (('full_length', 'false'), ('start_offset_cm', -.1),
                                   ('thread_length_cm', float('nan')), ('thread_length_cm', 0)):
                    with self.assertRaises(ValueError):
                        presets.save_thread_preset('bad', '', dict(settings, **{key:value}))
                    self.assertEqual(storage.read_bytes(), original)

    def test_section_resolution_and_chamfer_limits(self):
        tree = ast.parse((ADDIN / 'fusion/thread_geometry.py').read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'thread_section')
        cylinder_type = make_dataclass('Section', ['axis_start', 'axis_end', 'axis', 'length'])
        cylinder = cylinder_type(0, 4, 'axis', 4)
        ns = dict(replace=replace, math=math, tr=lambda key:key,
                  _translated_point=lambda point, axis, amount:point + amount,
                  _trim_reference_from_selected_circles=lambda cylinder, ends:cylinder,
                  capture_chamfer_ends=lambda cylinder, edges:[types.SimpleNamespace(is_start=edges[0] == 'first')])
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<section>', 'exec'), ns)
        p = replace(self.params, full_length=False, start_offset=.2, thread_length=1.5, start_edge='first')
        section = ns['thread_section'](cylinder, p, ())
        self.assertEqual((section.axis_start, section.axis_end, section.length), (.2, 1.7, 1.5))
        section = ns['thread_section'](cylinder, replace(p, start_edge='last'), ())
        self.assertAlmostEqual(section.axis_start, 2.3)
        self.assertAlmostEqual(section.axis_end, 3.8)
        with self.assertRaises(ValueError):
            ns['thread_section'](cylinder, replace(p, start_edge=None), ())
        for is_start in (True, False):
            with self.assertRaises(ValueError):
                ns['thread_section'](cylinder, p, (types.SimpleNamespace(is_start=is_start),))
        end = types.SimpleNamespace(is_start=True)
        self.assertEqual(ns['thread_section'](cylinder, replace(p, start_offset=0), (end,)).axis_start, 0)
        with self.assertRaises(ValueError):
            ns['thread_section'](cylinder, replace(p, start_offset=0, thread_length=.01), (end,))

    def test_external_partial_sweep_is_a_tool_not_a_direct_cut(self):
        tree = ast.parse((ADDIN / 'fusion/thread_geometry.py').read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_create_thread_sweep')
        ops = types.SimpleNamespace(CutFeatureOperation='cut', NewBodyFeatureOperation='new')
        for external, bounded, expected in ((True, False, 'cut'), (True, True, 'new'), (False, False, 'new')):
            sweeps = Mock()
            cylinder = types.SimpleNamespace(is_external=external, body=object(),
                         component=types.SimpleNamespace(features=types.SimpleNamespace(sweepFeatures=sweeps)))
            ns = dict(tr=lambda key:key, adsk=types.SimpleNamespace(fusion=types.SimpleNamespace(
                Path=types.SimpleNamespace(create=lambda *a:object()),
                ChainedCurveOptions=types.SimpleNamespace(noChainedCurves=0), FeatureOperations=ops)))
            exec(compile(ast.Module(body=[function], type_ignores=[]), '<sweep>', 'exec'), ns)
            ns['_create_thread_sweep'](cylinder, object(), object(), object(), bounded_external=bounded)
            self.assertEqual(sweeps.createInput.call_args.args[2], expected)

    def test_direction_preset_roundtrip_and_unknown_import(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Path(directory) / 'storage.json'
            source = Path(directory) / 'transfer.json'
            with patch.object(presets, 'preset_file_path', return_value=storage):
                for direction in ('right', 'left'):
                    saved = presets.save_thread_preset(direction, '', dict(self.settings, handedness=direction))
                    presets.export_thread_presets(str(source))
                    presets.delete_thread_preset(saved['id'])
                    presets.import_thread_presets(str(source))
                    actual = next(p for p in presets.load_thread_presets() if p['id'] == saved['id'])
                    self.assertEqual(actual['settings']['handedness'], direction)
                original = storage.read_bytes()
                payload = json.loads(source.read_text(encoding='utf-8'))
                payload['presets'][0]['settings']['handedness'] = 'unknown'
                source.write_text(json.dumps(payload), encoding='utf-8')
                with self.assertRaises(ValueError):
                    presets.import_thread_presets(str(source))
                self.assertEqual(storage.read_bytes(), original)

    def test_helix_api_positive_turns_and_localized_failure(self):
        # Run the actual API boundary up to the injected kernel failure.
        # No B-Rep geometry is simulated by this test.
        tree = ast.parse((ADDIN / 'fusion/thread_geometry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_create_persistent_helix')
        for arg in handler.args.args:
            arg.annotation = None
        from test_localization import loc
        for locale in loc.SUPPORTED_LOCALES:
            for direction in ('right', 'left'):
                axis = Mock()
                helix_axis = axis.copy.return_value
                cylinder = types.SimpleNamespace(axis=axis, axis_start=object(), radial=object(), radius=1, length=2)
                manager = Mock()
                manager.createHelixWire.side_effect = RuntimeError('ASM_HELIX_NR_TURNS_TOO_SMALL')
                ns = dict(tr=loc.translator(locale), _translated_point=lambda *a:object(),
                          adsk=types.SimpleNamespace(fusion=types.SimpleNamespace(
                              TemporaryBRepManager=types.SimpleNamespace(get=lambda:manager))))
                exec(compile(ast.Module(body=[handler], type_ignores=[]), '<helix>', 'exec'), ns)
                with self.assertRaises(RuntimeError) as caught:
                    ns['_create_persistent_helix'](cylinder, replace(self.params, handedness=direction))
                self.assertEqual(str(caught.exception), loc.translator(locale)('helix_failed'))
                args = manager.createHelixWire.call_args.args
                self.assertIs(args[1], helix_axis)
                self.assertEqual(args[4], 10)
                self.assertEqual(args[3], -.2 if direction == 'left' else .2)
                if direction == 'left':
                    helix_axis.scaleBy.assert_called_once_with(-1)
                else:
                    helix_axis.scaleBy.assert_not_called()
                axis.scaleBy.assert_not_called()

    def test_metric_depth_and_diameter(self):
        # P=2 mm, results in Fusion cm; distinct external/internal depths.
        self.assertAlmostEqual(iso.radial_thread_depth(.2, True), .1226869)
        self.assertAlmostEqual(iso.radial_thread_depth(.2, False), .1082532)
        self.assertAlmostEqual(iso.minor_diameter(1, .2, True), .7546262)
        self.assertAlmostEqual(iso.minor_diameter(1, .2, False), .7834936)

    def test_invalid_numbers_and_profile(self):
        for field in ('flank_angle', 'thread_depth', 'pitch', 'fillet_radius', 'tolerance', 'chamfer_extra'):
            for value in (float('nan'), float('inf'), -float('inf')):
                with self.subTest(field=field, value=value):
                    self.assertTrue(replace(self.params, **{field:value}).validation_errors())
        for changes in (dict(pitch=0), dict(thread_depth=-1), dict(flank_angle=math.pi),
                        dict(fillet_radius=.06), dict(thread_depth=.2), dict(tolerance=-.01)):
            self.assertTrue(replace(self.params, **changes).validation_errors())
        self.assertEqual(self.params.validation_errors(), [])

    def test_legacy_and_failed_import_preserve_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Path(directory) / 'storage.json'
            source = Path(directory) / 'import.json'
            with patch.object(presets, 'preset_file_path', return_value=storage):
                saved = presets.save_thread_preset('Legacy', '', self.settings)
                original = storage.read_bytes()
                # Schema 1 missing tolerance and chamfer extra still loads unchanged.
                self.assertEqual(presets.load_thread_presets()[0]['settings'], self.settings)
                for payload in ([], dict(schema_version=presets.SCHEMA_VERSION + 1, presets=[]),
                    dict(schema_version=1, presets=[saved, dict(name='bad', settings={})]),
                    dict(schema_version=1, presets=[], preferences=dict(default_tolerance_cm=float('nan')))):
                    source.write_text(json.dumps(payload), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        presets.import_thread_presets(str(source))
                    self.assertEqual(storage.read_bytes(), original)
                for key, value in (('pitch_cm', float('nan')), ('tolerance_cm', float('inf')),
                                   ('calculation_mode', 'unknown'), ('fillet_radius_cm', -1)):
                    with self.assertRaises(ValueError):
                        presets.save_thread_preset('Bad', '', dict(self.settings, **{key:value}))
                    self.assertEqual(storage.read_bytes(), original)

    def test_execute_failure_requests_transaction_abort(self):
        # Exercise the real handler with a failing geometry operation, no fake B-Rep.
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_execute')
        handler.args.args[0].annotation = None
        ns = dict(traceback=traceback, _calibration_enabled=lambda _: False, _apply_calculation_mode=lambda _:None, _read_parameters=lambda _:self.params,
                  _request_errors=lambda *args:[], _partner_parameters=lambda *args:None,
                  CMD_NAME='test', tr=lambda key:key,
                  futil=types.SimpleNamespace(log=lambda *a, **k:None),
                  ui=types.SimpleNamespace(messageBox=lambda _:None),
                  adsk=types.SimpleNamespace(core=types.SimpleNamespace(LogLevels=types.SimpleNamespace(ErrorLogLevel=1))))
        def fail(_):
            raise RuntimeError('injected after body edit')
        ns['create_thread'] = fail
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<handler>', 'exec'), ns)
        args = types.SimpleNamespace(command=types.SimpleNamespace(commandInputs=None))
        ns['command_execute'](args)
        self.assertTrue(args.executeFailed)
        self.assertEqual(args.executeFailedMessage, 'injected after body edit')

    def test_all_clearance_distributions_preserve_total_radial_gap(self):
        for mode, expected in (('balanced', (-.01, .01)),
                               ('internal', (0, .02)), ('external', (-.02, 0))):
            p = replace(self.params, tolerance=.02, clearance_distribution=mode)
            offsets = (p.tolerance_radius_offset(True), p.tolerance_radius_offset(False))
            self.assertEqual(offsets, expected)
            self.assertAlmostEqual(offsets[1] - offsets[0], .02)
            self.assertEqual(p.validation_errors(), [])
        self.assertTrue(replace(self.params, clearance_distribution='invalid').validation_errors())

    def test_pair_rejects_same_native_body_types_and_diameter_mismatch(self):
        validate = importlib.import_module('printthread_test.core.thread_pair').validate_pair
        first = types.SimpleNamespace(body=object(), is_external=True, radius=1.)
        second = types.SimpleNamespace(body=object(), is_external=False, radius=1.)
        validate(first, second)
        for changes in (dict(body=first.body), dict(is_external=True), dict(radius=1.01),
                        dict(radius=float('nan'))):
            bad = types.SimpleNamespace(**{**vars(second), **changes})
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate(first, bad)

    def test_failure_on_second_thread_aborts_complete_command(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_execute')
        handler.args.args[0].annotation = None
        partner = replace(self.params, face=object())
        create = Mock(side_effect=[object(), RuntimeError('second failed')])
        ns = dict(traceback=traceback, _calibration_enabled=lambda _: False, _apply_calculation_mode=lambda _: None, _read_parameters=lambda _: self.params,
                  _request_errors=lambda *a: [], _partner_parameters=lambda *a: partner,
                  create_thread=create, CMD_NAME='test', tr=lambda key: key,
                  futil=types.SimpleNamespace(log=lambda *a, **k: None),
                  ui=types.SimpleNamespace(messageBox=lambda _: None),
                  adsk=types.SimpleNamespace(core=types.SimpleNamespace(LogLevels=types.SimpleNamespace(ErrorLogLevel=1))))
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<pair-command>', 'exec'), ns)
        args = types.SimpleNamespace(command=types.SimpleNamespace(commandInputs=None))
        ns['command_execute'](args)
        self.assertEqual(create.call_args_list[0].args, (self.params,))
        self.assertEqual(create.call_args_list[1].args, (partner,))
        self.assertTrue(args.executeFailed)
        self.assertEqual(args.executeFailedMessage, 'second failed')
        create.reset_mock()
        ns['_request_errors'] = lambda *a: ['invalid second section']
        ns['command_execute'](args)
        create.assert_not_called()
        self.assertEqual(args.executeFailedMessage, 'invalid second section')

    def test_pair_preset_roundtrip_and_invalid_import_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Path(directory) / 'storage.json'
            source = Path(directory) / 'export.json'
            with patch.object(presets, 'preset_file_path', return_value=storage):
                settings = dict(self.settings, clearance_distribution='internal', pair_mode=True,
                                partner_full_length=False, partner_start_offset_cm=.2,
                                partner_thread_length_cm=1.5)
                presets.save_thread_preset('pair', '', settings)
                presets.export_thread_presets(str(source))
                presets.import_thread_presets(str(source))
                self.assertEqual(presets.load_thread_presets()[0]['settings'], settings)
                original = storage.read_bytes()
                for field, bad in (('clearance_distribution', 'invalid'),
                                   ('pair_mode', 1),
                                   ('partner_full_length', 'false'),
                                   ('partner_start_offset_cm', -.1),
                                   ('partner_thread_length_cm', float('inf'))):
                    data = json.loads(source.read_text(encoding='utf-8'))
                    data['presets'][0]['settings'][field] = bad
                    source.write_text(json.dumps(data), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        presets.import_thread_presets(str(source))
                    self.assertEqual(storage.read_bytes(), original)
                    presets.export_thread_presets(str(source))

    def test_partner_has_independent_section_and_iso_depth(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_partner_parameters')
        face, edge, chamfer = object(), object(), object()
        def selection(*entities):
            return types.SimpleNamespace(selectionCount=len(entities),
                                         selection=lambda i: types.SimpleNamespace(entity=entities[i]))
        fields = dict(pair_mode=types.SimpleNamespace(value=True), partner_face=selection(face),
                      partner_start_edge=selection(edge), partner_chamfer_edges=selection(chamfer),
                      partner_full_length=types.SimpleNamespace(value=False),
                      partner_start_offset=types.SimpleNamespace(value=.2),
                      partner_thread_length=types.SimpleNamespace(value=1.5))
        ns = dict(replace=replace, _input_by_id=lambda _, key: fields[key],
                  _is_iso_mode=lambda _: True, radial_thread_depth=iso.radial_thread_depth,
                  analyze_cylinder=lambda _: types.SimpleNamespace(is_external=False))
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<partner>', 'exec'), ns)
        partner = ns['_partner_parameters'](None, self.params)
        self.assertIs(partner.face, face)
        self.assertEqual(partner.chamfer_edges, (chamfer,))
        self.assertIs(partner.start_edge, edge)
        self.assertEqual(partner.axial_range(4), (.2, 1.7))
        self.assertAlmostEqual(partner.thread_depth, iso.radial_thread_depth(self.params.pitch, False))
        self.assertNotEqual(partner.thread_depth, iso.radial_thread_depth(self.params.pitch, True))
        self.assertTrue(self.params.full_length)
        ns['_is_iso_mode'] = lambda _: False
        self.assertEqual(ns['_partner_parameters'](None, self.params).thread_depth, self.params.thread_depth)
        fields['pair_mode'].value = False
        self.assertIsNone(ns['_partner_parameters'](None, self.params))
