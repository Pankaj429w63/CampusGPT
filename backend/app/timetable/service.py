"""
Timetable Query and Scheduling Service for CampusGPT.
Provides high-level queries:
- Today's timetable
- Specific class / section timetable
- Subject, faculty, and room lookup
- Free periods and next class detection
- Strict handling of ambiguity without guessing
"""
import os
import re
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Any
from zoneinfo import ZoneInfo

from app.timetable.models import ParsedTimetable, TimetableEntry
from app.timetable.parser import parse_master_timetable_workbook

logger = logging.getLogger(__name__)

DEFAULT_TT_PATH = "data/timetables/aiml/Master TT-26-27-ODD Sem.xlsx"
TIMEZONE = ZoneInfo("Asia/Kolkata")

class TimetableService:
    def __init__(self, file_path: str = DEFAULT_TT_PATH):
        self.file_path = file_path
        self._parsed_data: Optional[ParsedTimetable] = None

    def get_data(self) -> ParsedTimetable:
        if self._parsed_data is None:
            self.load()
        return self._parsed_data

    def load(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Timetable file not found: {self.file_path}")
        self._parsed_data = parse_master_timetable_workbook(self.file_path)
        logger.info(f"Loaded {self._parsed_data.total_entries} timetable entries from {self.file_path}")

    def normalize_sheet_alias(self, query: str) -> Optional[str]:
        """
        Map user query mentions (e.g. 'SY A', 'SY-A', 'Second Year A', 'TY B', 'BTech A', 'Final Year B')
        to canonical sheet names: ['SY-A', 'SY-B', 'SY-C', 'TY-A', 'TY-B', 'TY-C', 'B.Tech-A', 'B.Tech-B', 'M.Tech-FY', 'M.Tech-SY']
        """
        q = query.lower().replace("-", " ").replace(".", " ")
        patterns = [
            (r"\b(sy|second year)\s*(a|1)\b", "SY-A"),
            (r"\b(sy|second year)\s*(b|2)\b", "SY-B"),
            (r"\b(sy|second year)\s*(c|3)\b", "SY-C"),
            (r"\b(ty|third year)\s*(a|1)\b", "TY-A"),
            (r"\b(ty|third year)\s*(b|2)\b", "TY-B"),
            (r"\b(ty|third year)\s*(c|3)\b", "TY-C"),
            (r"\b(b\s*tech|final year|4th year)\s*(a|1)\b", "B.Tech-A"),
            (r"\b(b\s*tech|final year|4th year)\s*(b|2)\b", "B.Tech-B"),
            (r"\b(m\s*tech)\s*(fy|first year|1st year)\b", "M.Tech-FY"),
            (r"\b(m\s*tech)\s*(sy|second year|2nd year)\b", "M.Tech-SY"),
            (r"\b(intern|internship|7th sem)\b", "7th Sem- Internship Students"),
            (r"\b(sdp|iot)\b", "SDP-IoT")
        ]
        for pattern, sheet_name in patterns:
            if re.search(pattern, q):
                return sheet_name
        return None

    def get_class_timetable(self, sheet_name: str, day: Optional[str] = None, batch: Optional[str] = None) -> List[TimetableEntry]:
        """Return timetable entries for a specific class sheet, optionally filtered by day and batch."""
        data = self.get_data()
        entries = [e for e in data.entries if e.sheet_name.lower() == sheet_name.lower()]

        if day:
            day_clean = day.strip().capitalize()
            entries = [e for e in entries if e.day.lower() == day_clean.lower()]

        if batch and batch.lower() != "all":
            batch_clean = batch.strip().upper()
            entries = [e for e in entries if e.batch in [batch_clean, "All", None]]

        # Sort by slot_index
        entries.sort(key=lambda x: (x.day, x.slot_index, x.batch or ""))
        return entries

    def get_today_timetable(self, sheet_name: str, batch: Optional[str] = None, custom_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Fetch timetable for today. Handles Sunday as weekend holiday without guessing.
        """
        now = custom_time or datetime.now(TIMEZONE)
        day_name = now.strftime("%A")

        if day_name == "Sunday":
            return {
                "day": "Sunday",
                "is_holiday": True,
                "message": "Today is Sunday. There are no scheduled classes on Sundays.",
                "entries": []
            }

        entries = self.get_class_timetable(sheet_name, day=day_name, batch=batch)
        return {
            "day": day_name,
            "is_holiday": False,
            "class_name": sheet_name,
            "batch": batch or "All",
            "total_slots": len(entries),
            "entries": entries
        }

    def get_next_class(self, sheet_name: str, batch: Optional[str] = None, custom_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Finds the current or upcoming class for a section based on current clock time.
        """
        now = custom_time or datetime.now(TIMEZONE)
        curr_time_str = now.strftime("%H:%M")
        day_name = now.strftime("%A")

        if day_name == "Sunday":
            return {
                "day": "Sunday",
                "message": "Today is Sunday. The next classes will resume on Monday morning at 09:00.",
                "next_class": None
            }

        entries = self.get_class_timetable(sheet_name, day=day_name, batch=batch)
        # Exclude breaks
        class_entries = [e for e in entries if not e.is_break and not e.is_activity]

        current_class = None
        upcoming_class = None

        for e in class_entries:
            if e.start_time <= curr_time_str < e.end_time:
                current_class = e
                break
            elif e.start_time >= curr_time_str:
                if upcoming_class is None or e.start_time < upcoming_class.start_time:
                    upcoming_class = e

        if current_class:
            return {
                "status": "ongoing",
                "message": f"Currently in session: {current_class.subject_name or current_class.subject_code}",
                "current_class": current_class,
                "next_class": upcoming_class
            }
        elif upcoming_class:
            return {
                "status": "upcoming",
                "message": f"Next class is {upcoming_class.subject_name or upcoming_class.subject_code} at {upcoming_class.time_slot}",
                "current_class": None,
                "next_class": upcoming_class
            }
        else:
            return {
                "status": "completed",
                "message": f"All classes for today ({day_name}) have concluded.",
                "current_class": None,
                "next_class": None
            }

    def get_free_periods(self, sheet_name: str, day: Optional[str] = None, batch: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Identifies unallocated / free lecture slots for a class on a given day.
        Standard day has 8 slots: 1 to 8 (excluding lunch break slot).
        """
        target_day = day or datetime.now(TIMEZONE).strftime("%A")
        if target_day.capitalize() == "Sunday":
            return [{"slot": "All Day", "message": "Sunday is a holiday (completely free)."}]

        entries = self.get_class_timetable(sheet_name, day=target_day, batch=batch)
        occupied_slots = {e.slot_index for e in entries if not e.is_break}
        all_time_slots = {
            1: "9:00 - 9:55",
            2: "9:55 - 10:50",
            3: "10:55 - 11:50",
            4: "11:50 - 12:45",
            5: "12:45 - 1:35 (Lunch)",
            6: "1:35 - 2:30",
            7: "2:30 - 3:25",
            8: "3:25 - 4:20"
        }

        free = []
        for idx in range(1, 9):
            if idx == 5:
                continue # Lunch break is standard
            if idx not in occupied_slots:
                free.append({
                    "slot_index": idx,
                    "time_slot": all_time_slots.get(idx, ""),
                    "day": target_day
                })
        return free

    def search_by_faculty(self, faculty_query: str) -> List[TimetableEntry]:
        """Find all teaching slots for a given faculty member (by name or initials)."""
        data = self.get_data()
        fq = faculty_query.strip().lower()
        results = []
        for e in data.entries:
            if e.is_break:
                continue
            fac_name = (e.faculty_name or "").lower()
            fac_ini = (e.faculty_initials or "").lower()
            if fq in fac_name or fq == fac_ini or fq in fac_ini:
                results.append(e)
        return results

    def search_by_subject(self, subject_query: str) -> List[TimetableEntry]:
        """Find all timetable slots teaching a specific subject."""
        data = self.get_data()
        sq = subject_query.strip().lower()
        results = []
        for e in data.entries:
            if e.is_break:
                continue
            sub_code = (e.subject_code or "").lower()
            sub_name = (e.subject_name or "").lower()
            if sq in sub_code or sq in sub_name:
                results.append(e)
        return results

    def search_by_room(self, room_query: str) -> List[TimetableEntry]:
        """Find all timetable slots occupying a specific room or lab."""
        data = self.get_data()
        rq = room_query.strip().lower()
        results = []
        for e in data.entries:
            if e.is_break:
                continue
            r_code = (e.room_code or "").lower()
            r_name = (e.room_name or "").lower()
            if rq == r_code or rq in r_name or rq in r_code:
                results.append(e)
        return results

# Singleton instance
timetable_service = TimetableService()

