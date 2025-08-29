import tkinter as tk
from tkinter import ttk, messagebox
from ..models.event import Event, Session, EventType, StrokeType

class EventDialog:
    def __init__(self, parent, db, event=None):
        self.db = db
        self.event = event
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Event" if not event else "Edit Event")
        self.dialog.geometry("450x450")  # Made taller to ensure buttons are visible
        self.dialog.resizable(False, False)
        
        # Center the dialog on screen
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        
        if event:
            self.load_event_data()
    
    def create_widgets(self):
        # Event Information
        info_frame = ttk.LabelFrame(self.dialog, text="Event Information", padding="10")
        info_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(info_frame, text="Event Number:").grid(row=0, column=0, sticky='w', pady=2)
        self.event_number_var = tk.IntVar()
        ttk.Entry(info_frame, textvariable=self.event_number_var, width=10).grid(row=0, column=1, sticky='w', pady=2)
        
        ttk.Label(info_frame, text="Event Name:").grid(row=1, column=0, sticky='w', pady=2)
        self.event_name_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.event_name_var, width=30).grid(row=1, column=1, pady=2)
        
        # Session
        session_frame = ttk.LabelFrame(self.dialog, text="Session", padding="10")
        session_frame.pack(fill='x', padx=10, pady=5)
        
        self.session_var = tk.StringVar(value='AM')
        ttk.Radiobutton(session_frame, text="Morning (AM)", variable=self.session_var, value='AM').pack(side='left')
        ttk.Radiobutton(session_frame, text="Afternoon (PM)", variable=self.session_var, value='PM').pack(side='left', padx=(20, 0))
        
        # Gender Type
        gender_frame = ttk.LabelFrame(self.dialog, text="Gender Type", padding="10")
        gender_frame.pack(fill='x', padx=10, pady=5)
        
        self.gender_type_var = tk.StringVar(value='Men')
        ttk.Radiobutton(gender_frame, text="Men's", variable=self.gender_type_var, value='Men').pack(side='left')
        ttk.Radiobutton(gender_frame, text="Women's", variable=self.gender_type_var, value='Women').pack(side='left', padx=(20, 0))
        ttk.Radiobutton(gender_frame, text="Mixed", variable=self.gender_type_var, value='Mixed').pack(side='left', padx=(20, 0))
        
        # Event Details
        details_frame = ttk.LabelFrame(self.dialog, text="Event Details", padding="10")
        details_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(details_frame, text="Stroke Type:").grid(row=0, column=0, sticky='w', pady=5)
        self.stroke_type_var = tk.StringVar(value='Free')
        stroke_frame = ttk.Frame(details_frame)
        stroke_frame.grid(row=0, column=1, sticky='w', pady=5)
        ttk.Radiobutton(stroke_frame, text="Freestyle", variable=self.stroke_type_var, value='Free').pack(side='left')
        ttk.Radiobutton(stroke_frame, text="Medley", variable=self.stroke_type_var, value='Medley').pack(side='left', padx=(20, 0))
        
        ttk.Label(details_frame, text="Distance:").grid(row=1, column=0, sticky='w', pady=5)
        self.distance_var = tk.IntVar(value=50)
        distance_frame = ttk.Frame(details_frame)
        distance_frame.grid(row=1, column=1, sticky='w', pady=5)
        for dist in [25, 50, 100, 200]:
            ttk.Radiobutton(distance_frame, text=f"4x{dist}m", variable=self.distance_var, value=dist).pack(side='left', padx=5)
        
        ttk.Label(details_frame, text="Competition Level:").grid(row=2, column=0, sticky='w', pady=5)
        self.competition_var = tk.IntVar(value=3)
        comp_frame = ttk.Frame(details_frame)
        comp_frame.grid(row=2, column=1, sticky='w', pady=5)
        
        scale = ttk.Scale(comp_frame, from_=1, to=5, orient='horizontal', variable=self.competition_var, length=200)
        scale.pack(side='left')
        self.comp_label = ttk.Label(comp_frame, text="Normal")
        self.comp_label.pack(side='left', padx=(10, 0))
        
        # Update label when scale changes
        scale.configure(command=self.update_competition_label)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self.save_event).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side='right')
    
    def update_competition_label(self, value):
        level = int(float(value))
        labels = {1: "Low", 2: "Below Normal", 3: "Normal", 4: "High", 5: "Extreme"}
        self.comp_label.configure(text=labels[level])
    
    def load_event_data(self):
        if not self.event:
            return
        
        self.event_number_var.set(self.event.event_number)
        self.event_name_var.set(self.event.event_name)
        self.session_var.set(self.event.session.value)
        self.gender_type_var.set(self.event.gender_type.value)
        self.stroke_type_var.set(self.event.stroke_type.value)
        self.distance_var.set(self.event.distance)
        self.competition_var.set(self.event.competition_level)
    
    def save_event(self):
        # Validate input
        if not self.event_number_var.get():
            messagebox.showerror("Error", "Please enter an event number")
            return
        
        if not self.event_name_var.get():
            messagebox.showerror("Error", "Please enter an event name")
            return
        
        # Create event object
        event = Event(
            event_number=self.event_number_var.get(),
            event_name=self.event_name_var.get(),
            session=Session(self.session_var.get()),
            gender_type=EventType(self.gender_type_var.get()),
            stroke_type=StrokeType(self.stroke_type_var.get()),
            distance=self.distance_var.get(),
            competition_level=self.competition_var.get(),
            event_id=self.event.event_id if self.event else None
        )
        
        # Save to database
        try:
            self.db.add_event(event)
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save event: {e}")