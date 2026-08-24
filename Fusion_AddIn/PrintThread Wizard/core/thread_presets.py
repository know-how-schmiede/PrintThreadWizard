import json
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
        raise ValueError('Bitte einen Gewindebezeichner eingeben.')
    if len(clean_name) > 100:
        raise ValueError('Der Gewindebezeichner darf höchstens 100 Zeichen lang sein.')
    if len(clean_note) > 500:
        raise ValueError('Die Notiz darf höchstens 500 Zeichen lang sein.')

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
    if value < 0:
        raise ValueError('Die Standardtoleranz darf nicht negativ sein.')
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
        raise ValueError(f'Die Importdatei ist nicht lesbar: {error}') from error
    if imported.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('Die Importdatei hat eine nicht unterstützte Formatversion.')
    presets = imported.get('presets')
    if not isinstance(presets, list):
        raise ValueError('Die Importdatei enthält keine gültige Preset-Liste.')

    normalized = []
    for preset in presets:
        if not isinstance(preset, dict) or not str(preset.get('name', '')).strip():
            raise ValueError('Die Importdatei enthält einen Eintrag ohne Bezeichner.')
        if not isinstance(preset.get('settings'), dict):
            raise ValueError(f'Der Eintrag „{preset.get("name", "")}“ enthält keine Parameter.')
        entry = dict(preset)
        entry['id'] = str(entry.get('id') or uuid4())
        entry['name'] = str(entry['name']).strip()
        entry['note'] = str(entry.get('note', '')).strip()
        entry['created_at'] = str(
            entry.get('created_at') or datetime.now(timezone.utc).isoformat()
        )
        normalized.append(entry)

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
        json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    temporary_path.replace(path)


def _read_storage(path: Path) -> dict:
    if not path.exists():
        return {'schema_version': SCHEMA_VERSION, 'presets': []}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f'Die gespeicherte Gewindeliste ist nicht lesbar: {error}') from error

    if data.get('schema_version') != SCHEMA_VERSION or not isinstance(data.get('presets'), list):
        raise ValueError('Die gespeicherte Gewindeliste hat ein unbekanntes Format.')
    return data
