"""Application services and JSON persistence shared by every interface."""

import hashlib
import hmac
import json
import secrets
import threading
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from enums import ApprovalOutcome, ReservationStatus, Role, SupportType
from models import Approval, Facility, Reservation, Room, SupportRequest, User

DEFAULT_DATA_FILE = Path(__file__).parent / "booking_data.json"
DATE_FORMAT = "%Y-%m-%dT%H:%M"
HELD_STATUSES = {
    ReservationStatus.PENDING,
    ReservationStatus.APPROVED,
    ReservationStatus.IN_PROGRESS,
}


class DomainError(ValueError):
    """A validation or business-rule error safe to show to an end user."""


def synchronized(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapped


def parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise DomainError("Enter a valid date and time.")
    for date_format in (DATE_FORMAT, "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            pass
    raise DomainError("Use the date and time format YYYY-MM-DD HH:MM.")


def hash_password(password, salt=None):
    password = str(password or "")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 180_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password, encoded):
    try:
        algorithm, salt, expected = encoded.split("$", 2)
        actual = hash_password(password, salt).rsplit("$", 1)[1]
    except (AttributeError, TypeError, ValueError):
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    return hmac.compare_digest(actual, expected)


def _dt_text(value):
    return value.strftime(DATE_FORMAT)


def _seed_state(now=None):
    now = now or datetime.now()
    facility = Facility(
        "F001", "Curtis Laws Wilson Library", "North Campus", 8 * 60, 22 * 60,
        [
            Room("G102", "Collaboration Room", 20),
            Room("G201", "Seminar Room", 40),
            Room("G203", "Event Hall", 120),
        ],
    )
    requester = User(
        "U1", "Jordan Lee", "student@mst.edu",
        Role.STUDENT_ORG_REPRESENTATIVE, hash_password("Miner2026!"),
    )
    approver = User(
        "U2", "Morgan Chen", "approver@mst.edu",
        Role.EVENT_APPROVER, hash_password("Miner2026!"),
    )
    sample_start = (now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
    reservation = Reservation(
        "R-DEMO-1", requester.user_id, facility.facility_id, "G201",
        "Miner Makers Meetup", sample_start, sample_start + timedelta(hours=1), 28,
        ReservationStatus.APPROVED,
        [Approval(ApprovalOutcome.APPROVED, now, approver.user_id, "Demo booking")],
    )
    return {
        "users": [requester, approver],
        "facilities": [facility],
        "reservations": [reservation],
        "notifications": [],
    }


def _serialize(state):
    return {
        "version": 1,
        "users": [
            {
                "user_id": u.user_id, "name": u.name, "email": u.email,
                "role": u.role.name, "password_hash": u.password_hash,
            }
            for u in state["users"]
        ],
        "facilities": [
            {
                "facility_id": f.facility_id, "name": f.name, "location": f.location,
                "open_minutes": f.open_minutes, "close_minutes": f.close_minutes,
                "rooms": [
                    {"room_id": r.room_id, "name": r.name, "capacity": r.capacity}
                    for r in f.rooms
                ],
            }
            for f in state["facilities"]
        ],
        "reservations": [
            {
                "reservation_id": r.reservation_id, "user_id": r.user_id,
                "facility_id": r.facility_id, "room_id": r.room_id,
                "event_title": r.event_title, "start_at": _dt_text(r.start_at),
                "end_at": _dt_text(r.end_at), "expected_attendance": r.expected_attendance,
                "status": r.status.name,
                "approvals": [
                    {
                        "decision": a.decision.name, "decided_at": _dt_text(a.decided_at),
                        "reviewer_id": a.reviewer_id, "comments": a.comments,
                    }
                    for a in r.approvals
                ],
                "support_requests": [
                    {
                        "request_id": s.request_id, "support_type": s.support_type.name,
                        "details": s.details, "created_at": _dt_text(s.created_at),
                    }
                    for s in r.support_requests
                ],
            }
            for r in state["reservations"]
        ],
        "notifications": state["notifications"],
    }


def _deserialize(data):
    users = [
        User(u["user_id"], u["name"], u["email"], Role[u["role"]], u.get("password_hash", ""))
        for u in data["users"]
    ]
    facilities = [
        Facility(
            f["facility_id"], f["name"], f["location"], f["open_minutes"], f["close_minutes"],
            [Room(r["room_id"], r["name"], r["capacity"]) for r in f["rooms"]],
        )
        for f in data["facilities"]
    ]
    reservations = []
    for r in data["reservations"]:
        reservations.append(
            Reservation(
                r["reservation_id"], r["user_id"], r["facility_id"], r["room_id"],
                r["event_title"], parse_datetime(r["start_at"]), parse_datetime(r["end_at"]),
                r["expected_attendance"], ReservationStatus[r["status"]],
                [
                    Approval(
                        ApprovalOutcome[a["decision"]], parse_datetime(a["decided_at"]),
                        a["reviewer_id"], a.get("comments", ""),
                    )
                    for a in r.get("approvals", [])
                ],
                [
                    SupportRequest(
                        s["request_id"], SupportType[s["support_type"]], s["details"],
                        parse_datetime(s["created_at"]),
                    )
                    for s in r.get("support_requests", [])
                ],
            )
        )
    return {
        "users": users,
        "facilities": facilities,
        "reservations": reservations,
        "notifications": data.get("notifications", []),
    }


class BookingService:
    """Use-case layer. UI adapters call these methods instead of owning rules."""

    def __init__(self, data_file=DEFAULT_DATA_FILE, now_fn=datetime.now):
        self.data_file = Path(data_file)
        self.now_fn = now_fn
        self._lock = threading.RLock()
        if self.data_file.exists():
            try:
                self.state = _deserialize(json.loads(self.data_file.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise RuntimeError(f"Could not load booking data from {self.data_file}: {error}") from error
        else:
            self.state = _seed_state(self.now_fn())
            self._save()
        self._refresh_statuses()

    def _save(self):
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.data_file.with_suffix(self.data_file.suffix + ".tmp")
        temp_file.write_text(json.dumps(_serialize(self.state), indent=2), encoding="utf-8")
        temp_file.replace(self.data_file)

    @synchronized
    def reset_demo(self):
        with self._lock:
            self.state = _seed_state(self.now_fn())
            self._save()

    @synchronized
    def _refresh_statuses(self):
        now = self.now_fn()
        changed = False
        for reservation in self.state["reservations"]:
            if reservation.status == ReservationStatus.APPROVED and reservation.start_at <= now:
                reservation.status = ReservationStatus.IN_PROGRESS
                changed = True
            if reservation.status == ReservationStatus.IN_PROGRESS and reservation.end_at <= now:
                reservation.status = ReservationStatus.COMPLETED
                changed = True
        if changed:
            self._save()

    def _user(self, user_id):
        user = next((u for u in self.state["users"] if u.user_id == user_id), None)
        if user is None:
            raise DomainError("Your account is no longer available. Please sign in again.")
        return user

    def _facility(self, facility_id):
        facility = next((f for f in self.state["facilities"] if f.facility_id == facility_id), None)
        if facility is None:
            raise DomainError("That facility could not be found.")
        return facility

    def _reservation(self, reservation_id):
        reservation = next(
            (r for r in self.state["reservations"] if r.reservation_id == reservation_id), None
        )
        if reservation is None:
            raise DomainError("That reservation could not be found.")
        return reservation

    def _notify(self, user_id, message):
        self.state["notifications"].append(
            {
                "notification_id": uuid.uuid4().hex[:12],
                "user_id": user_id,
                "message": message,
                "created_at": _dt_text(self.now_fn()),
                "read": False,
            }
        )

    @synchronized
    def get_user(self, user_id):
        return self.public_user(self._user(user_id))

    @synchronized
    def authenticate(self, email, password):
        email = str(email or "").strip().lower()
        user = next((u for u in self.state["users"] if u.email.lower() == email), None)
        if user is None or not verify_password(str(password or ""), user.password_hash):
            raise DomainError("Email or password is incorrect.")
        return self.public_user(user)

    @synchronized
    def register(self, name, email, password):
        name, email = str(name or "").strip(), str(email or "").strip().lower()
        password = str(password or "")
        if not name:
            raise DomainError("Enter your name.")
        if len(name) > 80:
            raise DomainError("Name must be 80 characters or fewer.")
        if len(email) > 254 or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            raise DomainError("Enter a valid email address.")
        if any(u.email.lower() == email for u in self.state["users"]):
            raise DomainError("An account already exists for that email.")
        if len(str(password or "")) < 8:
            raise DomainError("Choose a password with at least 8 characters.")
        with self._lock:
            user = User(
                f"U-{uuid.uuid4().hex[:8].upper()}", name, email,
                Role.STUDENT_ORG_REPRESENTATIVE, hash_password(password),
            )
            self.state["users"].append(user)
            self._save()
        return self.public_user(user)

    @staticmethod
    def public_user(user):
        return {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role.value,
            "can_approve": user.is_authorized("approve"),
        }

    @synchronized
    def list_facilities(self):
        return [
            {
                "facility_id": f.facility_id,
                "name": f.name,
                "location": f.location,
                "open_time": f"{f.open_minutes // 60:02d}:{f.open_minutes % 60:02d}",
                "close_time": f"{f.close_minutes // 60:02d}:{f.close_minutes % 60:02d}",
                "rooms": [
                    {"room_id": r.room_id, "name": r.name, "capacity": r.capacity}
                    for r in f.rooms
                ],
            }
            for f in self.state["facilities"]
        ]

    @synchronized
    def dashboard(self, user_id):
        self._refresh_statuses()
        user = self._user(user_id)
        all_reservations = self.state["reservations"]
        own = [r for r in all_reservations if r.user_id == user_id]
        pending = [
            r for r in all_reservations if r.status == ReservationStatus.PENDING
        ] if user.is_authorized("approve") else []
        notifications = [
            n for n in reversed(self.state["notifications"]) if n["user_id"] == user_id
        ][:8]
        return {
            "user": self.public_user(user),
            "facilities": self.list_facilities(),
            "reservations": [self.public_reservation(r) for r in sorted(own, key=lambda x: x.start_at)],
            "pending_requests": [self.public_reservation(r) for r in pending],
            "notifications": notifications,
            "summary": {
                "my_reservations": len(own),
                "pending_requests": len(pending),
                "upcoming_events": sum(
                    r.status == ReservationStatus.APPROVED and r.start_at > self.now_fn()
                    for r in own
                ),
            },
        }

    def public_reservation(self, reservation):
        user = self._user(reservation.user_id)
        facility = self._facility(reservation.facility_id)
        room = next(r for r in facility.rooms if r.room_id == reservation.room_id)
        return {
            "reservation_id": reservation.reservation_id,
            "requester": user.name,
            "requester_email": user.email,
            "user_id": reservation.user_id,
            "facility_id": facility.facility_id,
            "facility_name": facility.name,
            "room_id": room.room_id,
            "room_name": room.name,
            "capacity": room.capacity,
            "event_title": reservation.event_title,
            "start_at": _dt_text(reservation.start_at),
            "end_at": _dt_text(reservation.end_at),
            "expected_attendance": reservation.expected_attendance,
            "status": reservation.status.value,
            "approvals": [
                {
                    "decision": a.decision.value,
                    "decided_at": _dt_text(a.decided_at),
                    "reviewer_id": a.reviewer_id,
                    "reviewer_name": self._user(a.reviewer_id).name,
                    "comments": a.comments,
                }
                for a in reservation.approvals
            ],
            "support_requests": [
                {
                    "request_id": s.request_id,
                    "support_type": s.support_type.value,
                    "details": s.details,
                    "created_at": _dt_text(s.created_at),
                }
                for s in reservation.support_requests
            ],
        }

    @synchronized
    def search_rooms(self, facility_id, start_at, end_at, minimum_capacity):
        facility = self._facility(facility_id)
        start_at, end_at = parse_datetime(start_at), parse_datetime(end_at)
        if start_at <= self.now_fn():
            raise DomainError("Search for a date and time in the future.")
        if end_at <= start_at:
            raise DomainError("End time must be after start time.")
        try:
            minimum_capacity = int(minimum_capacity)
        except (ValueError, TypeError):
            raise DomainError("Enter a whole-number minimum capacity.") from None
        if minimum_capacity < 1:
            raise DomainError("Minimum capacity must be at least 1.")
        if not facility.is_open(start_at, end_at):
            return []
        results = []
        for room in facility.rooms:
            if room.capacity < minimum_capacity:
                continue
            if self._room_is_free(facility_id, room.room_id, start_at, end_at):
                results.append(
                    {
                        "facility_id": facility_id, "facility_name": facility.name,
                        "room_id": room.room_id, "room_name": room.name,
                        "capacity": room.capacity,
                    }
                )
        return results

    def _room_is_free(self, facility_id, room_id, start_at, end_at, ignore_id=None):
        return not any(
            r.reservation_id != ignore_id
            and r.facility_id == facility_id
            and r.room_id == room_id
            and r.status in HELD_STATUSES
            and start_at < r.end_at
            and end_at > r.start_at
            for r in self.state["reservations"]
        )

    @synchronized
    def create_reservation(self, user_id, payload):
        user = self._user(user_id)
        if not user.is_authorized("reserve"):
            raise DomainError("Your account cannot submit reservations.")
        facility = self._facility(payload.get("facility_id"))
        room_id = str(payload.get("room_id") or "")
        room = next((r for r in facility.rooms if r.room_id == room_id), None)
        if room is None:
            raise DomainError("Choose a room in the selected facility.")
        title = str(payload.get("event_title") or "").strip()
        if not title or len(title) > 120:
            raise DomainError("Event title is required and must be 120 characters or fewer.")
        start_at, end_at = parse_datetime(payload.get("start_at")), parse_datetime(payload.get("end_at"))
        if start_at <= self.now_fn():
            raise DomainError("Choose a start time in the future.")
        if end_at <= start_at:
            raise DomainError("End time must be after start time.")
        if not facility.is_open(start_at, end_at):
            raise DomainError(
                f"Choose a time within facility hours ({facility.open_minutes // 60:02d}:"
                f"{facility.open_minutes % 60:02d}–{facility.close_minutes // 60:02d}:"
                f"{facility.close_minutes % 60:02d}) on one day."
            )
        try:
            attendance = int(payload.get("expected_attendance"))
        except (ValueError, TypeError):
            raise DomainError("Expected attendance must be a whole number.") from None
        if attendance < 1:
            raise DomainError("Expected attendance must be at least 1.")
        if attendance > room.capacity:
            raise DomainError(f"Attendance exceeds this room's capacity of {room.capacity}.")
        with self._lock:
            if not self._room_is_free(facility.facility_id, room_id, start_at, end_at):
                raise DomainError("That room is already requested or booked for this time.")
            reservation = Reservation(
                f"R-{uuid.uuid4().hex[:8].upper()}", user_id, facility.facility_id, room_id,
                title, start_at, end_at, attendance,
            )
            self.state["reservations"].append(reservation)
            self._notify(user_id, f"{title} was submitted and is waiting for approval.")
            self._save()
        return self.public_reservation(reservation)

    @synchronized
    def decide_reservation(self, reviewer_id, reservation_id, decision, comments=""):
        reviewer = self._user(reviewer_id)
        if not reviewer.is_authorized("approve"):
            raise DomainError("Only an event approver or system administrator can review requests.")
        decision = str(decision or "").lower()
        if decision not in {"approve", "reject"}:
            raise DomainError("Choose approve or reject.")
        with self._lock:
            reservation = self._reservation(reservation_id)
            if reservation.status != ReservationStatus.PENDING:
                raise DomainError("Only pending requests can be reviewed.")
            outcome = ApprovalOutcome.APPROVED if decision == "approve" else ApprovalOutcome.REJECTED
            reservation.status = (
                ReservationStatus.APPROVED if decision == "approve" else ReservationStatus.REJECTED
            )
            reservation.approvals.append(
                Approval(outcome, self.now_fn(), reviewer_id, str(comments or "").strip()[:300])
            )
            self._notify(
                reservation.user_id,
                f"{reservation.event_title} was {decision}d by {reviewer.name}."
                if decision == "approve"
                else f"{reservation.event_title} was rejected by {reviewer.name}.",
            )
            self._save()
        return self.public_reservation(reservation)

    @synchronized
    def add_support_request(self, user_id, reservation_id, support_type, details):
        with self._lock:
            reservation = self._reservation(reservation_id)
            if reservation.user_id != user_id:
                raise DomainError("You can only add support to your own reservation.")
            if reservation.status not in {ReservationStatus.PENDING, ReservationStatus.APPROVED}:
                raise DomainError("Support can only be added to pending or approved reservations.")
            try:
                support_type = SupportType[str(support_type).upper()]
            except KeyError:
                raise DomainError("Choose equipment, security, or event support.") from None
            details = str(details or "").strip()
            if not details or len(details) > 300:
                raise DomainError("Describe the request (300 characters or fewer).")
            reservation.support_requests.append(
                SupportRequest(f"S-{uuid.uuid4().hex[:8].upper()}", support_type, details, self.now_fn())
            )
            self._save()
        return self.public_reservation(reservation)

    @synchronized
    def cancel_reservation(self, user_id, reservation_id):
        with self._lock:
            reservation = self._reservation(reservation_id)
            if reservation.user_id != user_id:
                raise DomainError("You can only cancel your own reservation.")
            if reservation.status not in {ReservationStatus.PENDING, ReservationStatus.APPROVED}:
                raise DomainError("Only pending or approved reservations can be cancelled.")
            reservation.status = ReservationStatus.CANCELLED
            self._notify(user_id, f"{reservation.event_title} was cancelled.")
            self._save()
        return self.public_reservation(reservation)

    @synchronized
    def usage_report(self, user_id, facility_id, start_at, end_at):
        user = self._user(user_id)
        if not user.is_authorized("report"):
            raise DomainError("Only an event approver or system administrator can view reports.")
        facility = self._facility(facility_id)
        start_at, end_at = parse_datetime(start_at), parse_datetime(end_at)
        if end_at <= start_at:
            raise DomainError("Report end must be after its start.")
        matches = [
            self.public_reservation(r)
            for r in self.state["reservations"]
            if r.facility_id == facility.facility_id
            and r.start_at < end_at
            and r.end_at > start_at
        ]
        return sorted(matches, key=lambda r: r["start_at"])

    @synchronized
    def update_facility_hours(self, user_id, facility_id, open_time, close_time):
        user = self._user(user_id)
        if not user.is_authorized("manage_facility"):
            raise DomainError("Only an event approver or system administrator can change hours.")
        facility = self._facility(facility_id)
        try:
            opening = datetime.strptime(open_time, "%H:%M")
            closing = datetime.strptime(close_time, "%H:%M")
        except (TypeError, ValueError):
            raise DomainError("Use 24-hour HH:MM times.") from None
        open_minutes = opening.hour * 60 + opening.minute
        close_minutes = closing.hour * 60 + closing.minute
        if close_minutes <= open_minutes:
            raise DomainError("Closing time must be after opening time.")
        affected = [
            r for r in self.state["reservations"]
            if r.facility_id == facility_id and r.status in HELD_STATUSES
            and not (
                r.start_at.hour * 60 + r.start_at.minute >= open_minutes
                and r.end_at.hour * 60 + r.end_at.minute <= close_minutes
            )
        ]
        if affected:
            raise DomainError(
                "Hours cannot change because active reservations would fall outside them. "
                "Resolve those bookings first."
            )
        with self._lock:
            facility.open_minutes, facility.close_minutes = open_minutes, close_minutes
            self._save()
        return self.list_facilities()
