"""Bounded schematic line geometry, using only local cm coordinates."""
import math


def preview_lines(start, end, radial, radius, parameters):
    """Return range, directional helix and sharp profile envelope segments.

    The helix is limited to one turn regardless of thread length. Rounded root
    geometry and chamfers are deliberately omitted from this selection aid.
    """
    def add(a, b): return tuple(x + y for x, y in zip(a, b))
    def sub(a, b): return tuple(x - y for x, y in zip(a, b))
    def scale(v, s): return tuple(x * s for x in v)
    def norm(v): return math.sqrt(sum(x * x for x in v))
    length = norm(sub(end, start))
    if length <= 0 or radius <= 0 or not all(math.isfinite(v) for v in (*start, *end, *radial, radius)):
        raise ValueError('Invalid preview frame')
    axis = scale(sub(end, start), 1 / length)
    radial = scale(radial, 1 / norm(radial))
    tangent = (axis[1]*radial[2]-axis[2]*radial[1],
               axis[2]*radial[0]-axis[0]*radial[2],
               axis[0]*radial[1]-axis[1]*radial[0])
    def point(z, angle, r=radius):
        return add(add(start, scale(axis, z)),
                   add(scale(radial, r * math.cos(angle)), scale(tangent, r * math.sin(angle))))
    extent = [(start, end)]
    for z in (0, length):
        ring = [point(z, 2 * math.pi * i / 48) for i in range(49)]
        extent.extend(zip(ring, ring[1:]))
    for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        extent.append((point(0, angle), point(length, angle)))
    travel = min(length, parameters.pitch)
    sign = -1 if parameters.handedness == 'left' else 1
    curve = [point(travel * i / 64, sign * 2 * math.pi * travel / parameters.pitch * i / 64)
             for i in range(65)]
    direction = list(zip(curve, curve[1:]))
    # Arrow at the end of the one-turn helix.
    tip, before = curve[-1], curve[-3]
    back = sub(before, tip)
    arrow_length = min(radius * .15, travel * .2)
    back = scale(back, arrow_length / norm(back))
    for side in (-1, 1):
        direction.append((tip, add(add(tip, back), scale(radial, side * arrow_length * .4))))
    depth = parameters.sharp_profile_depth
    half_width = depth * math.tan(parameters.flank_angle / 2)
    profile = []
    if half_width * 2 <= length:
        a = point(length / 2 - half_width, 0)
        b = point(length / 2, 0, radius - depth)
        c = point(length / 2 + half_width, 0)
        profile = [(a, b), (b, c), (c, a)]
    return extent, direction, profile
