"""Constant Velocity motion profile.

Displacement: s = t
Velocity:     v = 1
Acceleration: a = 0
Jerk:         j = 0

Simplest profile. Infinite jerk at entry/exit points (velocity discontinuity).
Use with caution - only suitable for low-speed applications.
"""

from .base import MotionProfile
from .registry import register


@register
class ConstantVelocity(MotionProfile):

    @property
    def name(self) -> str:
        return "Constant Velocity"

    @property
    def category(self) -> str:
        return "standard"

    def displacement(self, t: float) -> float:
        return t

    def velocity(self, t: float) -> float:
        return 1.0

    def acceleration(self, t: float) -> float:
        return 0.0

    def jerk(self, t: float) -> float:
        return 0.0
