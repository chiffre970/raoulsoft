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
- Max Events (default 6, but can be 1-6 based on swimmer preference)
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
- Expected Competition (1-5 scale: 1=low/none, 3=average, 5=extreme)

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

### Two-Phase Optimization: Monte Carlo Baseline + Systematic Search

The optimizer uses Monte Carlo simulation to establish statistical baselines, then systematically searches for configurations that maximize the standard deviation gap from those baselines.

#### 1. Phase 1: Monte Carlo Baseline Generation
- Generate **100-200 random valid team configurations** per event/age group
- Calculate mean and standard deviation of times
- This establishes "what random selection looks like" as our benchmark
- Parallelized computation: <1 second for typical meets

```python
def generate_baselines_parallel(events, swimmers):
    """Generate baseline distributions for all events in parallel"""
    with Pool(processes=cpu_count()) as pool:
        results = pool.starmap(
            generate_baseline_for_event,
            [(event, swimmers, 200) for event in events]
        )
    return dict(zip(events, results))

def generate_baseline_for_event(event, swimmers, n_simulations):
    baselines = {}
    for age_group in AGE_GROUPS:
        random_times = []
        for _ in range(n_simulations):
            # Select random valid team for this age group
            team = select_random_valid_team(event, age_group, swimmers)
            if team:
                random_times.append(calculate_team_time(team))
        
        if random_times:
            baselines[age_group] = {
                'mean': np.mean(random_times),
                'std': np.std(random_times)
            }
    return baselines
```

#### 2. Phase 2: Systematic Configuration Search
- Generate all valid team combinations for each event
- Use branch-and-bound or dynamic programming to explore configurations
- For each configuration, calculate z-score: `(baseline_mean - team_time) / baseline_std`
- Select configuration that maximizes total expected points across all events

```python
def optimize_teams():
    # Phase 1: Establish baselines
    baselines = generate_baselines_parallel(events, swimmers)
    
    # Phase 2: Systematic search for optimal configuration
    best_score = 0
    best_allocation = None
    
    # Pre-compute all valid teams for each event (with pruning)
    event_teams = {}
    for event in events:
        event_teams[event] = generate_all_valid_teams(event, swimmers)
        # Prune obviously slow teams if too many combinations
        if len(event_teams[event]) > 1000:
            event_teams[event] = prune_slow_teams(event_teams[event], keep_top=1000)
    
    # Branch and bound search with memoization
    memo = {}
    
    def search(event_idx, used_swimmers, current_allocation, current_score):
        nonlocal best_score, best_allocation
        
        # Memoization key
        key = (event_idx, frozenset(used_swimmers))
        if key in memo and memo[key] >= current_score:
            return  # Already found better path
        memo[key] = current_score
        
        # Base case: all events processed
        if event_idx == len(events):
            if current_score > best_score:
                best_score = current_score
                best_allocation = current_allocation.copy()
            return
        
        # Bound: estimate max possible remaining score
        max_remaining = estimate_max_score(events[event_idx:], used_swimmers)
        if current_score + max_remaining <= best_score:
            return  # Prune this branch
        
        event = events[event_idx]
        
        # Try not entering a team for this event
        search(event_idx + 1, used_swimmers, current_allocation, current_score)
        
        # Try each valid team for this event
        for team in event_teams[event]:
            # Check constraints
            if not team_fits_constraints(team, used_swimmers):
                continue
            
            # Calculate expected points using z-score
            team_time = calculate_team_time(team, event)
            age_group = calculate_age_group(team)
            
            if age_group in baselines[event]:
                mean = baselines[event][age_group]['mean']
                std = baselines[event][age_group]['std']
                z_score = (mean - team_time) / std if std > 0 else 0
                points = estimate_points_from_z_score(z_score, event.competition_level)
                
                # Recursively explore with this choice
                new_used = used_swimmers.copy()
                for swimmer in team:
                    new_used[swimmer] = new_used.get(swimmer, 0) + 1
                
                new_allocation = current_allocation.copy()
                new_allocation.append((event, team, age_group, points))
                
                search(event_idx + 1, new_used, new_allocation, current_score + points)
    
    # Start search
    search(0, {}, [], 0)
    return best_allocation

def estimate_points_from_z_score(z_score, competition_level):
    """Convert z-score to expected points based on competition level"""
    # Competition adjustment (1=low, 5=extreme)
    thresholds = {
        1: [0.5, 0.3, 0.1, -0.1],  # Low competition
        2: [0.8, 0.5, 0.3, 0.1],   
        3: [1.2, 0.8, 0.5, 0.2],   # Normal competition
        4: [1.5, 1.1, 0.7, 0.4],   
        5: [2.0, 1.5, 1.0, 0.6]    # Extreme competition
    }
    
    thresh = thresholds[competition_level]
    if z_score > thresh[0]: return 20    # 1st place
    elif z_score > thresh[1]: return 18  # 2nd place
    elif z_score > thresh[2]: return 16  # 3rd place
    elif z_score > thresh[3]: return 14  # 4th place
    elif z_score > thresh[3] - 0.3: return 12  # 5th place
    elif z_score > thresh[3] - 0.5: return 10  # 6th place
    else: return 2  # Participation points
```

