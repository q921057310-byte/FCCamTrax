"""FCCamTrax Workbench GUI Registration

Registers the FCCamTrax workbench in FreeCAD with toolbar commands and menus.
"""

import os
import sys
import FreeCAD as App
import FreeCADGui as Gui


class FCCamTraxWorkbench(Gui.Workbench):
    MenuText = "FCCamTrax"
    ToolTip = "专业凸轮设计工作台"

    def GetClassName(self):
        return "Gui::PythonWorkbench"

    def Initialize(self):
        App.Console.PrintMessage("FCCamTrax: 工作台初始化中...\n")

        try:
            from fccamtrax.ui.commands import create_cam, new_design
            self.appendToolbar("FCCamTrax", [
                "FCCamTrax_NewDesign",
                "FCCamTrax_CreateCam",
            ])
            self.appendMenu("FCCamTrax", [
                "FCCamTrax_NewDesign",
                "FCCamTrax_CreateCam",
            ])
        except Exception as e:
            App.Console.PrintError(f"FCCamTrax: 加载命令失败 - {e}\n")

        try:
            from fccamtrax.ui.task_panels import cam_panel
        except Exception as e:
            App.Console.PrintError(f"FCCamTrax: 任务面板加载失败 - {e}\n")

        App.Console.PrintMessage("FCCamTrax: 工作台就绪。\n")

    def Activated(self):
        App.Console.PrintMessage("FCCamTrax: 工作台已激活。\n")

    def Deactivated(self):
        App.Console.PrintMessage("FCCamTrax: 工作台已停用。\n")


Gui.addWorkbench(FCCamTraxWorkbench())
