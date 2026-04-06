# shared/uix/theme/theme.py
from pathlib import Path
from . import tokens  # Import your File 2

def load_solunex_theme() -> str:
    qss_path = Path(__file__).parent / "solunex.qss"
    style = qss_path.read_text(encoding="utf-8")
    
    # Map Python tokens to QSS placeholders
    replacements = {
        "@PRIMARY": tokens.PRIMARY,
        "@ACCENT": tokens.ACCENT,
        "@BACKGROUND": tokens.BACKGROUND,
        "@SURFACE": tokens.SURFACE,
        "@BORDER": tokens.BORDER,
        "@TEXT_PRIMARY": tokens.TEXT_PRIMARY
    }
    
    for placeholder, value in replacements.items():
        style = style.replace(placeholder, value)
        
    return style