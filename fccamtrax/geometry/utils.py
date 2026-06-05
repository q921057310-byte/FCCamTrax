"""Geometric utility functions for cam profile computation."""

from __future__ import annotations
import math


def polar_to_cartesian(r: float, theta: float) -> tuple[float, float]:
    """Convert polar coordinates (r, theta) to Cartesian (x, y)."""
    return r * math.cos(theta), r * math.sin(theta)


def pressure_angle_oncenter(rb: float, h: float, dh_dtheta: float) -> float:
    """On-center translating: α = atan(|dh/dθ| / (rb+h))."""
    denom = max(rb + h, 1e-12)
    return math.degrees(math.atan2(abs(dh_dtheta), denom))


def pressure_angle_offcenter(rb: float, h: float, e: float, dh_dtheta: float) -> float:
    """Off-center translating: α = atan(|dh/dθ| / sqrt((rb+h)² - e²))."""
    r_pitch = rb + h
    denom = math.sqrt(max(r_pitch * r_pitch - e * e, 1e-12))
    return math.degrees(math.atan2(abs(dh_dtheta), denom))


def pressure_angle_oscillating(rb: float, h: float, L: float, dh_dtheta: float) -> float:
    """Oscillating: α = atan(|L·dψ/dθ| / (rb+h)) where dψ/dθ = (1/L)·dh/dθ."""
    if L < 1e-12:
        return 90.0
    denom = max(rb + h, 1e-12)
    dpsi_dtheta = dh_dtheta / L
    return math.degrees(math.atan2(abs(L * dpsi_dtheta), denom))


def pressure_angle_linear_cyl(R: float, dh_dtheta: float) -> float:
    """Linear/cylindrical: α = atan(|dh/dθ| / R)."""
    denom = max(R, 1e-12)
    return math.degrees(math.atan2(abs(dh_dtheta), denom))
