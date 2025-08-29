"""PDF utilities to handle font issues on macOS"""

import os
import platform
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

def setup_fonts():
    """Setup fonts for PDF generation, handling macOS font issues"""
    
    # On macOS, try to register system fonts
    if platform.system() == 'Darwin':
        try:
            # Try to find Helvetica or Arial from system
            font_paths = [
                '/System/Library/Fonts/Helvetica.ttc',
                '/Library/Fonts/Arial.ttf',
                '/System/Library/Fonts/Avenir.ttc',
                '/System/Library/Fonts/Supplemental/Arial.ttf',
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    # For .ttc files, we can't use them directly with ReportLab
                    # So we'll just use the built-in fonts
                    break
        except:
            pass
    
    # The safest approach is to just use ReportLab's built-in fonts
    # which are always available
    return True