from dataclasses import dataclass, replace
import math
from ..localization import translate as tr


def parse_clearances(text):
    try:
        return tuple(float(value.strip().replace(',', '.')) / 10 for value in text.split(';'))
    except (AttributeError, ValueError, TypeError, OverflowError):
        raise ValueError(tr('cal_invalid')) from None


def clearance_label(gap_cm):
    whole, fraction = f'{gap_cm * 10:.6f}'.split('.')
    return whole + '.' + fraction.rstrip('0').ljust(2, '0')


@dataclass(frozen=True)
class CalibrationSpecimen:
    pair_id: str
    clearance: float
    x: float
    y: float
    is_external: bool

    @property
    def label(self):
        return f'{self.pair_id}-{"A" if self.is_external else "I"} {clearance_label(self.clearance)} mm'


@dataclass(frozen=True)
class CalibrationSeries:
    """Lengths in cm; each gap gets a dedicated matching pair."""
    diameter: float = 2.0
    pitch: float = .2
    length: float = .8
    clearances: tuple = (.01, .015, .02, .025, .03)
    handedness: str = 'right'
    wall: float = .3
    clearance_distribution: str = 'balanced'
    engrave: bool = True
    text_height: float = .12
    mark_depth: float = .03

    def validate(self):
        numbers = (self.diameter, self.pitch, self.length, self.wall,
                   self.text_height, self.mark_depth, *self.clearances)
        if (any(isinstance(v, bool) or not isinstance(v, (int, float))
                or not math.isfinite(v) for v in numbers)
                or min(self.diameter, self.pitch, self.length, self.wall) <= 0
                or self.handedness not in ('right', 'left')
                or self.clearance_distribution not in ('balanced', 'internal', 'external')
                or type(self.engrave) is not bool
                or not 1 <= len(self.clearances) <= 12
                or any(v < 0 for v in self.clearances)
                or len(set(self.clearances)) != len(self.clearances)):
            raise ValueError(tr('cal_invalid'))
        from .iso_metric import radial_thread_depth
        from .thread_parameters import ThreadParameters
        p = ThreadParameters(object(), (), math.pi / 3, radial_thread_depth(self.pitch, True),
                             self.pitch, 0, clearance_distribution=self.clearance_distribution)
        internal_offset = max(replace(p, tolerance=gap).tolerance_radius_offset(False)
                              for gap in self.clearances)
        if (radial_thread_depth(self.pitch, True) >= self.diameter / 2
                or self.wall <= internal_offset + radial_thread_depth(self.pitch, False)
                or self.length < self.pitch * 2):
            raise ValueError(tr('cal_invalid'))
        if len({clearance_label(gap) for gap in self.clearances}) != len(self.clearances):
            raise ValueError(tr('cal_mark_invalid'))
        for gap in self.clearances:
            corrected = replace(p, tolerance=gap)
            if self.diameter / 2 + corrected.tolerance_radius_offset(True) <= corrected.thread_depth:
                raise ValueError(tr('cal_invalid'))
            if self.engrave:
                if (self.text_height <= 0 or self.mark_depth <= 0
                        or self.mark_depth >= min(self.length / 4, self.wall / 2)):
                    raise ValueError(tr('cal_mark_invalid'))
                for external in (True, False):
                    self.marking_rectangle(gap, external)
        return self

    def specimens(self):
        self.validate()
        spacing = self.diameter + 2 * self.wall + .5
        return tuple(CalibrationSpecimen(f'P{i + 1:02d}', gap, i * spacing,
                                        0 if external else spacing, external)
                     for i, gap in enumerate(self.clearances) for external in (True, False))

    def marking_rectangle(self, gap, external):
        """A conservative text box contained in solid material away from threads."""
        from .iso_metric import radial_thread_depth
        from .thread_parameters import ThreadParameters
        p = ThreadParameters(object(), (), math.pi / 3, radial_thread_depth(self.pitch, external),
                             self.pitch, 0, tolerance=gap,
                             clearance_distribution=self.clearance_distribution)
        radius = self.diameter / 2 + p.tolerance_radius_offset(external)
        margin = .02  # 0.2 mm from the safe material boundary.
        inner = 0 if external else radius + margin
        outer = radius - p.thread_depth - margin if external else self.diameter / 2 + self.wall - margin
        width = len(clearance_label(gap)) * self.text_height * .9 + .04
        height = self.text_height * 1.4
        center_y = 0 if external else (inner + outer) / 2
        box = (-width / 2, center_y - height / 2, width / 2, center_y + height / 2)
        if not rectangle_in_material(box, inner, outer):
            raise ValueError(tr('cal_mark_invalid'))
        return box, inner, outer


def rectangle_in_material(box, inner, outer):
    x0, y0, x1, y1 = box
    nearest_x = max(x0, min(0, x1))
    nearest_y = max(y0, min(0, y1))
    return (x1 > x0 and y1 > y0 and outer > inner >= 0
            and math.hypot(nearest_x, nearest_y) >= inner - 1e-9
            and max(math.hypot(x, y) for x in (x0, x1) for y in (y0, y1)) <= outer + 1e-9)


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
