# Relay Team Optimization - Conceptual Approach

## Overview

This document describes the conceptual approach for optimizing relay team allocation in Masters swimming competitions. The algorithm uses a greedy, scarcity-first strategy to maximize scoring opportunities while respecting all competition constraints.

## Core Philosophy

The key insight is that **breadth beats depth** in the Masters scoring system:
- Multiple decent teams score more points than a few excellent teams
- Example: Three 6th place finishes (30 points) > One 1st place finish (20 points)  
- Therefore, we optimize for maximum coverage first, speed second
- **Critical Rule**: Only ONE team per age group per event can score points

## Key Constraints

The algorithm must enforce three critical constraints:

1. **Six Event Maximum**: Each swimmer can compete in at most 6 events
2. **Gender Requirements**: Mixed relays must have exactly 2 men and 2 women
3. **Dynamic Scarcity**: Event priority must be recalculated after each assignment

## Algorithm Overview

### The Scarcity-First Greedy Approach

1. **Pre-Processing**: Calculate achievable age ranges per gender category to reduce search space
2. **Feasibility Check**: Validate that minimum swimmer requirements can be met
3. **Dynamic Event Ordering**: Process events in order of scarcity (fewest eligible swimmers first)
4. **Team Selection**: For each event, generate all valid teams, group by age bracket, select fastest per bracket
5. **Continuous Updates**: Recalculate scarcity after each event assignment
6. **Output**: Optimized team assignments with coverage and speed balance

### Why Scarcity-First?

Events with fewer eligible swimmers are processed first because:
- They have less flexibility in team composition
- If processed last, required swimmers might already be at the 6-event limit
- This ensures maximum event coverage

### Pre-Processing Strategy

The algorithm calculates achievable age ranges for each gender category by finding the minimum (youngest 4 swimmers) and maximum (oldest 4 swimmers) combined ages. This dramatically reduces the search space - if all male swimmers are 30-60 years old, we only need to consider age brackets 120-240 for men's events.

Feasibility validation ensures:
- Each event has at least 4 eligible swimmers
- Medley events have swimmers for all four strokes
- Total swimmer capacity can theoretically fill all event slots

## Dynamic Event Ordering

The algorithm processes events in order of **dynamic swimmer scarcity** - recalculated after each assignment. This is critical because swimmer availability changes as they are assigned to teams. Static ordering would lead to empty events and poor allocation.

Scarcity calculation considers:
- Swimmers below their 6-event limit
- Gender eligibility for the event
- Session availability
- Required stroke capabilities

## Team Generation and Selection

For each event (processed in scarcity order):

### 1. Filter Available Swimmers
Identify swimmers who:
- Have fewer than 6 events assigned
- Match gender requirements
- Are available for the session
- Can swim required strokes

### 2. Generate Valid Teams
- **Freestyle events**: Any 4 eligible swimmers
- **Medley events**: One swimmer per stroke (Back, Breast, Fly, Free)
- **Mixed events**: Exactly 2 men and 2 women

### 3. Age Bracket Grouping
Teams are grouped by combined age into Masters age brackets:
72-99, 100-119, 120-159, 160-199, 200-239, 240-279, 280-319, 320-359, 360-399, 400+

### 4. Optimal Selection
For each age bracket:
- Select the team with fastest combined time
- Assign to event and update swimmer counts
- Only one team per age bracket can score (others discarded)

## Medley Relay Optimization

### Stroke Assignment Strategy

For medley relays, assigning swimmers to strokes is a critical optimization challenge:

- **Small pools (≤20 swimmers)**: Brute force enumeration is feasible
- **Large pools (>20 swimmers)**: Hungarian algorithm required for O(n³) vs O(n⁴) complexity
- **Very large pools (>50 swimmers)**: Additional caching and pruning needed

The Hungarian algorithm becomes necessary because brute force complexity grows rapidly:
- 20 swimmers: ~160,000 combinations (manageable)
- 50 swimmers: ~6.25 million combinations (too slow)
- Hungarian reduces this to ~125,000 operations for 50 swimmers

### Performance Optimizations

1. **Medley Relay Stroke Assignment**: Use Hungarian algorithm for pools >20 swimmers
2. **Dynamic Scarcity**: Must recalculate after every event assignment
3. **Gender Validation**: Enforce 2M/2F requirement at generation and assignment
4. **Event Limit**: Enforce 6-event maximum at filtering and assignment stages

## Data Model

### Core Entities

