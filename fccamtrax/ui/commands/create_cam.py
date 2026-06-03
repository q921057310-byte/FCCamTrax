"""'Create Cam' command — opens the cam parameter task panel."""

import os
import FreeCAD as App
import FreeCADGui as Gui


def _icon(name):
    base = os.path.join(App.getUserAppDataDir(), "Mod", "FCCamTrax", "resources", "icons")
    return os.path.join(base, name)


class CreateCamCommand:
    """Open the cam creation task panel."""

    def GetResources(self):
        return {
            "MenuText": "创建凸轮",
            "ToolTip": "打开凸轮参数编辑面板",
            "Pixmap": _icon("create_cam.svg"),
        }

    def Activated(self):
        from ..task_panels.cam_panel import CamTaskPanel
        panel = CamTaskPanel()
        Gui.Control.showDialog(panel)

    def IsActive(self):
        return App.ActiveDocument is not None


Gui.addCommand("FCCamTrax_CreateCam", CreateCamCommand())
