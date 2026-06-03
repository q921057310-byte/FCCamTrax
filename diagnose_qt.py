"""Diagnostic macro: run this inside FreeCAD to check available Qt bindings."""

import FreeCAD as App

modules_to_check = [
    "PySide6", "PySide2", "PySide",
    "PyQt6", "PyQt5", "PyQt4",
    "QtWidgets", "QtCore", "QtGui",
    "qtpy", "qtinter",
]

App.Console.PrintMessage("=== FCCamTrax Qt Diagnosis ===\n")

for mod in modules_to_check:
    try:
        m = __import__(mod)
        ver = getattr(m, "__version__", "unknown")
        App.Console.PrintMessage(f"  {mod}: AVAILABLE (v{ver})\n")
    except ImportError:
        App.Console.PrintMessage(f"  {mod}: NOT FOUND\n")
    except Exception as e:
        App.Console.PrintMessage(f"  {mod}: ERROR - {e}\n")

# Check FreeCAD's own Qt access
App.Console.PrintMessage("\n=== FreeCAD Qt Access ===\n")
try:
    import FreeCADGui as Gui
    App.Console.PrintMessage(f"  FreeCADGui: OK\n")
    App.Console.PrintMessage(f"  Gui.getMainWindow(): {Gui.getMainWindow()}\n")
except Exception as e:
    App.Console.PrintMessage(f"  FreeCADGui: ERROR - {e}\n")

# Check if Shiboken is available
for mod in ["shiboken6", "shiboken2", "shiboken"]:
    try:
        __import__(mod)
        App.Console.PrintMessage(f"  {mod}: AVAILABLE\n")
    except ImportError:
        pass

App.Console.PrintMessage("\n=== Python Info ===\n")
import sys
App.Console.PrintMessage(f"  Python: {sys.version}\n")
App.Console.PrintMessage(f"  Executable: {sys.executable}\n")
App.Console.PrintMessage(f"  Path:\n")
for p in sys.path[:10]:
    App.Console.PrintMessage(f"    {p}\n")
