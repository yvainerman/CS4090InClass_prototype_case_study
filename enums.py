# ENUMS

from enum import Enum


class Role(Enum):
    # one role per user. all six actors here

    STUDENT_ORG_REPRESENTATIVE = "StudentOrgRepresentative"
    FACULTY_STAFF = "FacultyStaff"
    FACILITY_COORDINATOR = "FacilityCoordinator"
    EVENT_APPROVER = "EventApprover"
    CAMPUS_SECURITY = "CampusSecurity"
    SYSTEM_ADMINISTRATOR = "SystemAdministrator"


class ReservationStatus(Enum):
    # states of reservation lifecycle

    DRAFT = "Draft"
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"


class RoomStatus(Enum):
    # states of room availability

    AVAILABLE = "Available"
    PENDING = "Pending"
    RESERVED = "Reserved"
    IN_USE = "In_Use"


class ApprovalOutcome(Enum):
    # possible decision for a booking

    APPROVED = "Approved"
    REJECTED = "Rejected"


class SupportType(Enum):
    # support types

    EQUIPMENT = "Equipment"
    SECURITY = "Security"
    EVENT_SUPPORT = "EventSupport"
