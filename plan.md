# Relay Swim Team Optimizer - Development Plan

## Project Overview
Building a discrete optimization tool to determine the optimal allocation of swimmers to relay teams for competitive swimming meets. The system will maximize points scored by strategically assigning swimmers to different relay events based on age groups, stroke capabilities, and availability constraints.

## Core Requirements

### Competition Rules
1. **Age Groups** (40-year bands):
   - 72-99, 100-119, 120-159, 160-199, 200-239, 240-279, 280-319, 320-359, 360-399, 400+
   - Age calculated by summing all 4 swimmers' ages (as of December 31st)

2. **Scoring System**:
   - 1st: 20pts, 2nd: 18pts, 3rd: 16pts, 4th: 14pts, 5th-9th: decrease by 2, 10th+: 2pts
   - **Critical**: Only ONE team per age group per event per club scores points

3. **Event Structure**:
   - **Types**: Men's (4M), Women's (4W), Mixed (2M+2W)
   - **Strokes**: Freestyle, Medley (Back→Breast→Fly→Free)
   - **Distances**: 4×25m, 4×50m, 4×100m, 4×200m
   - **Schedule**: Sequential events (no overlap), AM/PM sessions

### Data Schemas

#### Swimmer Data
- Last Name, First Name
- Date of Birth, Gender, Age (calculated)
- Lane assignment
- Preferred strokes (for tiebreaking)
- Excluded strokes (cannot swim)
- Morning Available (Y/N)
- Afternoon Available (Y/N)
- Performance times for each stroke/distance combination

#### Event Data
- Event Number
- Session (AM/PM)
- Event Name
- Gender Type (Men/Women/Mixed)
- Stroke Type (Freestyle/Medley)
- Distance (4×25/4×50/4×100/4×200)

### Constraints

#### Hard Constraints (MUST satisfy)
1. Each swimmer max 6 events
2. Swimmers only compete in available sessions (AM/PM)
3. Cannot swim excluded strokes
4. Mixed relays: exactly 2M + 2W
5. Each relay: exactly 4 swimmers
6. No swimmer in multiple teams for same event
7. Maximum ONE team per age group per event

#### Soft Constraints (preferences)
1. Some swimmers prefer <6 events
2. Use preferred strokes as tiebreaker
3. Aim for age group diversity

### Strategic Considerations
1. **Younger age groups**: Often have fewer competitors from other clubs (potential advantage)
2. **Medley optimization**: Assign swimmers to their fastest strokes
3. **Mixed relay optimization**: Minimize total time while maintaining 2M+2W
4. **No fatigue consideration**: Back-to-back events are acceptable

## Technical Architecture

### Technology Stack
- **Language**: Python 3.x
- **UI Framework**: Tkinter (built-in, reliable)
- **Optimization**: Google OR-Tools
- **Data Storage**: SQLite (local persistence)
- **Data Processing**: Pandas (CSV/Excel import)
- **PDF Generation**: ReportLab
- **Packaging**: PyInstaller (create standalone .app)

### Features
1. **Data Management**:
   - CSV/Excel import for swimmer data
   - Manual entry/edit for swimmers and events
   - Persistent local storage

2. **User Interface**:
   - Main dashboard (project management style)
   - Event list view
   - Swimmer roster management
   - Data editing capabilities

3. **Output**:
   - Optimal team assignments per event
   - Swimmer lists with predicted times
   - Expected points calculation
   - PDF and Excel export

## Optimization Approach

### [TO BE DETERMINED - DISCUSSION SECTION]

This section will detail the optimization algorithm and strategy. Key considerations:
- Mixed Integer Programming vs Constraint Programming vs Metaheuristics
- How to model the scoring system
- How to estimate placement probabilities without competitor data
- How to handle the strategic elements (age group targeting, etc.)
- Whether to use game-theoretic approaches
- Using Monte Carlo simulation to establish baseline performance distributions

## Implementation Phases

### Phase 1: Foundation
1. Set up project structure
2. Create data models (Swimmer, Event, Team, Result)
3. Implement SQLite database schema
4. Build basic CRUD operations

### Phase 2: Data Import/Export
1. CSV/Excel import functionality
2. Data validation and error handling
3. Export to PDF/Excel formats

### Phase 3: Optimization Engine
1. Implement constraint checking
2. Build optimization model
3. Create solver interface
4. Test with sample data

### Phase 4: User Interface
1. Main application window
2. Swimmer management screen
3. Event management screen
4. Results visualization
5. Export functionality

### Phase 5: Testing & Packaging
1. Create test scenarios
2. Performance optimization
3. Package as standalone Mac application
4. Documentation and user guide

## Project Structure
```
relay-optimizer/
├── src/
│   ├── models/
│   │   ├── swimmer.py
│   │   ├── event.py
│   │   ├── team.py
│   │   └── result.py
│   ├── optimization/
│   │   ├── constraints.py
│   │   ├── solver.py
│   │   └── strategies.py
│   ├── data/
│   │   ├── database.py
│   │   ├── importer.py
│   │   └── exporter.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── swimmer_view.py
│   │   ├── event_view.py
│   │   └── results_view.py
│   └── main.py
├── data/
│   └── relay_optimizer.db
├── tests/
├── docs/
├── requirements.txt
├── README.md
└── build.spec (PyInstaller config)
```

## Open Questions
1. Historical performance data availability (2019 results?)
2. Competitor seed times for placement estimation
3. Specific UI/UX preferences
4. Additional reporting requirements