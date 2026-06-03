"""圆柱凸轮（筒形凸轮）几何构建器。"""

from __future__ import annotations
import math
import FreeCAD as App
import Part
from .base import CamBuilder, CamBuilderFactory
from .follower import CamParams, FollowerParams


class CylindricalCamBuilder(CamBuilder):
    """圆柱凸轮构建器，沟槽沿圆柱表面分布。"""

    def __init__(self, cam_params: CamParams, follower_params: FollowerParams):
        super().__init__(cam_params, follower_params)
        self._n_points = max(int(360 * cam_params.points_per_degree), 360)

    def pitch_curve_points(self):
        lifts = self._motion_lifts(self._n_points)
        R = self.cam.base_radius
        return [(R * math.cos(2 * math.pi * i / self._n_points),
                 R * math.sin(2 * math.pi * i / self._n_points), h)
                for i, h in enumerate(lifts)]

    def profile_curve_points(self):
        return self.pitch_curve_points()

    def build(self):
        R = self.cam.base_radius
        gw = self.cam.groove_width
        gd = self.cam.groove_depth
        clearance = 1.0  # 比圆柱面稍大确保切透

        n = self._n_points
        n_loft = min(n, 72)  # 72 个截面（每 5° 一个）
        step = max(1, n // n_loft)

        min_h = float('inf')
        max_h = float('-inf')

        # 构建截面列表
        sections = []
        for i in range(n_loft):
            idx = (i * step) % n
            r_outer = R + clearance
            r_inner = R - gd

            theta = 2 * math.pi * idx / n
            lift = self._lift_at(idx / n * 360.0, self.cam.segments)
            if lift < min_h:
                min_h = lift
            if lift > max_h:
                max_h = lift

            cos_t = math.cos(theta)
            sin_t = math.sin(theta)

            pts = [
                App.Vector(r_outer * cos_t, r_outer * sin_t, lift - gw / 2),
                App.Vector(r_inner * cos_t, r_inner * sin_t, lift - gw / 2),
                App.Vector(r_inner * cos_t, r_inner * sin_t, lift + gw / 2),
                App.Vector(r_outer * cos_t, r_outer * sin_t, lift + gw / 2),
                App.Vector(r_outer * cos_t, r_outer * sin_t, lift - gw / 2),
            ]
            wire = Part.makePolygon(pts)
            sections.append(wire)

        margin = 20.0
        cyl_height = (max_h - min_h) + 2 * margin
        cyl = Part.makeCylinder(R, cyl_height,
                                App.Vector(0, 0, min_h - margin),
                                App.Vector(0, 0, 1))

        groove = Part.makeLoft(sections, solid=True, closed=True)

        result = cyl.cut(groove)

        if self.cam.bore_radius > 0:
            bore = Part.makeCylinder(
                self.cam.bore_radius, cyl_height * 3,
                App.Vector(0, 0, min_h - margin - cyl_height),
                App.Vector(0, 0, 1))
            result = result.cut(bore)

        return result


CamBuilderFactory.register("cylindrical", CylindricalCamBuilder)
