import math


ISO_FLANK_ANGLE = math.radians(60)
INTERNAL_RADIAL_DEPTH_FACTOR = 0.541266
EXTERNAL_RADIAL_DEPTH_FACTOR = 0.6134345


def radial_thread_depth(pitch: float, is_external: bool) -> float:
    """Berechnet die radiale ISO-Profiltiefe aus der Steigung."""
    factor = (
        EXTERNAL_RADIAL_DEPTH_FACTOR
        if is_external
        else INTERNAL_RADIAL_DEPTH_FACTOR
    )
    return pitch * factor


def minor_diameter(nominal_diameter: float, pitch: float, is_external: bool) -> float:
    return nominal_diameter - 2 * radial_thread_depth(pitch, is_external)
