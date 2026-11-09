"""
Unit tests for TimetableService.
Tests today schedule, class timetable, faculty/subject/room search, free periods, and next class.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from app.timetable.service import timetable_service

TIMEZONE = ZoneInfo("Asia/Kolkata")

def test_sheet_alias_normalization():
    assert timetable_service.normalize_sheet_alias("What is the timetable for SY A?") == "SY-A"
    assert timetable_service.normalize_sheet_alias("show me second year b schedule") == "SY-B"
    assert timetable_service.normalize_sheet_alias("TY-C classes on Friday") == "TY-C"
    assert timetable_service.normalize_sheet_alias("BTech A timetable") == "B.Tech-A"
    assert timetable_service.normalize_sheet_alias("M.Tech FY schedule") == "M.Tech-FY"

def test_get_class_timetable():
    entries = timetable_service.get_class_timetable("SY-A", day="Monday")
    assert len(entries) > 0
    # Must have theory slots and lab slots
    days = {e.day for e in entries}
    assert days == {"Monday"}
    sub_codes = {e.subject_code for e in entries}
    assert "SML" in sub_codes or "CC" in sub_codes

def test_today_timetable():
    # Test a Monday morning
    monday_time = datetime(2026, 8, 17, 9, 30, tzinfo=TIMEZONE) # 17 Aug 2026 is Monday
    res = timetable_service.get_today_timetable("SY-A", custom_time=monday_time)
    assert res["day"] == "Monday"
    assert not res["is_holiday"]
    assert res["total_slots"] > 0

    # Test Sunday
    sunday_time = datetime(2026, 8, 16, 10, 0, tzinfo=TIMEZONE) # 16 Aug 2026 is Sunday
    res_sun = timetable_service.get_today_timetable("SY-A", custom_time=sunday_time)
    assert res_sun["is_holiday"]
    assert "Sunday" in res_sun["message"]

def test_next_class_calculation():
    # Monday at 09:15 AM: Should be in session for Slot 1 (9:00 - 9:55)
    mon_915 = datetime(2026, 8, 17, 9, 15, tzinfo=TIMEZONE)
    next_res = timetable_service.get_next_class("SY-A", custom_time=mon_915)
    assert next_res["status"] == "ongoing"
    assert next_res["current_class"] is not None

    # Monday at 17:00 PM: Classes completed
    mon_eve = datetime(2026, 8, 17, 17, 0, tzinfo=TIMEZONE)
    comp_res = timetable_service.get_next_class("SY-A", custom_time=mon_eve)
    assert comp_res["status"] == "completed"

def test_free_periods():
    free = timetable_service.get_free_periods("SY-A", day="Monday")
    assert isinstance(free, list)

def test_faculty_search():
    # Search for Dr. Sumit Kumar (SUK)
    results = timetable_service.search_by_faculty("SUK")
    assert len(results) > 0
    assert any("Sumit Kumar" in (e.faculty_name or "") or e.faculty_initials == "SUK" for e in results)

def test_subject_search():
    results = timetable_service.search_by_subject("Operating Systems")
    assert len(results) > 0
    assert any("OS" in e.subject_code or "Operating Systems" in (e.subject_name or "") for e in results)

def test_room_search():
    # Search for classroom 503
    results = timetable_service.search_by_room("503")
    assert len(results) > 0
    assert all("503" in (e.room_code or "") for e in results)

