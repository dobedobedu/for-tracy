from engine.status import get_milestone, is_backward_move
from store.interface import EventLogStore, PermitRecord, Upload


def canonical_uploads(store: EventLogStore) -> list[Upload]:
    """One version per report date: the last uploaded revision wins."""
    by_date: dict[str, Upload] = {}
    for upload in store.get_upload_history():
        existing = by_date.get(upload.report_date)
        if existing is None or (upload.id or 0) > (existing.id or 0):
            by_date[upload.report_date] = upload
    return sorted(by_date.values(), key=lambda u: u.report_date)


def select_upload(uploads: list[Upload], report_date: str | None) -> Upload | None:
    if report_date is None:
        return uploads[-1] if uploads else None
    return next((u for u in uploads if u.report_date == report_date), None)


def snapshot_transitions(from_permits: list[PermitRecord], to_permits: list[PermitRecord], from_date: str) -> list[dict]:
    previous = {p.record_number: p for p in from_permits}
    transitions = []
    for p in sorted(to_permits, key=lambda permit: permit.record_number):
        prior = previous.get(p.record_number)
        if prior is not None and prior.current_status != p.current_status:
            transitions.append({
                'record_number': p.record_number, 'address': p.address,
                'from_status': prior.current_status, 'to_status': p.current_status,
                'is_new': False,
                'is_backward': is_backward_move(get_milestone(prior.current_status), get_milestone(p.current_status)),
                'is_tracked_milestone': prior.current_milestone != p.current_milestone,
            })
        elif prior is None and p.first_seen_date > from_date:
            # Export omissions must not relabel already-known records as new.
            transitions.append({
                'record_number': p.record_number, 'address': p.address,
                'from_status': 'New Application', 'to_status': p.current_status,
                'is_new': True, 'is_backward': False, 'is_tracked_milestone': True,
            })
    return transitions


def compare_reports(store: EventLogStore, from_date: str, to_date: str) -> dict:
    uploads = canonical_uploads(store)
    from_upload = select_upload(uploads, from_date)
    to_upload = select_upload(uploads, to_date)
    if not from_upload or not to_upload:
        return {'error': 'One or both reports not found'}
    if from_date > to_date:
        return {'error': 'From report must not be later than to report'}
    transitions = snapshot_transitions(store.get_snapshot(from_upload.id), store.get_snapshot(to_upload.id), from_date)
    return {
        'from_report': {'id': from_upload.id, 'date': from_date, 'filename': from_upload.filename},
        'to_report': {'id': to_upload.id, 'date': to_date, 'filename': to_upload.filename},
        'transitions': transitions,
    }
