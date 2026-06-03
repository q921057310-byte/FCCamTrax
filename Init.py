"""FCCamTrax - FreeCAD Cam Design Workbench

This file is loaded by FreeCAD at startup when the addon is installed.
"""

import FreeCAD as App

App.Console.PrintMessage("FCCamTrax: Initializing...\n")

try:
    import fccamtrax
    App.Console.PrintMessage("FCCamTrax: Module loaded successfully.\n")
except Exception as e:
    App.Console.PrintError(f"FCCamTrax: Failed to load module - {e}\n")
