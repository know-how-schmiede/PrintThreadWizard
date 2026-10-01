from ..localization import translate as tr

from dataclasses import dataclass
import math
from typing import Any


@dataclass(frozen=True)
class ThreadParameters:
    """Vom Dialog gelieferte, in Fusion-internen Einheiten gespeicherte Werte."""

    face: Any
    chamfer_edges: tuple[Any, ...]
    flank_angle: float
    thread_depth: float
    pitch: float
    fillet_radius: float
    tolerance: float = 0.0
    chamfer_extra: float = 0.0

    def tolerance_radius_offset(self, is_external: bool) -> float:
        """Versetzt das gesamte Gewinde um das halbe gewünschte Gesamtspiel."""
        half_clearance = self.tolerance / 2
        return -half_clearance if is_external else half_clearance

    @property
    def sharp_profile_depth(self) -> float:
        """Profiltiefe vor dem Abrunden, damit die fertige Tiefe erhalten bleibt."""
        if self.fillet_radius <= 0 or not 0 < self.flank_angle < math.pi:
            return self.thread_depth
        correction = self.fillet_radius * (1 / math.sin(self.flank_angle / 2) - 1)
        return self.thread_depth + correction

    def validation_errors(self) -> list[str]:
        errors = []
        if self.face is None:
            errors.append(tr('face_required'))
        if not 0 < self.flank_angle < math.pi:
            errors.append(tr('angle_invalid'))
        if self.thread_depth <= 0:
            errors.append(tr('depth_positive'))
        if self.pitch <= 0:
            errors.append(tr('pitch_positive'))
        if self.fillet_radius < 0:
            errors.append(tr('fillet_negative'))
        if self.tolerance < 0:
            errors.append(tr('tolerance_negative'))
        if not math.isfinite(self.chamfer_extra) or self.chamfer_extra < 0:
            errors.append(tr('chamfer_extra_invalid'))

        half_profile_width = self.sharp_profile_depth * math.tan(self.flank_angle / 2)
        if self.pitch > 0 and 2 * half_profile_width >= self.pitch:
            errors.append(tr('profile_wide'))
        if self.fillet_radius > 0 and self.fillet_radius >= self.thread_depth:
            errors.append(tr('fillet_large'))
        return errors
