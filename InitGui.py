"""FCCamTrax Workbench GUI Registration

Registers the FCCamTrax workbench in FreeCAD with toolbar commands and menus.
"""

import FreeCAD as App
import FreeCADGui as Gui


class FCCamTraxWorkbench(Gui.Workbench):
    MenuText = "FCCamTrax"
    ToolTip = "Professional cam design workbench"

    def GetClassName(self):
        return "Gui::PythonWorkbench"

    def Initialize(self):
        App.Console.PrintMessage("FCCamTrax: 工作台初始化中...\n")

        # 初始化翻译
        try:
            from fccamtrax.i18n import setup_translations, tr
            setup_translations()
        except Exception as e:
            App.Console.PrintError(f"FCCamTrax: 翻译初始化失败 - {e}\n")

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
