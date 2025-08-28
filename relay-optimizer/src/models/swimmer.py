from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Set
from enum import Enum

class Gender(Enum):
    MALE = 'M'
    FEMALE = 'F'

@dataclass
class Swimmer:
    first_name: str
    last_name: str
    birth_date: date
    gender: Gender
    max_events: int = 6
    morning_available: bool = True
    afternoon_available: bool = True
    excluded_strokes: Set[str] = field(default_factory=set)
    times: Dict[tuple[str, int], float] = field(default_factory=dict)
    events_assigned: int = 0
    swimmer_id: Optional[int] = None
    
    @property
    def name(self) -> str:
        return f"{self.last_name}, {self.first_name}"
    
    @property
    def age(self) -> int:
        reference_date = date(date.today().year, 12, 31)
        return reference_date.year - self.birth_date.year - (
            (reference_date.month, reference_date.day) < 
            (self.birth_date.month, self.birth_date.day)
        )
    
    def available_for(self, session: str) -> bool:
        if session == "AM":
            return self.morning_available
        elif session == "PM":
            return self.afternoon_available
        return False
    
    def can_swim(self, stroke: str) -> bool:
        return stroke not in self.excluded_strokes
    
    def has_time_for(self, stroke: str, distance: int) -> bool:
        return (stroke, distance) in self.times
    
    def get_time(self, stroke: str, distance: int) -> Optional[float]:
        return self.times.get((stroke, distance))
    
    def events_remaining(self) -> int:
        return self.max_events - self.events_assigned
    
    def __hash__(self):
        return hash((self.first_name, self.last_name, self.birth_date))