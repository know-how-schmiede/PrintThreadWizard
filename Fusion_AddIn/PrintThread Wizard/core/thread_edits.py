"""Validated parameter changes shared by M6 trials and restricted editing."""
from dataclasses import replace
import math
from .iso_metric import ISO_FLANK_ANGLE, radial_thread_depth
from ..localization import translate as tr


def validate_trial_changes(changes, full_length):
    if not isinstance(changes, dict) or set(changes) - {'pitch', 'tolerance', 'start_offset', 'thread_length', 'handedness'}:
        raise ValueError(tr('trial_changes_invalid'))
    for key, value in changes.items():
        if key == 'handedness':
            if value not in ('right', 'left'):
                raise ValueError(tr('direction_invalid'))
            continue
        if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                or value < 0 or (key in ('pitch', 'thread_length') and value == 0)):
            raise ValueError(tr('trial_changes_invalid'))
    if full_length and set(changes) & {'start_offset', 'thread_length'}:
        raise ValueError(tr('trial_length_limit'))
    return dict(changes)


def apply_trial_changes(parameters, calculation_mode, changes, is_external):
    changes = validate_trial_changes(changes, parameters.full_length)
    result = replace(parameters, **changes)
    if calculation_mode == 'iso_metric' and 'pitch' in changes:
        result = replace(result, flank_angle=ISO_FLANK_ANGLE,
                         thread_depth=radial_thread_depth(result.pitch, is_external))
    errors = result.validation_errors()
    if errors:
        raise ValueError('\n'.join(errors))
    return result
