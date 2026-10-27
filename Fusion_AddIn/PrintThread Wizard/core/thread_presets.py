from ..localization import translate as tr

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


SCHEMA_VERSION = 1
FILE_NAME = 'thread-presets.json'
DEFAULT_TOLERANCE_CM = 0.015


def preset_file_path() -> Path:
    """Gibt den benutzerspezifischen, auch für spätere Versionen stabilen Pfad zurück."""
    base_path = os.environ.get('APPDATA')
    if base_path:
        return Path(base_path) / 'PrintThread Wizard' / FILE_NAME
    return Path.home() / '.printthread-wizard' / FILE_NAME


def save_thread_preset(name: str, note: str, settings: dict) -> dict:
    """Hängt einen benannten Gewinde-Datensatz an die lokale Preset-Liste an."""
    clean_name = name.strip()
    clean_note = note.strip()
    if not clean_name:
        raise ValueError(tr('name_required'))
    if len(clean_name) > 100:
        raise ValueError(tr('name_long'))
    if len(clean_note) > 500:
        raise ValueError(tr('note_long'))
    settings = _validate_settings(settings, clean_name)

    path = preset_file_path()
    data = _read_storage(path)
    preset = {
        'id': str(uuid4()),
        'name': clean_name,
        'note': clean_note,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'settings': settings,
    }
    data['presets'].append(preset)

    _write_storage(path, data)
    return preset


def load_thread_presets() -> list[dict]:
    """Lädt die Presets alphabetisch nach Bezeichner und anschließend Erstellzeit."""
    presets = list(_read_storage(preset_file_path())['presets'])
    return sorted(
        presets,
        key=lambda preset: (
            str(preset.get('name', '')).casefold(),
            str(preset.get('created_at', '')),
        ),
    )


def load_default_tolerance() -> float:
    data = _read_storage(preset_file_path())
    value = data.get('preferences', {}).get('default_tolerance_cm', DEFAULT_TOLERANCE_CM)
    try:
        return float(value)
    except (TypeError, ValueError):
        return DEFAULT_TOLERANCE_CM


def save_default_tolerance(value: float) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(tr('default_negative'))
    path = preset_file_path()
    data = _read_storage(path)
    data.setdefault('preferences', {})['default_tolerance_cm'] = value
    _write_storage(path, data)


def delete_thread_preset(preset_id: str) -> bool:
    path = preset_file_path()
    data = _read_storage(path)
    original_count = len(data['presets'])
    data['presets'] = [
        preset for preset in data['presets'] if preset.get('id') != preset_id
    ]
    if len(data['presets']) == original_count:
        return False
    _write_storage(path, data)
    return True


def export_thread_presets(path: str) -> int:
    data = _read_storage(preset_file_path())
    export_data = {
        'schema_version': SCHEMA_VERSION,
        'exported_at': datetime.now(timezone.utc).isoformat(),
        'presets': data['presets'],
        'preferences': data.get('preferences', {}),
    }
    Path(path).write_text(
        json.dumps(export_data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    return len(export_data['presets'])


def import_thread_presets(path: str) -> int:
    try:
        imported = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(tr('import_unreadable', error=error)) from error
    if not isinstance(imported, dict) or imported.get('schema_version') != SCHEMA_VERSION:
        raise ValueError(tr('import_version'))
    presets = imported.get('presets')
    if not isinstance(presets, list):
        raise ValueError(tr('import_list'))

    normalized = []
    for preset in presets:
        if not isinstance(preset, dict) or not str(preset.get('name', '')).strip():
            raise ValueError(tr('import_name'))
        if not isinstance(preset.get('settings'), dict):
            raise ValueError(tr("import_parameters", name=preset.get("name", "")))
        entry = dict(preset)
        entry['settings'] = _validate_settings(preset['settings'], preset['name'])
        entry['id'] = str(entry.get('id') or uuid4())
        entry['name'] = str(entry['name']).strip()
        entry['note'] = str(entry.get('note', '')).strip()
        if len(entry['name']) > 100:
            raise ValueError(tr('name_long'))
        if len(entry['note']) > 500:
            raise ValueError(tr('note_long'))
        entry['created_at'] = str(
            entry.get('created_at') or datetime.now(timezone.utc).isoformat()
        )
        normalized.append(entry)

    _validate_preferences(imported.get('preferences', {}))

    storage_path = preset_file_path()
    data = _read_storage(storage_path)
    merged = {str(preset.get('id')): preset for preset in data['presets']}
    for preset in normalized:
        merged[preset['id']] = preset
    data['presets'] = list(merged.values())
    if isinstance(imported.get('preferences'), dict):
        data['preferences'] = imported['preferences']
    _write_storage(storage_path, data)
    return len(normalized)


def _write_storage(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix('.tmp')
    temporary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8'
    )
    temporary_path.replace(path)


def _read_storage(path: Path) -> dict:
    if not path.exists():
        return {'schema_version': SCHEMA_VERSION, 'presets': []}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(tr('storage_unreadable', error=error)) from error

    if not isinstance(data, dict) or data.get('schema_version') != SCHEMA_VERSION or not isinstance(data.get('presets'), list):
        raise ValueError(tr('storage_format'))
    _validate_preferences(data.get('preferences', {}))
    for preset in data['presets']:
        if not isinstance(preset, dict) or not isinstance(preset.get('name'), str):
            raise ValueError(tr('storage_format'))
        _validate_settings(preset.get('settings'), preset['name'])
    return data


def _validate_preferences(preferences):
    if not isinstance(preferences, dict):
        raise ValueError(tr('storage_format'))
    value = preferences.get('default_tolerance_cm', DEFAULT_TOLERANCE_CM)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(tr('default_negative'))


def _validate_settings(settings, name):
    """Validate portable schema-1 settings; absent legacy options retain defaults."""
    from .thread_parameters import ThreadParameters
    try:
        if settings['calculation_mode'] not in ('iso_metric', 'free'):
            raise ValueError()
        values = [settings[key] for key in (
            'flank_angle_rad', 'thread_depth_cm', 'pitch_cm', 'fillet_radius_cm')]
        values += [settings.get('tolerance_cm', 0.0), settings.get('chamfer_extra_cm', 0.0)]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
            raise ValueError()
        range_values = [settings.get('start_offset_cm', 0.0), settings.get('thread_length_cm', 1.0)]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in range_values):
            raise ValueError()
        if ThreadParameters(object(), (), *values, handedness=settings.get('handedness', 'right'),
                            clearance_distribution=settings.get('clearance_distribution', 'balanced'),
                            full_length=settings.get('full_length', True),
                            start_offset=range_values[0], thread_length=range_values[1]).validation_errors():
            raise ValueError()
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ValueError(tr('import_parameters', name=name)) from None
    partner_values = (settings.get('partner_start_offset_cm', 0.0),
                      settings.get('partner_thread_length_cm', 1.0))
    if (type(settings.get('pair_mode', False)) is not bool
            or type(settings.get('partner_full_length', True)) is not bool
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) for v in partner_values)
            or partner_values[0] < 0 or partner_values[1] <= 0):
        raise ValueError(tr('import_parameters', name=name))
    return dict(settings)
