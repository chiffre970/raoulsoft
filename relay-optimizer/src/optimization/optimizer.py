import random
import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from itertools import combinations, permutations
from multiprocessing import Pool, cpu_count
from ..models import Swimmer, Event, Team, TeamAssignment, OptimizationResult
from ..models.event import EventType, StrokeType
from ..models.swimmer import Gender

@dataclass
class EventBaseline:
    age_group: Tuple[int, int]
    mean_time: float
    std_time: float
    sample_size: int

class RelayOptimizer:
    def __init__(self, swimmers: List[Swimmer], events: List[Event]):
        self.swimmers = swimmers
        self.events = events
        self.baselines: Dict[int, Dict[Tuple[int, int], EventBaseline]] = {}
        
    def optimize(self, progress_callback=None) -> OptimizationResult:
        result = OptimizationResult()
        
        # Phase 1: Generate baselines
        if progress_callback:
            progress_callback("Generating Monte Carlo baselines...")
        self.generate_baselines()
        
        # Phase 2: Find optimal allocation
        if progress_callback:
            progress_callback("Finding optimal team configurations...")
        
        # Track swimmer usage across all events
        swimmer_usage = {s: 0 for s in self.swimmers}
        
        # Process events in order
        for event in self.events:
            if progress_callback:
                progress_callback(f"Optimizing Event {event.event_number}: {event.event_name}")
            
            # Find best team for this event
            best_team = self.find_best_team_for_event(event, swimmer_usage)
            
            if best_team:
                assignment = TeamAssignment(
                    event=event,
                    team=best_team,
                    age_group=best_team.age_group,
                    expected_time=best_team.calculate_time(),
                    expected_points=self.estimate_points(best_team, event)
                )
                result.add_assignment(assignment)
                
                # Update swimmer usage
                for swimmer in best_team.swimmers:
                    swimmer_usage[swimmer] += 1
                    swimmer.events_assigned += 1
            else:
                result.add_skipped_event(
                    event.event_name,
                    "Could not form valid team with available swimmers"
                )
        
        # Validate and add warnings
        issues = result.validate_constraints()
        for issue in issues:
            result.add_warning(issue)
        
        return result
    
    def generate_baselines(self, n_simulations: int = 100):
        self.baselines = {}
        
        for event in self.events:
            event_baselines = {}
            
            # For each age group, generate random teams
            for age_group in [(72, 99), (100, 119), (120, 159), (160, 199), 
                            (200, 239), (240, 279), (280, 319)]:
                times = []
                
                for _ in range(n_simulations):
                    random_team = self.generate_random_team(event, age_group)
                    if random_team:
                        time = random_team.calculate_time()
                        if time != float('inf'):
                            times.append(time)
                
                if len(times) >= 10:  # Need enough samples for meaningful statistics
                    event_baselines[age_group] = EventBaseline(
                        age_group=age_group,
                        mean_time=np.mean(times),
                        std_time=np.std(times),
                        sample_size=len(times)
                    )
            
            self.baselines[event.event_number] = event_baselines
    
    def generate_random_team(self, event: Event, target_age_group: Tuple[int, int]) -> Optional[Team]:
        # Filter eligible swimmers
        eligible = self.filter_eligible_swimmers(event)
        if len(eligible) < 4:
            return None
        
        # Try to build a team that fits the age group
        for _ in range(50):  # Max attempts
            if event.gender_type == EventType.MIXED:
                men = [s for s in eligible if s.gender == Gender.MALE]
                women = [s for s in eligible if s.gender == Gender.FEMALE]
                if len(men) < 2 or len(women) < 2:
                    return None
                selected = random.sample(men, min(2, len(men))) + random.sample(women, min(2, len(women)))
            else:
                selected = random.sample(eligible, min(4, len(eligible)))
            
            if len(selected) == 4:
                team = Team(selected, event)
                # Check if team is in target age group
                if team.age_group == target_age_group:
                    valid, _ = team.validate()
                    if valid:
                        return team
        
        return None
    
    def filter_eligible_swimmers(self, event: Event) -> List[Swimmer]:
        eligible = []
        
        for swimmer in self.swimmers:
            # Check availability
            if not swimmer.available_for(event.session.value):
                continue
            
            # Check gender
            if event.gender_type == EventType.MENS and swimmer.gender != Gender.MALE:
                continue
            if event.gender_type == EventType.WOMENS and swimmer.gender != Gender.FEMALE:
                continue
            
            # Check if can swim required strokes
            can_swim_event = False
            if event.stroke_type == StrokeType.FREESTYLE:
                if swimmer.can_swim("Free") and swimmer.has_time_for("Free", event.distance):
                    can_swim_event = True
            else:  # Medley
                # For medley, swimmer needs at least one of the strokes
                for stroke in ["Back", "Breast", "Fly", "Free"]:
                    if swimmer.can_swim(stroke) and swimmer.has_time_for(stroke, event.distance):
                        can_swim_event = True
                        break
            
            if can_swim_event:
                eligible.append(swimmer)
        
        return eligible
    
    def find_best_team_for_event(self, event: Event, swimmer_usage: Dict[Swimmer, int]) -> Optional[Team]:
        # Get eligible swimmers who haven't exceeded their event limit
        eligible = [s for s in self.filter_eligible_swimmers(event) 
                   if swimmer_usage[s] < s.max_events]
        
        if len(eligible) < 4:
            return None
        
        best_team = None
        best_score = -float('inf')
        
        # Generate candidate teams
        if event.gender_type == EventType.MIXED:
            men = [s for s in eligible if s.gender == Gender.MALE]
            women = [s for s in eligible if s.gender == Gender.FEMALE]
            
            if len(men) < 2 or len(women) < 2:
                return None
            
            # Try combinations of 2 men and 2 women
            for men_combo in combinations(men[:min(10, len(men))], 2):  # Limit for performance
                for women_combo in combinations(women[:min(10, len(women))], 2):
                    swimmers = list(men_combo) + list(women_combo)
                    team = self.evaluate_team_permutations(swimmers, event)
                    if team:
                        score = self.calculate_team_score(team, event)
                        if score > best_score:
                            best_score = score
                            best_team = team
        else:
            # Try combinations of 4 swimmers
            for combo in combinations(eligible[:min(20, len(eligible))], 4):  # Limit for performance
                team = self.evaluate_team_permutations(list(combo), event)
                if team:
                    score = self.calculate_team_score(team, event)
                    if score > best_score:
                        best_score = score
                        best_team = team
        
        return best_team
    
    def evaluate_team_permutations(self, swimmers: List[Swimmer], event: Event) -> Optional[Team]:
        if event.stroke_type == StrokeType.FREESTYLE:
            # For freestyle, order doesn't matter much, just validate
            team = Team(swimmers, event)
            valid, _ = team.validate()
            return team if valid else None
        else:
            # For medley, try different orders to find valid assignment
            strokes = ["Back", "Breast", "Fly", "Free"]
            best_team = None
            best_time = float('inf')
            
            for perm in permutations(swimmers):
                # Check if this order works for the strokes
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
    
    def calculate_team_score(self, team: Team, event: Event) -> float:
        # Calculate z-score relative to baseline
        time = team.calculate_time()
        age_group = team.age_group
        
        if event.event_number not in self.baselines:
            return -time  # No baseline, just minimize time
        
        if age_group not in self.baselines[event.event_number]:
            return -time  # No baseline for this age group
        
        baseline = self.baselines[event.event_number][age_group]
        if baseline.std_time > 0:
            z_score = (baseline.mean_time - time) / baseline.std_time
        else:
            z_score = 0 if time >= baseline.mean_time else 1
        
        # Convert to expected points
        points = self.estimate_points_from_z_score(z_score, event.competition_level)
        
        # Bonus for using swimmers with fewer events (preserves flexibility)
        avg_events = sum(s.events_assigned for s in team.swimmers) / 4
        flexibility_bonus = (6 - avg_events) * 0.5
        
        return points + flexibility_bonus
    
    def estimate_points(self, team: Team, event: Event) -> float:
        time = team.calculate_time()
        age_group = team.age_group
        
        if event.event_number not in self.baselines:
            return 2.0  # Participation points
        
        if age_group not in self.baselines[event.event_number]:
            return 2.0
        
        baseline = self.baselines[event.event_number][age_group]
        if baseline.std_time > 0:
            z_score = (baseline.mean_time - time) / baseline.std_time
        else:
            z_score = 0
        
        return self.estimate_points_from_z_score(z_score, event.competition_level)
    
    def estimate_points_from_z_score(self, z_score: float, competition_level: int) -> float:
        # Competition thresholds for place estimation
        thresholds = {
            1: [0.5, 0.3, 0.1, -0.1, -0.3, -0.5],     # Low competition
            2: [0.8, 0.5, 0.3, 0.1, -0.1, -0.3],     
            3: [1.2, 0.8, 0.5, 0.2, 0.0, -0.2],      # Normal competition
            4: [1.5, 1.1, 0.7, 0.4, 0.2, 0.0],       
            5: [2.0, 1.5, 1.0, 0.6, 0.4, 0.2]        # Extreme competition
        }
        
        thresh = thresholds.get(competition_level, thresholds[3])
        
        if z_score > thresh[0]: return 20.0    # 1st place
        elif z_score > thresh[1]: return 18.0  # 2nd place
        elif z_score > thresh[2]: return 16.0  # 3rd place
        elif z_score > thresh[3]: return 14.0  # 4th place
        elif z_score > thresh[4]: return 12.0  # 5th place
        elif z_score > thresh[5]: return 10.0  # 6th place
        else: return 2.0  # Participation points