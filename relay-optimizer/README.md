# Relay Team Optimizer

A discrete optimization tool for competitive swimming relay team assignments. Maximizes expected points by strategically assigning swimmers to relay events based on age groups, stroke capabilities, and availability constraints.

## Features

- **Monte Carlo Baseline + Systematic Search**: Two-phase optimization algorithm
- **Constraint Management**: Handles age groups, gender requirements, swimmer availability, and event limits
- **Direct-edit UI**: Spreadsheet-like interface with real-time validation
- **Import/Export**: CSV import for swimmers/events, Excel and PDF export for results
- **Visual Feedback**: Color-coded validation (green=optimal, yellow=suboptimal, red=invalid)

## Installation

1. Install Python 3.8 or higher with tkinter support:
   - **macOS**: `brew install python-tk` or use Python from python.org
   - **Ubuntu/Debian**: `sudo apt-get install python3-tk`
   - **Windows**: tkinter is included by default

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python src/main.py
```

Or use the provided run script:
```bash
./run.sh
```

## Quick Start

1. **Add Swimmers**: Click "Add Swimmer" or import from CSV (see `data/sample_swimmers.csv` for format)
2. **Add Events**: Click "Add Event" or import from CSV (see `data/sample_events.csv` for format)
3. **Run Optimizer**: Click "Optimize" to generate team assignments
4. **Export Results**: Export to Excel or PDF for meet documentation

## CSV Import Formats

### Swimmers CSV
- Required: Last Name, First Name, Birth Date, Gender (M/F)
- Optional: Max Events, Morning/Afternoon Available, Excluded/Preferred Strokes
- Times: Use format like `Free_50` or `Back_100` for column headers

### Events CSV
- Required: Event Number, Event Name, Session (AM/PM)
- Gender Type: Men/Women/Mixed
- Stroke Type: Free/Medley
- Distance: 25/50/100/200 (individual leg distance)
- Competition Level: 1-5 (1=low, 5=extreme)

## Age Groups

Teams are categorized into 40-year age bands based on total swimmer ages:
- 72-99, 100-119, 120-159, 160-199, 200-239, 240-279, 280-319

## Constraints

**Hard Constraints** (must satisfy):
- Each swimmer max 6 events
- Swimmers only in available sessions
- Cannot swim excluded strokes
- Mixed relays: exactly 2M + 2W
- Maximum one team per age group per event

**Soft Constraints** (preferences):
- Some swimmers prefer <6 events
- Use preferred strokes as tiebreaker
- Preserve swimmer capacity for later events

## Building Standalone App (Mac)

To create a standalone .app bundle:

```bash
pip install pyinstaller
pyinstaller --windowed --onefile --name "Relay Optimizer" src/main.py
```

The app will be in the `dist/` folder.