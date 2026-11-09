"""
Data models for the structured CampusGPT timetable system.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TimeSlot(BaseModel):
    raw_slot: str
    start_time: str  # e.g. "09:00"
    end_time: str    # e.g. "09:55"
    slot_index: int  # 1-based index (1 to 8)

class TimetableEntry(BaseModel):
    sheet_name: str
    class_name: str          # e.g. "SY AI-ML A", "TY AI-ML B"
    batch_year: Optional[str] = None # e.g. "2025-29 Batch"
    day: str                 # Monday, Tuesday, Wednesday, Thursday, Friday, Saturday
    time_slot: str           # e.g. "9:00 - 9:55"
    start_time: str          # "09:00"
    end_time: str            # "09:55"
    slot_index: int          # 1 to 8
    subject_code: str        # e.g. "SML", "DS", "OS"
    subject_name: Optional[str] = None # e.g. "Supervised Machine Learning"
    faculty_initials: Optional[str] = None # e.g. "SUK"
    faculty_name: Optional[str] = None     # e.g. "Dr. Sumit Kumar"
    room_code: Optional[str] = None        # e.g. "503", "MSAL", "Online"
    room_name: Optional[str] = None        # e.g. "Classroom 503", "Multimodal Sensor Analytics Lab"
    batch: Optional[str] = None            # e.g. "All", "A1", "A2", "A3", "B1"
    is_lab: bool = False
    is_tutorial: bool = False
    is_break: bool = False                 # Lunch break
    is_activity: bool = False              # Library Hour, Mentor-Mentee, Extended Learning

class RoomNomenclature(BaseModel):
    lab_nomenclature: str                  # e.g. "Computer Lab 8 (B Wing) (CL-08)"
    lab_name: str                          # e.g. "Multimodal Sensor Analytics Lab"
    abbreviation: str                      # e.g. "MSAL"

class SubjectLegend(BaseModel):
    subject_code: str                      # e.g. "DM", "OS", "SML"
    full_name: str                         # e.g. "Discrete Mathematics (DM)"
    faculty_name: str                      # e.g. "Dr. Sangeeta Pant (SAP)"
    credits: Optional[str] = None

class ParsedTimetable(BaseModel):
    entries: List[TimetableEntry] = Field(default_factory=list)
    rooms: Dict[str, RoomNomenclature] = Field(default_factory=dict)
    faculty_lookup: Dict[str, str] = Field(default_factory=dict) # initials -> full name
    subject_lookup: Dict[str, str] = Field(default_factory=dict) # code -> full name
    sheets_parsed: List[str] = Field(default_factory=list)
    total_entries: int = 0

