# Relay Swim Team Optimizer

## Project Overview
A discrete optimization tool to determine the optimal allocation of swimmers to relay teams for competitive swimming meets. The system maximizes points scored by strategically assigning swimmers to different relay events based on age groups, stroke capabilities, and availability constraints.

## Problem Statement
Given a pool of available swimmers and a set of relay events, determine the optimal team configurations that:
1. Maximize total points scored across all events
2. Respect swimmer constraints (availability, stroke capabilities, event limits)
3. Follow competition rules (age groups, scoring system, team composition)

## Competition Rules

### Age Groups
- Relay age is calculated by summing the ages of all 4 swimmers (as of December 31st)
- Age group brackets (40-year bands):
  - 72-99
  - 100-119
  - 120-159
  - 160-199
  - 200-239
  - 240-279
  - 280-319
  - 320-359
  - 360-399
  - 400+ (oldest category)

### Scoring System
- 1st place: 20 points
- 2nd place: 18 points
- 3rd place: 16 points
- 4th place: 14 points
- 5th-9th: Points decrease by 2 each place
- 10th and after: 2 points each

**Critical Rule**: Only ONE team per age group per event per club can score points. If a club enters multiple teams in the same age group for the same event, only the highest-placing team scores.

### Event Types
1. **Stroke Types**:
   - Freestyle relays
   - Medley relays (order: Backstroke → Breaststroke → Butterfly → Freestyle)

2. **Gender Categories**:
   - Men's relays (4 men)
   - Women's relays (4 women)
   - Mixed relays (2 men, 2 women)

3. **Distances**:
   - 4×25m
   - 4×50m
   - 4×100m
   - 4×200m

### Event Scheduling
- Events run sequentially (no overlapping events)
- Events are divided into morning (AM) and afternoon (PM) sessions

## Data Schemas

### Swimmer Information
Each swimmer record contains:
- **Last Name**: String
- **First Name**: String
- **Date of Birth**: Date (for age calculation)
- **Gender**: M/F
- **Age**: Integer (calculated as of Dec 31)
- **Lane**: String/Integer (swimming lane assignment)
- **Excluded Strokes**: List of strokes they cannot swim
- **Morning Available**: Boolean (Yes/No)
- **Afternoon Available**: Boolean (Yes/No)
- **Performance Times**: Matrix of times for each stroke/distance combination
  - Columns for each valid stroke-distance pair (e.g., 50m Free, 100m Back, etc.)
  - Times serve as performance rankings

### Event Information
Each event contains:
- **Event Number**: Integer
- **Session**: AM/PM
- **Event Name**: String
- **Gender Type**: Men/Women/Mixed
- **Stroke Type**: Freestyle/Medley
- **Distance**: 4×25/4×50/4×100/4×200

## Constraints

### Hard Constraints (Must be satisfied)
1. Each swimmer can participate in maximum 6 events
2. Swimmers can only compete in events during their available sessions (AM/PM)
3. Swimmers cannot swim strokes marked as "excluded"
4. Mixed relays must have exactly 2 men and 2 women
5. Each relay team must have exactly 4 swimmers
6. No swimmer can be in multiple teams for the same event

### Soft Constraints (Preferences)
1. Some swimmers may prefer fewer than 6 events
2. Swimmers have preferred strokes (use as tiebreaker)
3. Aim for age group diversity (better to have teams in different age groups)

## Optimization Objectives

### Primary Goal
Maximize total points scored across all events

### Strategy Considerations
The optimizer must balance:
1. **Quantity vs Quality**: More teams vs faster teams
2. **Age Group Distribution**: Spreading teams across age groups to avoid internal competition
3. **Swimmer Utilization**: Efficiently using the 6-event limit per swimmer
4. **Competitive Positioning**: Estimating placement based on seed times

## Technical Requirements

### Platform
- macOS application

### Features
1. **Data Input**:
   - CSV/Excel import for swimmer data
   - Manual entry forms for swimmers
   - Manual entry forms for events
   - Edit capability for all data

2. **Main Interface**:
   - Dashboard showing all events and swimmers
   - Project management style view
   - Swimmer roster management
   - Event schedule management

3. **Output**:
   - Optimal team assignments for each event
   - List of swimmers per team with predicted times
   - Expected points per event
   - Overall strategy summary

## Implementation Approach

### Algorithm Considerations
- Discrete optimization problem (likely mixed-integer programming)
- May benefit from game-theoretic approaches for competitive strategy
- Need to estimate placement probabilities based on seed times
- Consider using:
  - Constraint programming
  - Genetic algorithms
  - Simulated annealing
  - Or hybrid approaches

### Data Processing
1. Parse swimmer capabilities and times
2. Calculate age groups for all possible 4-swimmer combinations
3. Generate feasible teams per event
4. Optimize allocation considering all constraints
5. Output recommended team configurations

## Next Steps
1. Finalize optimization algorithm approach
2. Design user interface mockups
3. Implement data models
4. Build constraint solver
5. Create import/export functionality
6. Develop testing scenarios with sample data