#!/usr/bin/env python3
"""Quick test to ensure UI starts without errors"""

import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_ui():
    # Create root but don't show it
    root = tk.Tk()
    root.withdraw()
    
    try:
        from src.ui.main_window import MainWindow
        app = MainWindow(root)
        print("✓ Main window created successfully")
        
        # Test that database is initialized
        swimmers = app.db.get_all_swimmers()
        events = app.db.get_all_events()
        print(f"✓ Database connected (Swimmers: {len(swimmers)}, Events: {len(events)})")
        
        # Clean up
        app.db.close()
        root.destroy()
        
        print("\n✓ All UI tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ UI test failed: {e}")
        root.destroy()
        return False

if __name__ == "__main__":
    success = test_ui()
    sys.exit(0 if success else 1)