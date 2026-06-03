"""3-4-5 Polynomial motion profile.

Displacement: s = 10*t^3 - 15*t^4 + 6*t^5
Velocity:     v = 30*t^2 - 60*t^3 + 30*t^4
Acceleration: a = 60*t - 180*t^2 + 120*t^3
Jerk:         j = 60 - 360*t + 360*t^2

Zero jerk at both ends. Continuous acceleration. Very smooth.
"""

from .base import MotionProfile
from .registry import register


@register
class Polynomial345(MotionProfile):

    @property
    def name(self) -> str:
        return "3-4-5 Polynomial"

    @property
    def category(self) -> str:
        return "polynomial"

    def displacement(self, t: float) -> float:
        return 10*t**3 - 15*t**4 + 6*t**5

    def velocity(self, t: float) -> float:
        return 30*t**2 - 60*t**3 + 30*t**4

    def acceleration(self, t: float) -> float:
        return 60*t - 180*t**2 + 120*t**3

    def jerk(self, t: float) -> float:
        return 60 - 360*t + 360*t**2
