"""线性凸轮（平板往复凸轮）几何构建器。

将圆盘凸轮的升程曲线展开为平面轮廓，再拉伸为 3D 实体。
凸轮做直线往复运动，从动件在凸轮边缘上滑动实现升降。
"""

from __future__ import annotations
import math
import FreeCAD as App
import Part
from .base import CamBuilder, CamBuilderFactory
from .follower import CamParams, FollowerParams


class LinearCamBuilder(CamBuilder):
    """线性凸轮构建器，轮廓为展开的升程曲线拉伸体。"""

    def __init__(self, cam_params: CamParams, follower_params: FollowerParams):
        super().__init__(cam_params, follower_params)
        self._n_points = max(int(360 * cam_params.points_per_degree), 360)

    # ──────────────────────────────────────────────
    # Pitch curve: (x, h) — 展开后的升程曲线
    # ──────────────────────────────────────────────

    def pitch_curve_points(self) -> list[tuple[float, float]]:
        """展开升程曲线：x = R·θ, y = h(θ)。"""
        lifts = self._motion_lifts(self._n_points)
        R = self.cam.base_radius
        points = []
        for i, h in enumerate(lifts):
            theta_rad = 2 * math.pi * i / self._n_points
            x = R * theta_rad  # 弧长 = R·θ
            points.append((x, h))
        return points

    def profile_curve_points(self) -> list[tuple[float, float]]:
        """线性凸轮轮廓即为展开升程曲线本身。"""
        return self.pitch_curve_points()

    # ──────────────────────────────────────────────
    # 3D Solid: 升程曲线 + 底边 → 封闭面 → 拉伸
    # ──────────────────────────────────────────────

    def build(self):
        """构建线性凸轮 3D 实体。"""
        pitch = self.pitch_curve_points()
        if not pitch:
            raise RuntimeError("无升程数据")

        if self.cam.grooved:
            return self._build_grooved(pitch)
        else:
            return self._build_solid(pitch)

    def _build_solid(self, pitch):
        """无槽线性凸轮：升程曲线 + 底边 → 封闭面 → 拉伸。"""
        R = self.cam.base_radius
        base_h = self.cam.thickness
        gw = self.cam.groove_width
        L = R * 2 * math.pi

        top_pts = [App.Vector(x, h + base_h, 0) for x, h in pitch]
        if abs(top_pts[-1].x - L) > 0.01:
            top_pts.append(App.Vector(L, pitch[-1][1] + base_h, 0))
        if abs(top_pts[0].x) > 0.01:
            top_pts.insert(0, App.Vector(0, pitch[0][1] + base_h, 0))

        bottom_pts = [App.Vector(L, 0, 0), App.Vector(0, 0, 0)]
        all_pts = top_pts + bottom_pts

        edges = []
        for j in range(len(all_pts) - 1):
            e = Part.makeLine(
                (all_pts[j].x, all_pts[j].y, all_pts[j].z),
                (all_pts[j+1].x, all_pts[j+1].y, all_pts[j+1].z))
            edges.append(e)
        e = Part.makeLine(
            (all_pts[-1].x, all_pts[-1].y, all_pts[-1].z),
            (all_pts[0].x, all_pts[0].y, all_pts[0].z))
        edges.append(e)

        wire = Part.Wire(edges)
        face = Part.Face(wire)
        return face.extrude(App.Vector(0, 0, base_h))

    def _build_grooved(self, pitch):
        """带槽线性凸轮：Y 面沟槽，Z 宽=gw，Y 深=gd，X 两端开通。"""
        R = self.cam.base_radius
        base_h = self.cam.thickness
        gw = self.cam.groove_width
        gd = self.cam.groove_depth
        L = R * 2 * math.pi
        cleft = 1.0

        lifts = [h for _, h in pitch]
        max_lift = max(lifts) if lifts else 0.0

        # block Z 厚度 = base_h（非槽宽）
        block_h = base_h + max_lift + gd + cleft
        block = Part.makeBox(L, block_h, base_h,
                             App.Vector(0, -gd - cleft, 0))

        if len(pitch) > 2:
            step = max(1, len(pitch) // 90)
            indices = list(range(0, len(pitch), step))
            if indices and indices[-1] != len(pitch) - 1:
                indices.append(len(pitch) - 1)

            # Z 方向：沟槽范围 0..gw（在 block 表面内）
            # X 两端延伸 0.1mm 避免端面与 block 共面
            dx = 0.1
            x0 = pitch[0][0] - dx
            xL = pitch[-1][0] + dx
            # 用 _lift_at 计算延伸处的升程（保证曲线连续）
            da = dx / R * 180 / math.pi  # dx 对应的角度
            h0 = self._lift_at(-da, self.cam.segments)
            hL = self._lift_at(360.0 + da, self.cam.segments)

            sections = []
            for x, h in [(x0, h0)] + [(pitch[i][0], pitch[i][1]) for i in indices] + [(xL, hL)]:
                pts = [
                    App.Vector(x, h, 0.0),
                    App.Vector(x, h, gw),
                    App.Vector(x, h - gd, gw),
                    App.Vector(x, h - gd, 0.0),
                    App.Vector(x, h, 0.0),
                ]
                sections.append(Part.makePolygon(pts))

            groove = Part.makeLoft(sections, solid=True)
            return block.cut(groove)

        return block


# 注册构建器
CamBuilderFactory.register("linear", LinearCamBuilder)
