"""凸轮分析模块。"""

from __future__ import annotations
import math
from dataclasses import dataclass, field

from ..motion.registry import get as get_motion
from ..geometry.follower import CamParams, FollowerParams, FollowerType
from ..geometry.base import CamBuilder


@dataclass
class AnalysisResult:
    """分析结果容器。"""
    angles: list[float] = field(default_factory=list)
    displacement: list[float] = field(default_factory=list)
    velocity: list[float] = field(default_factory=list)
    acceleration: list[float] = field(default_factory=list)
    jerk: list[float] = field(default_factory=list)
    pressure_angle: list[float] = field(default_factory=list)
    torque: list[float] = field(default_factory=list)
    contact_stress: list[float] = field(default_factory=list)
    normal_force: list[float] = field(default_factory=list)
    curvature: list[float] = field(default_factory=list)


class CamAnalyst:
    """计算凸轮性能指标。"""

    SPRING_FORCE = 10.0
    CAM_SPEED = 1000.0
    YOUNGS_MODULUS = 210000

    @staticmethod
    def analyze(cam_params: CamParams, follower_params: FollowerParams) -> AnalysisResult:
        """运行完整分析。"""
        result = AnalysisResult()
        n_points = max(int(360 * cam_params.points_per_degree), 36)
        result.angles = [i * 360.0 / n_points for i in range(n_points)]

        builder = CamBuilder.create_builder(cam_params, follower_params)
        lifts = builder._motion_lifts(n_points)

        # 位移
        result.displacement = lifts

        # 速度、加速度、跃度（数值微分）
        dtheta = 2 * math.pi / n_points
        for i in range(n_points):
            idx_prev = (i - 1) % n_points
            idx_next = (i + 1) % n_points
            v = (lifts[idx_next] - lifts[idx_prev]) / (2 * dtheta)
            result.velocity.append(v)

        for i in range(n_points):
            idx_prev = (i - 1) % n_points
            idx_next = (i + 1) % n_points
            a = (result.velocity[idx_next] - result.velocity[idx_prev]) / (2 * dtheta)
            result.acceleration.append(a)

        for i in range(n_points):
            idx_prev = (i - 1) % n_points
            idx_next = (i + 1) % n_points
            j = (result.acceleration[idx_next] - result.acceleration[idx_prev]) / (2 * dtheta)
            result.jerk.append(j)

        # 压力角
        result.pressure_angle = builder.pressure_angles()

        # 曲率半径
        pitch = builder.pitch_curve_points()
        result.curvature = CamAnalyst._curvature_radius(pitch)

        return result

    @staticmethod
    def _curvature_radius(points):
        n = len(points)
        radii = []
        for i in range(n):
            p0 = points[(i - 1) % n]
            p1 = points[i]
            p2 = points[(i + 1) % n]
            a = math.sqrt((p1[0]-p0[0])**2 + (p1[1]-p0[1])**2)
            b = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            c = math.sqrt((p2[0]-p0[0])**2 + (p2[1]-p0[1])**2)
            s = (a + b + c) / 2
            area_sq = s * (s-a) * (s-b) * (s-c)
            if area_sq <= 0:
                radii.append(float('inf'))
            else:
                radii.append((a * b * c) / (4 * math.sqrt(area_sq)))
        return radii
