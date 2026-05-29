import re
from datetime import datetime


def parse_report_date_from_filename(filename: str) -> str:
    """Extract report date from filename in M.D.YY or MM-DD-YYYY format.
    
    Examples:
        "3.3.26_Report.csv" -> "2026-03-03"
        "12.25.25_Report.csv" -> "2025-12-25"
        "03-03-2026_Report.csv" -> "2026-03-03"
        "SomeRandomFile.csv" -> "2026-05-29" (today)
    """
    # Remove extension
    name = filename.rsplit('.', 1)[0]
    
    # Try M.D.YY or MM.DD.YY at the start
    match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})', name)
    if match:
        month, day, year = match.groups()
        year = int(year)
        if year < 100:
            year += 2000
        return f"{year:04d}-{int(month):02d}-{int(day):02d}"
    
    # Try MM-DD-YYYY
    match = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})', name)
    if match:
        month, day, year = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    
    # Fallback to today
    return datetime.now().strftime("%Y-%m-%d")
