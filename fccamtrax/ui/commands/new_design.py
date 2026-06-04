"""'New Cam Design' command — creates a new document for cam design."""

import os
import FreeCAD as App
import FreeCADGui as Gui


def _icon(name):
    base = os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "icons")
    return os.path.normpath(os.path.join(base, name))


class NewCamDesignCommand:
    """Create a new FreeCAD document for cam design."""

    def GetResources(self):
        return {
            "MenuText": "新建凸轮设计",
            "ToolTip": "新建凸轮设计文档",
            "Pixmap": _icon("new_design.svg"),
        }

    def Activated(self):
        doc = App.newDocument("CamDesign")
        App.setActiveDocument(doc.Name)
        App.Console.PrintMessage("FCCamTrax: 已创建新凸轮设计文档。\n")

    def IsActive(self):
        return True


Gui.addCommand("FCCamTrax_NewDesign", NewCamDesignCommand())
