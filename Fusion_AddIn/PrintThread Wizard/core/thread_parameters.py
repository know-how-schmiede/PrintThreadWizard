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
            errors.append('Eine Zylinderfläche muss ausgewählt werden.')
        if not 0 < self.flank_angle < math.pi:
            errors.append('Der Flankenwinkel muss zwischen 0° und 180° liegen.')
        if self.thread_depth <= 0:
            errors.append('Die Gewindetiefe muss größer als 0 sein.')
        if self.pitch <= 0:
            errors.append('Die Steigung muss größer als 0 sein.')
        if self.fillet_radius < 0:
            errors.append('Der Verrundungsradius darf nicht negativ sein.')

        half_profile_width = self.sharp_profile_depth * math.tan(self.flank_angle / 2)
        if self.pitch > 0 and 2 * half_profile_width >= self.pitch:
            errors.append('Das Gewindeprofil ist für diese Steigung zu breit.')
        if self.fillet_radius > 0 and self.fillet_radius >= self.thread_depth:
            errors.append('Der Verrundungsradius muss kleiner als die Gewindetiefe sein.')
        return errors
