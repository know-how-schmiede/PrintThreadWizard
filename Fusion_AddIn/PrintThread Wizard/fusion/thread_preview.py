"""Disposable viewport graphics only: no sketches, features or B-Rep bodies."""
import adsk.core
import adsk.fusion
from ..core.thread_preview import preview_lines
from .face_analysis import analyze_cylinder
from .thread_geometry import thread_section


class ThreadPreview:
    def __init__(self):
        self.groups = []

    def clear(self):
        for group in self.groups:
            if group.isValid:
                group.deleteMe()
        self.groups.clear()

    def update(self, design, requests):
        self.clear()
        try:
            for parameters in requests:
                cylinder = analyze_cylinder(parameters.face)
                section = thread_section(cylinder, parameters)
                def xyz(v): return (v.x, v.y, v.z)
                sets = preview_lines(xyz(section.axis_start), xyz(section.axis_end),
                                     xyz(cylinder.radial), cylinder.radius +
                                     parameters.tolerance_radius_offset(cylinder.is_external), parameters)
                group = design.rootComponent.customGraphicsGroups.add()
                self.groups.append(group)
                group.isSelectable = False
                occurrence = parameters.face.assemblyContext
                if occurrence is not None:
                    group.transform = occurrence.transform2
                for segments, color in zip(sets, ((0, 180, 255), (255, 150, 0), (220, 70, 220))):
                    if not segments:
                        continue
                    coords = adsk.fusion.CustomGraphicsCoordinates.create(
                        [v for segment in segments for point in segment for v in point])
                    lines = group.addLines(coords, [], False)
                    lines.isSelectable = False
                    lines.weight = 3
                    # Clearance-corrected outlines can lie beneath the original
                    # face. Keep this schematic overlay visible through solids.
                    lines.color = adsk.fusion.CustomGraphicsShowThroughColorEffect.create(
                        adsk.core.Color.create(*color, 255), .8)
        except Exception:
            self.clear()
            raise
