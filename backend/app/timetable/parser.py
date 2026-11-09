"""
Robust Excel parser for CampusGPT timetables using openpyxl.
Handles all 13 worksheets, merged cell ranges, lab batches, legends, and rooms.
"""
import re
import os
import logging
from typing import Dict, List, Optional, Tuple, Any
import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

from app.timetable.models import (
    ParsedTimetable,
    TimetableEntry,
    RoomNomenclature,
    TimeSlot
)

logger = logging.getLogger(__name__)

# Standard days of week
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

def normalize_time(t_str: str) -> str:
    """Normalize '9:00' to '09:00', '1:35' to '13:35' if afternoon."""
    if not t_str:
        return ""
    parts = t_str.strip().split(":")
    if len(parts) != 2:
        return t_str.strip()
    try:
        h = int(parts[0])
        m = int(parts[1])
        # Convert afternoon hours 1..7 to 13..19 (since college classes run 8am - 5pm)
        if 1 <= h <= 7:
            h += 12
        return f"{h:02d}:{m:02d}"
    except ValueError:
        return t_str.strip()

def parse_time_slot(raw: str, slot_idx: int) -> Optional[TimeSlot]:
    """Parse time slot string like '9:00 - 9:55' or '1:35- 2:30'."""
    if not raw or not isinstance(raw, str):
        return None
    cleaned = raw.replace("\n", " ").strip()
    # match patterns like '9:00 - 9:55'
    m = re.search(r"(\d{1,2}:\d{2})\s*[-–to]+\s*(\d{1,2}:\d{2})", cleaned)
    if not m:
        return None
    start_raw, end_raw = m.group(1), m.group(2)
    start_norm = normalize_time(start_raw)
    end_norm = normalize_time(end_raw)
    return TimeSlot(
        raw_slot=cleaned,
        start_time=start_norm,
        end_time=end_norm,
        slot_index=slot_idx
    )

def extract_nomenclature(sheet: Worksheet) -> Dict[str, RoomNomenclature]:
    """Extract room and lab abbreviations from 'Classroom Lab Nomenclature' sheet."""
    rooms = {}
    # Row 3 has headers: Lab Nomenclature | Lab Name | Abbreviation of Lab Name
    for r in range(4, sheet.max_row + 1):
        nom = sheet.cell(r, 1).value
        name = sheet.cell(r, 2).value
        abbr = sheet.cell(r, 3).value
        if abbr and name:
            abbr_clean = str(abbr).strip().upper()
            nom_clean = str(nom).strip() if nom else ""
            name_clean = str(name).strip()
            rn = RoomNomenclature(
                lab_nomenclature=nom_clean,
                lab_name=name_clean,
                abbreviation=abbr_clean
            )
            rooms[abbr_clean] = rn
            # Also store with trailing 'L' stripped or added if common
            if abbr_clean.endswith("L"):
                rooms[abbr_clean[:-1]] = rn
            else:
                rooms[abbr_clean + "L"] = rn
    return rooms

