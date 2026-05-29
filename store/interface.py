from abc import ABC, abstractmethod
from dataclasses import dataclass
from engine.status import Milestone


@dataclass
class PermitRecord:
    record_number: str
    record_type: str
    description: str
    address: str
    city_state_zip: str
    first_seen_date: str
    last_seen_date: str
    current_status: str
    current_milestone: str
    community: str = ""


@dataclass
class Observation:
    id: int | None
    record_number: str
    status: str
    milestone: str
    observed_date: str
    upload_id: int
    created_at: str | None = None


@dataclass
class Upload:
    id: int | None
    filename: str
    report_date: str
    row_count_raw: int
    row_count_after_scope: int
    uploaded_at: str | None = None


@dataclass
class StatusChangeRecord:
    id: int | None
    record_number: str
    from_status: str
    to_status: str
    from_milestone: str
    to_milestone: str
    detected_on_upload_id: int
    change_date: str
    is_tracked_milestone: bool
    is_backward: bool


@dataclass
class TimelineEntry:
    observed_date: str
    status: str
    milestone: str
    upload_id: int


class EventLogStore(ABC):
    @abstractmethod
    def initialize(self) -> None:
        ...

    @abstractmethod
    def get_current_statuses(self) -> dict[str, PermitRecord]:
        ...

    @abstractmethod
    def get_current_status_map(self) -> tuple[dict[str, str], dict[str, Milestone], dict[str, str]]:
        ...

    @abstractmethod
    def record_upload(self, upload: Upload) -> int:
        ...

    @abstractmethod
    def upsert_permit(self, permit: PermitRecord) -> None:
        ...

    @abstractmethod
    def append_observation(self, obs: Observation) -> None:
        ...

    @abstractmethod
    def record_status_change(self, change: StatusChangeRecord) -> None:
        ...

    @abstractmethod
    def get_timeline(self, record_number: str) -> list[TimelineEntry]:
        ...

    @abstractmethod
    def get_latest_changes(self, upload_id: int) -> list[StatusChangeRecord]:
        ...

    @abstractmethod
    def get_all_permits(self) -> list[PermitRecord]:
        ...

    @abstractmethod
    def get_upload_history(self) -> list[Upload]:
        ...

    @abstractmethod
    def get_latest_upload(self) -> Upload | None:
        ...

    @abstractmethod
    def get_disappeared_permits(self, current_record_numbers: set[str]) -> list[PermitRecord]:
        ...

    @abstractmethod
    def get_permit_status_at_date(self, record_number: str, date: str) -> str | None:
        ...
