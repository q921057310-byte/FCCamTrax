"""修正正弦运动曲线（三段式，C2 连续）。

三段：
  0 ≤ t ≤ B:      正弦加速段，v: 0→1/(1-B)
  B ≤ t ≤ 1-B:    匀速段，v = 1/(1-B)
  1-B ≤ t ≤ 1:    反向摆线减速段，v: 1/(1-B)→0, a:0→(peak)→0
"""

import math
from .base import MotionProfile
from .registry import register


@register
class ModifiedSine(MotionProfile):

    def __init__(self, B: float = 0.25):
        self._B = max(0.01, min(0.49, B))

    @property
    def name(self) -> str:
        return "Modified Sine"

    @property
    def category(self) -> str:
        return "standard"

    @property
    def params(self) -> dict:
        return {"B": self._B}

    @params.setter
    def params(self, d: dict):
        if "B" in d:
            self._B = max(0.01, min(0.49, d["B"]))

    def _mid_vel(self) -> float:
        return 1 / (1 - self._B)

    def _seg1_disp(self, t: float) -> float:
        B = self._B
        u = t / B
        return B / (2 * (1 - B)) * (u - math.sin(math.pi * u) / math.pi)

    def _seg1_vel(self, t: float) -> float:
        B = self._B
        u = t / B
        return (1 - math.cos(math.pi * u)) / (2 * (1 - B))

    def _seg1_accel(self, t: float) -> float:
        B = self._B
        u = t / B
        return math.pi * math.sin(math.pi * u) / (2 * B * (1 - B))

    def _seg3_disp(self, t: float) -> float:
        B = self._B
        u = (t - (1 - B)) / B
        s_start = 1 - B / (2 * (1 - B))
        return s_start + B / (2 * (1 - B)) * (u + math.sin(math.pi * u) / math.pi)

    def _seg3_vel(self, t: float) -> float:
        B = self._B
        u = (t - (1 - B)) / B
        return (1 + math.cos(math.pi * u)) / (2 * (1 - B))

    def _seg3_accel(self, t: float) -> float:
        B = self._B
        u = (t - (1 - B)) / B
        return -math.pi * math.sin(math.pi * u) / (2 * B * (1 - B))

    def displacement(self, t: float) -> float:
        B = self._B
        if t < B:
            return self._seg1_disp(t)
        elif t < 1 - B:
            return B / (2 * (1 - B)) + (t - B) / (1 - B)
        else:
            return self._seg3_disp(t)

    def velocity(self, t: float) -> float:
        B = self._B
        if t < B:
            return self._seg1_vel(t)
        elif t < 1 - B:
            return self._mid_vel()
        else:
            return self._seg3_vel(t)

    def acceleration(self, t: float) -> float:
        B = self._B
        if t < B:
            return self._seg1_accel(t)
        elif t < 1 - B:
            return 0.0
        else:
            return self._seg3_accel(t)
