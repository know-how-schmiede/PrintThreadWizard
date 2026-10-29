"""Calibration mathematics, persistence and command transaction regressions."""
import ast
from dataclasses import replace
import importlib
import json
from pathlib import Path
import tempfile
import types
import traceback
import unittest
from unittest.mock import Mock, patch
from test_localization import ADDIN, presets

cal = importlib.import_module('printthread_test.core.calibration')


class CalibrationTests(unittest.TestCase):
    def test_sweep_path_resolves_calibration_edge_in_assembly_context(self):
        tree = ast.parse((ADDIN / 'fusion/thread_geometry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_create_thread_sweep')
        edge, proxy, occurrence = Mock(), object(), object()
        edge.createForAssemblyContext.return_value = proxy
        path = object()
        def resolve(curve, options):
            if curve is edge:
                raise RuntimeError('Utils::getObjectPath(edge, objPath, nullptr, contextPath)')
            self.assertIs(curve, proxy)
            return path
        path_create = Mock(side_effect=resolve)
        sweeps = Mock()
        cylinder = types.SimpleNamespace(is_external=True, body=object(),
                   component=types.SimpleNamespace(features=types.SimpleNamespace(sweepFeatures=sweeps)))
        ns = dict(tr=lambda key: key, adsk=types.SimpleNamespace(fusion=types.SimpleNamespace(
             Path=types.SimpleNamespace(create=path_create),
             ChainedCurveOptions=types.SimpleNamespace(noChainedCurves=0),
             FeatureOperations=types.SimpleNamespace(CutFeatureOperation=1, NewBodyFeatureOperation=2))))
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<sweep-path>', 'exec'), ns)
        profile, guide = object(), object()
        result = ns['_create_thread_sweep'](cylinder, profile, edge, guide, creation_occurrence=occurrence)
        edge.createForAssemblyContext.assert_called_once_with(occurrence)
        sweeps.createInput.assert_called_once_with(profile, path, 1)
        self.assertIs(result, sweeps.add.return_value)
        # Legacy model threads still pass their original native edge through.
        with self.assertRaisesRegex(RuntimeError, 'getObjectPath'):
            ns['_create_thread_sweep'](cylinder, profile, edge, guide)

    def test_profile_plane_uses_occurrence_and_edge_proxy(self):
        tree = ast.parse((ADDIN / 'fusion/thread_geometry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_create_profile_plane')
        planes = Mock()
        edge, occurrence = Mock(), object()
        ns = dict(adsk=types.SimpleNamespace(core=types.SimpleNamespace(
                    ValueInput=types.SimpleNamespace(createByReal=lambda value: value))), tr=lambda key: key)
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<profile-plane>', 'exec'), ns)
        component = types.SimpleNamespace(constructionPlanes=planes)
        ns['_create_profile_plane'](component, edge, occurrence)
        planes.createInput.assert_called_once_with(occurrence)
        edge.createForAssemblyContext.assert_called_once_with(occurrence)
        planes.createInput.return_value.setByDistanceOnPath.assert_called_once_with(
            edge.createForAssemblyContext.return_value, 0)
        planes.reset_mock()
        edge.reset_mock()
        ns['_create_profile_plane'](component, edge)
        planes.createInput.assert_called_once_with()
        edge.createForAssemblyContext.assert_not_called()

    def test_failed_series_removes_owned_component_and_propagates_error(self):
        from uuid import uuid4
        tree = ast.parse((ADDIN / 'fusion/calibration.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'create_calibration')
        occurrence = Mock(isValid=True)
        design = Mock()
        design.rootComponent.occurrences.addNewComponent.return_value = occurrence
        ns = dict(uuid4=uuid4, _create_specimens=Mock(side_effect=RuntimeError('edge path failed')),
                  adsk=types.SimpleNamespace(core=types.SimpleNamespace(Matrix3D=types.SimpleNamespace(create=lambda: None))))
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<series>', 'exec'), ns)
        with self.assertRaisesRegex(RuntimeError, 'edge path failed'):
            ns['create_calibration'](design, cal.CalibrationSeries())
        occurrence.deleteMe.assert_called_once()
        ns['_create_specimens'].assert_called_once_with(occurrence.component, occurrence, cal.CalibrationSeries())

    def test_no_native_required_selection_blocks_calibration(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == 'setSelectionLimits']
        self.assertTrue(calls)
        # Native required selections block OK independently of areInputsValid.
        for call in calls:
            self.assertEqual(ast.literal_eval(call.args[0]), 0)
        params = importlib.import_module('printthread_test.core.thread_parameters')
        self.assertTrue(params.ThreadParameters(None, (), 1, .1, .3, 0).validation_errors())

    def test_calibration_validation_accepts_reported_dimensions_without_face(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_validate_input')
        handler.args.args[0].annotation = None
        status = types.SimpleNamespace(text='')
        series = cal.CalibrationSeries(diameter=3, pitch=.4, length=2, wall=.3)
        ns = dict(thread_preview=Mock(), traceback=traceback, _calibration_enabled=lambda _: True, active_command_inputs=None,
                  calibration_tab=types.SimpleNamespace(read_series=lambda _: series.validate()),
                  _input_by_id=lambda inputs, key: status)
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<validate>', 'exec'), ns)
        args = types.SimpleNamespace(areInputsValid=False)
        ns['command_validate_input'](args)
        self.assertTrue(args.areInputsValid)
        self.assertIn('R05', status.text)
        ns['calibration_tab'].read_series = lambda _: replace(series, wall=.01).validate()
        ns['command_validate_input'](args)
        self.assertFalse(args.areInputsValid)

    def test_all_calibration_controls_receive_localized_tooltips(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/calibration_tab.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_add_tooltips')
        controls = [types.SimpleNamespace(id='cal_' + key) for key in
                    ('enabled', 'diameter', 'pitch', 'length', 'wall', 'direction', 'gaps')]
        profiles = [types.SimpleNamespace(id='profile_' + key) for key in
                    ('name', 'printer', 'material', 'orientation', 'note', 'nozzle', 'layer_height',
                     'tolerance', 'distribution', 'diameter_min', 'diameter_max', 'pitch_min', 'pitch_max',
                     'save', 'apply', 'delete')]
        profiles.append(types.SimpleNamespace(id='print_profile_selector'))
        def collection(values):
            return types.SimpleNamespace(count=len(values), item=lambda i: values[i])
        controls.append(types.SimpleNamespace(id='print_profiles', children=collection(profiles)))
        loc = importlib.import_module('printthread_test.localization')
        ns = dict(tr=loc.translator('de'))
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<tooltips>', 'exec'), ns)
        ns['_add_tooltips'](collection(controls))
        for control in controls[:-1] + profiles:
            self.assertTrue(control.tooltip, control.id)
            self.assertNotIn('tip_', control.tooltip)

    def profile(self, **changes):
        return dict(name='PLA vertical', printer='Test', material='PLA',
                    orientation='Z', note='Measured', nozzle_cm=.04,
                    layer_height_cm=.02, tolerance_cm=.023,
                    clearance_distribution='internal', **changes)

    def test_series_positions_ids_and_total_radial_gap(self):
        series = cal.CalibrationSeries().validate()
        samples = series.specimens()
        self.assertEqual(len(samples), 6)
        self.assertEqual(samples[0], ('REF', 0, 0))
        self.assertEqual([gap * 10 for _, gap, _ in samples[1:]], [.1, .15, .2, .25, .3])
        self.assertEqual(len({name for name, _, _ in samples}), 6)
        for previous, current in zip(samples, samples[1:]):
            self.assertGreater(current[2] - previous[2], series.diameter + 2 * series.wall)
        parameters = importlib.import_module('printthread_test.core.thread_parameters')
        for _, gap, _ in samples[1:]:
            p = parameters.ThreadParameters(object(), (), 1, .1, .3, 0,
                                            tolerance=gap, clearance_distribution='internal')
            self.assertEqual(p.tolerance_radius_offset(True), 0)
            self.assertEqual(p.tolerance_radius_offset(False), gap)

    def test_invalid_series(self):
        series = cal.CalibrationSeries()
        for changes in (dict(diameter=0), dict(pitch=float('nan')), dict(length=.1),
                        dict(wall=.01), dict(clearances=()), dict(clearances=(.01, .01)),
                        dict(clearances=(float('inf'),)), dict(clearances=(-.1,)),
                        dict(handedness='other'), dict(clearances=tuple(i / 100 for i in range(13)))):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(series, **changes).validate()
        replace(series, handedness='left', clearances=(0, .02)).validate()

    def test_profile_scope_and_invalid_values(self):
        p = self.profile(diameter_min_cm=1, diameter_max_cm=3, pitch_max_cm=.3)
        self.assertTrue(cal.profile_matches(p, 1, .3))
        self.assertFalse(cal.profile_matches(p, .9, .2))
        self.assertFalse(cal.profile_matches(p, 2, .4))
        for changes in (dict(nozzle_cm=0), dict(layer_height_cm=float('nan')),
                        dict(tolerance_cm=True), dict(name=''), dict(note=3),
                        dict(diameter_min_cm=4, diameter_max_cm=2),
                        dict(clearance_distribution='invalid')):
            bad = self.profile()
            bad.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                cal.validate_print_profile(bad)

    def test_legacy_migration_profiles_and_atomic_import(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Path(directory) / 'storage.json'
            transfer = Path(directory) / 'export.json'
            storage.write_text(json.dumps(dict(schema_version=1, presets=[],
                                              preferences=dict(default_tolerance_cm=.015))), encoding='utf-8')
            with patch.object(presets, 'preset_file_path', return_value=storage):
                self.assertEqual(presets.load_print_profiles(), [])
                saved = presets.save_print_profile(self.profile())
                self.assertEqual(json.loads(storage.read_text())['schema_version'], 2)
                presets.export_thread_presets(str(transfer))
                presets.delete_print_profile(saved['id'])
                presets.import_thread_presets(str(transfer))
                self.assertEqual(presets.load_print_profiles(), [saved])
                original = storage.read_bytes()
                data = json.loads(transfer.read_text())
                data['print_profiles'].append(dict(saved, id='broken', tolerance_cm=-1))
                transfer.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    presets.import_thread_presets(str(transfer))
                self.assertEqual(storage.read_bytes(), original)
                transfer.write_text(json.dumps(dict(schema_version=1, presets=[])), encoding='utf-8')
                presets.import_thread_presets(str(transfer))
                self.assertEqual(presets.load_print_profiles(), [saved])

    def test_calibration_command_routes_without_face_and_aborts_series_failure(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'command_execute')
        handler.args.args[0].annotation = None
        creator = Mock(side_effect=RuntimeError('ring 3 failed'))
        thread_reader = Mock(side_effect=AssertionError('must not read thread face'))
        ns = dict(thread_preview=Mock(), traceback=traceback, _calibration_enabled=lambda _: True, create_calibration=creator,
                  calibration_tab=types.SimpleNamespace(read_series=lambda _: cal.CalibrationSeries()),
                  _read_parameters=thread_reader, CMD_NAME='test',
                  app=types.SimpleNamespace(activeProduct='design'),
                  futil=types.SimpleNamespace(log=lambda *a, **k: None),
                  ui=types.SimpleNamespace(messageBox=lambda _: None),
                  adsk=types.SimpleNamespace(fusion=types.SimpleNamespace(Design=types.SimpleNamespace(cast=lambda d: d)),
                       core=types.SimpleNamespace(LogLevels=types.SimpleNamespace(ErrorLogLevel=1))))
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<calibration>', 'exec'), ns)
        args = types.SimpleNamespace(command=types.SimpleNamespace(commandInputs=None))
        ns['command_execute'](args)
        creator.assert_called_once()
        thread_reader.assert_not_called()
        self.assertTrue(args.executeFailed)
        self.assertEqual(args.executeFailedMessage, 'ring 3 failed')

    def test_apply_profile_only_changes_clearance_and_distribution(self):
        tree = ast.parse((ADDIN / 'commands/commandDialog/entry.py').read_text(encoding='utf-8'))
        handler = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_apply_print_profile')
        items = []
        class Items:
            @property
            def count(self):
                return len(items)
            def item(self, i):
                return items[i]
            def add(self, name, selected):
                items.append(types.SimpleNamespace(name=name, isSelected=selected))
        distribution = [types.SimpleNamespace(isSelected=False) for _ in range(3)]
        controls = {'tolerance': types.SimpleNamespace(listItems=Items()),
                    'clearance_distribution': types.SimpleNamespace(listItems=types.SimpleNamespace(item=lambda i: distribution[i]))}
        params = types.SimpleNamespace(face=object(), pitch=.2)
        selected = Mock()
        ns = dict(TOLERANCE_OPTIONS=(), active_command_inputs=object(),
                  _read_parameters=lambda _: params, analyze_cylinder=lambda _: types.SimpleNamespace(radius=1),
                  profile_matches=cal.profile_matches, _partner_parameters=lambda *a: None,
                  _input_by_id=lambda inputs, key: controls[key], _select_dropdown_item=selected,
                  _update_result_text=lambda _: None, tr=lambda k: k)
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<apply>', 'exec'), ns)
        ns['_apply_print_profile'](self.profile())
        self.assertEqual(ns['TOLERANCE_OPTIONS'][0][1], .023)
        self.assertTrue(distribution[1].isSelected)
        self.assertEqual(params.pitch, .2)
        self.assertEqual(selected.call_count, 1)
