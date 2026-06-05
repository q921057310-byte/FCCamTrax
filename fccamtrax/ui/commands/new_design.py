"""'New Cam Design' command — creates a new document for cam design."""

import os
import FreeCAD as App
import FreeCADGui as Gui
from ...i18n import tr


def _icon(name):
    base = os.path.join(os.path.dirname(__file__), "..", "..", "..", "resources", "icons")
    return os.path.normpath(os.path.join(base, name))


class NewCamDesignCommand:
    """Create a new FreeCAD document for cam design."""

    def GetResources(self):
        return {
            "MenuText": tr("New Cam Design"),
            "ToolTip": tr("Create new cam design document"),
            "Pixmap": _icon("new_design.svg"),
        }

    def Activated(self):
        doc = App.newDocument("CamDesign")
        App.setActiveDocument(doc.Name)
        App.Console.PrintMessage("FCCamTrax: " + tr("New cam design document created.") + "\n")

    def IsActive(self):
        return True


Gui.addCommand("FCCamTrax_NewDesign", NewCamDesignCommand())
