"""Simple Harmonic motion profile.

Displacement: s = (1 - cos(pi*t)) / 2
Velocity:     v = pi/2 * sin(pi*t)
Acceleration: a = pi^2/2 * cos(pi*t)
Jerk:         j = -pi^3/2 * sin(pi*t)

Simple, but has impact at stroke ends (infinite jerk at boundaries).
"""

import math
from .base import MotionProfile
from .registry import register


@register
class Harmonic(MotionProfile):

    @property
    def name(self) -> str:
        return "Harmonic"

    @property
    def category(self) -> str:
        return "standard"

    def displacement(self, t: float) -> float:
        return (1 - math.cos(math.pi * t)) / 2

    def velocity(self, t: float) -> float:
        return (math.pi / 2) * math.sin(math.pi * t)

    def acceleration(self, t: float) -> float:
        return (math.pi**2 / 2) * math.cos(math.pi * t)

    def jerk(self, t: float) -> float:
        return -(math.pi**3 / 2) * math.sin(math.pi * t)
