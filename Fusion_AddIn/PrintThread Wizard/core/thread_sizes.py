"""Small metric selection aid. Values in mm at this data boundary only.

Source: Bossard, Metric ISO threads, F-en-2023.05, coarse selection series
and fine-thread limits. See doku/groessenhilfe-0.9.5.md for source and scope.
This is not a tolerance table or a promise of standard-compliant geometry.
"""
import math

# diameter: (coarse pitch, selected fine pitches). Intentionally not exhaustive.
METRIC_SIZES = {
    3: (.5, ()), 4: (.7, ()), 5: (.8, ()), 6: (1, ()),
    8: (1.25, (1,)), 10: (1.5, (1, 1.25)),
    12: (1.75, (1.25, 1.5)), 14: (2, (1.5,)),
    16: (2, (1.5,)), 18: (2.5, (1.5, 2)),
    20: (2.5, (1.5, 2)), 24: (3, (2,)), 30: (3.5, (2,)), 36: (4, (3,)),
}


def size_options():
    return tuple((diameter / 10, pitch / 10, kind)
                 for diameter, (coarse, fine) in METRIC_SIZES.items()
                 for pitch, kind in [(coarse, 'coarse')] + [(p, 'fine') for p in fine])


def diameter_matches(actual_cm, nominal_cm):
    """Comparison threshold of 0.01 mm is a UI warning threshold, not a fit."""
    return (all(math.isfinite(v) and v > 0 for v in (actual_cm, nominal_cm))
            and abs(actual_cm - nominal_cm) <= .001 + 1e-9)
