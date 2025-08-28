import sqlite3
from typing import List, Optional, Dict, Any
from datetime import date, datetime
import json
from pathlib import Path
from ..models import Swimmer, Event, Gender, Session, EventType, StrokeType

class Database:
    def __init__(self, db_path: str = "data/relay_optimizer.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS swimmers (
                swimmer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                birth_date DATE NOT NULL,
                gender TEXT NOT NULL,
                max_events INTEGER DEFAULT 6,
                morning_available BOOLEAN DEFAULT 1,
                afternoon_available BOOLEAN DEFAULT 1,
                excluded_strokes TEXT,
                times TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(first_name, last_name, birth_date)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_number INTEGER UNIQUE NOT NULL,
                event_name TEXT NOT NULL,
                session TEXT NOT NULL,
                gender_type TEXT NOT NULL,
                stroke_type TEXT NOT NULL,
                distance INTEGER NOT NULL,
                competition_level INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_name TEXT NOT NULL,
                result_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def add_swimmer(self, swimmer: Swimmer) -> int:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO swimmers 
            (first_name, last_name, birth_date, gender, max_events,
             morning_available, afternoon_available, excluded_strokes, times)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            swimmer.first_name,
            swimmer.last_name,
            swimmer.birth_date.isoformat(),
            swimmer.gender.value,
            swimmer.max_events,
            swimmer.morning_available,
            swimmer.afternoon_available,
            json.dumps(list(swimmer.excluded_strokes)),
            json.dumps({f"{k[0]}_{k[1]}": v for k, v in swimmer.times.items()})
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_swimmers(self) -> List[Swimmer]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM swimmers')
        swimmers = []
        
        for row in cursor.fetchall():
            times_dict = json.loads(row['times'] or '{}')
            times = {}
            for key, value in times_dict.items():
                stroke, distance = key.rsplit('_', 1)
                times[(stroke, int(distance))] = value
            
            swimmer = Swimmer(
                first_name=row['first_name'],
                last_name=row['last_name'],
                birth_date=date.fromisoformat(row['birth_date']),
                gender=Gender(row['gender']),
                max_events=row['max_events'],
                morning_available=bool(row['morning_available']),
                afternoon_available=bool(row['afternoon_available']),
                excluded_strokes=set(json.loads(row['excluded_strokes'] or '[]')),
                times=times,
                swimmer_id=row['swimmer_id']
            )
            swimmers.append(swimmer)
        
        return swimmers
    
    def add_event(self, event: Event) -> int:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO events 
            (event_number, event_name, session, gender_type, 
             stroke_type, distance, competition_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.event_number,
            event.event_name,
            event.session.value,
            event.gender_type.value,
            event.stroke_type.value,
            event.distance,
            event.competition_level
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_events(self) -> List[Event]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM events ORDER BY event_number')
        events = []
        
        for row in cursor.fetchall():
            event = Event(
                event_number=row['event_number'],
                event_name=row['event_name'],
                session=Session(row['session']),
                gender_type=EventType(row['gender_type']),
                stroke_type=StrokeType(row['stroke_type']),
                distance=row['distance'],
                competition_level=row['competition_level'],
                event_id=row['event_id']
            )
            events.append(event)
        
        return events
    
    def delete_swimmer(self, swimmer_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM swimmers WHERE swimmer_id = ?', (swimmer_id,))
        self.conn.commit()
    
    def delete_event(self, event_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM events WHERE event_id = ?', (event_id,))
        self.conn.commit()
    
    def clear_all_data(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM swimmers')
        cursor.execute('DELETE FROM events')
        self.conn.commit()
    
    def close(self):
        self.conn.close()