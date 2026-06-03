"""Analysis panel — lazy re-export of CamAnalysisPanel from chart.widgets."""

CamAnalysisPanel = None
try:
    from ...chart.widgets import CamAnalysisPanel
except Exception:
    pass

__all__ = ["CamAnalysisPanel"]
