from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from .swimmer import Swimmer, Gender
from .event import Event, EventType, StrokeType

AGE_GROUPS = [
    (72, 99),
    (100, 119),
    (120, 159),
    (160, 199),
    (200, 239),
    (240, 279),
    (280, 319)  # Realistically the oldest competitive group
]

@dataclass
class Team:
    swimmers: List[Swimmer]
    event: Event
    
    def __post_init__(self):
        if len(self.swimmers) != 4:
            raise ValueError(f"Team must have exactly 4 swimmers, got {len(self.swimmers)}")
    
    @property
    def total_age(self) -> int:
        return sum(swimmer.age for swimmer in self.swimmers)
    
    @property
    def age_group(self) -> Tuple[int, int]:
        total_age = self.total_age
        for min_age, max_age in AGE_GROUPS:
            if min_age <= total_age <= max_age:
                return (min_age, max_age)
        # If somehow older than 319, put in highest group
        if total_age >= 320:
            return (280, 319)
        # If somehow younger than 72, put in youngest group  
        return (72, 99)
    
    @property
    def age_group_str(self) -> str:
        group = self.age_group
        return f"{group[0]}-{group[1]}"
    
    def calculate_time(self) -> float:
        total_time = 0.0
        strokes = self.event.get_strokes()
        
        for swimmer, stroke in zip(self.swimmers, strokes):
            time = swimmer.get_time(stroke, self.event.distance)
            if time is None:
                return float('inf')
            total_time += time
        
        return total_time
    
    def validate(self) -> Tuple[bool, str]:
        if len(self.swimmers) != 4:
            return False, "Team must have exactly 4 swimmers"
        
        if self.event.gender_type == EventType.MENS:
            if any(s.gender != Gender.MALE for s in self.swimmers):
                return False, "Men's event requires 4 men"
        elif self.event.gender_type == EventType.WOMENS:
            if any(s.gender != Gender.FEMALE for s in self.swimmers):
                return False, "Women's event requires 4 women"
        elif self.event.gender_type == EventType.MIXED:
            men = sum(1 for s in self.swimmers if s.gender == Gender.MALE)
            women = sum(1 for s in self.swimmers if s.gender == Gender.FEMALE)
            if men != 2 or women != 2:
                return False, f"Mixed relay needs 2M+2W, got {men}M+{women}W"
        
        for swimmer in self.swimmers:
            if not swimmer.available_for(self.event.session.value):
                return False, f"{swimmer.name} not available {self.event.session.value}"
            
            if swimmer.events_assigned >= swimmer.max_events:
                return False, f"{swimmer.name} at max events ({swimmer.max_events})"
        
        strokes = self.event.get_strokes()
        for swimmer, stroke in zip(self.swimmers, strokes):
            if not swimmer.can_swim(stroke):
                return False, f"{swimmer.name} cannot swim {stroke}"
            if not swimmer.has_time_for(stroke, self.event.distance):
                return False, f"{swimmer.name} has no time for {self.event.distance}m {stroke}"
        
        return True, "Valid team"

@dataclass
class TeamAssignment:
    event: Event
    team: Team
    age_group: Tuple[int, int]
    expected_time: float
    expected_points: float = 0.0  # Deprecated - use z_score
    z_score: float = 0.0  # Standard deviations from mean (positive = faster than average)