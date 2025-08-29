#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.importer import parse_swimmer_row_flexible

row2 = {
    'surname': 'Jones',
    'given name': 'Mary',
    'DOB': '1985-03-20',
    'Sex': 'Female',
    '50 Free': '27.2',
    'Breast 100': '1:15.5'
}

swimmer = parse_swimmer_row_flexible(row2)
print(f"Gender string found: {row2.get('Sex')}")
print(f"Parsed gender: {swimmer.gender}")
print(f"Gender value: {swimmer.gender.value}")