from dataclasses import dataclass, field
from typing import List, Dict
from .team import TeamAssignment

@dataclass
class OptimizationResult:
    assignments: List[TeamAssignment] = field(default_factory=list)
    total_expected_points: float = 0.0
    events_skipped: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    swimmer_event_counts: Dict[str, int] = field(default_factory=dict)
    
    def add_assignment(self, assignment: TeamAssignment):
        self.assignments.append(assignment)
        self.total_expected_points += assignment.expected_points
        
        for swimmer in assignment.team.swimmers:
            key = swimmer.name
            self.swimmer_event_counts[key] = self.swimmer_event_counts.get(key, 0) + 1
    
    def add_warning(self, warning: str):
        if warning not in self.warnings:
            self.warnings.append(warning)
    
    def add_skipped_event(self, event_name: str, reason: str):
        self.events_skipped.append(f"{event_name}: {reason}")
    
    def get_assignments_by_event(self, event_number: int) -> List[TeamAssignment]:
        return [a for a in self.assignments if a.event.event_number == event_number]
    
    def validate_constraints(self) -> List[str]:
        issues = []
        
        # Check swimmer event limits
        for swimmer_name, count in self.swimmer_event_counts.items():
            if count > 6:
                issues.append(f"{swimmer_name} assigned to {count} events (max 6)")
        
        # Check for duplicate age groups per event
        event_age_groups = {}
        for assignment in self.assignments:
            key = assignment.event.event_number
            if key not in event_age_groups:
                event_age_groups[key] = []
            
            age_group = assignment.age_group
            if age_group in event_age_groups[key]:
                issues.append(f"Event {key} has multiple teams in age group {age_group}")
            event_age_groups[key].append(age_group)
        
        return issues