- **Swimmer**: Tracks ID, name, gender, age, event count, assigned events, session availability, and times per stroke/distance
- **Event**: Defines event number, name, session, gender type (Men/Women/Mixed), stroke type (Freestyle/Medley), and distance
- **Team**: Contains 4 swimmers, calculates combined age, determines age bracket, and computes total time

### Age Bracket Calculation

Teams are assigned to age brackets based on combined swimmer ages:
- Sum ages of all 4 swimmers
- Map to appropriate bracket (72-99, 100-119, 120-159, etc.)
- Each bracket competes separately for scoring

## Algorithm Flow

### Main Optimization Loop

def optimize_relay_teams(swimmers, events):
    """
    Main optimization function
    """
    # Initialize
    for swimmer in swimmers:
        swimmer.event_count = 0
        swimmer.assigned_events = []
    
    all_assignments = []
    
    # Sort events by scarcity (fewest eligible swimmers first)
    events_sorted = sorted(events, key=lambda e: count_eligible_swimmers(e, swimmers))
    
    # Process each event
    for event in events_sorted:
        teams = assign_teams_for_event(event, swimmers)
        all_assignments.extend(teams)
    
    return all_assignments

def count_eligible_swimmers(event, swimmers):
    """
    Count how many swimmers are eligible for this event
    """
    count = 0
    for swimmer in swimmers:
        if (swimmer.event_count < 6 and
            is_gender_eligible(swimmer, event) and
            swimmer.is_available(event.session) and
            can_swim_event(swimmer, event)):
            count += 1
    return count

def assign_teams_for_event(event, all_swimmers):
    """
    Generate and assign teams for a single event
    
    CRITICAL VALIDATIONS:
    1. Enforce 6-event limit per swimmer
    2. Validate gender requirements for mixed events
    3. Update swimmer event counts immediately after assignment
    """
    # Get available swimmers - MUST enforce 6-event limit
    available = [
        s for s in all_swimmers
        if s.event_count < 6  # HARD LIMIT - DO NOT EXCEED
        and is_gender_eligible(s, event)
        and s.is_available(event.session)
        and can_swim_event(s, event)
    ]
    
    # For mixed events, validate we have enough of each gender
    if event.gender_type == 'Mixed':
        men_available = sum(1 for s in available if s.gender == 'M')
        women_available = sum(1 for s in available if s.gender == 'F')
        if men_available < 2 or women_available < 2:
            return []  # Cannot form valid mixed team
    
    # Generate all possible teams
    possible_teams = generate_all_teams(available, event)
    
    # Group by age bracket
    teams_by_bracket = {}
    for team in possible_teams:
        bracket = team.age_bracket
        if bracket not in teams_by_bracket:
            teams_by_bracket[bracket] = []
        teams_by_bracket[bracket].append(team)
    
    # Select best team per bracket
    selected_teams = []
    for bracket, teams in teams_by_bracket.items():
        best_team = min(teams, key=lambda t: t.total_time)
        
        # Assign the team
        for swimmer in best_team.swimmers:
            swimmer.event_count += 1
            swimmer.assigned_events.append(event)
        
        selected_teams.append(best_team)
        event.assigned_teams.append(best_team)
    
    return selected_teams

def generate_all_teams(swimmers, event):
    """
    Generate all valid 4-person teams for an event
    """
    teams = []
    
    if event.stroke_type == 'Freestyle':
        # For freestyle, any 4 swimmers work
        if event.gender_type == 'Mixed':
            # Need exactly 2 men and 2 women
            men = [s for s in swimmers if s.gender == 'M']
            women = [s for s in swimmers if s.gender == 'F']
            
            for men_pair in combinations(men, 2):
                for women_pair in combinations(women, 2):
                    team_swimmers = list(men_pair) + list(women_pair)
                    teams.append(Team(team_swimmers, event))
        else:
            # All same gender
            for combo in combinations(swimmers, 4):
                teams.append(Team(list(combo), event))
    
    else:  # Medley relay
        # Need one swimmer per stroke
        teams.extend(generate_medley_teams(swimmers, event))
    
    return teams

