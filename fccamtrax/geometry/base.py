"""凸轮几何构建器基类和工厂。"""

from __future__ import annotations
import math
from abc import ABC, abstractmethod

from ..motion.registry import get as get_motion
from .follower import CamParams, FollowerParams, MotionSegment

# 运动规律中英文双向映射
_MOTION_CN: dict[str, str] = {
    "Cycloidal": "摆线运动",
    "Harmonic": "简谐运动",
    "Modified Sine": "修正正弦",
    "3-4-5 Polynomial": "3-4-5 多项式",
    "Constant Velocity": "等速运动",
}
_MOTION_EN: dict[str, str] = {v: k for k, v in _MOTION_CN.items()}

# 段间过渡角度（°），在此范围内用 Hermite 匹配升程+速度
_TRANSITION_DEG = 5.0


class CamBuilder(ABC):
    """凸轮构建器基类，支持多段运动。"""

    def __init__(self, cam_params: CamParams, follower_params: FollowerParams):
        self.cam = cam_params
        self.follower = follower_params

    @abstractmethod
    def build(self):
        ...

    @abstractmethod
    def pitch_curve_points(self) -> list[tuple[float, float]]:
        ...

    @abstractmethod
    def profile_curve_points(self) -> list[tuple[float, float]]:
        ...

    def pressure_angles(self) -> list[float]:
        """压力角（默认返回空列表，子类可覆盖）。"""
        return []

    def motion_lifts(self, n_points: int = 360) -> list[float]:
        """公开接口：计算凸轮各角度处的升程 h(θ)。"""
        return self._motion_lifts(n_points)

    def curvature_radii(self) -> list[float]:
        """曲率半径（默认用 pitch_curve_points 的 2D 三点法）。"""
        pitch = self.pitch_curve_points()
        if not pitch:
            return []
        # 只取前两个坐标（2D 曲线），3D 点忽略 Z
        pts_2d = [(p[0], p[1]) for p in pitch]
        return self._curvature_radius_2d(pts_2d)

    @staticmethod
    def _curvature_radius_2d(points):
        """2D 曲线三点法曲率半径。"""
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

    def _motion_lifts(self, n_points: int = 360) -> list[float]:
        """计算凸轮各角度处的升程 h(θ)。"""
        segments = self.cam.segments
        if not segments:
            return [0.0] * n_points

        lifts = []
        for i in range(n_points):
            theta = (i / n_points) * 360.0
            lift = self._lift_at(theta, segments)
            lifts.append(lift)
        return lifts

    def _lift_at(self, theta: float, segments: list[MotionSegment]) -> float:
        """计算角度 θ 处的升程，段间统一 C2 过渡。"""
        theta = theta % 360.0
        n = len(segments)
        if n == 0:
            return 0.0

        # 先检查是否在任何一个过渡带内
        for i, seg in enumerate(segments):
            seg_len = seg.end_angle - seg.start_angle
            if seg_len <= 0:
                continue
            half_zone = min(_TRANSITION_DEG, seg_len / 3) / 2.0
            if half_zone <= 0:
                continue

            # 段首边界过渡带 [start-hz, start+hz)
            boundary = seg.start_angle
            entry = (boundary - half_zone) % 360.0
            exit_ = (boundary + half_zone) % 360.0
            if entry < exit_:
                in_zone = entry <= theta < exit_
            else:
                in_zone = theta >= entry or theta < exit_

            if in_zone:
                prev_seg = segments[(i - 1) % n]
                y0, dy0, ddy0 = self._seg_lift_vel_acc(prev_seg, entry)
                y1, dy1, ddy1 = self._seg_lift_vel_acc(seg, boundary + half_zone)
                z = 2.0 * half_zone
                raw_t = ((theta - entry) % 360.0) / z if z > 1e-12 else 0.0
                t = max(0.0, min(1.0, raw_t))
                return self._quintic_hermite(
                    y0, dy0 * z, ddy0 * z * z,
                    y1, dy1 * z, ddy1 * z * z, t)

        # 非过渡区：直接用所在段的原始值
        for seg in segments:
            if seg.start_angle <= theta < seg.end_angle:
                my_lift, _, _ = self._seg_lift_vel_acc(seg, theta)
                return my_lift

        return 0.0

    def _seg_lift_vel_acc(self, seg: MotionSegment, theta: float
                          ) -> tuple[float, float, float]:
        """计算某段在指定角度的升程、速度、加速度 (mm, mm/°, mm/°²)。"""
        seg_len = seg.end_angle - seg.start_angle
        if seg_len <= 0:
            return seg.end_lift, 0.0, 0.0
        t = max(0.0, min(1.0, (theta - seg.start_angle) / seg_len))
        try:
            name = _MOTION_EN.get(seg.motion_name, seg.motion_name)
            motion = get_motion(name)
            s = motion.displacement(t)
            v = motion.velocity(t)
            a = motion.acceleration(t)
        except (KeyError, ValueError):
            s = t
            v = 1.0
            a = 0.0
        lift_range = seg.end_lift - seg.start_lift
        lift = seg.start_lift + s * lift_range
        vel = v * lift_range / seg_len
        acc = a * lift_range / (seg_len * seg_len)
        return lift, vel, acc

    def _seg_velocity(self, seg: MotionSegment, theta: float) -> float:
        _, vel, _ = self._seg_lift_vel_acc(seg, theta)
        return vel

    def _raw_lift(self, seg: MotionSegment, theta: float) -> float:
        lift, _, _ = self._seg_lift_vel_acc(seg, theta)
        return lift

    @staticmethod
    def _quintic_hermite(y0: float, dy0: float, ddy0: float,
                         y1: float, dy1: float, ddy1: float,
                         t: float) -> float:
        """五阶 Hermite 插值：匹配两端升程、速度、加速度 (C2 连续)。"""
        t2 = t * t
        t3 = t2 * t
        t4 = t3 * t
        t5 = t4 * t
        h00 = 1 - 10*t3 + 15*t4 - 6*t5
        h10 = t - 6*t3 + 8*t4 - 3*t5
        h20 = 0.5*t2 - 1.5*t3 + 1.5*t4 - 0.5*t5
        h01 = 10*t3 - 15*t4 + 6*t5
        h11 = -4*t3 + 7*t4 - 3*t5
        h21 = 0.5*t3 - t4 + 0.5*t5
        return h00*y0 + h10*dy0 + h20*ddy0 + h01*y1 + h11*dy1 + h21*ddy1


