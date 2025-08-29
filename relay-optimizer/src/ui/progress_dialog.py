import tkinter as tk
from tkinter import ttk
import threading

class ProgressDialog:
    def __init__(self, parent, title="Optimizing...", cancel_callback=None):
        self.parent = parent
        self.cancel_callback = cancel_callback
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Progress message
        self.message_var = tk.StringVar(value="Initializing optimization...")
        message_label = ttk.Label(self.dialog, textvariable=self.message_var)
        message_label.pack(pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.dialog, mode='determinate', length=300, maximum=200)
        self.progress.pack(pady=10)
        
        # Status text
        self.status_var = tk.StringVar(value="")
        status_label = ttk.Label(self.dialog, textvariable=self.status_var)
        status_label.pack(pady=10)
        
        # Cancel button
        if cancel_callback:
            cancel_button = ttk.Button(self.dialog, text="Cancel", command=self.on_cancel)
            cancel_button.pack(pady=10)
        
        # Prevent closing
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        
    def update_message(self, message):
        """Update the progress message"""
        self.message_var.set(message)
        self.dialog.update()
        
    def update_status(self, status):
        """Update the status text"""
        try:
            self.status_var.set(status)
            # Parse generation from status if present
            if "Generation" in status:
                try:
                    # Extract "Generation X/200" pattern
                    parts = status.split()
                    for i, part in enumerate(parts):
                        if part == "Generation" and i + 1 < len(parts):
                            gen_str = parts[i + 1]
                            if "/" in gen_str:
                                current, total = gen_str.split("/")
                                self.progress['value'] = int(current)
                                self.progress['maximum'] = int(total)
                except:
                    pass
            self.dialog.update_idletasks()  # Use update_idletasks instead of update
        except:
            pass  # Ignore errors if dialog was closed
    
    def on_cancel(self):
        """Handle cancel button click"""
        if self.cancel_callback:
            self.cancel_callback()
        self.close()
        
    def close(self):
        """Close the progress dialog"""
        self.progress.stop()
        self.dialog.destroy()