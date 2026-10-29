"""Versioned document metadata, independent of user preset storage."""
import json
import math
from dataclasses import fields
from uuid import uuid4
from .thread_parameters import ThreadParameters
from ..localization import translate as tr

SCHEMA_VERSION = 1
GROUP = 'PrintThreadWizard'
ATTRIBUTE = 'thread_record'


def parameter_values(parameters):
    return {field.name: getattr(parameters, field.name) for field in fields(parameters)
            if field.name not in ('face', 'chamfer_edges', 'start_edge')}


def make_record(parameters, references, calculation_mode, version):
    record = dict(schema_version=SCHEMA_VERSION, id=str(uuid4()),
                  created_with=version, calculation_mode=calculation_mode,
                  parameters=parameter_values(parameters), references=references)
    return validate_record(record, require_result=False)


def validate_record(record, require_result=True):
    try:
        if (not isinstance(record, dict) or type(record.get('schema_version')) is not int
                or record['schema_version'] != SCHEMA_VERSION
                or not isinstance(record['id'], str) or not record['id']
                or not isinstance(record['created_with'], str)
                or record['calculation_mode'] not in ('free', 'iso_metric')):
            raise ValueError()
        values = record['parameters']
        allowed = set(parameter_values(ThreadParameters(None, (), 1, .1, .3, 0)))
        if not isinstance(values, dict) or set(values) != allowed:
            raise ValueError()
        for key, value in values.items():
            if key not in ('handedness', 'clearance_distribution', 'full_length'):
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError()
        if ThreadParameters(face=object(), chamfer_edges=(), **values).validation_errors():
            raise ValueError()
        refs = record['references']
        if not isinstance(refs, dict):
            raise ValueError()
        required = ('face', 'body', 'component') + (('first_feature', 'result_feature') if require_result else ())
        if any(not isinstance(refs.get(key), str) or not refs[key] for key in required):
            raise ValueError()
        for key in ('occurrence', 'start_edge'):
            if refs.get(key) is not None and (not isinstance(refs[key], str) or not refs[key]):
                raise ValueError()
        if (not isinstance(refs.get('chamfer_edges'), list) or len(refs['chamfer_edges']) > 2
                or any(not isinstance(token, str) or not token for token in refs['chamfer_edges'])):
            raise ValueError()
        if not values['full_length'] and not refs.get('start_edge'):
            raise ValueError()
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ValueError(tr('record_invalid')) from None
    return record


def encode_record(record):
    validate_record(record)
    return json.dumps(record, ensure_ascii=False, allow_nan=False)


def decode_record(value):
    try:
        return validate_record(json.loads(value))
    except (ValueError, TypeError):
        raise ValueError(tr('record_invalid')) from None
