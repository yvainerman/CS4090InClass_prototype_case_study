"""Domain objects shared by the terminal and web interfaces."""

from dataclasses import dataclass, field
from datetime import datetime

from enums import ApprovalOutcome, ReservationStatus, Role, SupportType


@dataclass
class User:
    user_id: str
    name: str
    email: str
    role: Role
    password_hash: str = ""

    def is_authorized(self, action: str) -> bool:
        if action in {"approve", "reject", "report", "manage_facility"}:
            return self.role in {Role.EVENT_APPROVER, Role.SYSTEM_ADMINISTRATOR}
        return action in {"reserve", "edit", "cancel", "request_support"}


@dataclass
class Room:
    room_id: str
    name: str
    capacity: int


@dataclass
class Facility:
    facility_id: str
    name: str
    location: str
    open_minutes: int
    close_minutes: int
    rooms: list[Room] = field(default_factory=list)

    def is_open(self, start_at: datetime, end_at: datetime) -> bool:
        if start_at.date() != end_at.date() or end_at <= start_at:
            return False
        start_minutes = start_at.hour * 60 + start_at.minute
        end_minutes = end_at.hour * 60 + end_at.minute
        return self.open_minutes <= start_minutes and end_minutes <= self.close_minutes


@dataclass
class SupportRequest:
    request_id: str
    support_type: SupportType
    details: str
    created_at: datetime


@dataclass
class Approval:
    decision: ApprovalOutcome
    decided_at: datetime
    reviewer_id: str
    comments: str = ""


@dataclass
class Reservation:
    reservation_id: str
    user_id: str
    facility_id: str
    room_id: str
    event_title: str
    start_at: datetime
    end_at: datetime
    expected_attendance: int
    status: ReservationStatus = ReservationStatus.PENDING
    approvals: list[Approval] = field(default_factory=list)
    support_requests: list[SupportRequest] = field(default_factory=list)
