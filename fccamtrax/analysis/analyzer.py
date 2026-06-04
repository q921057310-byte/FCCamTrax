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

    SPRING_FORCE = 10.0       # N — 回程弹簧预紧力
    CAM_SPEED = 1000.0        # rpm
    YOUNGS_MODULUS = 210000   # MPa (钢)
    POISSON_RATIO = 0.3
    CONTACT_WIDTH = 10.0      # mm — 凸轮厚度（接触宽度）

    @staticmethod
    def analyze(cam_params: CamParams, follower_params: FollowerParams) -> AnalysisResult:
        """运行完整分析。"""
        result = AnalysisResult()
        n_points = max(int(360 * cam_params.points_per_degree), 360)
        result.angles = [i * 360.0 / n_points for i in range(n_points)]

        builder = CamBuilder.create_builder(cam_params, follower_params)
        lifts = builder.motion_lifts(n_points)

        result.displacement = lifts

        # 速度、加速度、跃度（数值微分，dθ in rad）
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
        # 如果 builder 没实现，用通用公式
        if not result.pressure_angle:
            rb = cam_params.base_radius
            for i, h in enumerate(lifts):
                idx_next = (i + 1) % n_points
                dh = (lifts[idx_next] - lifts[i]) / dtheta
                denom = max(rb + h, 1e-6)
                result.pressure_angle.append(math.degrees(math.atan2(abs(dh), denom)))

        # 曲率半径
        result.curvature = builder.curvature_radii()

        # 法向力、扭矩、接触应力
        omega = CamAnalyst.CAM_SPEED * 2 * math.pi / 60  # rad/s
        F_spring = CamAnalyst.SPRING_FORCE
        rb = cam_params.base_radius
        roller_r = follower_params.roller_radius

        for i in range(n_points):
            h = lifts[i]
            alpha_rad = math.radians(result.pressure_angle[i]) if i < len(result.pressure_angle) else 0.0
            acc_i = result.acceleration[i] if i < len(result.acceleration) else 0.0

            # 从动件惯性力 (简化: F_inertial = m * a * ω², 假设 m=1kg)
            F_inertial = abs(acc_i) * omega * omega * 0.001  # 转换单位
            # 法向力
            F_normal = (F_spring + F_inertial) / max(math.cos(alpha_rad), 0.01)
            result.normal_force.append(F_normal)

            # 扭矩
            torque = F_normal * abs(math.sin(alpha_rad)) * (rb + h)
            result.torque.append(torque)

            # 接触应力 (Hertz 线接触)
            curvature_radius = result.curvature[i] if i < len(result.curvature) else float('inf')
            if curvature_radius > 0 and math.isfinite(curvature_radius) and roller_r > 0:
                E_star = CamAnalyst.YOUNGS_MODULUS / (1 - CamAnalyst.POISSON_RATIO**2)
                rho_eq = 1.0 / (1.0/curvature_radius + 1.0/roller_r) if roller_r > 0 else curvature_radius
                if rho_eq > 0:
                    q = F_normal / CamAnalyst.CONTACT_WIDTH
                    sigma = math.sqrt(q * E_star / (math.pi * rho_eq))
                    result.contact_stress.append(min(sigma, 9999.0))
                else:
                    result.contact_stress.append(float('inf'))
            else:
                result.contact_stress.append(float('inf'))

        return result
