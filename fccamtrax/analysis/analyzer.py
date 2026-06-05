"""Cam Analysis模块。"""

from __future__ import annotations
import math
from dataclasses import dataclass, field

from ..geometry.follower import CamParams, FollowerParams, FollowerType
from ..geometry.base import CamBuilder
from ..geometry.utils import pressure_angle_oncenter


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
    FOLLOWER_MASS = 1.0       # kg — Follower质量（用于惯性力）

    @staticmethod
    def analyze(cam_params: CamParams, follower_params: FollowerParams) -> AnalysisResult:
        """运行完整分析。"""
        result = AnalysisResult()
        n_points = max(int(360 * cam_params.points_per_degree), 360)
        result.angles = [i * 360.0 / n_points for i in range(n_points)]

        builder = CamBuilder.create_builder(cam_params, follower_params)
        lifts = builder.motion_lifts(n_points)

        result.displacement = lifts

        # Velocity、Acceleration、Jerk（数值微分，dθ in rad）
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

        # Pressure Angle
        result.pressure_angle = builder.pressure_angles()
        # 如果 builder 没实现，用通用公式（Translating On-center）
        if not result.pressure_angle:
            rb = cam_params.base_radius
            for i, h in enumerate(lifts):
                idx_next = (i + 1) % n_points
                dh = (lifts[idx_next] - lifts[i]) / dtheta
                result.pressure_angle.append(pressure_angle_oncenter(rb, h, dh))

        # Curvature Radius
        result.curvature = builder.curvature_radii()

        # Normal Force、Torque、Contact Stress
        omega = CamAnalyst.CAM_SPEED * 2 * math.pi / 60  # rad/s
        F_spring = CamAnalyst.SPRING_FORCE
        rb = cam_params.base_radius
        roller_r = follower_params.roller_radius

        for i in range(n_points):
            h = lifts[i]
            alpha_rad = math.radians(result.pressure_angle[i]) if i < len(result.pressure_angle) else 0.0
            acc_i = result.acceleration[i] if i < len(result.acceleration) else 0.0

            # Follower惯性力: F_inertial = m * a (mm/s²) / 1000 (→m/s²)
            # acc_i 是 d²h/dθ² (mm/rad²), a_actual = acc_i * ω² (mm/s²)
            F_inertial = CamAnalyst.FOLLOWER_MASS * abs(acc_i) * omega * omega / 1000.0
            # Normal Force
            F_normal = (F_spring + F_inertial) / max(math.cos(alpha_rad), 0.01)
            result.normal_force.append(F_normal)

            # Torque
            torque = F_normal * abs(math.sin(alpha_rad)) * (rb + h)
            result.torque.append(torque)

            # Contact Stress (Hertz 线接触)
            curvature_radius = result.curvature[i] if i < len(result.curvature) else float('inf')
            if math.isfinite(curvature_radius) and abs(curvature_radius) > 1e-12 and roller_r > 0:
                E_star = CamAnalyst.YOUNGS_MODULUS / (1 - CamAnalyst.POISSON_RATIO**2)
                cr_abs = abs(curvature_radius)
                rho_eq = 1.0 / (1.0/cr_abs + 1.0/roller_r)
                if rho_eq > 0:
                    q = F_normal / CamAnalyst.CONTACT_WIDTH
                    sigma = math.sqrt(q * E_star / (math.pi * rho_eq))
                    result.contact_stress.append(min(sigma, 9999.0))
                else:
                    result.contact_stress.append(float('inf'))
            else:
                result.contact_stress.append(float('inf'))

        return result
