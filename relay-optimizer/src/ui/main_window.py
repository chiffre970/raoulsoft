import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from typing import List, Optional
from ..data.database import Database
from ..models import Swimmer, Event, Team, TeamAssignment, OptimizationResult
from ..optimization.optimizer import RelayOptimizer
from .swimmer_dialog import SwimmerDialog
from .event_dialog import EventDialog
from .progress_dialog import ProgressDialog

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Relay Team Optimizer")
        self.root.geometry("1200x700")
        
        # Initialize database
        self.db = Database()
        self.swimmers = []
        self.events = []
        self.current_result = None
        
        # Create menu bar
        self.create_menu()
        
        # Create main layout
        self.create_widgets()
        
        # Load initial data
        self.load_data()
    
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import Swimmers (CSV/Excel)", command=self.import_swimmers)
        file_menu.add_command(label="Import Events (CSV)", command=self.import_events)
        file_menu.add_separator()
        file_menu.add_command(label="Export to Excel", command=self.export_excel)
        file_menu.add_command(label="Export to PDF", command=self.export_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Clear All Teams", command=self.clear_teams)
        edit_menu.add_command(label="Reset Database", command=self.reset_database)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Run Optimizer", command=self.run_optimizer)
        tools_menu.add_command(label="Validate All Teams", command=self.validate_teams)
    
    def create_widgets(self):
        # Top toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Add Swimmer", command=self.add_swimmer).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Add Event", command=self.add_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Optimize", command=self.run_optimizer).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Export Excel", command=self.export_excel).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Export PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=5)
        
        # Main content area with tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Events tab
        events_frame = ttk.Frame(notebook)
        notebook.add(events_frame, text="Events & Teams")
        self.create_events_view(events_frame)
        
        # Swimmers tab
        swimmers_frame = ttk.Frame(notebook)
        notebook.add(swimmers_frame, text="Swimmers")
        self.create_swimmers_view(swimmers_frame)
        
        # Results tab
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="Results Summary")
        self.create_results_view(results_frame)
    
    def create_events_view(self, parent):
        # Create scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        self.events_frame = scrollable_frame
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_swimmers_view(self, parent):
        # Create treeview for swimmers with time columns
        columns = ('Name', 'Age', 'Gender', 'AM', 'PM', 
                  '50 Free', '50 Back', '50 Breast', '50 Fly',
                  '100 Free', '100 Back', '100 Breast', '100 Fly', 
                  '200 Free')
        self.swimmers_tree = ttk.Treeview(parent, columns=columns, show='headings')  # Changed to just 'headings' to hide tree column
        
        # No ID column needed
        
        for col in columns:
            self.swimmers_tree.heading(col, text=col)
            if col == 'Name':
                self.swimmers_tree.column(col, width=200)
            elif col in ['Age', 'Gender', 'AM', 'PM']:
                self.swimmers_tree.column(col, width=60)
            else:  # Time columns
                self.swimmers_tree.column(col, width=80)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=self.swimmers_tree.yview)
        self.swimmers_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.swimmers_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Add context menu
        self.swimmers_tree.bind('<Double-Button-1>', self.edit_swimmer)
        self.swimmers_tree.bind('<Button-3>', self.show_swimmer_context_menu)
    
    def create_results_view(self, parent):
        # Create text widget for results summary
        self.results_text = tk.Text(parent, wrap=tk.WORD, height=20)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def load_data(self):
        self.swimmers = self.db.get_all_swimmers()
        self.events = self.db.get_all_events()
        self.refresh_display()
    
    def refresh_display(self):
        self.refresh_swimmers_list()
        self.refresh_events_list()
        if self.current_result:
            self.display_results()
    
    def refresh_swimmers_list(self):
        # Clear existing items
        for item in self.swimmers_tree.get_children():
            self.swimmers_tree.delete(item)
        
        # Add swimmers
        for swimmer in self.swimmers:
            # Helper to format time
            def format_time(stroke, distance):
                time = swimmer.get_time(stroke, distance)
                if time:
                    # Format as MM:SS.HH or SS.HH
                    if time >= 60:
                        mins = int(time // 60)
                        secs = time % 60
                        return f"{mins}:{secs:05.2f}"
                    else:
                        return f"{time:.2f}"
                return ''
            
            values = (
                swimmer.name,
                swimmer.age,
                swimmer.gender.value,
                '✓' if swimmer.morning_available else '',
                '✓' if swimmer.afternoon_available else '',
                format_time('Free', 50),
                format_time('Back', 50),
                format_time('Breast', 50),
                format_time('Fly', 50),
                format_time('Free', 100),
                format_time('Back', 100),
                format_time('Breast', 100),
                format_time('Fly', 100),
                format_time('Free', 200)
            )
            # Store swimmer_id as tag for internal reference, not as visible text
            item_id = self.swimmers_tree.insert('', 'end', values=values, tags=(swimmer.swimmer_id,))
    
    def refresh_events_list(self):
        # Clear existing widgets
        for widget in self.events_frame.winfo_children():
            widget.destroy()
        
        if not self.current_result:
            # Show events without assignments
            for event in self.events:
                self.create_event_widget(event, None)
        else:
            # Show events with assignments
            for event in self.events:
                assignments = self.current_result.get_assignments_by_event(event.event_number)
                assignment = assignments[0] if assignments else None
                self.create_event_widget(event, assignment)
    
    def create_event_widget(self, event: Event, assignment: Optional[TeamAssignment]):
        # Event frame
        event_frame = ttk.LabelFrame(self.events_frame, 
                                    text=f"Event {event.event_number}: {event.event_name} ({event.session.value})",
                                    padding="10")
        event_frame.pack(fill='x', padx=5, pady=5)
        
        if assignment:
            # Show team assignment
            team_frame = ttk.Frame(event_frame)
            team_frame.pack(fill='x')
            
            # Age group and expected results
            info_label = ttk.Label(team_frame, 
                                 text=f"Age Group: {assignment.age_group[0]}-{assignment.age_group[1]} | "
                                      f"Total Time: {self.format_time(assignment.expected_time)} | "
                                      f"Z-Score: {assignment.z_score:+.2f} SD")
            info_label.pack(pady=5)
            
            # Swimmers table
            columns = ('Position', 'Swimmer', 'Age', 'Time', 'Events')
            tree = ttk.Treeview(team_frame, columns=columns, show='headings', height=4)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=150 if col == 'Swimmer' else 100)
            
            # Add swimmers
            strokes = event.get_strokes()
            for i, (swimmer, stroke) in enumerate(zip(assignment.team.swimmers, strokes)):
                position = stroke if event.stroke_type.value == "Medley" else f"Leg {i+1}"
                time = swimmer.get_time(stroke, event.distance)
                values = (
                    position,
                    swimmer.name,
                    swimmer.age,
                    self.format_time(time) if time else 'N/A',
                    f"{swimmer.events_assigned}/{swimmer.max_events}"
                )
                tree.insert('', 'end', values=values)
            
            tree.pack(fill='x')
        else:
            # Show empty slot
            ttk.Label(event_frame, text="No team assigned", foreground='gray').pack()
    
    def format_time(self, seconds: float) -> str:
        if seconds == float('inf'):
            return "N/A"
        minutes = int(seconds // 60)
        seconds = seconds % 60
        if minutes > 0:
            return f"{minutes}:{seconds:05.2f}"
        else:
            return f"{seconds:.2f}"
    
    def add_swimmer(self):
        dialog = SwimmerDialog(self.root, self.db)
        self.root.wait_window(dialog.dialog)
        self.load_data()
    
    def add_event(self):
        dialog = EventDialog(self.root, self.db)
        self.root.wait_window(dialog.dialog)
        self.load_data()
    
    def edit_swimmer(self, event):
        selection = self.swimmers_tree.selection()
        if selection:
            # Get swimmer ID from tags
            item = self.swimmers_tree.item(selection[0])
            tags = item.get('tags', [])
            swimmer_id = tags[0] if tags else None
            
            # Find swimmer
            swimmer = next((s for s in self.swimmers if s.swimmer_id == swimmer_id), None)
            if swimmer:
                dialog = SwimmerDialog(self.root, self.db, swimmer)
                self.root.wait_window(dialog.dialog)
                self.load_data()
    
    def show_swimmer_context_menu(self, event):
        # Create context menu
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Edit", command=lambda: self.edit_swimmer(None))
        menu.add_command(label="Delete", command=self.delete_swimmer)
        menu.post(event.x_root, event.y_root)
    
    def delete_swimmer(self):
        selection = self.swimmers_tree.selection()
        if selection:
            if messagebox.askyesno("Delete Swimmer", "Are you sure you want to delete this swimmer?"):
                item = self.swimmers_tree.item(selection[0])
                tags = item.get('tags', [])
                swimmer_id = tags[0] if tags else None
                if swimmer_id:
                    self.db.delete_swimmer(swimmer_id)
                    self.load_data()
    
    def run_optimizer(self):
        if not self.swimmers:
            messagebox.showwarning("No Swimmers", "Please add swimmers before optimizing.")
            return
        
        if not self.events:
            messagebox.showwarning("No Events", "Please add events before optimizing.")
            return
        
        # Show progress dialog
        progress_dialog = ProgressDialog(self.root, "Running Optimization")
        
        # Run optimization in background thread
        def optimize():
            # Reset event assignments
            for swimmer in self.swimmers:
                swimmer.events_assigned = 0
            
            # Create optimizer
            optimizer = RelayOptimizer(self.swimmers, self.events)
            
            # Progress callback to update dialog with throttling
            import time
            last_update = [0]  # Use list to allow modification in nested function
            
            def progress(msg):
                # Throttle updates to every 100ms to prevent recursion
                current_time = time.time()
                if current_time - last_update[0] >= 0.1:  # 100ms minimum between updates
                    last_update[0] = current_time
                    self.root.after(0, lambda: progress_dialog.update_status(msg))
            
            result = optimizer.optimize(progress_callback=progress)
            
            # Update UI in main thread
            self.root.after(0, lambda: self.optimization_complete_with_dialog(result, progress_dialog))
        
        thread = threading.Thread(target=optimize)
        thread.daemon = True  # Make thread daemon so it closes with main program
        thread.start()
    
    def optimization_complete_with_dialog(self, result: OptimizationResult, progress_dialog):
        """Complete optimization and close progress dialog"""
        progress_dialog.close()
        self.optimization_complete(result)
    
    def optimization_complete(self, result: OptimizationResult):
        self.current_result = result
        
        # Show warnings if any
        if result.warnings:
            warnings_text = "\n".join(result.warnings)
            messagebox.showwarning("Optimization Warnings", warnings_text)
        
        self.refresh_display()
        self.display_results()
        
        # Show completion message
        messagebox.showinfo("Optimization Complete", 
                          f"Total Z-Score: {result.total_z_score:+.2f} SD\n"
                          f"Events assigned: {len(result.assignments)}")
    
    def display_results(self):
        if not self.current_result:
            return
        
        self.results_text.delete(1.0, tk.END)
        
        # Summary
        self.results_text.insert(tk.END, "=== OPTIMIZATION RESULTS ===\n\n")
        self.results_text.insert(tk.END, f"Total Z-Score: {self.current_result.total_z_score:+.2f} SD\n")
        self.results_text.insert(tk.END, f"Average Z-Score per Event: {self.current_result.total_z_score/len(self.current_result.assignments) if self.current_result.assignments else 0:+.2f} SD\n")
        self.results_text.insert(tk.END, f"Events with Teams: {len(self.current_result.assignments)}\n")
        self.results_text.insert(tk.END, f"Events Skipped: {len(self.current_result.events_skipped)}\n\n")
        
        # Swimmer usage
        self.results_text.insert(tk.END, "=== SWIMMER USAGE ===\n")
        for name, count in sorted(self.current_result.swimmer_event_counts.items()):
            self.results_text.insert(tk.END, f"{name}: {count} events\n")
        
        # Skipped events
        if self.current_result.events_skipped:
            self.results_text.insert(tk.END, "\n=== SKIPPED EVENTS ===\n")
            for skip in self.current_result.events_skipped:
                self.results_text.insert(tk.END, f"• {skip}\n")
        
        # Warnings
        if self.current_result.warnings:
            self.results_text.insert(tk.END, "\n=== WARNINGS ===\n")
            for warning in self.current_result.warnings:
                self.results_text.insert(tk.END, f"• {warning}\n")
    
    def validate_teams(self):
        if not self.current_result:
            messagebox.showinfo("No Results", "Please run the optimizer first.")
            return
        
        issues = self.current_result.validate_constraints()
        if issues:
            messagebox.showwarning("Validation Issues", "\n".join(issues))
        else:
            messagebox.showinfo("Validation", "All teams are valid!")
    
    def clear_teams(self):
        self.current_result = None
        for swimmer in self.swimmers:
            swimmer.events_assigned = 0
        self.refresh_display()
    
    def clear_all(self):
        if messagebox.askyesno("Clear All", "Delete all swimmers and events from the database?"):
            cursor = self.db.conn.cursor()
            cursor.execute('DELETE FROM swimmers')
            cursor.execute('DELETE FROM events')
            # Reset the autoincrement counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='swimmers'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='events'")
            self.db.conn.commit()
            self.load_data()
            self.current_result = None
    
    def reset_database(self):
        if messagebox.askyesno("Reset Database", "This will delete all swimmers and events. Continue?"):
            self.db.clear_all_data()
            self.load_data()
            self.current_result = None
    
    def import_swimmers(self):
        filename = filedialog.askopenfilename(
            title="Import Swimmers from CSV or Excel",
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        if filename:
            try:
                from ..data.importer import import_swimmers_csv
                count = import_swimmers_csv(filename, self.db)
                messagebox.showinfo("Import Complete", f"Imported {count} swimmers")
                self.load_data()
            except Exception as e:
                messagebox.showerror("Import Error", str(e))
    
    def import_events(self):
        filename = filedialog.askopenfilename(
            title="Import Events CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            try:
                from ..data.importer import import_events_csv
                count = import_events_csv(filename, self.db)
                messagebox.showinfo("Import Complete", f"Imported {count} events")
                self.load_data()
            except Exception as e:
                messagebox.showerror("Import Error", str(e))
    
    def export_excel(self):
        if not self.current_result:
            messagebox.showinfo("No Results", "Please run the optimizer first.")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export to Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            try:
                from ..data.exporter import export_to_excel
                export_to_excel(self.current_result, self.events, filename)
                messagebox.showinfo("Export Complete", f"Results exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
    
    def export_pdf(self):
        if not self.current_result:
            messagebox.showinfo("No Results", "Please run the optimizer first.")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export to PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filename:
            try:
                from ..data.exporter import export_to_pdf
                export_to_pdf(self.current_result, self.events, filename)
                messagebox.showinfo("Export Complete", f"Results exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()