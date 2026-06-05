"""2D cam mechanism preview — shows cam profile, arm, roller, and pivot.

Uses QPainter for rendering, compatible with PySide6/PySide2/PyQt6/PyQt5.
"""

from __future__ import annotations
import math
from ..geometry.base import CamBuilderFactory
from ..geometry.follower import CamParams, FollowerParams, FollowerType
from ..geometry.utils import pressure_angle_oncenter, pressure_angle_offcenter, pressure_angle_oscillating, pressure_angle_linear_cyl
from ..i18n import tr

_QtWidgets = _QtCore = _QtGui = None
for _mod_name in ["PySide6", "PySide2", "PyQt6", "PyQt5"]:
    try:
        _mod = __import__(_mod_name)
        _QtWidgets = getattr(_mod, "QtWidgets", None)
        _QtCore = getattr(_mod, "QtCore", None)
        _QtGui = getattr(_mod, "QtGui", None)
        if _QtWidgets and _QtCore:
            break
        _QtWidgets = _QtCore = _QtGui = None
    except ImportError:
        continue

if _QtWidgets is None:
    # 无 Qt 环境：创建空壳类避免崩溃
    class _DummyWidget:
        def __init__(self, parent=None): pass
        def setMinimumSize(self, *a): pass
        def setSizePolicy(self, *a): pass
        def update(self): pass
        def width(self): return 200
        def height(self): return 150
        def rect(self):
            class R:
                def __init__(s):
                    s.x = s.y = lambda: 0
                    s.width = s.height = lambda: 200
            return R()
    _QtWidgets = type("DummyQtWidgets", (), {"QWidget": _DummyWidget,
        "QSizePolicy": type("QSP", (), {"Policy": type("P", (), {"Expanding": 1})})})()
    _QtCore = type("DummyQtCore", (), {"Qt": type("Q", (), {"white": 0, "red": 0, "black": 0, "gray": 0,
        "AlignCenter": 0, "DashLine": 0, "NoBrush": 0, "Horizontal": 0, "TicksBelow": 0})})()
    _QtGui = type("DummyQtGui", (), {"QPainter": type("QP", (), {"RenderHint": type("R", (), {"Antialiasing": 1})}),
        "QPen": lambda *a: None, "QColor": lambda *a: None, "QPainterPath": lambda: None})()

QtWidgets = _QtWidgets
QtCore = _QtCore
QtGui = _QtGui


