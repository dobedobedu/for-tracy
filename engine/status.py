from enum import Enum


class Milestone(Enum):
    APPLICATION_REVIEW = "Application / Review"
    PENDING_NO_ISSUES = "Pending (no issues)"
    READY_TO_ISSUE = "Ready to Issue"
    PERMIT_ISSUED = "Permit Issued (Inspection)"
    PENDING_CO = "Pending CO"
    TCO_ISSUED = "TCO Issued"
    CLOSED = "Closed"
    PERMIT_EXPIRED = "Permit Expired"
    UNRECOGNIZED = "Unrecognized"


# Map each status to its milestone
STATUS_TO_MILESTONE: dict[str, Milestone] = {
    "Submitted": Milestone.APPLICATION_REVIEW,
    "In Review": Milestone.APPLICATION_REVIEW,
    "Plan Review": Milestone.APPLICATION_REVIEW,
    "Revisions Required": Milestone.APPLICATION_REVIEW,
    "Additional Info Required": Milestone.APPLICATION_REVIEW,
    "Pending": Milestone.PENDING_NO_ISSUES,
    "Ready to Issue": Milestone.READY_TO_ISSUE,
    "Inspection Phase": Milestone.PERMIT_ISSUED,
    "Pending CO": Milestone.PENDING_CO,
    "TCO Issued": Milestone.TCO_ISSUED,
    "Closed - Complete": Milestone.CLOSED,
    "Closed - Approved": Milestone.CLOSED,
    "Closed - Issued": Milestone.CLOSED,
    "Closed - Withdrawn": Milestone.CLOSED,
    "Permit Expired": Milestone.PERMIT_EXPIRED,
}

# Sub-statuses within the Closed milestone
CLOSED_SUB_STATUSES = ["Closed - Complete", "Closed - Approved", "Closed - Issued", "Closed - Withdrawn"]

MILESTONE_ORDER: list[Milestone] = [
    Milestone.APPLICATION_REVIEW,
    Milestone.PENDING_NO_ISSUES,
    Milestone.READY_TO_ISSUE,
    Milestone.PERMIT_ISSUED,
    Milestone.PENDING_CO,
    Milestone.TCO_ISSUED,
    Milestone.CLOSED,
    Milestone.PERMIT_EXPIRED,
]

MILESTONE_RANK: dict[Milestone, int] = {m: i for i, m in enumerate(MILESTONE_ORDER)}

TRACKED_TRANSITIONS: dict[str, Milestone] = {
    "permit_issued": Milestone.PERMIT_ISSUED,
    "co_pending": Milestone.PENDING_CO,
    "co_issued": Milestone.CLOSED,  # Now maps to Closed instead of CO Issued / Complete
}


def get_milestone(status: str) -> Milestone:
    return STATUS_TO_MILESTONE.get(status, Milestone.UNRECOGNIZED)


def is_tracked_transition(to_milestone: Milestone) -> bool:
    return to_milestone in TRACKED_TRANSITIONS.values()


def is_backward_move(from_milestone: Milestone, to_milestone: Milestone) -> bool:
    from_rank = MILESTONE_RANK.get(from_milestone, -1)
    to_rank = MILESTONE_RANK.get(to_milestone, -1)
    if from_rank == -1 or to_rank == -1:
        return False
    if from_milestone == Milestone.CLOSED or to_milestone == Milestone.CLOSED:
        return False
    return to_rank < from_rank
