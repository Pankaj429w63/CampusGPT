"""
Tests for timetable parser and data models.
"""
import os
import pytest
from app.timetable.parser import parse_master_timetable_workbook

WORKBOOK_PATH = "data/timetables/aiml/Master TT-26-27-ODD Sem.xlsx"

def test_workbook_parsing():
    assert os.path.exists(WORKBOOK_PATH)
    tt = parse_master_timetable_workbook(WORKBOOK_PATH)
    
    assert tt.total_entries > 0
    assert len(tt.sheets_parsed) == 13
    assert "Classroom Lab Nomenclature" in tt.sheets_parsed
    assert "SY-A" in tt.sheets_parsed
    assert "SY-B" in tt.sheets_parsed
    assert "TY-A" in tt.sheets_parsed
    assert "B.Tech-A" in tt.sheets_parsed
    assert "M.Tech-FY" in tt.sheets_parsed

def test_nomenclature_extraction():
    tt = parse_master_timetable_workbook(WORKBOOK_PATH)
    assert len(tt.rooms) > 0
    # Check MSAL
    assert "MSAL" in tt.rooms
    assert "Multimodal Sensor Analytics Lab" in tt.rooms["MSAL"].lab_name
    # Check CVL
    assert "CVL" in tt.rooms
    assert "Computer Vision Lab" in tt.rooms["CVL"].lab_name

def test_faculty_and_subject_lookup():
    tt = parse_master_timetable_workbook(WORKBOOK_PATH)
    # Check known faculty initials
    assert "SUK" in tt.faculty_lookup
    assert "Sumit Kumar" in tt.faculty_lookup["SUK"]
    assert "SAP" in tt.faculty_lookup
    assert "Sangeeta Pant" in tt.faculty_lookup["SAP"]
    assert "SVB" in tt.faculty_lookup
    assert "Sheetal Borhade" in tt.faculty_lookup["SVB"]

    # Check known subject codes
    assert "DM" in tt.subject_lookup or "OS" in tt.subject_lookup or "SML" in tt.subject_lookup

def test_merged_cell_lab_batches():
    tt = parse_master_timetable_workbook(WORKBOOK_PATH)
    # Filter SY-A entries for Monday
    sya_mon = [e for e in tt.entries if e.sheet_name == "SY-A" and e.day == "Monday"]
    assert len(sya_mon) > 0

    # There should be lab entries with batches A1, A2, A3
    batches = {e.batch for e in sya_mon if e.is_lab}
    assert "A1" in batches or "A2" in batches or "A3" in batches

def test_lunch_break_handling():
    tt = parse_master_timetable_workbook(WORKBOOK_PATH)
    breaks = [e for e in tt.entries if e.is_break]
    assert len(breaks) > 0
    assert all("12:45" in b.time_slot or "1:35" in b.time_slot for b in breaks)

