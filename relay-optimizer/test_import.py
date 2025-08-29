#!/usr/bin/env python3
"""Test flexible import functionality"""

import sys
from pathlib import Path
import tempfile
import pandas as pd
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))

from src.data.importer import parse_swimmer_row_flexible
from src.models.swimmer import Gender

def test_flexible_import():
    print("Testing flexible import functionality...")
    
    # Test 1: Standard format
    row1 = {
        'Last Name': 'Smith',
        'First Name': 'John',
        'Birth Date': '1990-05-15',
        'Gender': 'M',
        'Free_50': '25.5',
        'Back_50': '28.3'
    }
    swimmer1 = parse_swimmer_row_flexible(row1)
    assert swimmer1.last_name == 'Smith'
    assert swimmer1.first_name == 'John'
    assert swimmer1.gender == Gender.MALE
    assert swimmer1.times[('Free', 50)] == 25.5
    print("✓ Standard format")
    
    # Test 2: Alternative column names
    row2 = {
        'surname': 'Jones',
        'given name': 'Mary',
        'DOB': '1985-03-20',
        'Gender': 'Female',  # Changed to Gender
        '50 Free': '27.2',
        'Breast 100': '1:15.5'
    }
    swimmer2 = parse_swimmer_row_flexible(row2)
    assert swimmer2.last_name == 'Jones'
    assert swimmer2.first_name == 'Mary'
    assert swimmer2.gender == Gender.FEMALE
    assert swimmer2.times[('Free', 50)] == 27.2
    assert swimmer2.times[('Breast', 100)] == 75.5  # 1:15.5 = 75.5 seconds
    print("✓ Alternative column names")
    
    # Test 3: Full name field
    row3 = {
        'Name': 'Johnson, Mike',
        'Age': '35',
        'Gender': 'M',
        'free50': '24.8'
    }
    swimmer3 = parse_swimmer_row_flexible(row3)
    assert swimmer3.last_name == 'Johnson'
    assert swimmer3.first_name == 'Mike'
    # Age should be converted to birth date
    assert swimmer3.birth_date.year == date.today().year - 35
    print("✓ Full name parsing")
    
    # Test 4: Missing data with defaults
    row4 = {
        'Last Name': 'Williams',
        # No first name
        # No birth date
        # No gender
        '50Free': '26.0'
    }
    swimmer4 = parse_swimmer_row_flexible(row4)
    assert swimmer4.last_name == 'Williams'
    assert swimmer4.first_name == 'Unknown'
    assert swimmer4.gender == Gender.MALE  # Default
    assert swimmer4.max_events == 6  # Default
    assert swimmer4.morning_available == True  # Default
    assert swimmer4.times[('Free', 50)] == 26.0
    print("✓ Missing data handling")
    
    # Test 5: Excel-style with NaN values
    row5 = {
        'Last Name': 'Brown',
        'First Name': 'Sarah',
        'DOB': pd.NaT,  # Not a Time (pandas null for datetime)
        'Gender': 'F',
        'Free_25': None,
        'Free_50': 28.5,
        'Back_50': float('nan'),  # NaN value
        'Breast_50': '32.1'
    }
    swimmer5 = parse_swimmer_row_flexible(row5)
    assert swimmer5.last_name == 'Brown'
    assert swimmer5.gender == Gender.FEMALE
    assert ('Free', 25) not in swimmer5.times  # None should be skipped
    assert swimmer5.times[('Free', 50)] == 28.5
    assert ('Back', 50) not in swimmer5.times  # NaN should be skipped
    assert swimmer5.times[('Breast', 50)] == 32.1
    print("✓ Excel NaN handling")
    
    # Test 6: Time format variations
    row6 = {
        'Name': 'Davis, Tom',
        'Gender': 'M',
        'Free_50': '25.5',      # Seconds
        'Free_100': '55.25',     # Seconds with decimals
        'Free_200': '1:58.5',    # MM:SS.H format
        'Back_100': '1:03.25'    # MM:SS.HH format
    }
    swimmer6 = parse_swimmer_row_flexible(row6)
    assert swimmer6.times[('Free', 50)] == 25.5
    assert swimmer6.times[('Free', 100)] == 55.25
    assert swimmer6.times[('Free', 200)] == 118.5  # 1:58.5 = 118.5
    assert swimmer6.times[('Back', 100)] == 63.25  # 1:03.25 = 63.25
    print("✓ Time format variations")
    
    print("\n✅ All import tests passed!")
    return True

if __name__ == "__main__":
    success = test_flexible_import()
    sys.exit(0 if success else 1)