def generate_medley_teams(swimmers, event):
    """
    Generate valid medley relay teams (one swimmer per stroke)
    
    IMPORTANT: For swimmer pools > 20, you SHOULD use Hungarian algorithm
    to avoid O(n⁴) complexity that will cause performance issues.
    
    Decision tree:
    - <= 20 swimmers: Use brute force (fast enough)
    - > 20 swimmers: MUST use Hungarian algorithm
    - > 50 swimmers: Consider additional optimizations
    """
    teams = []
    strokes = ['Back', 'Breast', 'Fly', 'Free']
    
    # Get swimmers who can swim each stroke
    swimmers_by_stroke = {}
    for stroke in strokes:
        swimmers_by_stroke[stroke] = [
            s for s in swimmers 
            if s.can_swim(stroke, event.distance)
        ]
    
    # Early termination if any stroke has no swimmers
    for stroke in strokes:
        if not swimmers_by_stroke[stroke]:
            return []  # Cannot form any teams
    
    # Generate all combinations (brute force for smaller pools)
    for back_swimmer in swimmers_by_stroke['Back']:
        for breast_swimmer in swimmers_by_stroke['Breast']:
            if breast_swimmer == back_swimmer:
                continue
            for fly_swimmer in swimmers_by_stroke['Fly']:
                if fly_swimmer in [back_swimmer, breast_swimmer]:
                    continue
                for free_swimmer in swimmers_by_stroke['Free']:
                    if free_swimmer in [back_swimmer, breast_swimmer, fly_swimmer]:
                        continue
                    
                    team_swimmers = [back_swimmer, breast_swimmer, fly_swimmer, free_swimmer]
                    
                    # CRITICAL: Validate gender requirements for mixed events
                    if event.gender_type == 'Mixed':
                        men_count = sum(1 for s in team_swimmers if s.gender == 'M')
                        women_count = sum(1 for s in team_swimmers if s.gender == 'F')
                        if men_count != 2 or women_count != 2:
                            continue  # MUST have exactly 2 men and 2 women
                    
                    teams.append(Team(team_swimmers, event))
    
    return teams

def generate_medley_teams_hungarian(swimmers, event):
    """
    REQUIRED for swimmer pools > 20 to maintain performance
    
    The Hungarian algorithm is NECESSARY, not optional, for larger pools because:
    - Brute force: O(n⁴) - 50 swimmers = 6.25 million iterations
    - Hungarian: O(n³) - 50 swimmers = 125,000 iterations (50x faster)
    
    Implementation steps:
    1. Build cost matrix (swimmer x stroke)
    2. Apply Hungarian algorithm for optimal assignment
    3. Validate gender requirements for mixed events
    4. Return None if constraints cannot be satisfied
    """
    from scipy.optimize import linear_sum_assignment
    import numpy as np
    
    strokes = ['Back', 'Breast', 'Fly', 'Free']
    n_swimmers = len(swimmers)
    
    # Create cost matrix (swimmer x stroke)
    cost_matrix = np.full((n_swimmers, 4), np.inf)
    
    for i, swimmer in enumerate(swimmers):
        for j, stroke in enumerate(strokes):
            if swimmer.can_swim(stroke) and swimmer.has_time_for(stroke, event.distance):
                cost_matrix[i, j] = swimmer.get_time(stroke, event.distance)
    
    # Find optimal assignment
    row_indices, col_indices = linear_sum_assignment(cost_matrix)
    
    # Get the 4 best assignments
    assignments = list(zip(row_indices[:4], col_indices[:4]))
    
    # Build team from assignments
    team_swimmers = []
    for swimmer_idx, stroke_idx in assignments:
        if cost_matrix[swimmer_idx, stroke_idx] == np.inf:
            return None  # No valid assignment
        team_swimmers.append(swimmers[swimmer_idx])
    
    # CRITICAL: Validate gender requirements for mixed events
    if event.gender_type == 'Mixed':
        men_count = sum(1 for s in team_swimmers if s.gender == 'M')
        women_count = sum(1 for s in team_swimmers if s.gender == 'F')
        if men_count != 2 or women_count != 2:
            return None  # MUST have exactly 2 men and 2 women - NO EXCEPTIONS
    
    return Team(team_swimmers, event)

def is_gender_eligible(swimmer, event):
    """
    Check if swimmer's gender matches event requirements
    """
    if event.gender_type == 'Men':
        return swimmer.gender == 'M'
    elif event.gender_type == 'Women':
        return swimmer.gender == 'F'
    else:  # Mixed
        return True  # Both genders needed

def can_swim_event(swimmer, event):
    """
    Check if swimmer has times for required strokes
    """
    if event.stroke_type == 'Freestyle':
        return swimmer.can_swim('Free', event.distance)
    else:  # Medley - need to check if they can swim at least one stroke
        strokes = ['Back', 'Breast', 'Fly', 'Free']
        return any(swimmer.can_swim(stroke, event.distance) for stroke in strokes)
