import random
import csv
import io
from dataclasses import dataclass, field

from engine.status import STATUS_TO_MILESTONE, Milestone, MILESTONE_ORDER, MILESTONE_RANK

STREET_NAMES = [
    "RUNNING TIDE", "RACIMO", "FLORIDA ROCK", "WATERFRONT", "BLUE SHELL",
    "PALM VIEW", "HIDDEN LAKE", "SILVER OAK", "CRYSTAL RIVER", "SUNSET RIDGE",
    "GOLDEN GATE", "PINE HURST", "CEDAR CREST", "MAPLE GROVE", "WILLOW BROOK",
    "HARBOR VIEW", "LAKESHORE", "OCEAN BREEZE", "SUMMIT PEAK", "VALLEY FORGE",
    "STONE BRIDGE", "EAGLE NEST", "FOX HOLLOW", "DEER PATH", "BIRCHWOOD",
    "ASHFORD", "KENSINGTON", "WELLINGTON", "CANTERBURY", "NOTTINGHAM",
    "OXFORD", "CAMBRIDGE", "HAMPTON", "BERKSHIRE", "GLOUCESTER",
    "DEVONSHIRE", "WARWICK", "LANCASTER", "YORKTOWN", "PROVIDENCE",
    "INDEPENDENCE", "CONSTITUTION", "LIBERTY", "PATRIOT", "FREEDOM",
    "HERITAGE", "COLONIAL", "PIONEER", "FRONTIER", "LEGACY",
]

LIFECYCLE_STATUSES = [
    "Submitted", "In Review", "Plan Review", "Ready to Issue",
    "Inspection Phase", "Pending CO", "Closed - Complete",
]


@dataclass
class MockPermit:
    record_number: str
    address: str
    record_type: str = "Residential New Construction Permit"
    description: str = "New single family residence"
    city_state_zip: str = "Sarasota, FL 34240"
    lifecycle_stage: int = 0
    disappeared_in: set[int] = field(default_factory=set)


@dataclass
class GroundTruthChange:
    record_number: str
    from_status: str
    to_status: str
    snapshot_index: int
    is_tracked_milestone: bool
    is_backward: bool
    is_new: bool = False
    is_disappeared: bool = False
    is_unrecognized: bool = False


@dataclass
class MockSnapshot:
    rows: list[dict]
    report_date: str
    ground_truth_changes: list[GroundTruthChange] = field(default_factory=list)


