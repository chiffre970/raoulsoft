from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Session(Enum):
    AM = "AM"
    PM = "PM"

class EventType(Enum):
    MENS = "Men"
    WOMENS = "Women"
    MIXED = "Mixed"

class StrokeType(Enum):
    FREESTYLE = "Free"
    MEDLEY = "Medley"

@dataclass
class Event:
    event_number: int
    event_name: str
    session: Session
    gender_type: EventType
    stroke_type: StrokeType
    distance: int  # Individual leg distance (25, 50, 100, 200)
    competition_level: int = 3  # 1-5 scale
    event_id: Optional[int] = None
    
    @property
    def total_distance(self) -> int:
        return self.distance * 4
    
    @property
    def relay_name(self) -> str:
        return f"4x{self.distance}"
    
    def get_strokes(self) -> list[str]:
        if self.stroke_type == StrokeType.MEDLEY:
            return ["Back", "Breast", "Fly", "Free"]
        else:
            return ["Free", "Free", "Free", "Free"]
    
    def __str__(self) -> str:
        return f"Event {self.event_number}: {self.event_name}"
    
    def __hash__(self):
        return hash(self.event_number)