"""凸轮参数任务面板（支持动态多段Motion）。"""

from __future__ import annotations
import math
import FreeCAD as App
import FreeCADGui as Gui

from ...motion.registry import list_all as list_motion_profiles
from ...geometry.follower import CamParams, FollowerParams, FollowerType, MotionSegment, get_roller_radius
from ...geometry.base import CamBuilderFactory
from ...chart.preview import CamPreviewWidget
from ...i18n import tr, trf

def _get_qt():
    for mod_name in ["PySide6", "PySide2", "PyQt6", "PyQt5"]:
        try:
            mod = __import__(mod_name)
            QtWidgets = getattr(mod, "QtWidgets", None)
            QtCore = getattr(mod, "QtCore", None)
            QtGui = getattr(mod, "QtGui", None)
            if QtWidgets and QtCore:
                return QtWidgets, QtCore, QtGui
        except ImportError:
            continue
    raise ImportError("找不到 Qt 绑定")


def _get_chart_panel():
    """惰性加载图表面板（QtCharts 可能不可用）。"""
    try:
        from .analysis_panel import CamAnalysisPanel
        return CamAnalysisPanel
    except Exception as e:
        import FreeCAD as App
        App.Console.PrintError(f"FCCamTrax: 图表面板加载失败: {e}\n")
        return None


# ──────────────────────────────────────────────
# Motion Segments器对话框（独立大表格）
# ──────────────────────────────────────────────