#### 3. Comprehensive Constraint Validation & Edge Cases
```python
def validate_team_complete(team, event):
    """Validate a complete team for an event with all edge cases"""
    # 1. Basic team size
    if len(team) != 4:
        return False, "Need exactly 4 swimmers"
    
    # 2. Gender requirements
    if event.gender_type == "Men" and any(s.gender != 'M' for s in team):
        return False, "Men's event requires 4 men"
    elif event.gender_type == "Women" and any(s.gender != 'F' for s in team):
        return False, "Women's event requires 4 women"
    elif event.gender_type == "Mixed":
        men = sum(1 for s in team if s.gender == 'M')
        if men != 2:
            return False, f"Mixed needs exactly 2M + 2F, got {men}M + {4-men}F"
    
    # 3. Availability check
    for swimmer in team:
        if not swimmer.available_for(event.session):
            return False, f"{swimmer.name} not available {event.session}"
    
    # 4. Event limit check
    for swimmer in team:
        if swimmer.events_assigned >= swimmer.max_events:
            return False, f"{swimmer.name} already at max events ({swimmer.max_events})"
    
    # 5. Medley relay stroke assignments
    if event.stroke_type == "Medley":
        strokes = ['Back', 'Breast', 'Fly', 'Free']
        for position, stroke in enumerate(strokes):
            swimmer = team[position]
            if stroke in swimmer.excluded_strokes:
                return False, f"{swimmer.name} cannot swim {stroke}"
            if not swimmer.has_time_for(stroke, event.distance):
                return False, f"{swimmer.name} has no time for {event.distance} {stroke}"
    
    # 6. Freestyle relay - all swimmers need freestyle times
    elif event.stroke_type == "Freestyle":
        for swimmer in team:
            if 'Free' in swimmer.excluded_strokes:
                return False, f"{swimmer.name} cannot swim freestyle"
            if not swimmer.has_time_for('Free', event.distance):
                return False, f"{swimmer.name} has no freestyle time for {event.distance}"
    
    return True, "Valid team"

def check_event_feasibility(event, available_swimmers):
    """Check if an event can be populated at all"""
    eligible = [s for s in available_swimmers if 
                s.available_for(event.session) and
                s.events_count < s.max_events]
    
    # Gender feasibility
    if event.gender_type == "Men":
        eligible = [s for s in eligible if s.gender == 'M']
        if len(eligible) < 4:
            return False, f"Only {len(eligible)} men available"
    elif event.gender_type == "Women":
        eligible = [s for s in eligible if s.gender == 'F']
        if len(eligible) < 4:
            return False, f"Only {len(eligible)} women available"
    elif event.gender_type == "Mixed":
        men = [s for s in eligible if s.gender == 'M']
        women = [s for s in eligible if s.gender == 'F']
        if len(men) < 2 or len(women) < 2:
            return False, f"Need 2M+2F, have {len(men)}M+{len(women)}F"
    
    # Medley stroke coverage
    if event.stroke_type == "Medley":
        for stroke in ['Back', 'Breast', 'Fly', 'Free']:
            can_swim = [s for s in eligible if stroke not in s.excluded_strokes 
                       and s.has_time_for(stroke, event.distance)]
            if not can_swim:
                return False, f"No eligible swimmer for {stroke}"
    
    return True, f"{len(eligible)} eligible swimmers available"

def break_ties(team1, team2, team1_score, team2_score):
    """When teams have equal expected points, choose based on swimmer availability"""
    if team1_score != team2_score:
        return team1 if team1_score > team2_score else team2
    
    # Prefer team with swimmers who have fewer events (preserves capacity)
    events1 = sum(s.events_assigned for s in team1)
    events2 = sum(s.events_assigned for s in team2)
    return team1 if events1 < events2 else team2

# Edge Case Handling Strategy
"""
1. Insufficient swimmers for event -> Skip event entirely (no partial teams)
2. Mixed relay gender placement -> Optimize for speed regardless of position
3. Swimmer at max events -> Cannot be selected for additional events
4. Tie breaking -> Choose team with swimmers having fewer total events
5. Manual overrides -> Always validate but allow coach to force changes
"""
```

#### 4. Safety & Reliability Features
- **Input validation**: Check for impossible times, missing data, conflicts
- **Graceful degradation**: Always return valid solution, even if suboptimal
- **Progress reporting**: Show optimization progress to user
- **Explanation**: Report why certain decisions were made
- **Warnings**: Flag any concerns (swimmer at max capacity, weak teams, etc.)

## User Interface Design

### Main Event Table View
The primary interface is a spreadsheet-like table showing all events with their assigned teams. Users can directly edit swimmer assignments by clicking and typing.

