#!/usr/bin/env python3
"""
Relay Team Optimizer
A tool for optimizing relay team assignments in competitive swimming.
"""

import tkinter as tk
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.main_window import MainWindow

def main():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()