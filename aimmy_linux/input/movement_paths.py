"""
Movement path algorithms for Aimmy Linux.
Port of InputLogic/MovementPaths.cs

Provides various mouse movement interpolation methods:
- Cubic Bezier
- Linear (Lerp)
- Exponential
- Adaptive (auto-selects based on distance)
- Perlin Noise (natural-looking jitter)
"""

import math
import random
from typing import Tuple

# Perlin noise permutation table
_perm = list(range(256))
random.shuffle(_perm)
_perm = _perm + _perm  # Duplicate for overflow


def cubic_bezier(
    start: Tuple[int, int],
    end: Tuple[int, int],
    control1: Tuple[int, int],
    control2: Tuple[int, int],
    t: float,
) -> Tuple[int, int]:
    """Cubic Bezier curve interpolation."""
    u = 1 - t
    tt = t * t
    uu = u * u

    x = uu * u * start[0] + 3 * uu * t * control1[0] + 3 * u * tt * control2[0] + tt * t * end[0]
    y = uu * u * start[1] + 3 * uu * t * control1[1] + 3 * u * tt * control2[1] + tt * t * end[1]

    return (int(x), int(y))


def lerp(start: Tuple[int, int], end: Tuple[int, int], t: float) -> Tuple[int, int]:
    """Linear interpolation between two points."""
    x = int(start[0] + (end[0] - start[0]) * t)
    y = int(start[1] + (end[1] - start[1]) * t)
    return (x, y)


def exponential(
    start: Tuple[int, int],
    end: Tuple[int, int],
    t: float,
    exponent: float = 2.0,
) -> Tuple[int, int]:
    """Exponential ease-in interpolation."""
    x = start[0] + (end[0] - start[0]) * math.pow(t, exponent)
    y = start[1] + (end[1] - start[1]) * math.pow(t, exponent)
    return (int(x), int(y))


def adaptive(
    start: Tuple[int, int],
    end: Tuple[int, int],
    t: float,
    threshold: float = 100.0,
) -> Tuple[int, int]:
    """Adaptive interpolation: linear for short distances, bezier for long."""
    distance = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
    if distance < threshold:
        return lerp(start, end, t)
    else:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        control1 = (start[0] + dx // 3, start[1] + dy // 3)
        control2 = (start[0] + 2 * dx // 3, start[1] + 2 * dy // 3)
        return cubic_bezier(start, end, control1, control2, t)


# --- Perlin noise helpers ---

def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp_f(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def _grad(hash_val: int, x: float, y: float) -> float:
    h = hash_val & 15
    u = x if h < 8 else y
    v = y if h < 4 else (x if h == 12 or h == 14 else 0)
    return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)


def _noise(x: float, y: float) -> float:
    """2D Perlin noise."""
    xi = int(math.floor(x)) & 255
    yi = int(math.floor(y)) & 255

    xf = x - math.floor(x)
    yf = y - math.floor(y)

    u = _fade(xf)
    v = _fade(yf)

    a = _perm[xi] + yi
    aa = _perm[a]
    ab = _perm[a + 1]
    b = _perm[xi + 1] + yi
    ba = _perm[b]
    bb = _perm[b + 1]

    return _lerp_f(
        _lerp_f(_grad(_perm[aa], xf, yf), _grad(_perm[ba], xf - 1, yf), u),
        _lerp_f(_grad(_perm[ab], xf, yf - 1), _grad(_perm[bb], xf - 1, yf - 1), u),
        v,
    )


def perlin_noise(
    start: Tuple[int, int],
    end: Tuple[int, int],
    t: float,
    amplitude: float = 10.0,
    frequency: float = 0.1,
) -> Tuple[int, int]:
    """Perlin noise-modulated interpolation for natural-looking movement."""
    base_x = start[0] + (end[0] - start[0]) * t
    base_y = start[1] + (end[1] - start[1]) * t

    noise_x = _noise(t * frequency, 0) * amplitude
    noise_y = _noise(t * frequency, 100) * amplitude

    perp_x = -(end[1] - start[1])
    perp_y = end[0] - start[0]
    perp_length = math.sqrt(perp_x * perp_x + perp_y * perp_y)

    if perp_length > 0:
        perp_x /= perp_length
        perp_y /= perp_length

    final_x = base_x + perp_x * noise_x + noise_y * 0.3
    final_y = base_y + perp_y * noise_x + noise_y * 0.3

    return (int(final_x), int(final_y))


def apply_movement_path(
    start: Tuple[int, int],
    end: Tuple[int, int],
    sensitivity: float,
    path_name: str = "Cubic Bezier",
) -> Tuple[int, int]:
    """Apply the selected movement path algorithm.

    Args:
        start: Starting position (typically (0, 0) for relative movement)
        end: Target position
        sensitivity: Mouse sensitivity from settings (0-1)
        path_name: Name of the movement path algorithm

    Returns:
        New position as (x, y) tuple
    """
    t = 1.0 - sensitivity  # Invert: higher sensitivity = more movement

    if path_name == "Cubic Bezier":
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        c1 = (start[0] + dx // 3, start[1] + dy // 3)
        c2 = (start[0] + 2 * dx // 3, start[1] + 2 * dy // 3)
        return cubic_bezier(start, end, c1, c2, t)
    elif path_name == "Linear":
        return lerp(start, end, t)
    elif path_name == "Exponential":
        return exponential(start, end, t - 0.2, 3.0)
    elif path_name == "Adaptive":
        return adaptive(start, end, t)
    elif path_name == "Perlin Noise":
        return perlin_noise(start, end, t, 20, 0.5)
    else:
        return lerp(start, end, t)
