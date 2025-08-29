"""
Simple relay optimizer - always maintains validity
"""

import random
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import numpy as np
from itertools import combinations, permutations

from ..models import Swimmer, Event, Team, TeamAssignment, OptimizationResult
from ..models.event import EventType, StrokeType
from ..models.swimmer import Gender


@dataclass
class Baseline:
    """Statistical baseline for an event/age group"""
    mean_time: float
    std_time: float
    sample_size: int


class RelayOptimizer:
    """
    Simple relay optimizer that always maintains valid state.
    
    Key principles:
    1. Never violate constraints
    2. When at 6-event limit, swap worst for better
    3. Always check validity before making changes
    """
    
    def __init__(self, swimmers: List[Swimmer], events: List[Event]):
        self.swimmers = swimmers
        self.events = events
        self.baselines: Dict[int, Dict[Tuple[int, int], Baseline]] = {}
        # Track swimmer events for easy lookup
        self.swimmer_events: Dict[Swimmer, Set[int]] = {s: set() for s in swimmers}
        
    def optimize(self, progress_callback=None) -> OptimizationResult:
        """Main optimization entry point"""
        result = OptimizationResult()
        
        # Step 1: Generate baselines for z-score calculation
        if progress_callback:
            progress_callback("Generating baselines...")
        self.generate_baselines()
        
        # Step 2: Initial greedy assignment
        if progress_callback:
            progress_callback("Initial team assignment...")
        
        # Solution maps event_number -> Team
        solution = {}
        
        # First pass - assign best available teams
        for i, event in enumerate(self.events):
            if progress_callback and i % 5 == 0:
                progress_callback(f"Assigning event {i+1}/{len(self.events)}")
            
            team = self.find_best_team_for_event(event, solution)
            if team:
                solution[event.event_number] = team
                # Update swimmer tracking
                for swimmer in team.swimmers:
                    self.swimmer_events[swimmer].add(event.event_number)
                    swimmer.events_assigned = len(self.swimmer_events[swimmer])
        
        # Step 3: Fill any gaps (events without teams)
        if progress_callback:
            progress_callback("Filling gaps...")
        
        for event in self.events:
            if event.event_number not in solution or solution[event.event_number] is None:
                team = self.find_any_valid_team(event, solution)
                if team:
                    solution[event.event_number] = team
                    for swimmer in team.swimmers:
                        self.swimmer_events[swimmer].add(event.event_number)
                        swimmer.events_assigned = len(self.swimmer_events[swimmer])
        
        # Step 4: Improvement loop
        if progress_callback:
            progress_callback("Optimizing assignments...")
        
        no_improvement_count = 0
        for iteration in range(1000):  # More iterations
            if progress_callback and iteration % 100 == 0:
                progress_callback(f"Optimization iteration {iteration}/1000")
            
            improved = self.try_improve_swimmer(solution)
            
            if not improved:
                no_improvement_count += 1
                if no_improvement_count > 100:  # Give it more tries
                    break
            else:
                no_improvement_count = 0
        
        # Step 5: Convert solution to result
        if progress_callback:
            progress_callback("Finalizing results...")
        
        for event in self.events:
            team = solution.get(event.event_number)
            if team:
                z_score = self.calculate_z_score(team, event)
                assignment = TeamAssignment(
                    event=event,
                    team=team,
                    age_group=team.age_group,
                    expected_time=team.calculate_time(),
                    expected_points=0,  # Not using points
                    z_score=z_score  # Store the z-score
                )
                result.add_assignment(assignment)
            else:
                result.add_skipped_event(event.event_name, "Could not form valid team")
        
        return result
    
    def find_best_team_for_event(self, event: Event, current_solution: Dict) -> Optional[Team]:
        """Find the best valid team for an event, respecting constraints"""
        eligible = self.get_eligible_swimmers(event)
        
        # Filter by gender requirements
        if event.gender_type == EventType.MENS:
            eligible = [s for s in eligible if s.gender == Gender.MALE]
        elif event.gender_type == EventType.WOMENS:
            eligible = [s for s in eligible if s.gender == Gender.FEMALE]
        
        # Filter by availability (under 6 events OR this event is worth swapping for)
        available = []
        for swimmer in eligible:
            event_count = len(self.swimmer_events[swimmer])
            if event_count < swimmer.max_events:
                available.append(swimmer)
            elif event_count == swimmer.max_events:
                # Check if this event would be better than their worst
                if self.would_swap_improve(swimmer, event, current_solution):
                    available.append(swimmer)
        
        if len(available) < 4:
            return None
        
        # Build best team
        best_team = None
        best_z_score = -float('inf')
        
        if event.gender_type == EventType.MIXED:
            men = [s for s in available if s.gender == Gender.MALE]
            women = [s for s in available if s.gender == Gender.FEMALE]
            
            if len(men) < 2 or len(women) < 2:
                return None
            
            # Sort by best time for this event
            men.sort(key=lambda s: self.get_swimmer_best_time_for_event(s, event))
            women.sort(key=lambda s: self.get_swimmer_best_time_for_event(s, event))
            
            # Try more combinations (top 20 swimmers)
            for men_combo in combinations(men[:min(20, len(men))], 2):
                for women_combo in combinations(women[:min(20, len(women))], 2):
                    swimmers = list(men_combo) + list(women_combo)
                    team = self.create_valid_team(swimmers, event)
                    if team:
                        z_score = self.calculate_z_score(team, event)
                        if z_score > best_z_score:
                            best_z_score = z_score
                            best_team = team
                            
                            # Auto-swap if needed
                            for swimmer in team.swimmers:
                                if len(self.swimmer_events[swimmer]) == swimmer.max_events:
                                    worst_event = self.find_worst_event_for_swimmer(swimmer, current_solution)
                                    if worst_event:
                                        self.remove_swimmer_from_event(swimmer, worst_event, current_solution)
        else:
            # Single gender event - sort by speed first
            available.sort(key=lambda s: self.get_swimmer_best_time_for_event(s, event))
            
            # Try more combinations (top 30 swimmers)
            for combo in combinations(available[:min(30, len(available))], 4):
                team = self.create_valid_team(list(combo), event)
                if team:
                    z_score = self.calculate_z_score(team, event)
                    if z_score > best_z_score:
                        best_z_score = z_score
                        best_team = team
                        
                        # Auto-swap if needed
                        for swimmer in team.swimmers:
                            if len(self.swimmer_events[swimmer]) == swimmer.max_events:
                                worst_event = self.find_worst_event_for_swimmer(swimmer, current_solution)
                                if worst_event:
                                    self.remove_swimmer_from_event(swimmer, worst_event, current_solution)
        
        return best_team
    
    def try_improve_swimmer(self, solution: Dict) -> bool:
        """Try to improve one swimmer's assignment"""
        # Pick ANY swimmer with at least 1 event (not just those at limit)
        candidates = [s for s in self.swimmers if len(self.swimmer_events[s]) >= 1]
        if not candidates:
            return False
        
        swimmer = random.choice(candidates)
        
        # Find their worst event
        worst_event_num = self.find_worst_event_for_swimmer(swimmer, solution)
        if not worst_event_num:
            return False
        
        worst_event = next(e for e in self.events if e.event_number == worst_event_num)
        worst_contribution = self.calculate_swimmer_contribution(swimmer, worst_event, solution)
        
        # Find events they're not in
        current_events = self.swimmer_events[swimmer]
        potential_events = [e for e in self.events if e.event_number not in current_events]
        
        # Find best potential event
        best_new_event = None
        best_improvement = 0
        
        for event in potential_events:
            # Check if they could join this event
            if not self.can_swimmer_join_event(swimmer, event, solution):
                continue
            
            potential_contribution = self.estimate_swimmer_contribution(swimmer, event)
            improvement = potential_contribution - worst_contribution
            
            if improvement > best_improvement:
                best_improvement = improvement
                best_new_event = event
        
        # Do the swap if it improves things
        if best_new_event and best_improvement > 0.01:  # Lower threshold for more swaps
            # Remove from worst event
            self.remove_swimmer_from_event(swimmer, worst_event_num, solution)
            
            # Add to better event
            return self.add_swimmer_to_event(swimmer, best_new_event, solution)
        
        return False
    
    def would_swap_improve(self, swimmer: Swimmer, new_event: Event, solution: Dict) -> bool:
        """Check if swapping to new event would improve overall score"""
        worst_event_num = self.find_worst_event_for_swimmer(swimmer, solution)
        if not worst_event_num:
            return False
        
        worst_event = next(e for e in self.events if e.event_number == worst_event_num)
        
        worst_contrib = self.calculate_swimmer_contribution(swimmer, worst_event, solution)
        new_contrib = self.estimate_swimmer_contribution(swimmer, new_event)
        
        return new_contrib > worst_contrib + 0.05  # Lower threshold for swaps
    
    def find_worst_event_for_swimmer(self, swimmer: Swimmer, solution: Dict) -> Optional[int]:
        """Find the event where swimmer contributes least"""
        worst_event = None
        worst_contribution = float('inf')
        
        for event_num in self.swimmer_events[swimmer]:
            event = next(e for e in self.events if e.event_number == event_num)
            contribution = self.calculate_swimmer_contribution(swimmer, event, solution)
            
            if contribution < worst_contribution:
                worst_contribution = contribution
                worst_event = event_num
        
        return worst_event
    
    def calculate_swimmer_contribution(self, swimmer: Swimmer, event: Event, solution: Dict) -> float:
        """Calculate how much a swimmer contributes to an event's z-score"""
        team = solution.get(event.event_number)
        if not team or swimmer not in team.swimmers:
            return 0.0
        
        # Current team z-score
        current_z = self.calculate_z_score(team, event)
        
        # What would z-score be without this swimmer? (approximate)
        # This is simplified - in reality we'd need to find replacement
        team_time = team.calculate_time()
        swimmer_time = self.get_swimmer_time_for_event(swimmer, event, team)
        
        # Approximate z-score impact
        return current_z * (swimmer_time / team_time)
    
    def estimate_swimmer_contribution(self, swimmer: Swimmer, event: Event) -> float:
        """Estimate how much a swimmer would contribute to an event"""
        time = self.get_swimmer_best_time_for_event(swimmer, event)
        if time == float('inf'):
            return -10.0
        
        # Compare to baseline
        baseline = self.get_baseline_for_swimmer_age(swimmer, event)
        if not baseline:
            return 0.0
        
        # Individual z-score
        z_score = (baseline.mean_time/4 - time) / (baseline.std_time/4)
        return z_score
    
    def remove_swimmer_from_event(self, swimmer: Swimmer, event_num: int, solution: Dict):
        """Remove swimmer from event and find replacement"""
        team = solution.get(event_num)
        if not team or swimmer not in team.swimmers:
            return
        
        event = next(e for e in self.events if e.event_number == event_num)
        
        # Remove swimmer
        remaining = [s for s in team.swimmers if s != swimmer]
        self.swimmer_events[swimmer].discard(event_num)
        swimmer.events_assigned = len(self.swimmer_events[swimmer])
        
        # Find replacement
        replacement = self.find_replacement_swimmer(remaining, event, solution)
        if replacement:
            remaining.append(replacement)
            new_team = self.create_valid_team(remaining, event)
            if new_team:
                solution[event_num] = new_team
                self.swimmer_events[replacement].add(event_num)
                replacement.events_assigned = len(self.swimmer_events[replacement])
        else:
            # Can't find replacement - remove team
            solution[event_num] = None
    
    def add_swimmer_to_event(self, swimmer: Swimmer, event: Event, solution: Dict) -> bool:
        """Add swimmer to an event's team"""
        team = solution.get(event.event_number)
        
        if not team:
            # No team yet, try to create one
            new_team = self.find_any_valid_team(event, solution)
            if new_team:
                solution[event.event_number] = new_team
                for s in new_team.swimmers:
                    self.swimmer_events[s].add(event.event_number)
                    s.events_assigned = len(self.swimmer_events[s])
                return True
            return False
        
        # Team exists but may not have room
        if len(team.swimmers) >= 4:
            # Need to replace someone
            weakest = self.find_weakest_swimmer_in_team(team, event)
            if weakest:
                remaining = [s for s in team.swimmers if s != weakest]
                remaining.append(swimmer)
                new_team = self.create_valid_team(remaining, event)
                if new_team:
                    solution[event.event_number] = new_team
                    self.swimmer_events[weakest].discard(event.event_number)
                    weakest.events_assigned = len(self.swimmer_events[weakest])
                    self.swimmer_events[swimmer].add(event.event_number)
                    swimmer.events_assigned = len(self.swimmer_events[swimmer])
                    return True
        else:
            # Room to add
            new_swimmers = list(team.swimmers) + [swimmer]
            new_team = self.create_valid_team(new_swimmers, event)
            if new_team:
                solution[event.event_number] = new_team
                self.swimmer_events[swimmer].add(event.event_number)
                swimmer.events_assigned = len(self.swimmer_events[swimmer])
                return True
        
        return False
    
    def find_replacement_swimmer(self, current_swimmers: List[Swimmer], event: Event, solution: Dict) -> Optional[Swimmer]:
        """Find a swimmer to complete a team"""
        eligible = self.get_eligible_swimmers(event)
        
        # Filter by what we need
        if event.gender_type == EventType.MIXED:
            # Count current genders
            men_count = sum(1 for s in current_swimmers if s.gender == Gender.MALE)
            women_count = sum(1 for s in current_swimmers if s.gender == Gender.FEMALE)
            
            if men_count < 2:
                eligible = [s for s in eligible if s.gender == Gender.MALE]
            elif women_count < 2:
                eligible = [s for s in eligible if s.gender == Gender.FEMALE]
        elif event.gender_type == EventType.MENS:
            eligible = [s for s in eligible if s.gender == Gender.MALE]
        elif event.gender_type == EventType.WOMENS:
            eligible = [s for s in eligible if s.gender == Gender.FEMALE]
        
        # Filter by availability
        available = [s for s in eligible 
                    if s not in current_swimmers 
                    and len(self.swimmer_events[s]) < s.max_events]
        
        if not available:
            return None
        
        # Pick best available
        best_swimmer = None
        best_time = float('inf')
        
        for swimmer in available:
            time = self.get_swimmer_best_time_for_event(swimmer, event)
            if time < best_time:
                best_time = time
                best_swimmer = swimmer
        
        return best_swimmer
    
    def find_weakest_swimmer_in_team(self, team: Team, event: Event) -> Optional[Swimmer]:
        """Find swimmer contributing least to team"""
        weakest = None
        worst_contribution = float('inf')
        
        for swimmer in team.swimmers:
            time = self.get_swimmer_time_for_event(swimmer, event, team)
            if time < worst_contribution:
                worst_contribution = time
                weakest = swimmer
        
        return weakest
    
    def can_swimmer_join_event(self, swimmer: Swimmer, event: Event, solution: Dict) -> bool:
        """Check if swimmer can join an event's team"""
        # Check basic eligibility
        if not swimmer.available_for(event.session.value):
            return False
        
        # Check gender
        if event.gender_type == EventType.MENS and swimmer.gender != Gender.MALE:
            return False
        if event.gender_type == EventType.WOMENS and swimmer.gender != Gender.FEMALE:
            return False
        
        # Check if can swim required strokes
        if event.stroke_type == StrokeType.FREESTYLE:
            if not swimmer.can_swim("Free") or not swimmer.has_time_for("Free", event.distance):
                return False
        else:
            can_swim_any = False
            for stroke in ["Back", "Breast", "Fly", "Free"]:
                if swimmer.can_swim(stroke) and swimmer.has_time_for(stroke, event.distance):
                    can_swim_any = True
                    break
            if not can_swim_any:
                return False
        
        # Check team composition
        team = solution.get(event.event_number)
        if team:
            if event.gender_type == EventType.MIXED:
                men = sum(1 for s in team.swimmers if s.gender == Gender.MALE)
                women = sum(1 for s in team.swimmers if s.gender == Gender.FEMALE)
                if swimmer.gender == Gender.MALE and men >= 2:
                    return False
                if swimmer.gender == Gender.FEMALE and women >= 2:
                    return False
        
        return True
    
    def find_any_valid_team(self, event: Event, solution: Dict) -> Optional[Team]:
        """Find any valid team for an event (used for gap filling)"""
        eligible = self.get_eligible_swimmers(event)
        
        # Filter by gender
        if event.gender_type == EventType.MENS:
            eligible = [s for s in eligible if s.gender == Gender.MALE]
        elif event.gender_type == EventType.WOMENS:
            eligible = [s for s in eligible if s.gender == Gender.FEMALE]
        
        # Filter by availability
        available = [s for s in eligible if len(self.swimmer_events[s]) < s.max_events]
        
        if len(available) < 4:
            return None
        
        # For mixed, need right gender balance
        if event.gender_type == EventType.MIXED:
            men = [s for s in available if s.gender == Gender.MALE]
            women = [s for s in available if s.gender == Gender.FEMALE]
            if len(men) >= 2 and len(women) >= 2:
                swimmers = men[:2] + women[:2]
                return self.create_valid_team(swimmers, event)
        else:
            # Just take first 4 available
            return self.create_valid_team(available[:4], event)
        
        return None
    
    def get_swimmer_time_for_event(self, swimmer: Swimmer, event: Event, team: Team) -> float:
        """Get swimmer's time in a specific event/team context"""
        if event.stroke_type == StrokeType.FREESTYLE:
            return swimmer.get_time("Free", event.distance)
        else:
            # Find which leg they swim in medley
            strokes = ["Back", "Breast", "Fly", "Free"]
            for i, s in enumerate(team.swimmers):
                if s == swimmer:
                    return swimmer.get_time(strokes[i], event.distance)
        return float('inf')
    
    def get_swimmer_best_time_for_event(self, swimmer: Swimmer, event: Event) -> float:
        """Get swimmer's best possible time for an event"""
        if event.stroke_type == StrokeType.FREESTYLE:
            return swimmer.get_time("Free", event.distance)
        else:
            # Return best time for any stroke they can swim
            best_time = float('inf')
            for stroke in ["Back", "Breast", "Fly", "Free"]:
                if swimmer.can_swim(stroke) and swimmer.has_time_for(stroke, event.distance):
                    time = swimmer.get_time(stroke, event.distance)
                    best_time = min(best_time, time)
            return best_time
    
    def get_baseline_for_swimmer_age(self, swimmer: Swimmer, event: Event) -> Optional[Baseline]:
        """Get baseline for the age group this swimmer would put a team in"""
        # Simplified - assumes swimmer joins average age team
        avg_age = sum(s.age for s in self.swimmers) / len(self.swimmers)
        approx_team_age = swimmer.age + avg_age * 3
        
        # Find age group
        age_groups = [(72, 99), (100, 119), (120, 159), (160, 199), (200, 239), (240, 279), (280, 319)]
        for age_group in age_groups:
            if age_group[0] <= approx_team_age <= age_group[1]:
                return self.baselines.get(event.event_number, {}).get(age_group)
        
        return None
    
    def get_eligible_swimmers(self, event: Event) -> List[Swimmer]:
        """Get all swimmers eligible for an event"""
        eligible = []
        
        for swimmer in self.swimmers:
            if not swimmer.available_for(event.session.value):
                continue
            
            can_swim = False
            if event.stroke_type == StrokeType.FREESTYLE:
                if swimmer.can_swim("Free") and swimmer.has_time_for("Free", event.distance):
                    can_swim = True
            else:
                for stroke in ["Back", "Breast", "Fly", "Free"]:
                    if swimmer.can_swim(stroke) and swimmer.has_time_for(stroke, event.distance):
                        can_swim = True
                        break
            
            if can_swim:
                eligible.append(swimmer)
        
        return eligible
    
    def create_valid_team(self, swimmers: List[Swimmer], event: Event) -> Optional[Team]:
        """Create a valid team for an event"""
        if len(swimmers) != 4:
            return None
        
        if event.stroke_type == StrokeType.FREESTYLE:
            team = Team(swimmers, event)
            valid, _ = team.validate()
            return team if valid else None
        else:
            # Find valid stroke ordering for medley
            strokes = ["Back", "Breast", "Fly", "Free"]
            best_team = None
            best_time = float('inf')
            
            for perm in permutations(swimmers):
                valid = True
                time = 0
                for swimmer, stroke in zip(perm, strokes):
                    if not swimmer.can_swim(stroke) or not swimmer.has_time_for(stroke, event.distance):
                        valid = False
                        break
                    time += swimmer.get_time(stroke, event.distance)
                
                if valid and time < best_time:
                    best_time = time
                    best_team = Team(list(perm), event)
            
            return best_team
    
    def calculate_z_score(self, team: Team, event: Event) -> float:
        """Calculate z-score for a team"""
        if event.event_number not in self.baselines:
            return 0.0
        
        if team.age_group not in self.baselines[event.event_number]:
            return 0.0
        
        baseline = self.baselines[event.event_number][team.age_group]
        if baseline.std_time == 0:
            return 0.0
        
        team_time = team.calculate_time()
        z_score = (baseline.mean_time - team_time) / baseline.std_time
        
        return z_score
    
    def generate_baselines(self, n_simulations: int = 100):
        """Generate random baselines for statistical comparison"""
        self.baselines = {}
        
        age_groups = [
            (72, 99), (100, 119), (120, 159), (160, 199),
            (200, 239), (240, 279), (280, 319)
        ]
        
        for event in self.events:
            event_baselines = {}
            
            for age_group in age_groups:
                times = []
                
                for _ in range(n_simulations):
                    team = self.generate_random_team(event, age_group)
                    if team:
                        time = team.calculate_time()
                        if time != float('inf'):
                            times.append(time)
                
                if len(times) >= 10:
                    event_baselines[age_group] = Baseline(
                        mean_time=np.mean(times),
                        std_time=np.std(times),
                        sample_size=len(times)
                    )
            
            self.baselines[event.event_number] = event_baselines
    
    def generate_random_team(self, event: Event, target_age: Tuple[int, int]) -> Optional[Team]:
        """Generate random valid team for baseline"""
        eligible = self.get_eligible_swimmers(event)
        
        # Apply gender constraints
        if event.gender_type == EventType.MENS:
            eligible = [s for s in eligible if s.gender == Gender.MALE]
        elif event.gender_type == EventType.WOMENS:
            eligible = [s for s in eligible if s.gender == Gender.FEMALE]
        
        if len(eligible) < 4:
            return None
        
        for _ in range(50):
            if event.gender_type == EventType.MIXED:
                men = [s for s in eligible if s.gender == Gender.MALE]
                women = [s for s in eligible if s.gender == Gender.FEMALE]
                if len(men) >= 2 and len(women) >= 2:
                    selected = random.sample(men, 2) + random.sample(women, 2)
                else:
                    return None
            else:
                selected = random.sample(eligible, 4)
            
            team = self.create_valid_team(selected, event)
            if team and team.age_group == target_age:
                return team
        
        return None