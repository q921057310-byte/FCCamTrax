"""Disk (plate) cam geometry builder.

Generates pitch curves, profile curves, and 3D solids for disk cams
with translating (on/off center), oscillating, double, and conjugate followers.
"""

from __future__ import annotations
import math
import FreeCAD as App
import Part
from .base import CamBuilder, CamBuilderFactory
from .follower import CamParams, FollowerParams, FollowerType
from .utils import polar_to_cartesian


class DiskCamBuilder(CamBuilder):
    """盘形凸轮构建器，支持多段运动。"""

    def __init__(self, cam_params: CamParams, follower_params: FollowerParams):
        super().__init__(cam_params, follower_params)
        self._n_points = max(int(360 * cam_params.points_per_degree), 360)

    # ──────────────────────────────────────────────
    # Pitch curve computation (follower center path)
    # ──────────────────────────────────────────────

    def pitch_curve_points(self) -> list[tuple[float, float]]:
        """Compute theoretical pitch curve based on follower type."""
        ft = self.follower.follower_type
        if ft == FollowerType.TRANSLATING_ONCENTER:
            return self._pitch_translating_oncenter()
        elif ft == FollowerType.TRANSLATING_OFFCENTER:
            return self._pitch_translating_offcenter()
        elif ft == FollowerType.OSCILLATING:
            return self._pitch_oscillating()
        elif ft == FollowerType.DOUBLE:
            return self._pitch_translating_oncenter()  # primary follower
        elif ft == FollowerType.CONJUGATE:
            return self._pitch_translating_oncenter()  # primary follower
        else:
            raise ValueError(f"Unsupported follower type: {ft}")

    def _pitch_translating_oncenter(self) -> list[tuple[float, float]]:
        """r(θ) = r_b + h(θ), converted to Cartesian."""
        lifts = self._motion_lifts(self._n_points)
        rb = self.cam.base_radius
        points = []
        for i, h in enumerate(lifts):
            theta = 2 * math.pi * i / self._n_points
            r = rb + h
            points.append(polar_to_cartesian(r, theta))
        return points

    def _pitch_translating_offcenter(self) -> list[tuple[float, float]]:
        """Eccentric translating follower.

        从动件导路在 X=e 处（垂直方向），
        滚子中心沿导路移动距离 d = sqrt((rb+h)² - e²)，
        凸轮固连系坐标 = 旋转 (e, d) 向量 -θ 角度。
        """
        lifts = self._motion_lifts(self._n_points)
        rb = self.cam.base_radius
        e = self.follower.offset
        points = []

        for i, h in enumerate(lifts):
            theta = 2 * math.pi * i / self._n_points
            r_pitch = rb + h
            if r_pitch <= abs(e):
                r_pitch = abs(e) + 0.01
            d = math.sqrt(r_pitch**2 - e**2)
            # 在凸轮固连系中，导路在 X=e 处垂直。
            # 滚子中心在 (e, d)，旋转 -θ 得凸轮固连坐标
            xc = e * math.cos(theta) + d * math.sin(theta)
            yc = -e * math.sin(theta) + d * math.cos(theta)
            points.append((xc, yc))
        return points

    def _pitch_oscillating(self) -> list[tuple[float, float]]:
        """Oscillating (swinging arm) follower.

        支点 P 固定在空间 (pivot_x, pivot_y) 处。
        臂长 l，臂角 ψ(θ) = ψ₀ + h(θ)/l。
        滚子中心世界坐标 → 旋转 -θ 到凸轮固连系。
        """
        lifts = self._motion_lifts(self._n_points)
        l = self.follower.arm_length
        px = self.follower.pivot_x
        py = self.follower.pivot_y
        psi0 = math.radians(self.follower.initial_angle)

        points = []
        for i, h in enumerate(lifts):
            theta = 2 * math.pi * i / self._n_points
            # 臂角
            psi = psi0 + h / l
            # 滚子中心世界坐标
            rx = px + l * math.cos(psi)
            ry = py + l * math.sin(psi)
            # 旋转 -θ 到凸轮固连系
            fx = rx * math.cos(theta) + ry * math.sin(theta)
            fy = -rx * math.sin(theta) + ry * math.cos(theta)
            points.append((fx, fy))
        return points

    # ──────────────────────────────────────────────
    # Profile curve (actual cam surface, offset by roller)
    # ──────────────────────────────────────────────

    def profile_curve_points(self) -> list[tuple[float, float]]:
        """Compute actual cam profile offset by roller radius.

        沿切线法线方向偏移 roller_r（对所有曲线形状正确）。
        """
        pitch = self.pitch_curve_points()
        roller_r = self.follower.roller_radius
        if roller_r <= 0:
            return pitch  # knife-edge follower, no offset
        n = len(pitch)
        if n < 3:
            return pitch
        result = []
        for i in range(n):
            px, py = pitch[i]
            p_prev = pitch[(i - 1) % n]
            p_next = pitch[(i + 1) % n]
            tx = p_next[0] - p_prev[0]
            ty = p_next[1] - p_prev[1]
            tl = math.sqrt(tx * tx + ty * ty)
            if tl < 1e-12:
                result.append((px, py))
                continue
            # 法线方向（90° CCW 旋转切线）
            nx, ny = -ty / tl, tx / tl
            # 确保法线指向中心（点积 < 0 表示指向内）
            if px * nx + py * ny > 0:
                nx, ny = -nx, -ny
            # 向内偏移：法线已指向中心，加上 roller_r 即向内
            result.append((px + roller_r * nx, py + roller_r * ny))
        return result

    def _conjugate_profile_points(self) -> list[tuple[float, float]]:
        """Compute conjugate (complementary) profile for conjugate follower.

        沿切线法线方向远离中心偏移。
        """
        pitch = self.pitch_curve_points()
        roller_r = self.follower.conjugate_roller_radius
        n = len(pitch)
        if n < 3:
            return pitch
        result = []
        for i in range(n):
            px, py = pitch[i]
            p_prev = pitch[(i - 1) % n]
            p_next = pitch[(i + 1) % n]
            tx = p_next[0] - p_prev[0]
            ty = p_next[1] - p_prev[1]
            tl = math.sqrt(tx * tx + ty * ty)
            if tl < 1e-12:
                result.append((px, py))
                continue
            nx, ny = -ty / tl, tx / tl
            # 确保法线远离中心（点积 > 0 表示指向外）
            if px * nx + py * ny < 0:
                nx, ny = -nx, -ny
            # 向外偏移：法线已远离中心，加上 roller_r 即向外
            result.append((px + roller_r * nx, py + roller_r * ny))
        return result

    # ──────────────────────────────────────────────
    # Pressure angle
    # ──────────────────────────────────────────────

    def pressure_angles(self) -> list[float]:
        """Compute pressure angle at each cam angle.

        直动从动件：α = arctan(|dh/dθ - e| / sqrt((rb+h)² - e²))
        摆动从动件：α = arctan(|L·dψ/dθ| / (rb+h))
        """
        n = self._n_points
        lifts = self._motion_lifts(n)
        rb = self.cam.base_radius
        ft = self.follower.follower_type
        e = self.follower.offset if ft == FollowerType.TRANSLATING_OFFCENTER else 0.0
        L = self.follower.arm_length if ft == FollowerType.OSCILLATING else 0.0

        dtheta = 2 * math.pi / n
        pressures = []

        for i in range(n):
            idx_next = (i + 1) % n
            dh_dtheta = (lifts[idx_next] - lifts[i]) / dtheta
            h = lifts[i]
            r_pitch = rb + h

            if ft == FollowerType.OSCILLATING:
                # 摆动：tan(α) = |L·dψ/dθ| / (rb+h)
                # ψ = ψ₀ + h/L → dψ/dθ = (1/L)·dh/dθ
                if L > 1e-6:
                    dpsi_dtheta = dh_dtheta / L
                    denom = max(r_pitch, 1e-6)
                    alpha = math.atan2(abs(L * dpsi_dtheta), denom)
                else:
                    alpha = math.pi / 2
            elif e != 0.0:
                # 偏置直动
                denom = math.sqrt(max(r_pitch**2 - e**2, 1e-12))
                alpha = math.atan2(abs(dh_dtheta - e), denom)
            else:
                # 对心直动
                denom = max(r_pitch, 1e-6)
                alpha = math.atan2(abs(dh_dtheta), denom)
            pressures.append(math.degrees(alpha))

        return pressures

    # ──────────────────────────────────────────────
    # 3D Solid construction
    # ──────────────────────────────────────────────

    def build(self):
        """Build the 3D disk cam solid."""
        if self.cam.grooved:
            return self._build_grooved()
        else:
            profile = self.profile_curve_points()
            if not profile:
                raise RuntimeError("No profile points generated")
            return self._build_solid(profile)

    def _build_solid(self, profile):
        """Traditional disk cam: profile surface extruded.

        降采样到最多 90 点再 BSpline 拟合（精度由 _motion_lifts 保证），
        避免 OCC 对大点数 Periodic BSpline 的慢速插值。
        """
        n_pts = len(profile)
        n_loft = min(n_pts, 90)
        step = max(1, n_pts // n_loft)
        sampled = [profile[i * step % n_pts] for i in range(n_loft)]

        pts = [App.Vector(p[0], p[1], 0) for p in sampled]
        try:
            spline = Part.BSplineCurve()
            spline.interpolate(pts, PeriodicFlag=True)
            wire = Part.Wire(spline.toShape())
        except (Part.OCCError, RuntimeError):
            pts.append(pts[0])
            spline = Part.BSplineCurve()
            spline.interpolate(pts)
            wire = Part.Wire(spline.toShape())
        face = Part.Face(wire)
        solid = face.extrude(App.Vector(0, 0, self.cam.thickness))
        return self._add_features(solid)

    def _build_grooved(self):
        """Face-groove disk cam.

        用 pitch_curve_points() 实际坐标构建槽，
        槽壁沿切线法线方向偏移 ±gw/2（对所有从动件类型正确）。
        """
        gw = self.cam.groove_width
        gd = self.cam.groove_depth
        hw = gw / 2.0
        clearance = 1.0

        pitch = self.pitch_curve_points()
        n = len(pitch)
        if n < 3:
            raise RuntimeError("Too few pitch points for grooved cam")
        n_loft = min(n, 72)
        step = max(1, n // n_loft)

        max_r = 0.0
        sections = []
        for i in range(n_loft):
            idx = (i * step) % n
            idx_prev = (idx - step) % n
            idx_next = (idx + step) % n
            px, py = pitch[idx]
            p_prev = pitch[idx_prev]
            p_next = pitch[idx_next]

            # 切线方向
            tx = p_next[0] - p_prev[0]
            ty = p_next[1] - p_prev[1]
            tl = math.sqrt(tx * tx + ty * ty)
            if tl < 1e-12:
                continue
            # 法线方向（垂直于切线）
            nx, ny = -ty / tl, tx / tl

            ox = px + hw * nx
            oy = py + hw * ny
            ix = px - hw * nx
            iy = py - hw * ny
            max_r = max(max_r, math.sqrt(ox**2 + oy**2))

            pts = [
                App.Vector(ox, oy, -clearance),
                App.Vector(ix, iy, -clearance),
                App.Vector(ix, iy, gd),
                App.Vector(ox, oy, gd),
                App.Vector(ox, oy, -clearance),
            ]
            sections.append(Part.makePolygon(pts))

        groove = Part.makeLoft(sections, solid=True, closed=True)

        blank_r = max(max_r + 2, self.cam.blank_radius)
        blank = Part.makeCylinder(
            blank_r, self.cam.thickness,
            App.Vector(0, 0, 0),
            App.Vector(0, 0, 1))

        return self._add_features(blank.cut(groove))

    def _add_features(self, solid):
        """Add hub, bore, keyway, and mounting holes to a solid."""

        # Add hub
        if self.cam.hub_radius > 0:
            hub = Part.makeCylinder(
                self.cam.hub_radius,
                self.cam.thickness + self.cam.hub_length,
                App.Vector(0, 0, -self.cam.hub_length / 2),
                App.Vector(0, 0, 1)
            )
            solid = solid.fuse(hub)

        # Add bore
        if self.cam.bore_radius > 0:
            bore = Part.makeCylinder(
                self.cam.bore_radius,
                self.cam.thickness * 3,
                App.Vector(0, 0, -self.cam.thickness),
                App.Vector(0, 0, 1)
            )
            solid = solid.cut(bore)

        # Add keyway
        if self.cam.keyway_width > 0 and self.cam.keyway_depth > 0:
            kw = self.cam.keyway_width
            kd = self.cam.keyway_depth
            keyway = Part.makeBox(
                kw, kd, self.cam.thickness * 3,
                App.Vector(-kw/2, -kd, -self.cam.thickness)
            )
            solid = solid.cut(keyway)

        # Add mounting holes
        if self.cam.mounting_holes > 0:
            for i in range(self.cam.mounting_holes):
                angle = 2 * math.pi * i / self.cam.mounting_holes
                hx = self.cam.mounting_hole_distance * math.cos(angle)
                hy = self.cam.mounting_hole_distance * math.sin(angle)
                hole = Part.makeCylinder(
                    self.cam.mounting_hole_radius,
                    self.cam.thickness * 3,
                    App.Vector(hx, hy, -self.cam.thickness),
                    App.Vector(0, 0, 1)
                )
                solid = solid.cut(hole)

        return solid
