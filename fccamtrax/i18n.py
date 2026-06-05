"""Translation system using Qt .ts/.qm files.

English is the source language. Translations are loaded from .qm files
matching FreeCAD's UI locale. The module context is "FCCamTrax".
"""

import os
from PySide6.QtCore import QCoreApplication, QTranslator

CONTEXT = "FCCamTrax"
_installed: list[QTranslator] = []


def tr(text):
    """Translate text using Qt's translation system."""
    return QCoreApplication.translate(CONTEXT, text)


def trf(text, **kwargs):
    """Translate and format text with keyword args."""
    return QCoreApplication.translate(CONTEXT, text).format(**kwargs)


def _freecad_locale() -> str:
    """Return FreeCAD's UI locale string (e.g. 'zh_CN', 'en_US')."""
    try:
        import FreeCADGui as Gui
        return Gui.getLocale()
    except Exception:
        pass
    try:
        import FreeCAD as App
        lang = App.ParamGet("User parameter:BaseApp/Preferences/General").GetString("Language", "")
        if lang:
            return lang
    except Exception:
        pass
    return "en"


def setup_translations(module_dir: str = None):
    """Load .qm translation file matching FreeCAD's UI locale."""
    global _installed
    # Remove previously installed translators
    for t in _installed:
        QCoreApplication.removeTranslator(t)
    _installed.clear()

    if module_dir is None:
        module_dir = os.path.dirname(os.path.dirname(__file__))
    trans_dir = os.path.join(module_dir, "translations")
    if not os.path.isdir(trans_dir):
        return

    locale = _freecad_locale()
    if locale == "en" or locale == "en_US":
        return  # English: no translation needed

    qm_path = os.path.join(trans_dir, f"{CONTEXT}_{locale}.qm")
    if not os.path.exists(qm_path):
        locale_hyphen = locale.replace("_", "-")
        qm_path = os.path.join(trans_dir, f"{CONTEXT}_{locale_hyphen}.qm")
    if not os.path.exists(qm_path):
        return

    translator = QTranslator()
    if translator.load(qm_path):
        QCoreApplication.installTranslator(translator)
        _installed.append(translator)
