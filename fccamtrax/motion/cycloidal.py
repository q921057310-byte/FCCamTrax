"""Cycloidal motion profile.

Displacement: s = t - sin(2*pi*t) / (2*pi)
Velocity:     v = 1 - cos(2*pi*t)
Acceleration: a = 2*pi * sin(2*pi*t)
Jerk:         j = 4*pi^2 * cos(2*pi*t)

Zero jerk at both ends. Most commonly used in high-speed cams.
"""

import math
from .base import MotionProfile
from .registry import register


@register
class Cycloidal(MotionProfile):

    @property
    def name(self) -> str:
        return "Cycloidal"

    @property
    def category(self) -> str:
        return "standard"

    def displacement(self, t: float) -> float:
        return t - math.sin(2 * math.pi * t) / (2 * math.pi)

    def velocity(self, t: float) -> float:
        return 1 - math.cos(2 * math.pi * t)

    def acceleration(self, t: float) -> float:
        return 2 * math.pi * math.sin(2 * math.pi * t)

    def jerk(self, t: float) -> float:
        return 4 * math.pi**2 * math.cos(2 * math.pi * t)
