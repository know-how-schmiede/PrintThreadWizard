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
    handedness: str = 'right'
    full_length: bool = True
    start_offset: float = 0.0
    thread_length: float = 1.0
    start_edge: Any = None

    def axial_range(self, available_length: float, from_end: bool = False) -> tuple[float, float]:
        """Visible bounds in cm, independent of cylinder surface orientation."""
        if not math.isfinite(available_length) or available_length <= 0:
            raise ValueError(tr('range_invalid'))
        if self.full_length:
            return 0.0, available_length
        if (not math.isfinite(self.start_offset) or not math.isfinite(self.thread_length)
                or self.start_offset < 0 or self.thread_length <= 0
                or self.start_offset + self.thread_length > available_length + 1e-7):
            raise ValueError(tr('range_invalid'))
        end = min(self.start_offset + self.thread_length, available_length)
        return ((available_length - end, available_length - self.start_offset)
                if from_end else (self.start_offset, end))

    @property
    def signed_pitch(self) -> float:
        """Signed helix pitch; public pitch remains a positive axial distance."""
        return -self.pitch if self.handedness == 'left' else self.pitch

    def helix_turns(self, length: float) -> float:
        """Fusion requires a positive turn count for either handedness."""
        return length / self.pitch

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
        if self.handedness not in ('right', 'left'):
            errors.append(tr('direction_invalid'))
        if type(self.full_length) is not bool:
            errors.append(tr('range_invalid'))
        if (not math.isfinite(self.start_offset) or not math.isfinite(self.thread_length)
                or self.start_offset < 0 or self.thread_length <= 0):
            errors.append(tr('range_invalid'))
        if not all(math.isfinite(value) for value in (
            self.flank_angle, self.thread_depth, self.pitch, self.fillet_radius,
            self.tolerance, self.chamfer_extra
        )):
            return [tr('numeric_finite')]
        if self.face is None:
            errors.append(tr('face_required'))
        if not 0 < self.flank_angle < math.pi:
            errors.append(tr('angle_invalid'))
        if not math.isfinite(self.thread_depth) or self.thread_depth <= 0:
            errors.append(tr('depth_positive'))
        if not math.isfinite(self.pitch) or self.pitch <= 0:
            errors.append(tr('pitch_positive'))
        if not math.isfinite(self.fillet_radius) or self.fillet_radius < 0:
            errors.append(tr('fillet_negative'))
        if not math.isfinite(self.tolerance) or self.tolerance < 0:
            errors.append(tr('tolerance_negative'))
        if not math.isfinite(self.chamfer_extra) or self.chamfer_extra < 0:
            errors.append(tr('chamfer_extra_invalid'))

        if errors:
            return errors

        half_profile_width = self.sharp_profile_depth * math.tan(self.flank_angle / 2)
        if self.pitch > 0 and 2 * half_profile_width >= self.pitch:
            errors.append(tr('profile_wide'))
        if self.fillet_radius > 0 and self.fillet_radius >= self.thread_depth:
            errors.append(tr('fillet_large'))
        return errors