def extract_faculty_and_subjects_legends(sheet: Worksheet) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Extracts faculty initials -> Full name mapping and subject code -> Full name mapping
    from the legend table below row 23 of any timetable sheet.
    """
    faculty_map: Dict[str, str] = {}
    subject_map: Dict[str, str] = {}

    for r in range(23, min(sheet.max_row + 1, 60)):
        # Check all cells in row for patterns like 'Dr. First Last (INI)'
        for c in range(1, min(sheet.max_column + 1, 15)):
            val = sheet.cell(r, c).value
            if not val or not isinstance(val, str):
                continue
            text = val.strip()

            # Match faculty pattern: 'Dr. First Last (XYZ)' or 'Prof. First Last (XYZ)' or 'Mr./Ms. First Last (XYZ)'
            fac_matches = re.findall(r"((?:Dr\.|Prof\.|Mr\.|Ms\.)\s+[A-Za-z\s\.]+)\s*\(([A-Za-z]{2,5})\)", text)
            for full_name, initials in fac_matches:
                ini_clean = initials.strip().upper()
                name_clean = full_name.strip()
                faculty_map[ini_clean] = name_clean

            # Match subject code with parentheses at end: e.g. 'Operating Systems (OS)'
            sub_match = re.search(r"^([A-Za-z0-9\s,&/–-]+?)\s*\(([A-Za-z0-9\s/–-]{2,12})\)$", text)
            if sub_match:
                sub_name = sub_match.group(1).strip()
                sub_code = sub_match.group(2).strip().upper()
                if len(sub_code) <= 10 and not any(k in sub_code for k in ["DR", "MR", "MS", "TUT", "LAB"]):
                    subject_map[sub_code] = sub_name

    return faculty_map, subject_map

def parse_lab_or_tut_line(line: str) -> Dict[str, Any]:
    """
    Parse complex lab / tut string like:
    'SML Lab-A1-PVK - MSA' -> subject: 'SML Lab', batch: 'A1', faculty: 'PVK', room: 'MSA'
    'DM (TUT)-A3-SAP - AI' -> subject: 'DM (TUT)', batch: 'A3', faculty: 'SAP', room: 'AI'
    'OS Lab-B2-RYM -MDL'   -> subject: 'OS Lab', batch: 'B2', faculty: 'RYM', room: 'MDL'
    """
    cleaned = line.replace("\n", " ").strip()
    res = {
        "subject": cleaned,
        "batch": "All",
        "faculty": None,
        "room": None,
        "is_lab": "lab" in cleaned.lower(),
        "is_tut": "tut" in cleaned.lower()
    }

    # Pattern: Subject-Batch-Faculty - Room or Subject-Batch-Faculty-Room
    m = re.search(r"^(.*?)-([A-C][1-3]|ML[1-4])\s*[-–]\s*([A-Za-z0-9/\s]+?)(?:\s*[-–]\s*([A-Za-z0-9\.\s]+))?$", cleaned)
    if m:
        res["subject"] = m.group(1).strip()
        res["batch"] = m.group(2).strip().upper()
        res["faculty"] = m.group(3).strip() if m.group(3) else None
        res["room"] = m.group(4).strip() if m.group(4) else None
    else:
        # Check alternate pattern: 'Subject Lab (Faculty) - Room'
        m2 = re.search(r"^(.*?)\s*[-–]\s*([A-Za-z0-9/\s]+)$", cleaned)
        if m2:
            res["subject"] = m2.group(1).strip()
            res["room"] = m2.group(2).strip()

    return res

def parse_class_sheet(sheet: Worksheet, rooms_dict: Dict[str, RoomNomenclature]) -> Tuple[List[TimetableEntry], Dict[str, str], Dict[str, str]]:
    """
    Parses a single timetable worksheet into structured TimetableEntry records.
    """
    entries: List[TimetableEntry] = []
    sheet_name = sheet.title

    # 1. Extract class name & batch from Rows 1-3
    class_name = sheet_name
    batch_year = ""
    for r in range(1, 4):
        for c in range(1, 5):
            val = sheet.cell(r, c).value
            if val and isinstance(val, str) and any(k in val.lower() for k in ["sy", "ty", "b.tech", "m.tech", "batch", "intern"]):
                class_name = val.strip()
                # Check for batch year
                by_m = re.search(r"(\d{4}[-–]\d{2,4}\s*Batch)", val, re.IGNORECASE)
                if by_m:
                    batch_year = by_m.group(1).strip()
                break
        if batch_year:
            break

    # 2. Extract legends from bottom of sheet
    sheet_faculty, sheet_subjects = extract_faculty_and_subjects_legends(sheet)

    # 3. Locate Day/Time header
    header_row = -1
    day_col = -1
    for r in range(1, 8):
        for c in range(1, 4):
            v = str(sheet.cell(r, c).value or "").strip().lower()
            if "day/time" in v or v == "day":
                header_row = r
                day_col = c
                break
        if header_row != -1:
            break

    if header_row == -1:
        logger.warning(f"Could not find Day/Time header in sheet {sheet_name}")
        return entries, sheet_faculty, sheet_subjects

    # 4. Parse time slots in header_row
    time_slots: List[Tuple[int, TimeSlot]] = []
    slot_idx = 1
    for c in range(day_col + 1, min(sheet.max_column + 1, day_col + 15)):
        slot_val = sheet.cell(header_row, c).value
        if slot_val:
            ts = parse_time_slot(str(slot_val), slot_idx)
            if ts:
                time_slots.append((c, ts))
                slot_idx += 1

    if not time_slots:
        logger.warning(f"No valid time slots found in sheet {sheet_name}")
        return entries, sheet_faculty, sheet_subjects

    # 5. Build merged cell lookup map: (row, col) -> (min_row, max_row, min_col, max_col)
    merged_map: Dict[Tuple[int, int], Any] = {}
    for rng in sheet.merged_cells.ranges:
        for r in range(rng.min_row, rng.max_row + 1):
            for c in range(rng.min_col, rng.max_col + 1):
                merged_map[(r, c)] = rng

    # 6. Parse Day Grid (rows header_row + 1 to 23)
    # Days are marked in day_col (or row 1 of the day block)
    current_day = None
    r = header_row + 1
    max_grid_row = min(sheet.max_row, 24)

    while r <= max_grid_row:
        day_cell = sheet.cell(r, day_col).value
        if day_cell:
            day_str = str(day_cell).strip().split("\n")[0].capitalize()
            for d in DAYS_OF_WEEK:
                if d.lower() in day_str.lower():
                    current_day = d
                    break

        if not current_day:
            r += 1
            continue

        # Look ahead 3 rows for standard 3-row day structure (r, r+1, r+2)
        day_rows = [r, r + 1, r + 2]
        r += 3 # Advance to next day block

        for col_idx, ts in time_slots:
            cell_top = sheet.cell(day_rows[0], col_idx).value
            cell_mid = sheet.cell(day_rows[1], col_idx).value if len(day_rows) > 1 else None
            cell_bot = sheet.cell(day_rows[2], col_idx).value if len(day_rows) > 2 else None

            # Handle merged across columns (e.g. Lunch break or 2-hour lab)
            rng = merged_map.get((day_rows[0], col_idx))
            if rng:
                top_val = sheet.cell(rng.min_row, rng.min_col).value
            else:
                top_val = cell_top

            # Check if this slot is Lunch Break
            all_cell_texts = " ".join([str(v or "") for v in [top_val, cell_mid, cell_bot]]).lower()
            if "lunch" in all_cell_texts:
                entries.append(TimetableEntry(
                    sheet_name=sheet_name,
                    class_name=class_name,
                    batch_year=batch_year,
                    day=current_day,
                    time_slot=ts.raw_slot,
                    start_time=ts.start_time,
                    end_time=ts.end_time,
                    slot_index=ts.slot_index,
                    subject_code="LUNCH",
                    subject_name="Lunch Break",
                    is_break=True
                ))
                continue

            # Check for special activities: Library Hour, Mentor-Mentee, Extended Learning Hour
            if any(act in all_cell_texts for act in ["library hour", "mentor -mentee", "mentor-mentee", "extended learning"]):
                act_name = "Library Hour / Departmental Meeting" if "library" in all_cell_texts else (
                    "Mentor-Mentee Meeting" if "mentor" in all_cell_texts else "Extended Learning Hour"
                )
                entries.append(TimetableEntry(
                    sheet_name=sheet_name,
                    class_name=class_name,
                    batch_year=batch_year,
                    day=current_day,
                    time_slot=ts.raw_slot,
                    start_time=ts.start_time,
                    end_time=ts.end_time,
                    slot_index=ts.slot_index,
                    subject_code="ACTIVITY",
                    subject_name=act_name,
                    is_activity=True
                ))
                continue

            # Check if each row represents a separate lab batch (e.g. A1, A2, A3)
            # Pattern: cell contains 'Lab' or 'TUT' or '-'
            lines = [sheet.cell(dr, col_idx).value for dr in day_rows if sheet.cell(dr, col_idx).value is not None]
            has_batch_indicators = any(any(b in str(l) for b in ["-A1", "-A2", "-A3", "-B1", "-B2", "-B3", "-C1", "-C2", "-C3", "Lab", "TUT"]) for l in lines)

            if has_batch_indicators:
                for line_val in lines:
                    line_str = str(line_val).strip()
                    parsed = parse_lab_or_tut_line(line_str)
                    sub_code = parsed["subject"]
                    fac_ini = parsed["faculty"]
                    room_c = parsed["room"]

                    # Expand room & faculty if possible
                    sub_full = sheet_subjects.get(sub_code.upper(), sub_code)
                    fac_full = sheet_faculty.get(fac_ini.upper(), fac_ini) if fac_ini else None
                    room_obj = rooms_dict.get(str(room_c).strip().upper()) if room_c else None
                    room_full = room_obj.lab_name if room_obj else (f"Classroom {room_c}" if str(room_c).isdigit() else room_c)

                    entries.append(TimetableEntry(
                        sheet_name=sheet_name,
                        class_name=class_name,
                        batch_year=batch_year,
                        day=current_day,
                        time_slot=ts.raw_slot,
                        start_time=ts.start_time,
                        end_time=ts.end_time,
                        slot_index=ts.slot_index,
                        subject_code=sub_code,
                        subject_name=sub_full,
                        faculty_initials=fac_ini,
                        faculty_name=fac_full,
                        room_code=str(room_c) if room_c else None,
                        room_name=room_full,
                        batch=parsed["batch"],
                        is_lab=parsed["is_lab"],
                        is_tutorial=parsed["is_tut"]
                    ))
            else:
                # Standard theory lecture:
                # Row 1: Subject Code
                # Row 2: Faculty Initials
                # Row 3: Room Code
                sub_raw = str(cell_top).strip() if cell_top is not None else ""
                fac_raw = str(cell_mid).strip() if cell_mid is not None else ""
                room_raw = str(cell_bot).strip() if cell_bot is not None else ""

                if not sub_raw or sub_raw == "None":
                    continue

                # Room code may be float formatted as '503.0'
                if room_raw.endswith(".0"):
                    room_raw = room_raw[:-2]

                sub_full = sheet_subjects.get(sub_raw.upper(), sub_raw)
                fac_full = sheet_faculty.get(fac_raw.upper(), fac_raw) if fac_raw else None
                room_obj = rooms_dict.get(room_raw.upper()) if room_raw else None
                room_full = room_obj.lab_name if room_obj else (f"Classroom {room_raw}" if room_raw.isdigit() else room_raw)

                entries.append(TimetableEntry(
                    sheet_name=sheet_name,
                    class_name=class_name,
                    batch_year=batch_year,
                    day=current_day,
                    time_slot=ts.raw_slot,
                    start_time=ts.start_time,
                    end_time=ts.end_time,
                    slot_index=ts.slot_index,
                    subject_code=sub_raw,
                    subject_name=sub_full,
                    faculty_initials=fac_raw if fac_raw else None,
                    faculty_name=fac_full,
                    room_code=room_raw if room_raw else None,
                    room_name=room_full,
                    batch="All",
                    is_lab="lab" in sub_raw.lower(),
                    is_tutorial="tut" in sub_raw.lower()
                ))

    return entries, sheet_faculty, sheet_subjects

def parse_master_timetable_workbook(file_path: str) -> ParsedTimetable:
    """
    Parses all worksheets in the Master TT Excel workbook into a unified ParsedTimetable structure.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Timetable workbook not found at: {file_path}")

    wb = openpyxl.load_workbook(file_path, data_only=True)
    all_entries: List[TimetableEntry] = []
    global_rooms: Dict[str, RoomNomenclature] = {}
    global_faculty: Dict[str, str] = {}
    global_subjects: Dict[str, str] = {}

    # 1. Parse nomenclature sheet first if available
    if "Classroom Lab Nomenclature" in wb.sheetnames:
        global_rooms = extract_nomenclature(wb["Classroom Lab Nomenclature"])

    # 2. Parse all sheets
    for sheet_name in wb.sheetnames:
        if sheet_name == "Classroom Lab Nomenclature":
            continue
        sheet = wb[sheet_name]
        try:
            entries, fac_map, sub_map = parse_class_sheet(sheet, global_rooms)
            all_entries.extend(entries)
            global_faculty.update(fac_map)
            global_subjects.update(sub_map)
        except Exception as e:
            logger.error(f"Error parsing sheet '{sheet_name}': {e}", exc_info=True)

    # 3. Post-process entries to enrich faculty full names and subject names from global map
    for entry in all_entries:
        if entry.faculty_initials and not entry.faculty_name:
            ini_up = entry.faculty_initials.upper().strip()
            if ini_up in global_faculty:
                entry.faculty_name = global_faculty[ini_up]
        if entry.subject_code and not entry.subject_name:
            sub_up = entry.subject_code.upper().strip()
            if sub_up in global_subjects:
                entry.subject_name = global_subjects[sub_up]
        if entry.room_code and not entry.room_name:
            rm_up = entry.room_code.upper().strip()
            if rm_up in global_rooms:
                entry.room_name = global_rooms[rm_up].lab_name
            elif rm_up.isdigit():
                entry.room_name = f"Classroom {rm_up}"

    return ParsedTimetable(
        entries=all_entries,
        rooms=global_rooms,
        faculty_lookup=global_faculty,
        subject_lookup=global_subjects,
        sheets_parsed=wb.sheetnames,
        total_entries=len(all_entries)
    )

