import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from tkcalendar import DateEntry
from ..models.swimmer import Swimmer, Gender

class SwimmerDialog:
    def __init__(self, parent, db, swimmer=None):
        self.db = db
        self.swimmer = swimmer
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Swimmer" if not swimmer else "Edit Swimmer")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        
        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        
        if swimmer:
            self.load_swimmer_data()
    
    def create_widgets(self):
        # Basic Information
        info_frame = ttk.LabelFrame(self.dialog, text="Basic Information", padding="10")
        info_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(info_frame, text="First Name:").grid(row=0, column=0, sticky='w', pady=2)
        self.first_name_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.first_name_var, width=30).grid(row=0, column=1, pady=2)
        
        ttk.Label(info_frame, text="Last Name:").grid(row=1, column=0, sticky='w', pady=2)
        self.last_name_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.last_name_var, width=30).grid(row=1, column=1, pady=2)
        
        ttk.Label(info_frame, text="Birth Date:").grid(row=2, column=0, sticky='w', pady=2)
        self.birth_date = DateEntry(info_frame, width=12, background='darkblue',
                                   foreground='white', borderwidth=2)
        self.birth_date.grid(row=2, column=1, sticky='w', pady=2)
        
        ttk.Label(info_frame, text="Gender:").grid(row=3, column=0, sticky='w', pady=2)
        self.gender_var = tk.StringVar(value='M')
        gender_frame = ttk.Frame(info_frame)
        gender_frame.grid(row=3, column=1, sticky='w', pady=2)
        ttk.Radiobutton(gender_frame, text="Male", variable=self.gender_var, value='M').pack(side='left')
        ttk.Radiobutton(gender_frame, text="Female", variable=self.gender_var, value='F').pack(side='left', padx=(20, 0))
        
        # Availability
        avail_frame = ttk.LabelFrame(self.dialog, text="Availability", padding="10")
        avail_frame.pack(fill='x', padx=10, pady=5)
        
        self.morning_var = tk.BooleanVar(value=True)
        self.afternoon_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(avail_frame, text="Morning (AM)", variable=self.morning_var).pack(anchor='w')
        ttk.Checkbutton(avail_frame, text="Afternoon (PM)", variable=self.afternoon_var).pack(anchor='w')
        
        ttk.Label(avail_frame, text="Max Events:").pack(anchor='w', pady=(10, 0))
        self.max_events_var = tk.IntVar(value=6)
        max_events_frame = ttk.Frame(avail_frame)
        max_events_frame.pack(anchor='w')
        ttk.Spinbox(max_events_frame, from_=1, to=6, textvariable=self.max_events_var, width=10).pack(side='left')
        ttk.Label(max_events_frame, text="(1-6 events)").pack(side='left', padx=(10, 0))
        
        # Stroke Preferences
        strokes_frame = ttk.LabelFrame(self.dialog, text="Stroke Preferences", padding="10")
        strokes_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(strokes_frame, text="Excluded Strokes (cannot swim):").pack(anchor='w')
        excluded_frame = ttk.Frame(strokes_frame)
        excluded_frame.pack(anchor='w', pady=(5, 10))
        
        self.excluded_vars = {}
        for stroke in ["Back", "Breast", "Fly", "Free"]:
            var = tk.BooleanVar()
            self.excluded_vars[stroke] = var
            ttk.Checkbutton(excluded_frame, text=stroke, variable=var).pack(side='left', padx=5)
        
        # Times Entry
        times_frame = ttk.LabelFrame(self.dialog, text="Performance Times (seconds)", padding="10")
        times_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create grid for times
        distances = [25, 50, 100, 200]
        strokes = ["Free", "Back", "Breast", "Fly"]
        
        # Headers
        for i, distance in enumerate(distances):
            ttk.Label(times_frame, text=f"{distance}m").grid(row=0, column=i+1, padx=5)
        
        self.time_vars = {}
        for r, stroke in enumerate(strokes):
            ttk.Label(times_frame, text=stroke).grid(row=r+1, column=0, sticky='w', padx=5)
            for c, distance in enumerate(distances):
                var = tk.StringVar()
                self.time_vars[(stroke, distance)] = var
                ttk.Entry(times_frame, textvariable=var, width=10).grid(row=r+1, column=c+1, padx=5, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self.save_swimmer).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side='right')
    
    def load_swimmer_data(self):
        if not self.swimmer:
            return
        
        self.first_name_var.set(self.swimmer.first_name)
        self.last_name_var.set(self.swimmer.last_name)
        self.birth_date.set_date(self.swimmer.birth_date)
        self.gender_var.set(self.swimmer.gender.value)
        self.morning_var.set(self.swimmer.morning_available)
        self.afternoon_var.set(self.swimmer.afternoon_available)
        self.max_events_var.set(self.swimmer.max_events)
        
        # Set excluded strokes
        for stroke in self.swimmer.excluded_strokes:
            if stroke in self.excluded_vars:
                self.excluded_vars[stroke].set(True)
        
        # Set times
        for (stroke, distance), time in self.swimmer.times.items():
            if (stroke, distance) in self.time_vars:
                self.time_vars[(stroke, distance)].set(str(time))
    
    def save_swimmer(self):
        # Validate input
        if not self.first_name_var.get() or not self.last_name_var.get():
            messagebox.showerror("Error", "Please enter first and last name")
            return
        
        # Create swimmer object
        excluded_strokes = {stroke for stroke, var in self.excluded_vars.items() if var.get()}
        
        # Parse times
        times = {}
        for (stroke, distance), var in self.time_vars.items():
            if var.get():
                try:
                    time = float(var.get())
                    times[(stroke, distance)] = time
                except ValueError:
                    messagebox.showerror("Error", f"Invalid time for {stroke} {distance}m")
                    return
        
        swimmer = Swimmer(
            first_name=self.first_name_var.get(),
            last_name=self.last_name_var.get(),
            birth_date=self.birth_date.get_date(),
            gender=Gender(self.gender_var.get()),
            max_events=self.max_events_var.get(),
            morning_available=self.morning_var.get(),
            afternoon_available=self.afternoon_var.get(),
            excluded_strokes=excluded_strokes,
            times=times,
            swimmer_id=self.swimmer.swimmer_id if self.swimmer else None
        )
        
        # Save to database
        try:
            self.db.add_swimmer(swimmer)
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save swimmer: {e}")