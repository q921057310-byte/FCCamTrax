"""修正正弦运动曲线（三段式，C1 连续，无速度跳跃）。

三段：
  0 ≤ t ≤ B:    正弦加速段，v: 0→1/(1-B)
  B ≤ t ≤ 1-B:  匀速段，v = 1/(1-B)
  1-B ≤ t ≤ 1:  三次 Hermite 减速段，v: 1/(1-B)→0
"""

import math
from .base import MotionProfile
from .registry import register


@register
class ModifiedSine(MotionProfile):

    def __init__(self, B: float = 0.25):
        self._B = B

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

    def _seg3(self, t: float) -> float:
        B = self._B
        u = (t - (1 - B)) / B
        s_start = 1 - B / (2 * (1 - B))
        ds_start = B / (1 - B)
        s_end = 1.0
        ds_end = 0.0
        h00 = 2 * u ** 3 - 3 * u ** 2 + 1
        h10 = u ** 3 - 2 * u ** 2 + u
        h01 = -2 * u ** 3 + 3 * u ** 2
        h11 = u ** 3 - u ** 2
        return h00 * s_start + h10 * ds_start + h01 * s_end + h11 * ds_end

    def _seg3_vel(self, t: float) -> float:
        B = self._B
        u = (t - (1 - B)) / B
        s_start = 1 - B / (2 * (1 - B))
        ds_start = B / (1 - B)
        s_end = 1.0
        ds_end = 0.0
        dh00 = 6 * u ** 2 - 6 * u
        dh10 = 3 * u ** 2 - 4 * u + 1
        dh01 = -6 * u ** 2 + 6 * u
        dh11 = 3 * u ** 2 - 2 * u
        return (dh00 * s_start + dh10 * ds_start + dh01 * s_end + dh11 * ds_end) / B

    def displacement(self, t: float) -> float:
        B = self._B
        if t < B:
            return self._seg1_disp(t)
        elif t < 1 - B:
            return B / (2 * (1 - B)) + (t - B) / (1 - B)
        else:
            return self._seg3(t)

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
            u = (t - (1 - B)) / B
            s_start = 1 - B / (2 * (1 - B))
            ds_start = B / (1 - B)
            s_end = 1.0
            ds_end = 0.0
            d2h00 = 12 * u - 6
            d2h10 = 6 * u - 4
            d2h01 = -12 * u + 6
            d2h11 = 6 * u - 2
            return (d2h00 * s_start + d2h10 * ds_start + d2h01 * s_end + d2h11 * ds_end) / (B * B)