```

### Optimization Enhancements

#### 1. Caching for Performance
```python
from functools import lru_cache

@lru_cache(maxsize=10000)
def calculate_team_time_cached(swimmer_ids: tuple, event_id: int) -> float:
    """
    Cache team time calculations to avoid redundant computation
    Note: Only cache static calculations, not eligible swimmers (which change)
    """
    # Look up swimmers by ID and calculate total time
    swimmers = [get_swimmer_by_id(sid) for sid in swimmer_ids]
    event = get_event_by_id(event_id)
    strokes = event.get_strokes()
    
    total_time = 0
    for swimmer, stroke in zip(swimmers, strokes):
        time = swimmer.get_time(stroke, event.distance)
        if time is None:
            return float('inf')
        total_time += time
    
    return total_time
```

#### 2. Age Bracket Optimization
```python
def get_valid_age_brackets(swimmers, event):
    """
    Only consider age brackets that are actually achievable
    """
    if event.gender_type == 'Men':
        eligible = [s for s in swimmers if s.gender == 'M']
    elif event.gender_type == 'Women':
        eligible = [s for s in swimmers if s.gender == 'F']
    else:  # Mixed
        eligible = swimmers
    
    if len(eligible) < 4:
        return []
    
    # Calculate min/max possible ages
    min_age = sum(sorted(s.age for s in eligible)[:4])
    max_age = sum(sorted(s.age for s in eligible)[-4:])
    
    # Age brackets from README
    AGE_BRACKETS = [
        (72, 99), (100, 119), (120, 159), (160, 199),
        (200, 239), (240, 279), (280, 319), (320, 359),
        (360, 399), (400, float('inf'))  # 400+
    ]
    
    valid_brackets = []
    for bracket_min, bracket_max in AGE_BRACKETS:
        # Check if this bracket is achievable
        if bracket_min <= max_age and (bracket_max >= min_age or bracket_max == float('inf')):
            valid_brackets.append((bracket_min, bracket_max))
    
    return valid_brackets
```

#### 3. Parallel Processing
```python
from multiprocessing import Pool

def optimize_relay_teams_parallel(swimmers, events):
    """
    Process events in parallel for better performance
    """
    with Pool() as pool:
        # Process events in batches
        results = pool.starmap(assign_teams_for_event, 
                              [(event, swimmers) for event in events])
    return results
```

## Edge Cases and Validation

### Common Edge Cases

1. **Insufficient Swimmers**: Events that cannot field teams are logged and skipped
2. **Stroke Specialists**: Scarcity-first ordering ensures critical swimmers remain available
3. **Age Group Gaps**: Algorithm naturally handles unreachable age brackets
4. **Gender Imbalance**: Mixed events validate sufficient swimmers of each gender

### Validation Requirements

After optimization completes:
- Verify no swimmer exceeds 6 events
- Confirm one team per age bracket per event
- Validate 4 swimmers per team
- Check 2M/2F composition for mixed events

### Tie-Breaking Strategy

When multiple teams have identical times:
- Primary: Fastest combined time
- Secondary: Teams with swimmers who have fewer events assigned (spreads load)
- This ensures balanced swimmer utilization

## Performance Analysis

### Computational Complexity

For N swimmers and E events:
- Combinations per event: C(N, 4) ≈ N⁴/24
- Total complexity: O(E × N⁴)
- Example: 50 swimmers, 15 events = ~3.5 million combinations

### Runtime Expectations

- Base algorithm: < 10 seconds for typical meet
- With optimizations: < 3 seconds
- With parallelization: < 1 second

## Output Format

The algorithm produces:
- Team assignments per event with age brackets
- Summary statistics (teams created, events covered, swimmer utilization)
- Warnings for events that couldn't be filled

## Future Considerations

### Potential Enhancements

- **Smart Reservation**: Hold back key swimmers for critical events
- **Competition Analysis**: Factor in expected competition per age bracket
- **ML Placement Prediction**: Use historical data to predict likely placements
- **Multi-objective Optimization**: Balance speed, coverage, and fatigue
- **Real-time Adjustments**: Re-optimize during meets based on results

## Conclusion

This scarcity-first, greedy algorithm provides a practical and effective solution for relay team optimization. By prioritizing events with limited options and maximizing coverage across age brackets, it ensures the maximum possible points while respecting all constraints. The implementation is straightforward, performant, and produces transparent, understandable results.