def generate_mock_data(
    num_permits: int = 50,
    num_snapshots: int = 4,
    seed: int = 42,
) -> list[MockSnapshot]:
    rng = random.Random(seed)

    permits: list[MockPermit] = []
    for i in range(num_permits):
        street = STREET_NAMES[i % len(STREET_NAMES)]
        house_num = rng.randint(100, 9999)
        suffix = rng.choice(["Pl", "Dr", "St", "Ave", "Cir", "Ln", "Way", "Ct"])
        permits.append(MockPermit(
            record_number=f"RES-NEW-26-{i+1:06d}",
            address=f"{house_num} {street} {suffix}",
            lifecycle_stage=0,
        ))

    new_permit_indices = set()
    disappear_indices = set()
    backward_indices = set()
    skip_indices = set()
    unrecognized_indices = set()

    if num_permits > 10:
        new_permit_indices.add(rng.randint(num_permits // 2, num_permits - 1))
    if num_permits > 5:
        disappear_indices.add(rng.randint(0, num_permits - 1))
    if num_permits > 8:
        backward_indices.add(rng.randint(2, num_permits - 1))
    if num_permits > 6:
        skip_indices.add(rng.randint(1, num_permits - 1))
    if num_permits > 4:
        unrecognized_indices.add(rng.randint(0, num_permits - 1))

    snapshots: list[MockSnapshot] = []
    permit_prev_status: dict[str, str] = {}

    for snap_idx in range(num_snapshots):
        month = 1 + snap_idx
        report_date = f"{month}/15/2026"
        rows = []
        changes = []

        for p_idx, permit in enumerate(permits):
            if p_idx in new_permit_indices and snap_idx < 2:
                continue

            if p_idx in disappear_indices and snap_idx == 2:
                if permit.record_number in permit_prev_status:
                    changes.append(GroundTruthChange(
                        record_number=permit.record_number,
                        from_status=permit_prev_status[permit.record_number],
                        to_status="",
                        snapshot_index=snap_idx,
                        is_tracked_milestone=False,
                        is_backward=False,
                        is_disappeared=True,
                    ))
                continue

            if p_idx in unrecognized_indices and snap_idx == num_snapshots - 1:
                status = "Unknown Future Status"
                row = _make_row(permit, status, report_date, add_noise=True)
                rows.append(row)
                changes.append(GroundTruthChange(
                    record_number=permit.record_number,
                    from_status=permit_prev_status.get(permit.record_number, ""),
                    to_status=status,
                    snapshot_index=snap_idx,
                    is_tracked_milestone=False,
                    is_backward=False,
                    is_unrecognized=True,
                ))
                permit_prev_status[permit.record_number] = status
                continue

            is_new = p_idx in new_permit_indices and snap_idx == 2
            if is_new:
                permit.lifecycle_stage = 0

            if snap_idx > 0 and not is_new:
                advance_chance = 0.6
                if p_idx in skip_indices and snap_idx == 2:
                    permit.lifecycle_stage = min(
                        permit.lifecycle_stage + 2,
                        len(LIFECYCLE_STATUSES) - 1,
                    )
                elif rng.random() < advance_chance and permit.lifecycle_stage < len(LIFECYCLE_STATUSES) - 1:
                    permit.lifecycle_stage += 1

                if p_idx in backward_indices and snap_idx == 2:
                    permit.lifecycle_stage = max(0, permit.lifecycle_stage - 2)

            status = LIFECYCLE_STATUSES[permit.lifecycle_stage]
            row = _make_row(permit, status, report_date, add_noise=(snap_idx % 2 == 0))
            rows.append(row)

            prev = permit_prev_status.get(permit.record_number)
            if is_new:
                changes.append(GroundTruthChange(
                    record_number=permit.record_number,
                    from_status="",
                    to_status=status,
                    snapshot_index=snap_idx,
                    is_tracked_milestone=_is_tracked(status),
                    is_backward=False,
                    is_new=True,
                ))
            elif prev and prev != status:
                from_ms = STATUS_TO_MILESTONE.get(prev, Milestone.UNRECOGNIZED)
                to_ms = STATUS_TO_MILESTONE.get(status, Milestone.UNRECOGNIZED)
                is_backward = (
                    MILESTONE_RANK.get(to_ms, 0) < MILESTONE_RANK.get(from_ms, 0)
                    and from_ms != Milestone.CLOSED_NON_COMPLETION
                    and to_ms != Milestone.CLOSED_NON_COMPLETION
                )
                changes.append(GroundTruthChange(
                    record_number=permit.record_number,
                    from_status=prev,
                    to_status=status,
                    snapshot_index=snap_idx,
                    is_tracked_milestone=_is_tracked(status),
                    is_backward=is_backward,
                ))

            permit_prev_status[permit.record_number] = status

        snapshots.append(MockSnapshot(
            rows=rows,
            report_date=report_date,
            ground_truth_changes=changes,
        ))

    return snapshots


def _make_row(permit: MockPermit, status: str, report_date: str, add_noise: bool = False) -> dict:
    addr = permit.address
    if add_noise:
        addr = f"{addr}  "
    project_name = f"{addr},  {permit.city_state_zip}"
    if add_noise:
        project_name += " :"
    else:
        project_name += " :"

    return {
        "Date": report_date,
        "Record Number": permit.record_number,
        "Record Type": permit.record_type,
        "Description": permit.description,
        "Project Name": project_name,
        "Status": status,
        "Short Notes": "",
    }


def _is_tracked(status: str) -> bool:
    ms = STATUS_TO_MILESTONE.get(status, Milestone.UNRECOGNIZED)
    return ms in (Milestone.PERMIT_ISSUED, Milestone.PENDING_CO, Milestone.CLOSED)


def snapshot_to_csv(snapshot: MockSnapshot) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "Date", "Record Number", "Record Type", "Description",
        "Project Name", "Status", "Short Notes",
    ])
    writer.writeheader()
    writer.writerows(snapshot.rows)
    return output.getvalue()