class CamPreviewWidget(QtWidgets.QWidget):
    """2D mechanism preview: cam profile + follower arm + roller."""

    MARGIN = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 150)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self._cam: CamParams | None = None
        self._follower: FollowerParams | None = None
        self._pitch_curve: list[tuple[float, float]] = []
        self._lifts: list[float] = []
        self._cam_angle: float = 0.0
        self._roller_pos: tuple[float, float] = (0.0, 0.0)
        self._pivot_pos: tuple[float, float] = (0.0, 0.0)
        self._arm_length: float = 40.0

    # ── public API ──

    def set_params(self, cam: CamParams, follower: FollowerParams):
        self._cam = cam
        self._follower = follower
        self._arm_length = follower.arm_length
        self._rebuild()
        self._update_mechanism()
        self.update()

    def set_cam_angle(self, angle_deg: float):
        self._cam_angle = angle_deg
        self._update_mechanism()
        self.update()

    # ── internal computation ──

    def _rebuild(self):
        if not self._cam or not self._follower:
            self._pitch_curve = []
            self._profile_curve = []
            self._lifts = []
            return
        builder = CamBuilderFactory.create(
            self._cam.cam_type, self._cam, self._follower)
        pitch_raw = builder.pitch_curve_points()
        profile_raw = builder.profile_curve_points()
        self._lifts = builder.motion_lifts(len(pitch_raw))

        # Cylindrical Cam：3D 点 (x,y,z) → 展开 2D (R*θ, z)
        if self._cam.cam_type == "cylindrical":
            R = self._cam.base_radius
            n = len(pitch_raw)
            self._pitch_curve = []
            for i, p in enumerate(pitch_raw):
                theta = 2 * math.pi * i / n
                self._pitch_curve.append((R * theta, p[2]))
            self._profile_curve = list(self._pitch_curve)
        else:
            self._pitch_curve = pitch_raw
            self._profile_curve = profile_raw

    def _update_mechanism(self):
        """计算滚子在世界坐标系的位置。"""
        if not self._cam or not self._follower:
            return
        cam_angle_deg = self._cam_angle
        n = len(self._pitch_curve)
        if n == 0:
            self._roller_pos = (0.0, 0.0)
            self._pivot_pos = (0.0, 0.0)
            return

        cam_type = self._cam.cam_type
        contact_idx = int((cam_angle_deg / 360.0) * n) % n

        if cam_type in ("linear", "cylindrical"):
            # 线性/Cylindrical Cam：pitch_curve 已经是 (x, rb+h) 格式
            px, py = self._pitch_curve[contact_idx]
            roller_r = self._follower.roller_radius
            self._roller_pos = (px, py + roller_r)
            self._pivot_pos = (0.0, 0.0)
            return

        # ── Disk Cam ──
        theta = math.radians(cam_angle_deg)
        ct, st = math.cos(theta), math.sin(theta)
        ft = self._follower.follower_type

        contact_idx = int((-cam_angle_deg / 360.0) * n) % n
        rb = self._cam.base_radius
        h = self._lifts[contact_idx] if self._lifts else 0.0
        r_pitch = rb + h

        if ft == FollowerType.TRANSLATING_ONCENTER:
            self._roller_pos = (r_pitch, 0.0)
            self._pivot_pos = (0.0, 0.0)

        elif ft == FollowerType.TRANSLATING_OFFCENTER:
            e = self._follower.offset
            # 搜索旋转后 pitch_curve 上 x≈e 的点
            best_i = 0
            best_dist = float('inf')
            for i, p in enumerate(self._pitch_curve):
                wx = p[0] * ct - p[1] * st
                dist = abs(wx - e)
                if dist < best_dist:
                    best_dist = dist
                    best_i = i
            p = self._pitch_curve[best_i]
            wx = p[0] * ct - p[1] * st
            wy = p[0] * st + p[1] * ct
            self._roller_pos = (wx, wy)
            self._pivot_pos = (0.0, 0.0)

        elif ft == FollowerType.OSCILLATING:
            l = self._follower.arm_length
            px = self._follower.pivot_x
            py = self._follower.pivot_y
            # 搜索旋转后 pitch_curve 上距离支点 ≈ arm_length 的点
            best_i = 0
            best_err = float('inf')
            for i, p in enumerate(self._pitch_curve):
                wx = p[0] * ct - p[1] * st
                wy = p[0] * st + p[1] * ct
                dist = math.sqrt((wx - px)**2 + (wy - py)**2)
                err = abs(dist - l)
                if err < best_err:
                    best_err = err
                    best_i = i
            p = self._pitch_curve[best_i]
            wx = p[0] * ct - p[1] * st
            wy = p[0] * st + p[1] * ct
            self._pivot_pos = (px, py)
            self._roller_pos = (wx, wy)

        else:
            self._roller_pos = (r_pitch, 0.0)
            self._pivot_pos = (0.0, 0.0)

    # ── painting ──

    def paintEvent(self, event):
        if not self._pitch_curve:
            return
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QtCore.Qt.white)
            cam_type = self._cam.cam_type if self._cam else "disk"
            if cam_type == "disk":
                self._draw_disk_mechanism(painter)
            elif cam_type in ("linear", "cylindrical"):
                self._draw_linear_mechanism(painter)
            else:
                painter.drawText(self.rect(), QtCore.Qt.AlignCenter,
                                 tr("Preview: disk/linear/cylindrical cams only"))
        finally:
            painter.end()

    def _draw_disk_mechanism(self, painter):
        x0, y0, w, h_area = self._plot_area()
        cx, cy = x0 + w / 2, y0 + h_area / 2
        scale = self._compute_scale(w, h_area)
        theta = math.radians(self._cam_angle)
        ct, st = math.cos(theta), math.sin(theta)

        is_grooved = self._cam.grooved if self._cam else False

        # solid 用 profile_curve，grooved 用 pitch_curve（槽中心在 pitch 上）
        if is_grooved:
            curve = self._pitch_curve
        else:
            curve = self._profile_curve if self._profile_curve else self._pitch_curve

        if is_grooved:
            # 带槽凸轮：画槽壁（沿切线法线偏移 ±gw/2）
            pen_groove = QtGui.QPen(QtGui.QColor(100, 100, 200), 2)
            painter.setPen(pen_groove)
            gw = self._cam.groove_width / 2.0
            n_pts = len(curve)
            # 外壁
            path_outer = QtGui.QPainterPath()
            for i, p in enumerate(curve):
                p_prev = curve[(i - 1) % n_pts]
                p_next = curve[(i + 1) % n_pts]
                tx = p_next[0] - p_prev[0]
                ty = p_next[1] - p_prev[1]
                tl = math.sqrt(tx * tx + ty * ty)
                if tl < 1e-12:
                    continue
                nx, ny = -ty / tl, tx / tl
                ox, oy = p[0] + gw * nx, p[1] + gw * ny
                wx = ox * ct - oy * st
                wy = ox * st + oy * ct
                sx, sy = cx + wx * scale, cy - wy * scale
                if i == 0:
                    path_outer.moveTo(sx, sy)
                else:
                    path_outer.lineTo(sx, sy)
            path_outer.closeSubpath()
            painter.drawPath(path_outer)
            # 内壁
            path_inner = QtGui.QPainterPath()
            for i, p in enumerate(curve):
                p_prev = curve[(i - 1) % n_pts]
                p_next = curve[(i + 1) % n_pts]
                tx = p_next[0] - p_prev[0]
                ty = p_next[1] - p_prev[1]
                tl = math.sqrt(tx * tx + ty * ty)
                if tl < 1e-12:
                    continue
                nx, ny = -ty / tl, tx / tl
                ix, iy = p[0] - gw * nx, p[1] - gw * ny
                wx = ix * ct - iy * st
                wy = ix * st + iy * ct
                sx, sy = cx + wx * scale, cy - wy * scale
                if i == 0:
                    path_inner.moveTo(sx, sy)
                else:
                    path_inner.lineTo(sx, sy)
            path_inner.closeSubpath()
            painter.drawPath(path_inner)
        else:
            # 实心凸轮：画 profile 曲线
            pen_cam = QtGui.QPen(QtGui.QColor(100, 100, 200), 2)
            painter.setPen(pen_cam)
            path = QtGui.QPainterPath()
            for i, p in enumerate(curve):
                wx = p[0] * ct - p[1] * st
                wy = p[0] * st + p[1] * ct
                sx, sy = cx + wx * scale, cy - wy * scale
                if i == 0:
                    path.moveTo(sx, sy)
                else:
                    path.lineTo(sx, sy)
            path.closeSubpath()
            painter.drawPath(path)

        # Draw base circle (dashed)
        pen_base = QtGui.QPen(QtGui.QColor(180, 180, 180), 1)
        pen_base.setStyle(QtCore.Qt.DashLine)
        painter.setPen(pen_base)
        rb = self._cam.base_radius
        painter.drawEllipse(QtCore.QPointF(cx, cy), rb * scale, rb * scale)

        # Draw arm for oscillating
        if self._follower.follower_type == FollowerType.OSCILLATING:
            pen_arm = QtGui.QPen(QtCore.Qt.black, 2)
            painter.setPen(pen_arm)
            ppx = cx + self._pivot_pos[0] * scale
            ppy = cy - self._pivot_pos[1] * scale
            rrx = cx + self._roller_pos[0] * scale
            rry = cy - self._roller_pos[1] * scale
            painter.drawLine(int(ppx), int(ppy), int(rrx), int(rry))
            painter.setBrush(QtCore.Qt.gray)
            painter.drawEllipse(QtCore.QPointF(ppx, ppy), 5, 5)

        # Draw roller
        roller_r = self._follower.roller_radius
        rx = cx + self._roller_pos[0] * scale
        ry = cy - self._roller_pos[1] * scale
        pen_roller = QtGui.QPen(QtGui.QColor(200, 50, 200), 2)
        painter.setPen(pen_roller)
        painter.setBrush(QtGui.QColor(255, 200, 255, 80))
        painter.drawEllipse(
            QtCore.QPointF(rx, ry), roller_r * scale, roller_r * scale)

        # Draw cam center cross
        painter.setPen(QtGui.QPen(QtCore.Qt.red, 2))
        painter.drawLine(int(cx - 6), int(cy), int(cx + 6), int(cy))
        painter.drawLine(int(cx), int(cy - 6), int(cx), int(cy + 6))

        # Draw pressure angle text
        pa = self._calc_pressure_angle()
        if pa is not None:
            if pa <= 20:
                color = QtGui.QColor(0, 128, 0)
            elif pa <= 30:
                color = QtGui.QColor(200, 128, 0)
            else:
                color = QtGui.QColor(200, 0, 0)
            painter.setPen(color)
            font = painter.font()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(10, 20, f"α = {pa:.1f}°")

    def _draw_linear_mechanism(self, painter):
        """Linear Cam预览：凸轮体水平移动，Follower在固定位置上下运动。"""
        pitch = self._pitch_curve
        profile = self._profile_curve if self._profile_curve else pitch
        if not profile:
            return

        x0, y0, w, h_area = self._plot_area()
        rb = self._cam.base_radius
        base_h = self._cam.thickness
        roller_r = self._follower.roller_radius
        L = rb * 2 * math.pi  # 凸轮展开长度

        # 当前位置（0~1）
        frac = (self._cam_angle % 360.0) / 360.0
        # 凸轮偏移量（凸轮向左移动，Follower固定在中心）
        cam_offset = frac * L

        # 计算数据范围（显示Follower附近的一段）
        ys = [p[1] for p in profile]
        y_max = max(ys) + roller_r + 5

        # 缩放：水平方向显示约 1.5L 的范围，垂直方向自适应
        view_w = L * 1.5
        sx = w / view_w
        sy = h_area / (y_max + base_h + 1e-6)
        scale = min(sx, sy) * 0.9

        # Follower固定在屏幕中心
        foll_x = x0 + w / 2
        # 底部基线
        base_y = y0 + h_area * 0.75

        def to_screen(world_x, world_y):
            # 凸轮偏移后，Follower在中心
            sx = foll_x + (world_x - cam_offset) * scale
            sy = base_y - world_y * scale
            return sx, sy

        # ── 画凸轮体（底座矩形 + 轮廓曲线）──
        # 底座
        pen_body = QtGui.QPen(QtGui.QColor(180, 180, 180), 1)
        painter.setPen(pen_body)
        painter.setBrush(QtGui.QColor(220, 220, 220))

        # 画底座矩形（跟随凸轮偏移）
        bx1, by1 = to_screen(cam_offset - view_w / 2, 0)
        bx2, by2 = to_screen(cam_offset + view_w / 2, base_h)
        painter.drawRect(QtCore.QRectF(bx1, by1, bx2 - bx1, by2 - by1))

        # 轮廓曲线
        pen_prof = QtGui.QPen(QtGui.QColor(100, 100, 200), 2)
        painter.setPen(pen_prof)
        painter.setBrush(QtCore.Qt.NoBrush)
        path = QtGui.QPainterPath()
        for i, p in enumerate(profile):
            sx, sy = to_screen(p[0], p[1])
            if i == 0:
                path.moveTo(sx, sy)
            else:
                path.lineTo(sx, sy)
        painter.drawPath(path)

        # ── Follower（固定在中心）──
        # 滚子接触点：在 profile 上当前 frac 位置的高度
        contact_idx = int(frac * len(profile)) % len(profile)
        contact_h = profile[contact_idx][1]
        roller_screen_y = base_y - (contact_h + roller_r) * scale

        # 画Follower导路（垂直虚线）
        pen_guide = QtGui.QPen(QtGui.QColor(150, 150, 150), 1)
        pen_guide.setStyle(QtCore.Qt.DashLine)
        painter.setPen(pen_guide)
        painter.drawLine(int(foll_x), int(base_y - y_max * scale),
                         int(foll_x), int(base_y + 20))

        # 画滚子
        pen_roller = QtGui.QPen(QtGui.QColor(200, 50, 200), 2)
        painter.setPen(pen_roller)
        painter.setBrush(QtGui.QColor(255, 200, 255, 80))
        painter.drawEllipse(QtCore.QPointF(foll_x, roller_screen_y),
                            roller_r * scale, roller_r * scale)

        # 画Follower杆（从滚子向上）
        pen_foll = QtGui.QPen(QtCore.Qt.black, 2)
        painter.setPen(pen_foll)
        top_y = y0 + self.MARGIN
        painter.drawLine(int(foll_x), int(roller_screen_y),
                         int(foll_x), int(top_y))

        # ── 位置指示 ──
        painter.setPen(QtGui.QPen(QtCore.Qt.gray, 1))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(10, self.height() - 10,
                         tr("Pos:") + f" {self._cam_angle:.0f}° ({frac * L:.1f} mm)")

        # ── Pressure Angle文字 ──
        pa = self._calc_pressure_angle()
        if pa is not None:
            if pa <= 20:
                color = QtGui.QColor(0, 128, 0)
            elif pa <= 30:
                color = QtGui.QColor(200, 128, 0)
            else:
                color = QtGui.QColor(200, 0, 0)
            painter.setPen(color)
            font = painter.font()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(10, 20, f"α = {pa:.1f}°")

    def _calc_pressure_angle(self):
        """计算当前凸轮角度下的Pressure Angle。"""
        if not self._cam or not self._follower or not self._roller_pos:
            return None
        n = len(self._pitch_curve)
        if n < 2:
            return None

        cam_type = self._cam.cam_type
        R = self._cam.base_radius
        ft = self._follower.follower_type

        if cam_type in ("linear", "cylindrical"):
            idx = int((self._cam_angle / 360.0) * n) % n
            idx_next = (idx + 1) % n
            dx = self._pitch_curve[idx_next][0] - self._pitch_curve[idx][0]
            dh = self._pitch_curve[idx_next][1] - self._pitch_curve[idx][1]
            dtheta = dx / R if R > 1e-12 else 1.0
            dh_dtheta = dh / dtheta if abs(dtheta) > 1e-12 else 0.0
            return pressure_angle_linear_cyl(R, dh_dtheta)

        # ── Disk Cam ──
        rb = self._cam.base_radius
        idx = int((-self._cam_angle / 360.0) * n) % n
        idx_next = (idx + 1) % n
        r0 = math.sqrt(self._pitch_curve[idx][0]**2 + self._pitch_curve[idx][1]**2)
        r1 = math.sqrt(self._pitch_curve[idx_next][0]**2 + self._pitch_curve[idx_next][1]**2)
        dr = r1 - r0
        h = r0 - rb
        dtheta = 2 * math.pi / n
        dh_dtheta = dr / dtheta

        if ft == FollowerType.TRANSLATING_ONCENTER:
            return pressure_angle_oncenter(rb, h, dh_dtheta)

        elif ft == FollowerType.TRANSLATING_OFFCENTER:
            e = self._follower.offset
            return pressure_angle_offcenter(rb, h, e, dh_dtheta)

        elif ft == FollowerType.OSCILLATING:
            L = self._follower.arm_length
            return pressure_angle_oscillating(rb, h, L, dh_dtheta)

        return None

    def _plot_area(self):
        m = self.MARGIN
        return (m, m, self.width() - 2 * m, self.height() - 2 * m)

    def _compute_scale(self, w, h_area):
        if not self._pitch_curve or not self._cam:
            return 1.0
        rb = self._cam.base_radius
        all_r = [math.sqrt(p[0]**2 + p[1]**2) for p in self._pitch_curve]
        r_max = max(all_r) if all_r else rb
        r_max = max(r_max, rb + self._follower.roller_radius)
        if self._follower.follower_type == FollowerType.OSCILLATING:
            px, py = self._follower.pivot_x, self._follower.pivot_y
            d = math.sqrt(px**2 + py**2)
            r_max = max(r_max, d + self._arm_length)
        available = min(w, h_area) / 2
        return available / (r_max * 1.1) if r_max > 0 else 1.0
