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
from .utils import polar_to_cartesian, offset_curve


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

        The pitch curve in polar (relative to cam center):
          ψ(θ) = arctan(e / sqrt((r_b + h(θ))^2 - e^2)) + θ
          R(θ) = sqrt((r_b + h(θ))^2 - e^2) / cos(ψ(θ) - θ)
        where e = offset (eccentricity).
        """
        lifts = self._motion_lifts(self._n_points)
        rb = self.cam.base_radius
        e = self.follower.offset
        points = []

        for i, h in enumerate(lifts):
            theta = 2 * math.pi * i / self._n_points
            r_pitch = rb + h
            if r_pitch <= abs(e):
                r_pitch = abs(e) + 0.01  # prevent sqrt of negative
            # Distance from cam center to follower center line intersection
            d = math.sqrt(r_pitch**2 - e**2)
            # Angle offset due to eccentricity
            psi = math.atan2(e, d)
            angle = theta + psi
            R = d / math.cos(psi)
            points.append(polar_to_cartesian(R, angle))
        return points

    def _pitch_oscillating(self) -> list[tuple[float, float]]:
        """Oscillating (swinging arm) follower.

        支点 P 固定在凸轮上方的 (0, d) 处。
        臂长 l，臂角 ψ(θ) = ψ₀ + h(θ)/l。
        滚子中心世界坐标 → 旋转 -θ 到凸轮固连系。
        """
        lifts = self._motion_lifts(self._n_points)
        l = self.follower.arm_length
        d = self.follower.pivot_distance
        psi0 = math.radians(self.follower.initial_angle)

        points = []
        for i, h in enumerate(lifts):
            theta = 2 * math.pi * i / self._n_points
            # 臂角
            psi = psi0 + h / l
            # 固定支点（Y 轴正上方）
            px, py = 0.0, d
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
        """Compute actual cam profile offset by roller radius."""
        pitch = self.pitch_curve_points()
        roller_r = self.follower.roller_radius
        if roller_r <= 0:
            return pitch  # knife-edge follower, no offset
        # Offset inward (negative = toward cam center)
        return offset_curve(pitch, -roller_r, closed=True)

    def _conjugate_profile_points(self) -> list[tuple[float, float]]:
        """Compute conjugate (complementary) profile for conjugate follower."""
        pitch = self.pitch_curve_points()
        roller_r = self.follower.conjugate_roller_radius
        # Offset outward for the conjugate path
        return offset_curve(pitch, roller_r, closed=True)

    # ──────────────────────────────────────────────
    # Pressure angle
    # ──────────────────────────────────────────────

    def pressure_angles(self) -> list[float]:
        """Compute pressure angle at each cam angle.

        For translating follower:
          α(θ) = arctan((dh/dθ - e) / (r_b + h(θ)))
        where e = 0 for on-center, e = offset for off-center.
        """
        n = self._n_points
        lifts = self._motion_lifts(n)
        rb = self.cam.base_radius
        e = self.follower.offset if self.follower.follower_type == \
            FollowerType.TRANSLATING_OFFCENTER else 0.0

        dtheta = 2 * math.pi / n
        pressures = []

        for i in range(n):
            idx_next = (i + 1) % n
            dh_dtheta = (lifts[idx_next] - lifts[i]) / dtheta
            h = lifts[i]
            denom = rb + h
            if denom < 1e-6:
                denom = 1e-6
            alpha = math.atan2(abs(dh_dtheta - e), denom)
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
        except Exception:
            pts.append(pts[0])
            spline = Part.BSplineCurve()
            spline.interpolate(pts)
            wire = Part.Wire(spline.toShape())
        face = Part.Face(wire)
        solid = face.extrude(App.Vector(0, 0, self.cam.thickness))
        return self._add_features(solid)

    def _build_grooved(self):
        """Face-groove disk cam.

        和圆柱凸轮完全同构：
        72 个矩形截面 → Part.makeLoft(solid, closed) → blank.cut(groove)

        关键区别（vs 圆柱）：
        圆柱：r 固定，Z 随 lift 变
        盘形：Z 固定，r 随 lift 变（r = base_radius + lift）
        """
        R = self.cam.base_radius
        gw = self.cam.groove_width
        gd = self.cam.groove_depth
        hw = gw / 2.0
        clearance = 1.0

        n = self._n_points
        n_loft = min(n, 72)
        step = max(1, n // n_loft)

        max_r = 0.0
        sections = []
        for i in range(n_loft):
            idx = (i * step) % n
            theta = 2 * math.pi * idx / n
            lift = self._lift_at(idx / n * 360.0, self.cam.segments)
            r = R + lift
            if r + hw > max_r:
                max_r = r + hw

            c = math.cos(theta)
            s = math.sin(theta)
            pts = [
                App.Vector((r + hw) * c, (r + hw) * s, -clearance),
                App.Vector((r - hw) * c, (r - hw) * s, -clearance),
                App.Vector((r - hw) * c, (r - hw) * s, gd),
                App.Vector((r + hw) * c, (r + hw) * s, gd),
                App.Vector((r + hw) * c, (r + hw) * s, -clearance),
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
