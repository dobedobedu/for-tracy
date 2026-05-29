from store.interface import EventLogStore


def compare_reports(store: EventLogStore, from_date: str, to_date: str) -> dict:
    uploads = store.get_upload_history()
    from_upload = next((u for u in uploads if u.report_date == from_date), None)
    to_upload = next((u for u in uploads if u.report_date == to_date), None)

    if not from_upload or not to_upload:
        return {"error": "One or both reports not found"}

    all_permits = store.get_all_permits()

    # Build status at each date for all permits ever seen
    transitions = []
    for p in all_permits:
        fs = store.get_permit_status_at_date(p.record_number, from_date)
        ts = store.get_permit_status_at_date(p.record_number, to_date)
        if fs and ts and fs != ts:
            transitions.append({
                "record_number": p.record_number,
                "address": p.address,
                "from_status": fs,
                "to_status": ts,
            })

    return {
        "from_report": {"date": from_date, "filename": from_upload.filename},
        "to_report": {"date": to_date, "filename": to_upload.filename},
        "transitions": transitions,
    }
