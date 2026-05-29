from dataclasses import dataclass
from engine.status import Milestone, get_milestone, is_tracked_transition, is_backward_move


@dataclass
class NewPermit:
    record_number: str
    record_type: str
    description: str
    address: str
    city_state_zip: str
    status: str
    milestone: Milestone
    observed_date: str
    community: str


@dataclass
class StatusChange:
    record_number: str
    from_status: str
    to_status: str
    from_milestone: Milestone
    to_milestone: Milestone
    change_date: str
    is_tracked_milestone: bool
    is_backward: bool


@dataclass
class DisappearedPermit:
    record_number: str
    last_status: str
    last_milestone: Milestone
    last_seen_date: str


@dataclass
class DiffResult:
    new_permits: list[NewPermit]
    status_changes: list[StatusChange]
    unchanged: list[str]
    disappeared: list[DisappearedPermit]
    unrecognized_statuses: list[str]
    observation_count: int


def detect_changes(
    new_rows: list,
    prior_statuses: dict[str, str],
    prior_milestones: dict[str, Milestone],
    prior_dates: dict[str, str],
) -> DiffResult:
    new_dict = {}
    unrecognized = set()

    for row in new_rows:
        new_dict[row.record_number] = row
        if row.is_unrecognized_status:
            unrecognized.add(row.status)

    new_permits = []
    status_changes = []
    unchanged = []

    for rn, row in new_dict.items():
        if rn not in prior_statuses:
            new_permits.append(NewPermit(
                record_number=rn,
                record_type=row.record_type,
                description=row.description,
                address=row.address,
                city_state_zip=row.city_state_zip,
                status=row.status,
                milestone=row.milestone,
                observed_date=row.date,
                community=row.community,
            ))
        elif prior_statuses[rn] != row.status:
            from_ms = prior_milestones.get(rn, Milestone.UNRECOGNIZED)
            to_ms = row.milestone
            status_changes.append(StatusChange(
                record_number=rn,
                from_status=prior_statuses[rn],
                to_status=row.status,
                from_milestone=from_ms,
                to_milestone=to_ms,
                change_date=row.date,
                is_tracked_milestone=is_tracked_transition(to_ms),
                is_backward=is_backward_move(from_ms, to_ms),
            ))
        else:
            unchanged.append(rn)

    disappeared = []
    for rn in prior_statuses:
        if rn not in new_dict:
            disappeared.append(DisappearedPermit(
                record_number=rn,
                last_status=prior_statuses[rn],
                last_milestone=prior_milestones.get(rn, Milestone.UNRECOGNIZED),
                last_seen_date=prior_dates.get(rn, ""),
            ))

    return DiffResult(
        new_permits=new_permits,
        status_changes=status_changes,
        unchanged=unchanged,
        disappeared=disappeared,
        unrecognized_statuses=sorted(unrecognized),
        observation_count=len(new_rows),
    )
