# things outside our model

import json
from datetime import datetime
from pathlib import Path

from enums import ApprovalOutcome, ReservationStatus, Role, SupportType
from models import Approval, Reservation, SupportRequest, User

USERS_FILE = Path(__file__).parent / "users.json"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"

# sends messages (we can just print these for console)
class NotificationService:
    def notify_user(self, users, content):
        recipients = users if isinstance(users, list) else [users]
        for user in recipients:
            print(f"  [Notification to {user.name} <{user.email}>] {content}")


# read users.json and return a list of User objects.
# return empty if it doesnt exist / is empty 
# facilities is needed so each saved reservation can be linked back to its Room
def load_users(facilities):
    if not USERS_FILE.exists() or USERS_FILE.stat().st_size == 0:
        return []
 
    with USERS_FILE.open(encoding="utf-8") as file:
        data = json.load(file)
 
    rooms_by_id = {room.room_id: room for facility in facilities for room in facility.rooms}
    users = [User(u["user_id"], u["name"], u["email"], Role(u["role"])) for u in data]
    users_by_id = {user.user_id: user for user in users}
 
    # reservations need every user to exist first
    for user, user_data in zip(users, data):
        for res_data in user_data.get("reservations", []):
            room = rooms_by_id.get(res_data["room_id"])
            if room is None:
                print(f"  Warning: skipped reservation {res_data['reservation_id']} "
                      f"(room {res_data['room_id']} no longer exists).")
                continue
            reservation = _reservation_from_dict(res_data, room, users_by_id)
            reservation.requester = user  # who to notify
            user.reservations.append(reservation)
            room.reservations.append(reservation)
 
    return users
 
 
# write to users.json.
# each user's reservations are saved inside that user
def save_users(users):
    data = [
        {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role.value,
            "reservations": [_reservation_to_dict(r) for r in user.reservations],
        }
        for user in users
    ]
    # this justs write to a temp file first so a crash mid-save can't wipe users.json
    temp_file = USERS_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
    temp_file.replace(USERS_FILE)
 
 
# helpers for converting stuff from json file
 
def _to_text(value):
    return value.strftime(DATETIME_FORMAT) if value else None
 
 
def _to_datetime(text):
    return datetime.strptime(text, DATETIME_FORMAT) if text else None
 
 
def _reservation_to_dict(reservation):
    return {
        "reservation_id": reservation.reservation_id,
        "room_id": reservation.room.room_id,
        "event_title": reservation.event_title,
        "start_at": _to_text(reservation.start_at),
        "end_at": _to_text(reservation.end_at),
        "expected_attendance": reservation.expected_attendance,
        "status": reservation.status.value,
        "approvals": [
            {
                "decision": a.decision.value,
                "decided_at": _to_text(a.decided_at),
                "comments": a.comments,
                "reviewer_id": a.reviewer.user_id, 
            }
            for a in reservation.approvals
        ],
        "support_requests": [
            {
                "support_request_id": s.support_request_id,
                "support_type": s.support_type.value,
                "details": s.details,
            }
            for s in reservation.support_requests
        ],
    }
 
 
def _reservation_from_dict(data, room, users_by_id):
    reservation = Reservation(
        data["reservation_id"],
        room,
        data["event_title"],
        _to_datetime(data["start_at"]),
        _to_datetime(data["end_at"]),
        data["expected_attendance"],
    )
    reservation.status = ReservationStatus(data["status"])
 
    for a in data.get("approvals", []):
        reviewer = users_by_id[a["reviewer_id"]]
        approval = Approval(ApprovalOutcome(a["decision"]), _to_datetime(a["decided_at"]),
                            a["comments"], reviewer)
        reservation.approvals.append(approval)
        reviewer.approvals.append(approval)
 
    for s in data.get("support_requests", []):
        reservation.support_requests.append(
            SupportRequest(s["support_request_id"], SupportType(s["support_type"]), s["details"]))
 
    return reservation