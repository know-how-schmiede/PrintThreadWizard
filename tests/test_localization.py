"""Localization coverage and user-visible error regressions; no Fusion needed."""
import ast
import importlib
import json
import math
from pathlib import Path
import string
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ADDIN = ROOT / 'Fusion_AddIn' / 'PrintThread Wizard'
package = types.ModuleType('printthread_test')
package.__path__ = [str(ADDIN)]
sys.modules[package.__name__] = package
loc = importlib.import_module('printthread_test.localization')
extra = importlib.import_module('printthread_test.localization_extra')
parameters = importlib.import_module('printthread_test.core.thread_parameters')
presets = importlib.import_module('printthread_test.core.thread_presets')


class LocalizationTests(unittest.TestCase):
    def tearDown(self):
        loc.set_locale('en')

    def test_explicit_coverage_and_placeholders(self):
        tree = ast.parse((ADDIN / 'localization.py').read_text(encoding='utf-8'))
        dictionaries = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id == '_TRANSLATIONS' for t in n.targets))
        formatter = string.Formatter()
        for name, value in zip(dictionaries.keys, dictionaries.values):
            locale = name.value
            if locale != 'en':
                explicit = {key.value for key in value.keys if key is not None}
                explicit.update(extra.TRANSLATIONS[locale])
                self.assertEqual(set(loc._EN) - explicit, set(), locale)
            strings = loc._TRANSLATIONS[locale]
            self.assertEqual(set(strings), set(loc._TRANSLATIONS['en']), locale)
            for key, text in strings.items():
                self.assertTrue(text, (locale, key))
                fields = {f for _, f, _, _ in formatter.parse(text) if f is not None}
                expected = {f for _, f, _, _ in formatter.parse(loc._TRANSLATIONS['en'][key]) if f is not None}
                self.assertEqual(fields, expected, (locale, key))
                loc.translator(locale)(key, **{f: 'sample' for f in fields})

    def test_used_translation_keys_exist(self):
        for path in ADDIN.rglob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'tr' and n.args and isinstance(n.args[0], ast.Constant):
                    self.assertIn(n.args[0].value, loc._TRANSLATIONS['en'], str(path))
            compile(tree, str(path), 'exec')

    def test_shared_locale_and_fallback(self):
        params = parameters.ThreadParameters(None, (), math.pi / 3, 0.02, 0.1, 0)
        for locale in loc.SUPPORTED_LOCALES:
            loc.set_locale(locale)
            self.assertEqual(params.validation_errors(), [loc.translator(locale)('face_required')])
            with self.assertRaises(ValueError) as error:
                presets.save_thread_preset('', '', {})
            self.assertEqual(str(error.exception), loc.translator(locale)('name_required'))
        loc.set_locale('unknown')
        self.assertEqual(params.validation_errors(), ['A cylindrical face must be selected.'])
        self.assertEqual(loc.translator('unknown')('result'), 'Result')

    def test_language_detection(self):
        enums = types.SimpleNamespace(**{name: i for i, name in enumerate(loc._LANGUAGE_ENUM_NAMES.values())})
        core = types.SimpleNamespace(UserLanguages=enums)
        for locale, name in loc._LANGUAGE_ENUM_NAMES.items():
            app = types.SimpleNamespace(preferences=types.SimpleNamespace(generalPreferences=types.SimpleNamespace(userLanguage=getattr(enums, name))))
            self.assertEqual(loc.detect_locale(core, app), locale)
        app.preferences.generalPreferences.userLanguage = -1
        self.assertEqual(loc.detect_locale(core, app), 'en')

    def test_import_errors_and_preset_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with patch.object(presets, 'preset_file_path', return_value=folder / 'storage.json'):
                for locale in loc.SUPPORTED_LOCALES:
                    loc.set_locale(locale)
                    source = folder / 'invalid.json'
                    source.write_text(json.dumps({'schema_version': 1, 'presets': [{'name': 'M6'}]}), encoding='utf-8')
                    with self.assertRaises(ValueError) as error:
                        presets.import_thread_presets(str(source))
                    self.assertEqual(str(error.exception), loc.translate('import_parameters', name='M6'))
                    source.write_text('{', encoding='utf-8')
                    with self.assertRaises(ValueError) as error:
                        presets.import_thread_presets(str(source))
                    self.assertTrue(str(error.exception).startswith(loc.translate('import_unreadable', error='')))
                saved = presets.save_thread_preset('M6 – Test', 'Notiz', {'chamfer_extra_cm': 0.04})
                export = folder / 'export.json'
                self.assertEqual(presets.export_thread_presets(str(export)), 1)
                presets.delete_thread_preset(saved['id'])
                self.assertEqual(presets.import_thread_presets(str(export)), 1)
                self.assertEqual(presets.load_thread_presets()[0]['settings']['chamfer_extra_cm'], 0.04)

    def test_version_consistency(self):
        version = importlib.import_module('printthread_test.version').VERSION
        self.assertEqual(version, '0.8.4')
        manifest = json.loads((ADDIN / 'PrintThread Wizard.manifest').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], version)
        self.assertIn(f'#define MyAppVersion "{version}"', (ROOT / 'installer/PrintThreadWizard.iss').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
