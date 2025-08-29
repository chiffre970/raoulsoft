# Relay Optimizer Constraints

## Hard Constraints (MUST be satisfied)

### 1. Team Composition
- Exactly 4 swimmers per relay team
- No swimmer can appear in multiple teams for the same event
- Only one team per age group per event can score points. This means that you can field a team in the 120-159 and a team in the 160-199 if you want, and both can score points, but two teams in the same age group can't.

### 2. Gender Requirements
- Men's events: All 4 swimmers must be male
- Women's events: All 4 swimmers must be female
- Mixed events: Exactly 2 men + 2 women

### 3. Event Participation Limit
- Maximum 6 events per swimmer (absolute hard limit)
- Cannot exceed this under any circumstances

### 4. Session Availability
- Swimmers can only compete in sessions they're available for (AM/PM)

### 5. Stroke Capability
- Swimmers can only swim strokes they're capable of
- Swimmers must have recorded times for assigned stroke/distance

### 6. Age Group Rules
- Age calculated as of December 31st
- Age groups: 72-99, 100-119, 120-159, 160-199, 200-239, 240-279, 280-319, etc. (40-year brackets)
- Team age = sum of all 4 swimmers' ages

### 7. Scoring Constraint
- Only ONE team per age group per event can score points for the club
- If multiple teams in same age group/event, only highest placed scores

### 8. Medley Order
- Medley relays must be swum in order: Backstroke → Breaststroke → Butterfly → Freestyle
- Each swimmer swims exactly one leg in this order

### 9. Max events
- Any swimmer can participate in NO MORE than 6 events

## Soft Constraints (Optimization preferences)

### 1. Team Strength
- Optimize for fastest possible times within constraints
- Balance team strength across events

## Data Integrity Constraints

### 1. Unique Identification
- No duplicate swimmers (unique by first_name + last_name + birth_date)
- No duplicate event numbers

### 2. Required Information
- All swimmers must have: name, birth date, gender
- All events must have: number, name, session, gender type, stroke type, distance

## Scoring System

Points are awarded based on placement:
- 1st place: 20 points
- 2nd place: 18 points
- 3rd place: 16 points
- 4th place: 14 points
- 5th place: 12 points
- 6th place: 10 points
- 7th place: 8 points
- 8th place: 6 points
- 9th place: 4 points
- 10th place and after: 2 points

Note: Only the highest placed team per age group per event scores points for the club.

Adjustments: age groups away from the middle get a slight boost, because the competition is usually less deep

This is what our entries looked like last year, and you can take this as roughly representative of all clubs.

Age Group       Teams
72 - 119        1
120-169         10
160-199         14
200-239         15
240-279         10
280-319         0
320-359         0
360-399         0