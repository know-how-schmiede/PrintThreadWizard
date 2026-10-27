"""M0 regressions without Fusion."""
from dataclasses import replace
import ast
import importlib
import json
import math
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
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
                for payload in ([], dict(schema_version=2, presets=[]),
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
        ns = dict(_apply_calculation_mode=lambda _:None, _read_parameters=lambda _:self.params,
                  _validation_errors=lambda _:[], CMD_NAME='test', tr=lambda key:key,
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
