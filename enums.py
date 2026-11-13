from enum import Enum


class Role(Enum):
    STUDENT_ORG_REPRESENTATIVE = "Student Organization Representative"
    FACULTY_STAFF = "Faculty / Staff"
    FACILITY_COORDINATOR = "Facility Coordinator"
    EVENT_APPROVER = "Event Approver"
    CAMPUS_SECURITY = "Campus Security"
    SYSTEM_ADMINISTRATOR = "System Administrator"


class ReservationStatus(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    IN_PROGRESS = "In progress"
    COMPLETED = "Completed"


class ApprovalOutcome(Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"


class SupportType(Enum):
    EQUIPMENT = "Equipment"
    SECURITY = "Security"
    EVENT_SUPPORT = "Event support"
