"""内嵌图表组件，用于凸轮分析数据可视化。

使用 QPainter 手绘，不依赖 QtCharts。
兼容 PySide6 / PySide2 / PyQt6 / PyQt5。
"""

from __future__ import annotations
import math

from ..analysis.analyzer import AnalysisResult

QtWidgets = QtCore = QtGui = None
QT_LIB = None

for _mod_name in ["PySide6", "PySide2", "PyQt6", "PyQt5"]:
    try:
        _mod = __import__(_mod_name)
        QtWidgets = getattr(_mod, "QtWidgets", None)
        QtCore = getattr(_mod, "QtCore", None)
        QtGui = getattr(_mod, "QtGui", None)
        if QtWidgets and QtCore:
            QT_LIB = _mod_name
            break
        QtWidgets = QtCore = QtGui = None
    except ImportError:
        continue


class _PlotWidget(QtWidgets.QWidget):
    """单个曲线图，用 QPainter 手绘坐标轴、网格、曲线。"""

    MARGIN_LEFT = 60
    MARGIN_RIGHT = 20
    MARGIN_TOP = 10
    MARGIN_BOTTOM = 50

    def __init__(self, title: str, unit: str, color, parent=None):
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._color = QtGui.QColor(*color) if color else QtGui.QColor(0, 0, 0)
        self._angles: list[float] = []
        self._data: list[float] = []
        self.setMouseTracking(False)
        self.setMinimumSize(300, 200)

    def set_data(self, angles: list[float], data: list[float]):
        self._angles = list(angles)
        self._data = list(data)
        self.update()

    def _plot_area(self):
        w = self.width()
        h = self.height()
        return (self.MARGIN_LEFT, self.MARGIN_TOP,
                w - self.MARGIN_LEFT - self.MARGIN_RIGHT,
                h - self.MARGIN_TOP - self.MARGIN_BOTTOM)

    def _data_range(self):
        if not self._data:
            return 0.0, 1.0
        finite = [v for v in self._data if math.isfinite(v)]
        if not finite:
            return 0.0, 1.0
        y_min = min(finite)
        y_max = max(finite)
        if abs(y_max - y_min) < 1e-12:
            y_min -= 1.0
            y_max += 1.0
        margin = (y_max - y_min) * 0.1
        return y_min - margin, y_max + margin

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            self._draw_background(painter)
            self._draw_axes(painter)
            self._draw_grid(painter)
            self._draw_curve(painter)
        except Exception as e:
            import FreeCAD as App
            App.Console.PrintError(f"FCCamTrax: chart paint error: {e}\n")
        finally:
            painter.end()

    def _draw_background(self, painter):
        painter.fillRect(self.rect(), QtCore.Qt.white)

    def _draw_axes(self, painter):
        x0, y0, w, h = self._plot_area()
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        # X axis (bottom)
        painter.drawLine(x0, y0 + h, x0 + w, y0 + h)
        # Y axis (left)
        painter.drawLine(x0, y0, x0, y0 + h)

        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        # X ticks (0 to 360)
        n_ticks_x = 9
        for i in range(n_ticks_x):
            x = x0 + w * i / (n_ticks_x - 1)
            val = 360.0 * i / (n_ticks_x - 1)
            painter.drawLine(int(x), y0 + h, int(x), y0 + h + 4)
            painter.drawText(int(x) - 20, y0 + h + 16, 40, 16,
                             QtCore.Qt.AlignCenter, f"{val:.0f}")

        # Y ticks (auto)
        y_min, y_max = self._data_range()
        n_ticks_y = 5
        for i in range(n_ticks_y):
            y = y0 + h - h * i / (n_ticks_y - 1)
            val = y_min + (y_max - y_min) * i / (n_ticks_y - 1)
            painter.drawText(x0 - 50, int(y) - 8, 46, 16,
                             QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                             self._format_num(val))

        # Title
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.MARGIN_LEFT, 4, self.width() - self.MARGIN_LEFT - self.MARGIN_RIGHT, 16,
                         QtCore.Qt.AlignCenter, self._title)

        # X axis label
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(x0, y0 + h + 28, w, 20,
                         QtCore.Qt.AlignCenter, "凸轮转角 (°)")

        # Y axis label
        painter.save()
        painter.translate(12, y0 + h // 2)
        painter.rotate(-90)
        painter.drawText(-40, -8, 80, 16,
                         QtCore.Qt.AlignCenter, self._unit)
        painter.restore()

    def _draw_grid(self, painter):
        x0, y0, w, h = self._plot_area()
        pen = QtGui.QPen(QtGui.QColor(220, 220, 220), 1)
        pen.setStyle(QtCore.Qt.DashLine)
        painter.setPen(pen)

        n_ticks_x = 9
        for i in range(1, n_ticks_x - 1):
            x = x0 + w * i / (n_ticks_x - 1)
            painter.drawLine(int(x), y0, int(x), y0 + h)

        n_ticks_y = 5
        for i in range(1, n_ticks_y):
            y = y0 + h - h * i / (n_ticks_y - 1)
            painter.drawLine(x0, int(y), x0 + w, int(y))

    def _draw_curve(self, painter):
        n = min(len(self._data), len(self._angles))
        if n == 0:
            return
        x0, y0, w, h = self._plot_area()
        y_min, y_max = self._data_range()

        pen = QtGui.QPen(self._color, 2)
        painter.setPen(pen)

        path = QtGui.QPainterPath()
        first = True
        for i in range(n):
            val = self._data[i]
            if not math.isfinite(val):
                first = True
                continue
            x = x0 + w * self._angles[i] / 360.0
            y = y0 + h - h * (val - y_min) / (y_max - y_min)
            if first:
                path.moveTo(x, y)
                first = False
            else:
                path.lineTo(x, y)
        painter.drawPath(path)

    def _format_num(self, val):
        if abs(val) >= 1000:
            return f"{val:.1f}"
        elif abs(val) >= 1:
            return f"{val:.2f}"
        elif abs(val) >= 0.01:
            return f"{val:.4f}"
        else:
            return f"{val:.6f}"


class CamChartWidget(QtWidgets.QWidget):
    """多标签页分析图表容器。"""

    CHART_CONFIGS = [
        ("位移", "displacement", "mm", (0, 100, 200)),
        ("速度", "velocity", "mm/rad", (50, 100, 200)),
        ("加速度", "acceleration", "mm/rad²", (200, 50, 50)),
        ("跃度", "jerk", "mm/rad³", (150, 100, 50)),
        ("压力角", "pressure_angle", "°", (100, 150, 50)),
        ("扭矩", "torque", "N·mm", (50, 150, 100)),
        ("接触应力", "contact_stress", "MPa", (150, 50, 150)),
        ("法向力", "normal_force", "N", (50, 50, 150)),
        ("曲率半径", "curvature", "mm", (100, 100, 100)),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QtWidgets.QTabWidget()
        layout.addWidget(self._tabs)

        self._plot_widgets: dict[str, _PlotWidget] = {}
        for title, attr, unit, color in self.CHART_CONFIGS:
            pw = _PlotWidget(title, unit, color)
            self._tabs.addTab(pw, title)
            self._plot_widgets[attr] = pw

    def set_data(self, result):
        for title, attr, unit, color in self.CHART_CONFIGS:
            if attr not in self._plot_widgets:
                continue
            data = getattr(result, attr, None)
            if data is None:
                continue
            angles = result.angles[:len(data)] if hasattr(result, 'angles') else []
            if not angles:
                angles = [i * 360.0 / len(data) for i in range(len(data))]
            self._plot_widgets[attr].set_data(angles, data)


class CamAnalysisPanel(QtWidgets.QDockWidget):
    """可停靠的分析图表面板。"""

    def __init__(self, parent=None):
        super().__init__("凸轮分析", parent)
        self.chart_widget = CamChartWidget()
        self.setWidget(self.chart_widget)
        self.setMinimumSize(850, 650)

    def update_data(self, result):
        self.chart_widget.set_data(result)
