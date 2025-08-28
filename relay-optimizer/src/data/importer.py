import csv
import pandas as pd
from datetime import datetime, date
from typing import Dict, Any
from ..models import Swimmer, Event, Gender, Session, EventType, StrokeType
from .database import Database

def import_swimmers_csv(filename: str, db: Database) -> int:
    """Import swimmers from CSV file.
    
    Expected columns:
    - Last Name, First Name
    - Birth Date (MM/DD/YYYY or YYYY-MM-DD)
    - Gender (M/F)
    - Max Events (optional, defaults to 6)
    - Morning Available (Y/N, optional, defaults to Y)
    - Afternoon Available (Y/N, optional, defaults to Y)
    - Excluded Strokes (comma-separated, optional)
    - Time columns: Free_25, Free_50, etc. (optional)
    """
    count = 0
    
    # Try to read with pandas for better format detection
    try:
        df = pd.read_csv(filename)
    except Exception as e:
        # Fallback to basic CSV
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                swimmer = parse_swimmer_row(row)
                if swimmer:
                    db.add_swimmer(swimmer)
                    count += 1
        return count
    
    # Process dataframe
    for _, row in df.iterrows():
        swimmer = parse_swimmer_row(row.to_dict())
        if swimmer:
            db.add_swimmer(swimmer)
            count += 1
    
    return count

def parse_swimmer_row(row: Dict[str, Any]) -> Swimmer:
    """Parse a row of swimmer data into a Swimmer object."""
    
    # Required fields
    first_name = str(row.get('First Name', '')).strip()
    last_name = str(row.get('Last Name', '')).strip()
    
    if not first_name or not last_name:
        return None
    
    # Parse birth date
    birth_date_str = str(row.get('Birth Date', row.get('DOB', '')))
    birth_date = parse_date(birth_date_str)
    if not birth_date:
        return None
    
    # Parse gender
    gender_str = str(row.get('Gender', 'M')).upper()
    gender = Gender.MALE if gender_str == 'M' else Gender.FEMALE
    
    # Optional fields
    max_events = int(row.get('Max Events', 6))
    morning = str(row.get('Morning Available', 'Y')).upper() == 'Y'
    afternoon = str(row.get('Afternoon Available', 'Y')).upper() == 'Y'
    
    # Parse excluded strokes
    excluded_strokes = set()
    excluded_str = str(row.get('Excluded Strokes', ''))
    if excluded_str:
        excluded_strokes = {s.strip() for s in excluded_str.split(',')}
    
    # Parse times
    times = {}
    strokes = ['Free', 'Back', 'Breast', 'Fly']
    distances = [25, 50, 100, 200]
    
    for stroke in strokes:
        for distance in distances:
            # Try various column name formats
            col_names = [
                f'{stroke}_{distance}',
                f'{stroke} {distance}',
                f'{distance} {stroke}',
                f'{distance}{stroke}'
            ]
            
            for col_name in col_names:
                if col_name in row and row[col_name]:
                    try:
                        time = parse_time(str(row[col_name]))
                        if time:
                            times[(stroke, distance)] = time
                            break
                    except:
                        continue
    
    return Swimmer(
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        gender=gender,
        max_events=max_events,
        morning_available=morning,
        afternoon_available=afternoon,
        excluded_strokes=excluded_strokes,
        times=times
    )

def parse_date(date_str: str) -> date:
    """Parse various date formats."""
    date_str = date_str.strip()
    
    # Try common formats
    formats = [
        '%m/%d/%Y',
        '%Y-%m-%d',
        '%m-%d-%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%m/%d/%y',
        '%d-%m-%Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    
    return None

def parse_time(time_str: str) -> float:
    """Parse time from various formats (MM:SS.HH, SS.HH, etc.)."""
    time_str = time_str.strip()
    
    if not time_str:
        return None
    
    # Handle MM:SS.HH format
    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) == 2:
            try:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            except:
                return None
    
    # Handle plain seconds
    try:
        return float(time_str)
    except:
        return None

def import_events_csv(filename: str, db: Database) -> int:
    """Import events from CSV file.
    
    Expected columns:
    - Event Number
    - Event Name
    - Session (AM/PM)
    - Gender Type (Men/Women/Mixed)
    - Stroke Type (Free/Medley)
    - Distance (25/50/100/200)
    - Competition Level (1-5, optional)
    """
    count = 0
    
    try:
        df = pd.read_csv(filename)
    except:
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                event = parse_event_row(row)
                if event:
                    db.add_event(event)
                    count += 1
        return count
    
    for _, row in df.iterrows():
        event = parse_event_row(row.to_dict())
        if event:
            db.add_event(event)
            count += 1
    
    return count

def parse_event_row(row: Dict[str, Any]) -> Event:
    """Parse a row of event data into an Event object."""
    
    # Required fields
    try:
        event_number = int(row.get('Event Number', 0))
        if not event_number:
            return None
    except:
        return None
    
    event_name = str(row.get('Event Name', '')).strip()
    if not event_name:
        return None
    
    # Parse session
    session_str = str(row.get('Session', 'AM')).upper()
    session = Session.AM if session_str == 'AM' else Session.PM
    
    # Parse gender type
    gender_str = str(row.get('Gender Type', row.get('Gender', 'Men')))
    if 'Men' in gender_str or 'M' == gender_str:
        gender_type = EventType.MENS
    elif 'Women' in gender_str or 'W' == gender_str or 'F' == gender_str:
        gender_type = EventType.WOMENS
    else:
        gender_type = EventType.MIXED
    
    # Parse stroke type
    stroke_str = str(row.get('Stroke Type', row.get('Stroke', 'Free')))
    if 'Medley' in stroke_str:
        stroke_type = StrokeType.MEDLEY
    else:
        stroke_type = StrokeType.FREESTYLE
    
    # Parse distance
    try:
        distance = int(row.get('Distance', 50))
    except:
        distance = 50
    
    # Parse competition level
    try:
        competition_level = int(row.get('Competition Level', row.get('Competition', 3)))
        competition_level = max(1, min(5, competition_level))
    except:
        competition_level = 3
    
    return Event(
        event_number=event_number,
        event_name=event_name,
        session=session,
        gender_type=gender_type,
        stroke_type=stroke_type,
        distance=distance,
        competition_level=competition_level
    )