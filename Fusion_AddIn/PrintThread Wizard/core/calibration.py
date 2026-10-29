from dataclasses import dataclass
import math
from ..localization import translate as tr


@dataclass(frozen=True)
class CalibrationSeries:
    """Lengths in cm; clearance is the total radial gap, all on the rings."""
    diameter: float = 2.0
    pitch: float = .2
    length: float = .8
    clearances: tuple = (.01, .015, .02, .025, .03)
    handedness: str = 'right'
    wall: float = .3

    def validate(self):
        numbers = (self.diameter, self.pitch, self.length, self.wall, *self.clearances)
        if (any(isinstance(v, bool) or not isinstance(v, (int, float))
                or not math.isfinite(v) for v in numbers)
                or min(self.diameter, self.pitch, self.length, self.wall) <= 0
                or self.handedness not in ('right', 'left')
                or not 1 <= len(self.clearances) <= 12
                or any(v < 0 for v in self.clearances)
                or len(set(self.clearances)) != len(self.clearances)):
            raise ValueError(tr('cal_invalid'))
        from .iso_metric import radial_thread_depth
        if (radial_thread_depth(self.pitch, True) >= self.diameter / 2
                or self.wall <= max(self.clearances) + radial_thread_depth(self.pitch, False)
                or self.length < self.pitch * 2):
            raise ValueError(tr('cal_invalid'))
        return self

    def specimens(self):
        self.validate()
        spacing = self.diameter + 2 * self.wall + .5
        return [('REF', 0.0, 0.0)] + [
            (f'R{i + 1:02d} {gap * 10:.3f} mm', gap, (i + 1) * spacing)
            for i, gap in enumerate(self.clearances)]


def validate_print_profile(profile):
    """Portable process metadata, deliberately independent of geometry presets."""
    if not isinstance(profile, dict):
        raise ValueError(tr('profile_invalid'))
    result = dict(profile)
    for key in ('name', 'printer', 'material', 'orientation', 'note'):
        value = result.get(key, '')
        if not isinstance(value, str) or len(value) > (500 if key == 'note' else 100):
            raise ValueError(tr('profile_invalid'))
        result[key] = value.strip()
    if not result['name'] or result.get('clearance_distribution') not in ('internal', 'external', 'balanced'):
        raise ValueError(tr('profile_invalid'))
    for key in ('nozzle_cm', 'layer_height_cm', 'tolerance_cm',
                'diameter_min_cm', 'diameter_max_cm', 'pitch_min_cm', 'pitch_max_cm'):
        value = result.get(key)
        optional = key.startswith(('diameter_', 'pitch_'))
        if optional and value is None:
            result[key] = None
            continue
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0
                or (key != 'tolerance_cm' and value == 0)):
            raise ValueError(tr('profile_invalid'))
    for prefix in ('diameter', 'pitch'):
        low, high = result[prefix + '_min_cm'], result[prefix + '_max_cm']
        if low is not None and high is not None and low > high:
            raise ValueError(tr('profile_invalid'))
    return result


def profile_matches(profile, diameter, pitch):
    profile = validate_print_profile(profile)
    return all((profile[p + '_min_cm'] is None or value >= profile[p + '_min_cm'])
               and (profile[p + '_max_cm'] is None or value <= profile[p + '_max_cm'])
               for p, value in (('diameter', diameter), ('pitch', pitch)))
