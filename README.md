# FCCamTrax — 专业凸轮设计工作台

[![FreeCAD](https://img.shields.io/badge/FreeCAD-%E2%89%A51.0-2962FF)](https://freecad.org)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-LGPL--2.1-green)](LICENSE)

FCCamTrax 是 FreeCAD 的凸轮设计工作台，支持**盘形凸轮**、**圆柱凸轮**和**线性凸轮**的多段运动定义、性能分析和 3D 实体生成。

---

## 支持的凸轮类型

| 类型 | 图示 | 说明 |
|------|------|------|
| **盘形凸轮** | — | 基圆 + 升程轮廓，支持开槽/无槽，hub/bore/keyway/安装孔 |
| **圆柱凸轮** | — | 圆柱表面沟槽，C2 连续过渡，自动闭合成环 |
| **线性凸轮** | — | 展开式平板往复凸轮，支持 Y 面沟槽 |

## 运动曲线

| 名称 | C0 | C1 | C2 | 特点 |
|------|:--:|:--:|:--:|------|
| 摆线 (Cycloidal) | ✓ | ✓ | ✓ | 最平滑，加速度连续 |
| 简谐 (Harmonic) | ✓ | ✓ | ✗ | 简单，高速有冲击 |
| 修正正弦 (ModSine) | ✓ | ✓ | ✓ | 加速度峰值低 |
| 3-4-5 多项式 | ✓ | ✓ | ✓ | 停留段性能好 |
| 匀速 (Constant Vel) | ✓ | ✗ | ✗ | 低速/手动适用 |

段间统一使用 **五次 Hermite C2 过渡**，保证跨段位移、速度、加速度连续。

## 从动件类型

- 直动对心 (Translating On-Center)
- 直动偏置 (Translating Off-Center)
- 摆动 (Oscillating)
- 双从动件 (Double)
- 共轭 (Conjugate)

## 分析指标

| 指标 | 说明 |
|------|------|
| 位移 (Displacement) | 从动件升程曲线 |
| 速度 (Velocity) | 一阶数值微分 |
| 加速度 (Acceleration) | 二阶数值微分 |
| 跃度 (Jerk) | 三阶数值微分 |
| 压力角 (Pressure Angle) | 盘形凸轮从动件受力角度 |
| 曲率半径 (Curvature) | 轮廓最小曲率（防止根切） |
| 扭矩 (Torque) | 驱动扭矩估计 |
| 接触应力 (Contact Stress) | 赫兹接触应力 |
| 法向力 (Normal Force) | 弹簧力+惯性力 |

图表显示使用 PySide6/PySide2/PyQt6/PyQt5 自动回退。

## 安装

### 通过 Addon Manager（推荐）

1. FreeCAD → **工具** → **Addon Manager**
2. 搜索 "FCCamTrax"
3. 点击 **安装**

### 手动安装

```bash
# 克隆到 FreeCAD Mod 目录
cd %APPDATA%\FreeCAD\v1-1\Mod
git clone https://github.com/user/FCCamTrax.git
```

重启 FreeCAD，从工作台下拉菜单选择 **FCCamTrax**。

## 使用

1. 切换至 **FCCamTrax** 工作台
2. 点击 **新建设计** 创建文档
3. 点击 **创建凸轮** 打开参数面板
4. 选择凸轮类型、运动曲线、从动件类型
5. 添加运动段（起始角/终止角/升程/运动曲线）
6. 勾选 **开槽凸轮**（如需要）
7. 设置几何参数（基圆半径、厚度、槽宽/槽深等）
8. 点击 **生成凸轮**
9. 使用 **分析图表** 查看性能曲线

## 项目结构

```
FCCamTrax/
├── Init.py                        # FreeCAD 初始化入口
├── InitGui.py                     # 工作台 GUI 注册
├── package.xml                    # Addon Manager 元数据
├── README.md                      # 本文档
├── resources/
│   └── icons/                     # SVG 工具栏图标
│       ├── fccamtrax.svg
│       ├── create_cam.svg
│       └── new_design.svg
├── fccamtrax/
│   ├── __init__.py
│   ├── geometry/
│   │   ├── base.py                # CamBuilder 基类 + 工厂
│   │   ├── disk_cam.py            # 盘形凸轮构建器
│   │   ├── cylindrical_cam.py     # 圆柱凸轮构建器
│   │   ├── linear_cam.py          # 线性凸轮构建器
│   │   ├── follower.py            # CamParams / FollowerParams 数据类
│   │   └── utils.py               # 几何工具（极坐标/偏置曲线）
│   ├── motion/
│   │   ├── base.py                # 运动曲线基类
│   │   ├── registry.py            # @register_profile 装饰器注册
│   │   ├── cycloidal.py           # 摆线
│   │   ├── harmonic.py            # 简谐
│   │   ├── modified_sine.py       # 修正正弦
│   │   ├── polynomial345.py       # 3-4-5 多项式
│   │   └── constant_velocity.py   # 匀速
│   ├── analysis/
│   │   └── analyzer.py            # 性能分析（9 项指标）
│   ├── chart/
│   │   └── widgets.py             # QtCharts 图表控件
│   └── ui/
│       ├── commands/
│       │   ├── new_design.py      # 新建文档命令
│       │   └── create_cam.py      # 打开任务面板命令
│       └── task_panels/
│           ├── cam_panel.py       # 凸轮参数编辑面板
│           └── analysis_panel.py  # 分析图表面板
```

## 开发

### 环境

- FreeCAD v1-1 (Python 3.11, PySide6 6.11.0)
- `App.Vector` 没有 `normalized()` — 使用 `v / v.Length`
- `Part.makePolygon(points)` 返回 `Part.Wire`，无需再包装

### 添加新运动曲线

1. 在 `fccamtrax/motion/` 下新建文件
2. 继承 `MotionProfileBase`
3. 实现 `evaluate(t)`（返回升程）和 `derivative(t)`（返回速度）
4. 用 `@register_profile("name", "中文名")` 装饰
5. 在 `__init__.py` 中 import

### 测试

```bash
# 独立测试运动曲线（无需 FreeCAD GUI）
python test_motion_profiles.py
```

## 许可证

LGPL-2.1-or-later