```
┌─────────────────────────────────────────────────────────────────┐
│ Relay Optimizer                    [Add People] [Add Event] [⚙️] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Event 1: Men's 4x50 Free (AM)            Age Group: 120-159   │
│ ┌──────────┬──────────────┬──────┬──────────┬──────────────┐ │
│ │ Position │ Swimmer      │ Age  │ Time     │ Events       │ │
│ ├──────────┼──────────────┼──────┼──────────┼──────────────┤ │
│ │ 1        │ [Smith, John] │ 32   │ 24.5     │ 3/6         │ │
│ │ 2        │ [Doe, Mike]   │ 28   │ 25.1     │ 2/6         │ │
│ │ 3        │ [Lee, Kevin]  │ 35   │ 23.9     │ 4/6         │ │
│ │ 4        │ [Park, Sam]   │ 30   │ 24.8     │ 2/6         │ │
│ └──────────┴──────────────┴──────┴──────────┴──────────────┘ │
│ Team Time: 1:38.3  |  Expected Points: 18 (2nd)               │
│                                                                 │
│ Event 2: Women's 4x100 Medley (AM)       Age Group: 160-199   │
│ ┌──────────┬──────────────┬──────────┬──────────┬──────────┐ │
│ │ Stroke   │ Swimmer      │ Age      │ Time     │ Events   │ │
│ ├──────────┼──────────────┼──────────┼──────────┼──────────┤ │
│ │ Back     │ [Chen, Amy]   │ 42       │ 65.2     │ 3/6     │ │
│ │ Breast   │ [Kim, Lisa]   │ 38       │ 71.5     │ 1/4     │ │
│ │ Fly      │ [Wu, Tina]    │ 41       │ 63.8     │ 5/6     │ │
│ │ Free     │ [Liu, Mary]   │ 39       │ 58.9     │ 2/6     │ │
│ └──────────┴──────────────┴──────────┴──────────┴──────────┘ │
│                                                                 │
│ Event 3: Mixed 4x25 Free (AM)    ⚠️ Not enough swimmers       │
│ [Event skipped - need 2M + 2F available]                      │
│                                                                 │
│ [Optimize] [Export to Excel] [Export to PDF] [Clear All]      │
└─────────────────────────────────────────────────────────────────┘
```

### Key UI Features

1. **Direct Editing**: Click any swimmer cell to type a new name
   - Auto-complete suggests swimmers from roster
   - Real-time validation (red border if invalid)
   - Shows warning icons for constraint violations

2. **Visual Feedback**:
   - Green highlight: Optimal assignment
   - Yellow highlight: Valid but suboptimal
   - Red highlight: Invalid assignment
   - Gray text: Swimmer at max events

3. **Information Display**:
   - Events counter (current/max) for each swimmer
   - Total team time and expected placement
   - Age group calculation shown for each team
   - Warning messages for skipped events

### Secondary Windows

#### Add People Window
```
┌─────────────────────────────────────────┐
│ Add Swimmer                             │
├─────────────────────────────────────────┤
│ First Name: [___________]               │
│ Last Name:  [___________]               │
│ Birth Date: [MM/DD/YYYY]                │
│ Gender:     (•) M  ( ) F                │
│                                          │
│ Availability:                            │
│ □ Morning (AM)  □ Afternoon (PM)        │
│                                          │
│ Max Events: [6] (1-6)                   │
│                                          │
│ Excluded Strokes:                       │
│ □ Back  □ Breast  □ Fly  □ Free        │
│                                          │
│ [Import CSV] [Save] [Cancel]            │
└─────────────────────────────────────────┘
```

#### Add Event Window
```
┌─────────────────────────────────────────┐
│ Add Event                                │
├─────────────────────────────────────────┤
│ Event #:    [___]                        │
│ Event Name: [_____________________]     │
│                                          │
│ Session:    (•) AM  ( ) PM              │
│ Gender:     (•) Men ( ) Women ( ) Mixed │
│ Stroke:     (•) Free ( ) Medley         │
│ Distance:   (•) 4x25 ( ) 4x50           │
│             ( ) 4x100 ( ) 4x200         │
│                                          │
│ Competition Level:                       │
│ [1]--[2]--[3]--[4]--[5]                │
│  Low     Normal    Extreme              │
│                                          │
│ [Save] [Cancel]                          │
└─────────────────────────────────────────┘
```

### Menu Structure
```
File
├── New Project
├── Open Project
├── Save Project
├── Import
│   ├── Import Swimmers (CSV)
│   └── Import Events (CSV)
├── Export
│   ├── Export to Excel
│   └── Export to PDF
└── Quit

Edit
├── Undo (Cmd+Z)
├── Redo (Cmd+Shift+Z)
├── Clear All Teams
└── Reset to Optimal

Tools
├── Run Optimizer
├── Validate All Teams
└── Settings
    ├── Optimization Settings
    └── Display Preferences
```

### Interaction Flow
1. **Initial Setup**: Import or manually enter swimmers and events
2. **Optimization**: Click "Optimize" to generate assignments
3. **Manual Adjustment**: Click cells to override suggestions
4. **Validation**: Real-time checking with visual feedback
5. **Export**: One-click export to Excel or PDF formats

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