"""Geometric utility functions for cam profile computation."""

from __future__ import annotations
import math


def polar_to_cartesian(r: float, theta: float) -> tuple[float, float]:
    """Convert polar coordinates (r, theta) to Cartesian (x, y)."""
    return r * math.cos(theta), r * math.sin(theta)


def offset_curve(points: list[tuple[float, float]],
                 offset: float,
                 closed: bool = True) -> list[tuple[float, float]]:
    """Offset a 2D curve by a fixed distance (positive = outward).

    Computes offset normals at each point using neighboring points.
    """
    n = len(points)
    if n < 2:
        return points[:]

    result = []
    for i in range(n):
        # Tangent from neighbors
        if closed:
            prev = points[(i - 1) % n]
            next_pt = points[(i + 1) % n]
        else:
            prev = points[max(0, i - 1)]
            next_pt = points[min(n - 1, i + 1)]

        dx = next_pt[0] - prev[0]
        dy = next_pt[1] - prev[1]
        length = math.sqrt(dx*dx + dy*dy)
        if length < 1e-12:
            result.append(points[i])
            continue

        # Normal (perpendicular to tangent, rotated 90° CCW)
        nx = -dy / length
        ny = dx / length

        result.append((
            points[i][0] + offset * nx,
            points[i][1] + offset * ny
        ))

    return result


def compute_curvature(points: list[tuple[float, float]]) -> list[float]:
    """Compute signed curvature at each point of a 2D curve.

    Uses Menger curvature: κ = 2·|cross| / (|p0p1|·|p1p2|·|p0p2|)
    Positive = CCW, Negative = CW.
    """
    n = len(points)
    curvatures = []
    for i in range(n):
        p0 = points[(i - 1) % n]
        p1 = points[i]
        p2 = points[(i + 1) % n]

        dx1 = p1[0] - p0[0]
        dy1 = p1[1] - p0[1]
        dx2 = p2[0] - p1[0]
        dy2 = p2[1] - p1[1]

        cross = dx1 * dy2 - dy1 * dx2
        ds1 = math.sqrt(dx1*dx1 + dy1*dy1)
        ds2 = math.sqrt(dx2*dx2 + dy2*dy2)
        ds3 = math.sqrt((p2[0]-p0[0])**2 + (p2[1]-p0[1])**2)

        denom = ds1 * ds2 * ds3
        if denom < 1e-12:
            curvatures.append(0.0)
        else:
            curvatures.append(2.0 * cross / denom)

    return curvatures
