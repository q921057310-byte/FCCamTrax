"""Cam follower geometry types and motion segment definitions."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class FollowerType(Enum):
    TRANSLATING_ONCENTER = "translating_oncenter"
    TRANSLATING_OFFCENTER = "translating_offcenter"
    OSCILLATING = "oscillating"


@dataclass
class MotionSegment:
    """A motion segment with angle range and lift profile."""
    start_angle: float = 0.0      # Start angle (°)
    end_angle: float = 120.0      # End angle (°)
    start_lift: float = 0.0       # Start lift (mm)
    end_lift: float = 20.0        # End lift (mm)
    motion_name: str = "Cycloidal"

    def __post_init__(self):
        if self.end_angle < self.start_angle:
            raise ValueError(
                f"End angle ({self.end_angle}°) cannot be less than start angle ({self.start_angle}°)")
        if self.start_angle < 0 or self.end_angle > 360:
            raise ValueError(
                f"Angle range must be within 0~360° (got {self.start_angle}°~{self.end_angle}°)")


def get_roller_radius(grooved: bool, groove_width: float, default: float = 3.0) -> float:
    """Unified roller radius: grooved = groove_width/2, non-grooved = default."""
    return groove_width / 2.0 if grooved else default


@dataclass
class FollowerParams:
    """从动件参数。"""
    follower_type: FollowerType = FollowerType.TRANSLATING_ONCENTER
    roller_radius: float = 3.0
    offset: float = 0.0
    arm_length: float = 40.0
    pivot_x: float = 60.0
    pivot_y: float = 0.0
    initial_angle: float = 151.0
    color: tuple[float, float, float] = (0.8, 0.2, 0.2)


@dataclass
class CamParams:
    """凸轮几何参数。"""
    cam_type: str = "disk"
    base_radius: float = 30.0
    thickness: float = 15.0
    hub_radius: float = 0.0
    hub_length: float = 0.0
    keyway_width: float = 4.0
    keyway_depth: float = 3.0
    bore_radius: float = 8.0
    mounting_holes: int = 0
    mounting_hole_radius: float = 3.0
    mounting_hole_distance: float = 20.0
    # 凸轮几何参数（通用）
    points_per_degree: float = 1.0
    segments: list[MotionSegment] = field(default_factory=list)
    color: tuple[float, float, float] = (0.6, 0.6, 0.7)
    # 是否有沟槽（盘形/线性凸轮可选，圆柱凸轮默认有）
    grooved: bool = False
    # 沟槽参数
    groove_width: float = 6.0
    groove_depth: float = 4.0
    # 盘形凸轮：毛胚外径
    blank_radius: float = 60.0