class CamBuilderFactory:
    """凸轮构建器工厂。"""

    _builders: dict[str, type[CamBuilder]] = {}

    @classmethod
    def register(cls, cam_type: str, builder_class: type[CamBuilder]):
        cls._builders[cam_type] = builder_class

    @classmethod
    def create(cls, cam_type: str, cam_params: CamParams,
               follower_params: FollowerParams) -> CamBuilder:
        if not cls._builders:
            cls._lazy_import_builders()
        if cam_type not in cls._builders:
            raise KeyError(f"未知凸轮类型: {cam_type}")
        return cls._builders[cam_type](cam_params, follower_params)

    @classmethod
    def _lazy_import_builders(cls):
        """在首次需要时导入各构建器模块并注册。"""
        from .disk_cam import DiskCamBuilder
        from .cylindrical_cam import CylindricalCamBuilder
        from .linear_cam import LinearCamBuilder
        cls.register("disk", DiskCamBuilder)
        cls.register("cylindrical", CylindricalCamBuilder)
        cls.register("linear", LinearCamBuilder)

    @classmethod
    def available_types(cls) -> list[str]:
        return list(cls._builders.keys())


def _create_builder(cam_params, follower_params):
    """便捷函数：根据 cam_type 自动创建构建器。"""
    return CamBuilderFactory.create(cam_params.cam_type, cam_params, follower_params)


CamBuilder.create_builder = staticmethod(_create_builder)
