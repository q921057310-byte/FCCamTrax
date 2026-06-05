"""'Create Cam' command — opens the cam parameter task panel."""

import os
import FreeCAD as App
import FreeCADGui as Gui
from ...i18n import tr


def _icon(name):
    base = os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "icons")
    return os.path.normpath(os.path.join(base, name))


class CreateCamCommand:
    """Open the cam creation task panel."""

    def GetResources(self):
        return {
            "MenuText": tr("Create Cam"),
            "ToolTip": tr("Open cam parameter editor"),
            "Pixmap": _icon("create_cam.svg"),
        }

    def Activated(self):
        from ..task_panels.cam_panel import CamTaskPanel
        panel = CamTaskPanel()
        Gui.Control.showDialog(panel)

    def IsActive(self):
        return App.ActiveDocument is not None


Gui.addCommand("FCCamTrax_CreateCam", CreateCamCommand())
