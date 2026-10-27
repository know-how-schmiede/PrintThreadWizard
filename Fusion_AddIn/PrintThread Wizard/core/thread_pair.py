"""Pair compatibility checks without Fusion dependencies."""
import math

from ..localization import translate as tr


def validate_pair(first, second):
    """Accept analyzed cylinders on separate native bodies, in any position."""
    if first.body == second.body:
        raise ValueError(tr('pair_bodies'))
    if first.is_external == second.is_external:
        raise ValueError(tr('pair_types'))
    if not all(math.isfinite(c.radius) and c.radius > 0 for c in (first, second)):
        raise ValueError(tr('pair_diameter'))
    if not math.isclose(first.radius, second.radius, rel_tol=1e-6, abs_tol=1e-7):
        raise ValueError(tr('pair_diameter'))
