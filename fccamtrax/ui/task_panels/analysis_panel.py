"""Analysis panel — lazy re-export of CamAnalysisPanel from chart.widgets."""

CamAnalysisPanel = None
try:
    from ...chart.widgets import CamAnalysisPanel
except Exception as e:
    import FreeCAD as App
    App.Console.PrintError(f"FCCamTrax: analysis_panel import failed: {e}\n")

__all__ = ["CamAnalysisPanel"]
