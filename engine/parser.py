import re
from datetime import datetime
from dataclasses import dataclass

import pandas as pd

from engine.status import get_milestone, Milestone


@dataclass
class ParsedRow:
    date: str
    date_original: str
    record_number: str
    record_type: str
    description: str
    address: str
    city_state_zip: str
    status: str
    milestone: Milestone
    short_notes: str
    is_unrecognized_status: bool
    community: str


def parse_date(date_str: str) -> str:
    date_str = date_str.strip()
    for fmt in ("%m/%d/%Y", "%-m/%-d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    parts = date_str.split("/")
    if len(parts) == 3:
        month, day, year = parts
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return date_str


STREET_TYPES = {
    "st", "street", "rd", "road", "ave", "avenue", "ln", "lane", "loop", "cir", "circle",
    "way", "dr", "drive", "blvd", "boulevard", "ct", "court", "pl", "place", "trail",
    "path", "pkwy", "parkway", "hwy", "highway", "ter", "terrace",
}


def extract_community(address: str) -> str:
    """Extract the community/neighborhood name from a street address.

    Takes the street name portion (everything between house number and street type).
    Examples:
        "8504 ANTHIRIUM Loop" -> "ANTHIRIUM"
        "240 BLUE MIST Way" -> "BLUE MIST"
        "1262 PALM VIEW Rd" -> "PALM VIEW"
    """
    address = address.strip()
    # Take only the part before first comma if present
    street_part = address.split(",")[0].strip()
    words = street_part.split()
    if len(words) < 2:
        return street_part

    # Remove leading house number
    if words[0].replace("-", "").isdigit():
        words = words[1:]

    # Find the last street type and take everything before it
    for i in range(len(words) - 1, -1, -1):
        if words[i].lower().rstrip(".") in STREET_TYPES:
            words = words[:i]
            break

    return " ".join(words)


def parse_address(project_name: str) -> tuple[str, str]:
    project_name = project_name.strip()
    if project_name.endswith(" :"):
        project_name = project_name[:-2].strip()
    parts = project_name.split(",", 1)
    address = parts[0].strip()
    address = re.sub(r'\s+', ' ', address)
    city_state_zip = parts[1].strip() if len(parts) > 1 else ""
    city_state_zip = re.sub(r'\s+', ' ', city_state_zip)
    return address, city_state_zip


def parse_row(row: pd.Series) -> ParsedRow:
    date_original = str(row.get("Date", "")).strip()
    date_iso = parse_date(date_original)
    record_number = str(row.get("Record Number", "")).strip()
    record_type = str(row.get("Record Type", "")).strip()
    description = str(row.get("Description", "")).strip()
    project_name = str(row.get("Project Name", "")).strip()
    status = str(row.get("Status", "")).strip()
    short_notes = str(row.get("Short Notes", "")).strip()
    if short_notes.lower() == "nan":
        short_notes = ""
    if description.lower() == "nan":
        description = ""

    address, city_state_zip = parse_address(project_name)
    community = extract_community(address)
    milestone = get_milestone(status)
    is_unrecognized = milestone == Milestone.UNRECOGNIZED and status != ""

    return ParsedRow(
        date=date_iso,
        date_original=date_original,
        record_number=record_number,
        record_type=record_type,
        description=description,
        address=address,
        city_state_zip=city_state_zip,
        status=status,
        milestone=milestone,
        short_notes=short_notes,
        is_unrecognized_status=is_unrecognized,
        community=community,
    )


@dataclass
class ScopeFilter:
    record_type: str = "Residential New Construction Permit"
    zip_codes: list[str] | None = None
    communities: list[str] | None = None

    def __post_init__(self):
        if self.zip_codes is None:
            self.zip_codes = ["34240"]
        if self.communities is None:
            self.communities = []


def apply_scope_filter(df: pd.DataFrame, scope: ScopeFilter) -> tuple[pd.DataFrame, int]:
    original_count = len(df)

    if scope.record_type:
        df = df[df["Record Type"].str.strip() == scope.record_type]

    if scope.zip_codes:
        zip_pattern = "|".join(scope.zip_codes)
        df = df[df["Project Name"].str.contains(zip_pattern, na=False, regex=True)]

    if scope.communities:
        community_pattern = "|".join(c.upper() for c in scope.communities)
        df = df[df["Project Name"].str.upper().str.contains(community_pattern, na=False, regex=True)]

    dropped = original_count - len(df)
    return df.reset_index(drop=True), dropped


def parse_csv(df: pd.DataFrame, scope: ScopeFilter | None = None) -> tuple[list[ParsedRow], int]:
    if scope:
        df, dropped = apply_scope_filter(df, scope)
    else:
        dropped = 0

    rows = []
    for _, row in df.iterrows():
        parsed = parse_row(row)
        if parsed.record_number:
            rows.append(parsed)

    return rows, dropped
