"""凸轮从动件几何类型和运动段定义。"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FollowerType(Enum):
    TRANSLATING_ONCENTER = "translating_oncenter"
    TRANSLATING_OFFCENTER = "translating_offcenter"
    OSCILLATING = "oscillating"
    DOUBLE = "double"
    CONJUGATE = "conjugate"


@dataclass
class MotionSegment:
    """一段运动区间（可有任意多段）。"""
    start_angle: float = 0.0      # 起始角 (°)
    end_angle: float = 120.0      # 终止角 (°)
    start_lift: float = 0.0       # 起始升程 (mm)
    end_lift: float = 20.0        # 终止升程 (mm)
    motion_name: str = "摆线运动"  # 运动规律（中文名）


@dataclass
class FollowerParams:
    """从动件参数。"""
    follower_type: FollowerType = FollowerType.TRANSLATING_ONCENTER
    roller_radius: float = 5.0
    offset: float = 0.0
    arm_length: float = 40.0
    pivot_distance: float = 60.0
    initial_angle: float = 0.0
    phase_offset: float = 180.0
    follower2_roller_radius: float = 5.0
    follower2_offset: float = 0.0
    conjugate_roller_radius: float = 5.0
    color: tuple[float, float, float] = (0.8, 0.2, 0.2)


@dataclass
class CamParams:
    """凸轮几何参数。"""
    cam_type: str = "disk"
    base_radius: float = 30.0
    thickness: float = 15.0
    hub_radius: float = 12.0
    hub_length: float = 10.0
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
