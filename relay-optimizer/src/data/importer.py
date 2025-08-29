import csv
import pandas as pd
from datetime import datetime, date
from typing import Dict, Any
from ..models import Swimmer, Event, Gender, Session, EventType, StrokeType
from .database import Database

def import_swimmers_csv(filename: str, db: Database) -> int:
    """Import swimmers from CSV or Excel file.
    
    Flexible column matching - looks for columns containing:
    - Last Name, First Name (or just Name)
    - Birth Date/DOB (various formats)
    - Gender/Sex (M/F)
    - Times in various formats
    
    Missing data defaults to reasonable values.
    """
    count = 0
    
    # Read file based on extension
    if filename.lower().endswith(('.xlsx', '.xls')):
        # Read Excel file - try multiple sheets if needed
        try:
            xl_file = pd.ExcelFile(filename)
            # Try to find the swimmers sheet (could be named various things)
            sheet_name = None
            for sheet in xl_file.sheet_names:
                if any(keyword in sheet.lower() for keyword in ['swimmer', 'roster', 'athlete', 'participant', 'member']):
                    sheet_name = sheet
                    break
            # If no specific sheet found, use first sheet
            if not sheet_name:
                sheet_name = xl_file.sheet_names[0]
            
            df = pd.read_excel(filename, sheet_name=sheet_name)
        except Exception as e:
            # Try first sheet by default
            df = pd.read_excel(filename)
    else:
        # CSV file
        df = pd.read_csv(filename)
    
    # Process dataframe with flexible column matching
    for idx, row in df.iterrows():
        swimmer = parse_swimmer_row_flexible(row.to_dict())
        if swimmer:
            db.add_swimmer(swimmer)
            count += 1
    
    return count

def parse_swimmer_row_flexible(row: Dict[str, Any]) -> Swimmer:
    """Parse a row with flexible column name matching."""
    
    # Helper to find column by keywords
    def find_column(keywords: list, row_dict: dict) -> str:
        """Find column name containing any of the keywords (case-insensitive)."""
        for col_name in row_dict.keys():
            if col_name and any(keyword.lower() in str(col_name).lower() for keyword in keywords):
                return col_name
        return None
    
    def get_value(keywords: list, default=None):
        """Get value from row using flexible column matching."""
        col = find_column(keywords, row)
        if col and row.get(col) is not None:
            val = row[col]
            # Handle pandas NaN
            if pd.isna(val):
                return default
            return str(val).strip() if val else default
        return default
    
    # Try to extract names - looking specifically for "Last" and "First" columns
    first_name = get_value(['first'])
    last_name = get_value(['last'])
    
    # If no separate first/last, try full name field
    if not first_name or not last_name:
        full_name = get_value(['name', 'swimmer', 'athlete'])
        if full_name and ',' in full_name:
            # Format: "Last, First"
            parts = full_name.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ''
        elif full_name and ' ' in full_name:
            # Format: "First Last"
            parts = full_name.split(None, 1)
            first_name = parts[0].strip()
            last_name = parts[1].strip() if len(parts) > 1 else parts[0]
        elif full_name:
            # Single word - use as last name
            last_name = full_name
            first_name = 'Unknown'
    
    # Must have at least a name
    if not last_name:
        return None
    
    if not first_name:
        first_name = 'Unknown'
    
    # Parse birth date - look for "dob" column
    birth_date = None
    date_str = get_value(['dob'])
    if date_str:
        birth_date = parse_date(date_str)
    
    # If no birth date, try age column and estimate
    if not birth_date:
        age_str = get_value(['age'])
        if age_str:
            try:
                age = int(float(age_str))
                # Estimate birth year (assuming Dec 31 for age calculation)
                birth_year = date.today().year - age
                birth_date = date(birth_year, 1, 1)  # Use Jan 1 as placeholder
            except:
                pass
    
    # Default birth date if still none (assume 30 years old)
    if not birth_date:
        birth_date = date(date.today().year - 30, 1, 1)
    
    # Parse gender - look for "Gender" column only
    gender_str = get_value(['gender'], 'M')
    gender_str = str(gender_str).upper() if gender_str else 'M'
    # Check for Female indicators
    if any(gender_str.startswith(x) for x in ['F', 'W', 'FEMALE', 'WOMAN']):
        gender = Gender.FEMALE
    else:
        gender = Gender.MALE
    
    # Optional fields with defaults
    max_events = 6
    max_events_str = get_value(['max', 'limit', 'max events', 'event limit'])
    if max_events_str:
        try:
            max_events = int(float(max_events_str))
            max_events = max(1, min(6, max_events))  # Clamp to 1-6
        except:
            pass
    
    # Availability - check "Relay" column (1 = available for both AM and PM, blank/null = skip)
    relay_str = get_value(['relay'])
    
    # If relay column is empty/null, skip this swimmer entirely
    if not relay_str or pd.isna(relay_str) or str(relay_str).strip() == '':
        return None  # Skip this row
    
    # Check relay value
    if str(relay_str).strip() in ['1', '1.0', 'true', 'yes', 'y']:
        morning = True
        afternoon = True
    else:
        # If relay is 0 or any other value, they're not available
        morning = False
        afternoon = False
    
    # Parse excluded strokes
    excluded_strokes = set()
    excluded_str = get_value(['excluded', 'cannot', 'exclude'])
    if excluded_str:
        # Could be comma-separated or space-separated
        for sep in [',', ';', ' ']:
            if sep in excluded_str:
                excluded_strokes = {s.strip() for s in excluded_str.split(sep) if s.strip()}
                break
        if not excluded_strokes:
            excluded_strokes = {excluded_str.strip()}
    
    # Parse times - specific columns that will be there:
    # 50 Back, 50 Fly, 50 free, 50 breast, 100 back, 100 free, 100 fly, 100 breast, 200 free
    # Also check for 25m distances and other 200m strokes
    times = {}
    
    # Map the expected column names to our internal format
    time_columns = [
        # 25m distances
        ('25 back', 'Back', 25),
        ('25 fly', 'Fly', 25),
        ('25 free', 'Free', 25),
        ('25 breast', 'Breast', 25),
        # 50m distances
        ('50 back', 'Back', 50),
        ('50 fly', 'Fly', 50),
        ('50 free', 'Free', 50),
        ('50 breast', 'Breast', 50),
        # 100m distances
        ('100 back', 'Back', 100),
        ('100 fly', 'Fly', 100),
        ('100 free', 'Free', 100),
        ('100 breast', 'Breast', 100),
        # 200m distances
        ('200 back', 'Back', 200),
        ('200 fly', 'Fly', 200),
        ('200 free', 'Free', 200),
        ('200 breast', 'Breast', 200)
    ]
    
    # Look for each time column (case insensitive)
    for expected_col, stroke, distance in time_columns:
        # Find the column in a case-insensitive way
        found_col = None
        for col_name in row.keys():
            if col_name and expected_col.lower() == str(col_name).lower().strip():
                found_col = col_name
                break
        
        # If found, parse the time
        if found_col and row.get(found_col) is not None:
            val = row[found_col]
            if not pd.isna(val):
                time = parse_time(str(val))
                if time and time > 0:
                    times[(stroke, distance)] = time
    
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