class SegmentEditorDialog:
    """独立弹出的Motion Segments表格。"""

    def __init__(self, parent, segments: list[MotionSegment]):
        QtWidgets, QtCore, QtGui = _get_qt()
        self.QtWidgets = QtWidgets
        self.QtCore = QtCore
        self.dialog = QtWidgets.QDialog(parent)
        self.dialog.setWindowTitle(tr("Motion Segments"))
        self.dialog.setMinimumSize(720, 480)
        self.segments = list(segments)
        self._accepted = False
        self._setup_ui()

    def _setup_ui(self):
        QW = self.QtWidgets
        layout = QW.QVBoxLayout(self.dialog)

        # ── 表格 ──
        self.table = QW.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            tr("Start (°)"), tr("End (°)"),
            tr("Start Lift (mm)"), tr("End Lift (mm)"), tr("Motion Law")
        ])
        header = self.table.horizontalHeader()
        for col in range(4):
            header.setSectionResizeMode(col, QW.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QW.QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(32)
        layout.addWidget(self.table)

        # 填充已有数据
        for seg in self.segments:
            self._append_row(seg.start_angle, seg.end_angle,
                             seg.start_lift, seg.end_lift, seg.motion_name)

        # ── 工具栏 ──
        btn_row = QW.QHBoxLayout()
        btn_add = QW.QPushButton(tr("Add"))
        btn_del = QW.QPushButton(tr("Delete"))
        btn_up = QW.QPushButton(tr("Up"))
        btn_down = QW.QPushButton(tr("Down"))
        btn_default = QW.QPushButton(tr("Default 4"))
        btn_add.clicked.connect(self._add_segment)
        btn_del.clicked.connect(self._del_segment)
        btn_up.clicked.connect(self._move_up)
        btn_down.clicked.connect(self._move_down)
        btn_default.clicked.connect(self._default_segments)
        for b in (btn_add, btn_del, btn_up, btn_down, btn_default):
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── 确定/取消 ──
        btn_box = QW.QDialogButtonBox(QW.QDialogButtonBox.Ok | QW.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.dialog.reject)
        layout.addWidget(btn_box)

    def _append_row(self, sa, ea, sl, el, mn):
        QW = self.QtWidgets
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, val in enumerate([sa, ea, sl, el]):
            item = QW.QTableWidgetItem(str(val))
            self.table.setItem(row, col, item)
        combo = QW.QComboBox()
        cn_names = list(list_motion_profiles())
        combo.addItems(cn_names)
        idx = combo.findText(mn)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        self.table.setCellWidget(row, 4, combo)

    def _add_segment(self):
        row = self.table.rowCount()
        last_end = 0.0
        if row > 0:
            item = self.table.item(row - 1, 1)
            if item:
                last_end = float(item.text())
        self._append_row(last_end, min(last_end + 30, 360), 0, 0, "Cycloidal")
        self.table.scrollToBottom()

    def _del_segment(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _move_up(self):
        row = self.table.currentRow()
        if row > 0:
            self._swap_rows(row, row - 1)
            self.table.setCurrentCell(row - 1, 0)

    def _move_down(self):
        row = self.table.currentRow()
        if 0 <= row < self.table.rowCount() - 1:
            self._swap_rows(row, row + 1)
            self.table.setCurrentCell(row + 1, 0)

    def _swap_rows(self, r1, r2):
        for col in range(4):
            t1 = self.table.item(r1, col)
            t2 = self.table.item(r2, col)
            if t1 and t2:
                v1, v2 = t1.text(), t2.text()
                t1.setText(v2)
                t2.setText(v1)
        c1 = self.table.cellWidget(r1, 4)
        c2 = self.table.cellWidget(r2, 4)
        if c1 and c2:
            i1, i2 = c1.currentIndex(), c2.currentIndex()
            c1.setCurrentIndex(i2)
            c2.setCurrentIndex(i1)

    def _default_segments(self):
        self.table.setRowCount(0)
        defaults = [
            (0, 120, 0, 20, "Cycloidal"),
            (120, 150, 20, 20, "Cycloidal"),
            (150, 270, 20, 0, "Cycloidal"),
            (270, 360, 0, 0, "Cycloidal"),
        ]
        for sa, ea, sl, el, mn in defaults:
            self._append_row(sa, ea, sl, el, mn)

    def _on_accept(self):
        self.segments = self._read_segments()
        self._accepted = True
        self.dialog.accept()

    def _read_segments(self):
        segments = []
        for row in range(self.table.rowCount()):
            try:
                sa = float(self.table.item(row, 0).text())
                ea = float(self.table.item(row, 1).text())
                sl = float(self.table.item(row, 2).text())
                el = float(self.table.item(row, 3).text())
            except (ValueError, AttributeError):
                App.Console.PrintWarning(
                    f"FCCamTrax: Segment {row + 1} 行数据无效，已跳过。\n")
                continue
            combo = self.table.cellWidget(row, 4)
            mn = combo.currentText() if combo else "Cycloidal"
            segments.append(MotionSegment(start_angle=sa, end_angle=ea,
                                          start_lift=sl, end_lift=el, motion_name=mn))
        return segments

    def exec(self):
        self.dialog.exec()
        return self._accepted, self.segments


# ──────────────────────────────────────────────
# 主任务面板
# ──────────────────────────────────────────────

class CamTaskPanel:
    def __init__(self):
        QtWidgets, QtCore, QtGui = _get_qt()
        self.QtWidgets = QtWidgets
        self.QtCore = QtCore
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle(tr("Create Cam"))
        self._analysis_panel = None
        self._segments: list[MotionSegment] = []
        self._setup_ui()
        self._default_segments()

    def _setup_ui(self):
        QW = self.QtWidgets
        layout = QW.QVBoxLayout(self.form)

        self.form.setWindowTitle(tr("Create Cam"))

        # ── Cam Type ──
        group_cam = QW.QGroupBox(tr("Cam Type"))
        gl = QW.QFormLayout(group_cam)
        self.combo_cam_type = QW.QComboBox()
        self.combo_cam_type.addItems([tr("Disk Cam"), tr("Cylindrical Cam"), tr("Linear Cam")])
        self.combo_cam_type.currentIndexChanged.connect(self._on_cam_type_changed)
        gl.addRow(tr("Type:"), self.combo_cam_type)
        layout.addWidget(group_cam)

        # ── Geometry ──
        group_geom = QW.QGroupBox(tr("Geometry"))
        gl = QW.QFormLayout(group_geom)
        self.spin_base_radius = self._make_spin(30.0, 1.0, 500.0, "mm")
        self.spin_thickness = self._make_spin(15.0, 1.0, 200.0, "mm")
        self.spin_bore_radius = self._make_spin(8.0, 0.0, 100.0, "mm")
        self.spin_ppd = self._make_spin(1.0, 1.0, 20.0, tr("pts/°"))
        self.spin_groove_width = self._make_spin(6.0, 2.0, 50.0, "mm")
        self.spin_groove_depth = self._make_spin(4.0, 1.0, 30.0, "mm")
        self.spin_blank_radius = self._make_spin(60.0, 10.0, 500.0, "mm")
        self.check_grooved = QW.QCheckBox(tr("Grooved"))
        self.check_grooved.toggled.connect(self._on_grooved_toggled)
        gl.addRow(tr("Base Radius:"), self.spin_base_radius)
        gl.addRow(tr("Thickness:"), self.spin_thickness)
        gl.addRow(tr("Bore Radius:"), self.spin_bore_radius)
        gl.addRow("", self.check_grooved)
        gl.addRow(tr("Groove Width:"), self.spin_groove_width)
        gl.addRow(tr("Groove Depth:"), self.spin_groove_depth)
        gl.addRow(tr("Blank Radius:"), self.spin_blank_radius)
        gl.addRow(tr("Points/deg:"), self.spin_ppd)
        layout.addWidget(group_geom)

        # ── Motion（按钮打开独立表格）──
        group_seg = QW.QGroupBox(tr("Motion"))
        seg_layout = QW.QHBoxLayout(group_seg)
        self.lbl_seg_info = QW.QLabel("4" + tr(" seg"))
        self.lbl_seg_info.setMinimumWidth(60)
        btn_edit_seg = QW.QPushButton(tr("Edit Segments..."))
        btn_edit_seg.setMinimumHeight(36)
        btn_edit_seg.clicked.connect(self._open_segment_editor)
        seg_layout.addWidget(QW.QLabel(tr("Current:")))
        seg_layout.addWidget(self.lbl_seg_info)
        seg_layout.addWidget(btn_edit_seg)
        seg_layout.addStretch()
        layout.addWidget(group_seg)

        # ── Design Check按钮 ──
        btn_check = QW.QPushButton(tr("Design Check..."))
        btn_check.clicked.connect(self._open_design_check)
        layout.addWidget(btn_check)

        # ── Follower + 预览 并排 ──
        preview_row = QW.QHBoxLayout()

        # 左侧：Follower选项
        group_follower = QW.QGroupBox(tr("Follower"))
        fl = QW.QFormLayout(group_follower)
        self.combo_follower_type = QW.QComboBox()
        self.combo_follower_type.addItems([
            tr("Translating On-center"), tr("Translating Off-center"), tr("Oscillating"),
        ])
        self.combo_follower_type.currentIndexChanged.connect(self._on_follower_type_changed)
        fl.addRow(tr("Type:"), self.combo_follower_type)
        self.spin_offset = self._make_spin(0.0, -100.0, 100.0, "mm")
        self.spin_arm_length = self._make_spin(60.0, 1.0, 500.0, "mm")
        self.spin_pivot_x = self._make_spin(60.0, -500.0, 500.0, "mm")
        self.spin_pivot_y = self._make_spin(0.0, -500.0, 500.0, "mm")
        self.spin_initial_angle = self._make_spin(151.0, 0.0, 360.0, "°")
        fl.addRow(tr("Offset:"), self.spin_offset)
        fl.addRow(tr("Arm Length:"), self.spin_arm_length)
        fl.addRow(tr("Pivot X:"), self.spin_pivot_x)
        fl.addRow(tr("Pivot Y:"), self.spin_pivot_y)
        fl.addRow(tr("Initial Angle:"), self.spin_initial_angle)

        btn_auto = QW.QPushButton(tr("Recommend"))
        btn_auto.setToolTip(tr("Recommend arm, pivot, initial angle from base radius and max lift"))
        btn_auto.clicked.connect(self._auto_recommend_follower)
        self._btn_auto_recommend = btn_auto
        fl.addRow("", btn_auto)

        preview_row.addWidget(group_follower)

        # 右侧：预览
        preview_col = QW.QVBoxLayout()
        self._preview = CamPreviewWidget()
        self._preview.setMinimumHeight(200)
        preview_col.addWidget(self._preview)

        slider_layout = QW.QHBoxLayout()
        self._btn_play = QW.QPushButton("▶")
        self._btn_play.setCheckable(True)
        self._btn_play.setFixedWidth(40)
        self._btn_play.toggled.connect(self._on_play_toggled)
        slider_layout.addWidget(self._btn_play)

        self._slider_angle = QW.QSlider(self.QtCore.Qt.Horizontal)
        self._slider_angle.setRange(0, 360)
        self._slider_angle.setValue(0)
        self._slider_angle.setTickPosition(QW.QSlider.TicksBelow)
        self._slider_angle.setTickInterval(10)
        self._slider_angle.valueChanged.connect(self._on_angle_changed)
        slider_layout.addWidget(self._slider_angle, 1)

        self._lbl_angle = QW.QLabel("0°")
        self._lbl_angle.setMinimumWidth(40)
        slider_layout.addWidget(self._lbl_angle)

        preview_col.addLayout(slider_layout)
        preview_row.addLayout(preview_col, 1)

        layout.addLayout(preview_row)

        # ── 按钮 ──
        btn_layout = QW.QHBoxLayout()
        self.btn_generate = QW.QPushButton(tr("Generate Cam"))
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_analyze = QW.QPushButton(tr("Analysis Charts"))
        self.btn_analyze.clicked.connect(self._on_analyze)
        self.btn_analyze.setEnabled(False)
        btn_layout.addWidget(self.btn_generate)
        btn_layout.addWidget(self.btn_analyze)
        layout.addLayout(btn_layout)

        layout.addStretch()
        self._on_follower_type_changed(0)
        self._on_cam_type_changed(0)
        self._cam_params = None
        self._follower_params = None
        self._cached_builder = None

        # 动画定时器
        self._anim_timer = self.QtCore.QTimer()
        self._anim_timer.setInterval(30)  # ~33fps
        self._anim_timer.timeout.connect(self._on_anim_tick)

        # 参数变化 → 刷新预览
        for spin in [self.spin_base_radius,
                     self.spin_offset, self.spin_arm_length,
                     self.spin_pivot_x, self.spin_pivot_y,
                     self.spin_initial_angle]:
            spin.valueChanged.connect(self._update_preview)
        self.combo_follower_type.currentIndexChanged.connect(self._update_preview)

        # 初始刷新
        self._update_preview()

    def _make_spin(self, default, min_val, max_val, suffix=""):
        spin = self.QtWidgets.QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSuffix(f" {suffix}" if suffix else "")
        spin.setDecimals(1)
        return spin

    def _default_segments(self):
        self._segments = [
            MotionSegment(0, 120, 0, 20, "Cycloidal"),
            MotionSegment(120, 150, 20, 20, "Cycloidal"),
            MotionSegment(150, 270, 20, 0, "Cycloidal"),
            MotionSegment(270, 360, 0, 0, "Cycloidal"),
        ]
        self._update_seg_label()

    def _update_seg_label(self):
        self.lbl_seg_info.setText(f"{len(self._segments)}" + tr(" seg"))

    def _open_segment_editor(self):
        dlg = SegmentEditorDialog(self.form, self._segments)
        ok, segments = dlg.exec()
        if ok:
            self._segments = segments
            self._update_seg_label()

    def _on_follower_type_changed(self, index):
        is_offcenter = (index == 1)
        is_oscillating = (index == 2)
        self.spin_offset.setVisible(is_offcenter)
        self.spin_arm_length.setVisible(is_oscillating)
        self.spin_pivot_x.setVisible(is_oscillating)
        self.spin_pivot_y.setVisible(is_oscillating)
        self.spin_initial_angle.setVisible(is_oscillating)
        self._btn_auto_recommend.setVisible(is_oscillating)

    def _auto_recommend_follower(self):
        """根据基圆半径和最大升程自动推荐OscillatingFollower参数。"""
        rb = self.spin_base_radius.value()
        max_lift = max((s.end_lift for s in self._segments), default=0.0)
        if max_lift <= 0:
            self.QtWidgets.QMessageBox.warning(
                self.form, tr("Notice"), tr("Set motion segments first (max lift > 0)."))
            return

        # 推荐摆臂长度 L ≥ 3 × h_max 且 L ≥ 1.5 × rb
        L = max(3.0 * max_lift, 1.5 * rb)
        # 推荐支点距离 d ≥ rb + h_max 且 d ≥ L - rb（保证滚子能接触基圆）
        d = max(rb + max_lift, L - rb)
        # 支点角度 α = 60°（支点高于圆心，摆臂更自然）
        alpha = math.radians(60.0)
        px = d * math.cos(alpha)
        py = d * math.sin(alpha)
        # 初始角度 ψ₀ = α + arccos((rb² - d² - L²) / (2·L·d))
        cos_val = (rb**2 - d**2 - L**2) / (2 * L * d)
        cos_val = max(-1.0, min(1.0, cos_val))
        psi0 = math.degrees(alpha + math.acos(cos_val)) % 360

        self.spin_arm_length.setValue(round(L, 1))
        self.spin_pivot_x.setValue(round(px, 1))
        self.spin_pivot_y.setValue(round(py, 1))
        self.spin_initial_angle.setValue(round(psi0, 1))

    def _compute_design_check(self):
        """计算当前设计参数，返回 (pa, swing, recommended_text)。"""
        rb = self.spin_base_radius.value()
        max_lift = max((s.end_lift for s in self._segments), default=0.0)
        ft_idx = self.combo_follower_type.currentIndex()
        pa = None
        swing = None
        rec_lines = []
        max_lift_ok = max_lift > 0

        # 用 builder 算实际最大Pressure Angle
        actual_pa = None
        builder = self._get_builder()
        if builder:
            try:
                pas = builder.pressure_angles()
                if pas:
                    actual_pa = max(pas)
            except Exception:
                pass

        if ft_idx == 0:  # Translating On-center
            if actual_pa is not None:
                pa = actual_pa
            elif max_lift_ok and rb > 0:
                pa = math.degrees(math.atan2(max_lift, rb))
            if rb > 0 and max_lift_ok:
                rb_rec = max_lift / math.tan(math.radians(30))
                rec_lines.append(trf("• Recommended base radius ≥ {rec:.1f} mm (target ≤ 30°)", rec=rb_rec))
            if pa is not None:
                if pa <= 30:
                    rec_lines.append(trf("• Pressure angle ≤ 30°, current {pa:.1f}°", pa=pa))
                else:
                    rec_lines.append(trf("• ⚠ Pressure angle {pa:.1f}° > 30°, increase base radius", pa=pa))

        elif ft_idx == 1:  # Translating Off-center
            if actual_pa is not None:
                pa = actual_pa
            else:
                e = abs(self.spin_offset.value())
                if max_lift_ok and rb > e:
                    d = math.sqrt((rb + max_lift)**2 - e**2)
                    pa = math.degrees(math.atan2(max_lift, d))
            rec_lines.append(tr("• Reduce offset or increase base radius"))
            if pa:
                if pa <= 30:
                    rec_lines.append(trf("• Pressure angle ≤ 30°, current {pa:.1f}°", pa=pa))
                else:
                    rec_lines.append(trf("• ⚠ Pressure angle {pa:.1f}° > 30°, increase base radius or reduce offset", pa=pa))

        elif ft_idx == 2:  # Oscillating
            L = self.spin_arm_length.value()
            px = self.spin_pivot_x.value()
            py = self.spin_pivot_y.value()
            d_pivot = math.sqrt(px**2 + py**2)

            if L > 0 and d_pivot > 0:
                if max_lift_ok:
                    swing = math.degrees(max_lift / L)

                d_rec = rb + max_lift if max_lift_ok else rb * 1.5
                if d_pivot < d_rec:
                    rec_lines.append(trf("• Recommended pivot distance ≥ {d:.1f} mm (current {c:.1f} mm)",
                                         d=d_rec, c=d_pivot))

                alpha = math.atan2(py, px)
                cos_val = (rb**2 - d_pivot**2 - L**2) / (2 * L * d_pivot)
                if abs(cos_val) <= 1.0:
                    psi0_rec = math.degrees(alpha + math.acos(cos_val)) % 360
                    cur_angle = self.spin_initial_angle.value()
                    rec_lines.append(trf("• Recommended initial angle ≈ {r:.1f}° (current {c:.1f}°)",
                                         r=psi0_rec, c=cur_angle))

            if actual_pa is not None:
                pa = actual_pa
            elif L > rb:
                pa = math.degrees(math.atan2(max_lift if max_lift_ok else 1, L - rb))
            else:
                pa = 90.0

            L_rec = max(3 * max_lift, 1.5 * rb) if max_lift_ok else 1.5 * rb
            rec_lines.append(trf("• Recommended arm length ≥ {rec:.1f} mm (current {cur:.1f} mm)",
                                 rec=L_rec, cur=L))
            if L < L_rec:
                rec_lines.append(tr("  • ⚠ Arm too short, pressure angle may be too high"))
            if pa:
                if pa <= 30:
                    rec_lines.append(trf("• Pressure angle ≤ 30°, current {pa:.1f}°", pa=pa))
                else:
                    rec_lines.append(trf("• ⚠ Pressure angle {pa:.1f}° > 30°, increase arm length or base radius", pa=pa))
            if swing is not None:
                rec_lines.append(trf("• Max swing angle ≈ {swing:.1f}°", swing=swing))
        else:
            rec_lines.append(tr("• Design check not available for this follower type"))

        return pa, swing, rec_lines

    def _open_design_check(self):
        """弹出Design Check对话框。"""
        QW = self.QtWidgets
        pa, swing, rec_lines = self._compute_design_check()
        msg = QW.QMessageBox(self.form)
        msg.setWindowTitle(tr("Design Check"))
        msg.setIcon(QW.QMessageBox.Information)

        text = ""

        # Pressure Angle
        if pa is not None:
            if pa <= 20:
                color = "Green"
            elif pa <= 30:
                color = "Orange"
            else:
                color = "Red"
            text += tr("Pressure Angle") + f": {pa:.1f}° ({color})\n"
        if swing is not None:
            text += tr("Max swing angle") + f": {swing:.1f}°\n"

        text += "\n" + tr("Recommendations:") + "\n" + "\n".join(rec_lines)
        msg.setText(text)

        # 颜色Notice
        if pa is not None and pa > 30:
            msg.setIcon(QW.QMessageBox.Warning)

        msg.exec()

    def _on_cam_type_changed(self, index):
        is_disk = (index == 0)
        is_cyl = (index == 1)
        is_linear = (index == 2)
        self.spin_bore_radius.setVisible(is_disk)
        self.spin_thickness.setVisible(is_disk or is_linear)
        self.check_grooved.setVisible(is_disk or is_linear)
        if is_cyl:
            self.spin_groove_width.setVisible(True)
            self.spin_groove_depth.setVisible(True)
            self.spin_blank_radius.setVisible(False)
        else:
            self._on_grooved_toggled(self.check_grooved.isChecked())
        self._update_geom_labels(is_disk)

    def _on_grooved_toggled(self, checked):
        self.spin_groove_width.setVisible(checked)
        self.spin_groove_depth.setVisible(checked)
        self.spin_blank_radius.setVisible(checked)

    def _update_geom_labels(self, is_disk):
        idx_radius = 0
        layout = self.spin_base_radius.parent()
        if isinstance(layout, self.QtWidgets.QFormLayout):
            lbl = layout.itemAt(idx_radius, self.QtWidgets.QFormLayout.LabelRole)
            if lbl and lbl.widget():
                idx = self.combo_cam_type.currentIndex()
                labels = [tr("Base Radius:"), tr("Cylinder Radius:"), tr("Unwrap Radius:")]
                lbl.widget().setText(labels[idx] if idx < len(labels) else tr("Base Radius:"))

    def _build_params(self):
        cam_type_map = {tr("Disk Cam"): "disk", tr("Cylindrical Cam"): "cylindrical",
                        tr("Linear Cam"): "linear"}
        cam_type = cam_type_map.get(self.combo_cam_type.currentText(), "disk")
        is_cyl = (cam_type == "cylindrical")
        cam = CamParams(
            cam_type=cam_type,
            base_radius=self.spin_base_radius.value(),
            thickness=self.spin_thickness.value(),
            bore_radius=self.spin_bore_radius.value(),
            points_per_degree=self.spin_ppd.value(),
            grooved=is_cyl or self.check_grooved.isChecked(),
            groove_width=self.spin_groove_width.value(),
            groove_depth=self.spin_groove_depth.value(),
            blank_radius=self.spin_blank_radius.value(),
            segments=list(self._segments),
        )

        ft_map = {
            0: FollowerType.TRANSLATING_ONCENTER,
            1: FollowerType.TRANSLATING_OFFCENTER,
            2: FollowerType.OSCILLATING,
        }

        follower = FollowerParams(
            follower_type=ft_map.get(self.combo_follower_type.currentIndex(),
                                     FollowerType.TRANSLATING_ONCENTER),
            roller_radius=get_roller_radius(cam.grooved, cam.groove_width),
            offset=self.spin_offset.value(),
            arm_length=self.spin_arm_length.value(),
            pivot_x=self.spin_pivot_x.value(),
            pivot_y=self.spin_pivot_y.value(),
            initial_angle=self.spin_initial_angle.value(),
        )

        return cam, follower

    def _get_builder(self):
        """获取缓存的 builder（参数变化时清除）。"""
        if self._cached_builder is None:
            try:
                cam, follower = self._build_params()
                self._cached_builder = CamBuilderFactory.create(
                    cam.cam_type, cam, follower)
            except Exception:
                return None
        return self._cached_builder

    def _invalidate_builder_cache(self):
        """参数变化时清除缓存。"""
        self._cached_builder = None

    def _validate(self):
        segments = self._segments
        if not segments:
            self.QtWidgets.QMessageBox.warning(
                self.form, tr("Parameter Error"), tr("Add at least one motion segment.")
            )
            return False
        if abs(segments[0].start_angle) > 0.1:
            self.QtWidgets.QMessageBox.warning(
                self.form, tr("Parameter Error"),
                trf("First segment start angle must be 0° (current {angle}°)", angle=segments[0].start_angle)
            )
            return False
        if abs(segments[-1].end_angle - 360.0) > 0.1:
            self.QtWidgets.QMessageBox.warning(
                self.form, tr("Parameter Error"),
                trf("Last segment end angle must be 360° (current {angle}°)", angle=segments[-1].end_angle)
            )
            return False
        for i in range(len(segments) - 1):
            if abs(segments[i].end_angle - segments[i + 1].start_angle) > 0.1:
                self.QtWidgets.QMessageBox.warning(
                    self.form, tr("Parameter Error"),
                    trf("Segment {i} end angle ({a}°) ≠ segment {j} start angle ({b}°)",
                        i=i+1, a=segments[i].end_angle, j=i+2, b=segments[i+1].start_angle)
                )
                return False

        # 滚子半径检查
        rb = self.spin_base_radius.value()
        roller_r = 5.0
        try:
            _, follower = self._build_params()
            roller_r = follower.roller_radius
        except Exception:
            pass
        if roller_r > 0 and roller_r >= rb:
            self.QtWidgets.QMessageBox.warning(
                self.form, tr("Design Warning"),
                trf("Roller radius ({r:.1f} mm) ≥ base radius ({rb:.1f} mm), profile may cross to opposite side",
                    r=roller_r, rb=rb)
            )

        # Pressure Angle检查
        actual_pa = None
        builder = self._get_builder()
        if builder:
            try:
                pas = builder.pressure_angles()
                if pas:
                    actual_pa = max(pas)
            except Exception:
                pass

        max_lift = max((s.end_lift for s in segments), default=0.0)
        ft_idx = self.combo_follower_type.currentIndex()
        pa = actual_pa
        if pa is None:
            if ft_idx == 0:  # Translating On-center
                if max_lift > 0 and rb > 0:
                    pa = math.degrees(math.atan2(max_lift, rb))
            elif ft_idx == 1:  # Translating Off-center
                e = abs(self.spin_offset.value())
                if max_lift > 0 and rb > e:
                    d = math.sqrt((rb + max_lift)**2 - e**2)
                    pa = math.degrees(math.atan2(max_lift, d))
            elif ft_idx == 2:  # Oscillating
                L = self.spin_arm_length.value()
                if max_lift > 0 and L > rb:
                    pa = math.degrees(math.atan2(max_lift, L - rb))
                elif max_lift > 0:
                    pa = 90.0
        if pa is not None and pa > 30:
            self.QtWidgets.QMessageBox.warning(
                self.form, tr("Design Warning"),
                trf("Max pressure angle ≈ {pa:.1f}° > 30°, adjust parameters", pa=pa)
            )

        return True

    def _on_generate(self):
        if not self._validate():
            return

        doc = App.ActiveDocument
        if doc is None:
            doc = App.newDocument("CamDesign")

        cam, follower = self._build_params()

        try:
            builder = CamBuilderFactory.create(cam.cam_type, cam, follower)
            solid = builder.build()

            obj = doc.addObject("Part::Feature", "Cam")
            obj.Shape = solid
            obj.ViewObject.ShapeColor = cam.color

            pitch_points = builder.pitch_curve_points()
            z_off = cam.thickness + 1 if cam.cam_type != "cylindrical" else 0
            if cam.cam_type == "cylindrical":
                pts2 = [App.Vector(p[0], p[1], p[2]) for p in pitch_points]
            else:
                pts2 = [App.Vector(p[0], p[1], z_off) for p in pitch_points]
            import Part
            spline2 = Part.BSplineCurve()
            spline2.approximate(pts2, Tolerance=0.001, DegMax=6)
            close_edge2 = Part.makeLine(pts2[-1], pts2[0])
            wire2 = Part.Wire([spline2.toShape(), close_edge2])
            pitch_obj = doc.addObject("Part::Feature", "PitchCurve")
            pitch_obj.Shape = wire2
            pitch_obj.ViewObject.LineColor = (1.0, 0.0, 0.0)

            doc.recompute()
            Gui.SendMsgToActiveView("ViewFit")

            self._cam_params = cam
            self._follower_params = follower
            self.btn_analyze.setEnabled(True)
            self._update_preview()

            App.Console.PrintMessage("FCCamTrax: " + tr("Cam generated successfully.") + "\n")

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            App.Console.PrintError(f"FCCamTrax: 凸轮生成失败 - {e}\n{tb}\n")
            self.QtWidgets.QMessageBox.critical(
                self.form, tr("Error"), tr("Cam generation failed:\n") + f"{e}" + tr("\n\nSee report view for details.")
            )

    def _on_analyze(self):
        if self._cam_params is None:
            return

        try:
            from ...analysis.analyzer import CamAnalyst
            result = CamAnalyst.analyze(
                self._cam_params, self._follower_params
            )

            ChartPanel = _get_chart_panel()
            if ChartPanel is None:
                self.QtWidgets.QMessageBox.information(
                    self.form, tr("Charts Unavailable"),
                    tr("Chart panel failed to load. Check report view.")
                )
                return

            if self._analysis_panel is None:
                self._analysis_panel = ChartPanel(Gui.getMainWindow())
                Gui.getMainWindow().addDockWidget(
                    self.QtCore.Qt.RightDockWidgetArea, self._analysis_panel
                )

            self._analysis_panel.update_data(result)
            self._analysis_panel.show()
            App.Console.PrintMessage("FCCamTrax: " + tr("Analysis charts updated.") + "\n")

        except Exception as e:
            self.QtWidgets.QMessageBox.critical(
                self.form, tr("Error"), tr("Analysis failed:\n") + f"{e}"
            )
            App.Console.PrintError(f"FCCamTrax: {e}\n")

    # ── Preview ──

    def _on_angle_changed(self, angle: int):
        self._lbl_angle.setText(f"{angle}°")
        self._preview.set_cam_angle(float(angle))

    def _on_play_toggled(self, playing: bool):
        if playing:
            self._anim_timer.start()
        else:
            self._anim_timer.stop()

    def _on_anim_tick(self):
        v = (self._slider_angle.value() + 2) % 360
        self._slider_angle.setValue(v)

    def _update_preview(self):
        """刷新预览（参数变化后调用）。始终从控件读取最新参数。"""
        self._invalidate_builder_cache()
        cam, follower = self._build_params()
        self._preview.set_params(cam, follower)

    def getStandardButtons(self):
        b = self.QtWidgets.QDialogButtonBox
        val = getattr(b.Close, 'value', b.Close)
        return int(val)

    def reject(self):
        if self._analysis_panel:
            self._analysis_panel.close()
        self._anim_timer.stop()
        Gui.Control.closeDialog()
