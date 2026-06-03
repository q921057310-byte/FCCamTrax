"""凸轮参数任务面板（支持动态多段运动定义）。"""

from __future__ import annotations
import math
import FreeCAD as App
import FreeCADGui as Gui

from ...motion.registry import list_all as list_motion_profiles, get as get_motion
from ...geometry.follower import CamParams, FollowerParams, FollowerType, MotionSegment
from ...geometry.base import CamBuilderFactory

_MOTION_CN: dict[str, str] = {
    "Cycloidal": "摆线运动",
    "Harmonic": "简谐运动",
    "Modified Sine": "修正正弦",
    "3-4-5 Polynomial": "3-4-5 多项式",
    "Constant Velocity": "等速运动",
}


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


# ──────────────────────────────────────────────
# 运动段编辑器对话框（独立大表格）
# ──────────────────────────────────────────────

class SegmentEditorDialog:
    """独立弹出的运动段编辑表格。"""

    def __init__(self, parent, segments: list[MotionSegment]):
        QtWidgets, QtCore, QtGui = _get_qt()
        self.QtWidgets = QtWidgets
        self.QtCore = QtCore
        self.dialog = QtWidgets.QDialog(parent)
        self.dialog.setWindowTitle("运动段编辑")
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
            "起始角 (°)", "终止角 (°)", "起始升程 (mm)", "终止升程 (mm)", "运动规律"
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
        btn_add = QW.QPushButton("添加段")
        btn_del = QW.QPushButton("删除段")
        btn_up = QW.QPushButton("上移")
        btn_down = QW.QPushButton("下移")
        btn_default = QW.QPushButton("默认4段")
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
        cn_names = [_MOTION_CN.get(p, p) for p in list_motion_profiles()]
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
        self._append_row(last_end, min(last_end + 30, 360), 0, 0, "摆线运动")
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
            (0, 120, 0, 20, "摆线运动"),
            (120, 150, 20, 20, "摆线运动"),
            (150, 270, 20, 0, "摆线运动"),
            (270, 360, 0, 0, "摆线运动"),
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
                continue
            combo = self.table.cellWidget(row, 4)
            mn = combo.currentText() if combo else "摆线运动"
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
        self.form.setWindowTitle("创建凸轮")
        self._analysis_panel = None
        self._segments: list[MotionSegment] = []
        self._setup_ui()
        self._default_segments()

    def _setup_ui(self):
        QW = self.QtWidgets
        layout = QW.QVBoxLayout(self.form)

        # ── 凸轮类型 ──
        group_cam = QW.QGroupBox("凸轮类型")
        gl = QW.QFormLayout(group_cam)
        self.combo_cam_type = QW.QComboBox()
        self.combo_cam_type.addItems(["盘形凸轮", "圆柱凸轮", "线性凸轮"])
        self.combo_cam_type.currentIndexChanged.connect(self._on_cam_type_changed)
        gl.addRow("类型:", self.combo_cam_type)
        layout.addWidget(group_cam)

        # ── 几何参数 ──
        group_geom = QW.QGroupBox("几何参数")
        gl = QW.QFormLayout(group_geom)
        self.spin_base_radius = self._make_spin(30.0, 1.0, 500.0, "mm")
        self.spin_thickness = self._make_spin(15.0, 1.0, 200.0, "mm")
        self.spin_hub_radius = self._make_spin(12.0, 0.0, 100.0, "mm")
        self.spin_bore_radius = self._make_spin(8.0, 0.0, 100.0, "mm")
        self.spin_keyway_width = self._make_spin(4.0, 0.0, 50.0, "mm")
        self.spin_ppd = self._make_spin(5.0, 1.0, 20.0, "点/度")
        self.spin_groove_width = self._make_spin(6.0, 2.0, 50.0, "mm")
        self.spin_groove_depth = self._make_spin(4.0, 1.0, 30.0, "mm")
        self.spin_blank_radius = self._make_spin(60.0, 10.0, 500.0, "mm")
        self.check_grooved = QW.QCheckBox("开槽凸轮")
        self.check_grooved.toggled.connect(self._on_grooved_toggled)
        gl.addRow("基圆半径:", self.spin_base_radius)
        gl.addRow("凸轮厚度:", self.spin_thickness)
        gl.addRow("轮毂半径:", self.spin_hub_radius)
        gl.addRow("轴孔半径:", self.spin_bore_radius)
        gl.addRow("键槽宽度:", self.spin_keyway_width)
        gl.addRow("", self.check_grooved)
        gl.addRow("沟槽宽度:", self.spin_groove_width)
        gl.addRow("沟槽深度:", self.spin_groove_depth)
        gl.addRow("毛胚外径:", self.spin_blank_radius)
        gl.addRow("逼近精度:", self.spin_ppd)
        layout.addWidget(group_geom)

        # ── 运动定义（按钮打开独立表格）──
        group_seg = QW.QGroupBox("运动定义")
        seg_layout = QW.QHBoxLayout(group_seg)
        self.lbl_seg_info = QW.QLabel("4 段")
        self.lbl_seg_info.setMinimumWidth(60)
        btn_edit_seg = QW.QPushButton("编辑运动段...")
        btn_edit_seg.setMinimumHeight(36)
        btn_edit_seg.clicked.connect(self._open_segment_editor)
        seg_layout.addWidget(QW.QLabel("当前:"))
        seg_layout.addWidget(self.lbl_seg_info)
        seg_layout.addWidget(btn_edit_seg)
        seg_layout.addStretch()
        layout.addWidget(group_seg)

        # ── 从动件 ──
        group_follower = QW.QGroupBox("从动件")
        gl = QW.QFormLayout(group_follower)
        self.combo_follower_type = QW.QComboBox()
        self.combo_follower_type.addItems([
            "直动对心", "直动偏置", "摆动", "双从动件", "共轭",
        ])
        self.combo_follower_type.currentIndexChanged.connect(self._on_follower_type_changed)
        gl.addRow("类型:", self.combo_follower_type)
        self.spin_offset = self._make_spin(0.0, -100.0, 100.0, "mm")
        self.spin_arm_length = self._make_spin(40.0, 1.0, 500.0, "mm")
        self.spin_pivot_distance = self._make_spin(60.0, 1.0, 500.0, "mm")
        gl.addRow("偏置距:", self.spin_offset)
        gl.addRow("摆臂长度:", self.spin_arm_length)
        gl.addRow("摆臂支距:", self.spin_pivot_distance)
        layout.addWidget(group_follower)

        # ── 按钮 ──
        btn_layout = QW.QHBoxLayout()
        self.btn_generate = QW.QPushButton("生成凸轮")
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_analyze = QW.QPushButton("分析图表")
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

    def _make_spin(self, default, min_val, max_val, suffix=""):
        spin = self.QtWidgets.QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSuffix(f" {suffix}" if suffix else "")
        spin.setDecimals(1)
        return spin

    def _default_segments(self):
        self._segments = [
            MotionSegment(0, 120, 0, 20, "摆线运动"),
            MotionSegment(120, 150, 20, 20, "摆线运动"),
            MotionSegment(150, 270, 20, 0, "摆线运动"),
            MotionSegment(270, 360, 0, 0, "摆线运动"),
        ]
        self._update_seg_label()

    def _update_seg_label(self):
        self.lbl_seg_info.setText(f"{len(self._segments)} 段")

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
        self.spin_pivot_distance.setVisible(is_oscillating)

    def _on_cam_type_changed(self, index):
        is_disk = (index == 0)
        is_cyl = (index == 1)
        is_linear = (index == 2)
        self.spin_hub_radius.setVisible(is_disk)
        self.spin_keyway_width.setVisible(is_disk)
        self.spin_thickness.setVisible(is_disk or is_linear)
        # 显示/隐藏开槽选项
        self.check_grooved.setVisible(is_disk or is_linear)
        if is_cyl:
            # 圆柱凸轮始终开槽
            self.spin_groove_width.setVisible(True)
            self.spin_groove_depth.setVisible(True)
            self.spin_blank_radius.setVisible(False)
        else:
            # 盘形/线性凸轮：根据复选框
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
                labels = ["基圆半径:", "圆柱半径:", "展开半径:"]
                lbl.widget().setText(labels[idx] if idx < len(labels) else "基圆半径:")

    def _build_params(self):
        cam_type_map = {"盘形凸轮": "disk", "圆柱凸轮": "cylindrical", "线性凸轮": "linear"}
        cam_type = cam_type_map.get(self.combo_cam_type.currentText(), "disk")
        is_cyl = (cam_type == "cylindrical")
        cam = CamParams(
            cam_type=cam_type,
            base_radius=self.spin_base_radius.value(),
            thickness=self.spin_thickness.value(),
            hub_radius=self.spin_hub_radius.value(),
            bore_radius=self.spin_bore_radius.value(),
            keyway_width=self.spin_keyway_width.value(),
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
            3: FollowerType.DOUBLE,
            4: FollowerType.CONJUGATE,
        }

        follower = FollowerParams(
            follower_type=ft_map.get(self.combo_follower_type.currentIndex(),
                                     FollowerType.TRANSLATING_ONCENTER),
            offset=self.spin_offset.value(),
            arm_length=self.spin_arm_length.value(),
            pivot_distance=self.spin_pivot_distance.value(),
        )

        return cam, follower

    def _validate(self):
        segments = self._segments
        if not segments:
            self.QtWidgets.QMessageBox.warning(
                self.form, "参数错误", "请添加至少一个运动段。"
            )
            return False
        if abs(segments[0].start_angle) > 0.1:
            self.QtWidgets.QMessageBox.warning(
                self.form, "参数错误",
                f"第一段起始角应为 0°（当前 {segments[0].start_angle}°）"
            )
            return False
        if abs(segments[-1].end_angle - 360.0) > 0.1:
            self.QtWidgets.QMessageBox.warning(
                self.form, "参数错误",
                f"最后一段终止角应为 360°（当前 {segments[-1].end_angle}°）"
            )
            return False
        for i in range(len(segments) - 1):
            if abs(segments[i].end_angle - segments[i + 1].start_angle) > 0.1:
                self.QtWidgets.QMessageBox.warning(
                    self.form, "参数错误",
                    f"第 {i + 1} 段终止角 ({segments[i].end_angle}°) "
                    f"≠ 第 {i + 2} 段起始角 ({segments[i + 1].start_angle}°)"
                )
                return False
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
            pts2 = [App.Vector(p[0], p[1], cam.thickness + 1) for p in pitch_points]
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

            App.Console.PrintMessage("FCCamTrax: 凸轮生成成功。\n")

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            App.Console.PrintError(f"FCCamTrax: 凸轮生成失败 - {e}\n{tb}\n")
            self.QtWidgets.QMessageBox.critical(
                self.form, "错误", f"凸轮生成失败：\n{e}\n\n详情见报告视图。"
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
                    self.form, "图表不可用",
                    "QtCharts 不可用。分析数据已计算但无法显示图表。"
                )
                return

            if self._analysis_panel is None:
                self._analysis_panel = ChartPanel(Gui.getMainWindow())
                Gui.getMainWindow().addDockWidget(
                    self.QtCore.Qt.RightDockWidgetArea, self._analysis_panel
                )

            self._analysis_panel.update_data(result)
            self._analysis_panel.show()
            App.Console.PrintMessage("FCCamTrax: 分析图表已更新。\n")

        except Exception as e:
            self.QtWidgets.QMessageBox.critical(
                self.form, "错误", f"分析失败：\n{e}"
            )
            App.Console.PrintError(f"FCCamTrax: {e}\n")

    def getStandardButtons(self):
        b = self.QtWidgets.QDialogButtonBox
        val = getattr(b.Close, 'value', b.Close)
        return int(val)

    def reject(self):
        if self._analysis_panel:
            self._analysis_panel.close()
        Gui.Control.closeDialog()
