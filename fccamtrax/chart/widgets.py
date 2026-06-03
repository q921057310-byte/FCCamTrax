"""内嵌图表组件，用于凸轮分析数据可视化。

支持 PySide6 / PySide2 / PyQt6 / PyQt5。
Qt 不可用时类定义为 None。
"""

from ..analysis.analyzer import AnalysisResult

QtWidgets = QtCore = QtGui = QtCharts = None
QT_LIB = None

for _mod_name in ["PySide6", "PySide2", "PyQt6", "PyQt5"]:
    try:
        _mod = __import__(_mod_name)
        QtWidgets = getattr(_mod, "QtWidgets", None)
        QtCore = getattr(_mod, "QtCore", None)
        QtGui = getattr(_mod, "QtGui", None)
        QtCharts = getattr(_mod, "QtCharts", None)
        if QtWidgets and QtCore:
            QT_LIB = _mod_name
            break
        QtWidgets = QtCore = QtGui = QtCharts = None
    except ImportError:
        continue

if QtWidgets is not None:
    class CamChartWidget(QtWidgets.QWidget):
        """多标签页分析图表容器。"""

        # (中文标题, 属性名, Y轴单位, 颜色RGB)
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
            self.setWindowTitle("凸轮分析图表")
            self.setMinimumSize(800, 600)

            layout = QtWidgets.QVBoxLayout(self)

            if QtCharts is None:
                label = QtWidgets.QLabel(
                    "QtCharts 不可用。图表需要 PySide6-Addons 或 PyQt6-QtCharts。"
                )
                label.setAlignment(QtCore.Qt.AlignCenter)
                layout.addWidget(label)
                self._tabs = None
                return

            self._tabs = QtWidgets.QTabWidget()
            layout.addWidget(self._tabs)
            self._charts = {}
            self._setup_charts()

        def _setup_charts(self):
            if not QtCharts or not self._tabs:
                return

            for title, attr, unit, color in self.CHART_CONFIGS:
                chart = QtCharts.QChart()
                chart.setTitle(title)
                chart.setAnimationOptions(QtCharts.QChart.NoAnimation)
                chart.legend().hide()

                axis_x = QtCharts.QValueAxis()
                axis_x.setTitleText("凸轮转角 (°)")
                axis_x.setRange(0, 360)
                axis_x.setTickCount(9)
                chart.addAxis(axis_x, QtCore.Qt.AlignBottom)

                axis_y = QtCharts.QValueAxis()
                axis_y.setTitleText(unit)
                chart.addAxis(axis_y, QtCore.Qt.AlignLeft)

                series = QtCharts.QLineSeries()
                pen = series.pen()
                pen.setColor(QtCore.QColor(*color))
                pen.setWidth(2)
                series.setPen(pen)
                chart.addSeries(series)
                series.attachAxis(axis_x)
                series.attachAxis(axis_y)

                view = QtCharts.QChartView(chart)
                try:
                    view.setRenderHint(QtGui.QPainter.Antialiasing)
                except Exception:
                    pass

                self._tabs.addTab(view, title)
                self._charts[attr] = (series, axis_y)

        def set_data(self, result):
            if not QtCharts or not self._charts:
                return

            for title, attr, unit, color in self.CHART_CONFIGS:
                if attr not in self._charts:
                    continue

                series, axis_y = self._charts[attr]
                data = getattr(result, attr, None)
                if data is None:
                    continue

                series.clear()
                points = []
                for i, val in enumerate(data):
                    angle = result.angles[i] if i < len(result.angles) else i
                    points.append(QtCore.QPointF(angle, val))

                for p in points:
                    series.append(p)

                if data:
                    y_min = min(data)
                    y_max = max(data)
                    margin = (y_max - y_min) * 0.1 if y_max > y_min else 1.0
                    axis_y.setRange(y_min - margin, y_max + margin)

    class CamAnalysisPanel(QtWidgets.QDockWidget):
        """可停靠的分析图表面板。"""

        def __init__(self, parent=None):
            super().__init__("凸轮分析", parent)
            self.chart_widget = CamChartWidget()
            self.setWidget(self.chart_widget)
            self.setMinimumSize(850, 650)

        def update_data(self, result):
            self.chart_widget.set_data(result)

else:
    CamChartWidget = None
    CamAnalysisPanel = None
