from enums import ReservationStatus, Role
from datetime import datetime

# from services import NotificationService # CIRCULAR

ALL_ROLES = frozenset(Role)
REVIEWER_ROLES = frozenset({Role.EVENT_APPROVER, Role.SYSTEM_ADMINISTRATOR})
PERMISSIONS = {
    "approve": REVIEWER_ROLES,
    "reject": REVIEWER_ROLES,
    "reserve": ALL_ROLES,
    "edit": ALL_ROLES,
    "cancel": ALL_ROLES,
    "request_support": ALL_ROLES,
}

# user using the system. role decides what they're allowed to do.
class User:
    # store details. reservations & approvals should start empty.
    def __init__(self, user_id, name, email, role):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.role = role  # a role
        self.reservations = []  # reservations this user submitted
        self.approvals = []  # approvals this user made as a reviewer
        self.logged_in = False

    # sign up a new user so they can log in later
    # main.py should save this to users.json after registering
    def register(self):
        if not self.name.strip():
            raise ValueError("Name cannot be empty.")
        if "@" not in self.email or "." not in self.email.split("@")[-1]:
            raise ValueError("Email must look like name@campus.edu.")
        if not isinstance(self.role, Role):
            raise ValueError("Pick one of the listed roles.")

    # log the user in. True if worked, False if not
    def login(self):
        if self.logged_in:
            return False  # already logged in
        self.logged_in = True
        return True

    # log user out (program goes back to start menu)
    def logout(self):
        self.logged_in = False

    # check if user's role is allowed to do an action like "approve". return bool.
    # unknown actions are denied so a typo can't accidentaly grant access
    def is_authorized(self, action):
        return self.role in PERMISSIONS.get(action, frozenset())

    # return approved bookings that haven't started yet.
    def view_upcoming_events(self, now=None):
        now = now or datetime.now()
        upcoming = [
            r for r in self.reservations
            if r.status == ReservationStatus.APPROVED and r.start_at and r.start_at > now
        ]
        return sorted(upcoming, key=lambda r: r.start_at)


# building that contains rooms. owns opening & closing hours.
class Facility:
    # store facility details. hours should be unset when started and rooms all empty.
    def __init__(self, facility_id, name, location):
        self.facility_id = facility_id
        self.name = name
        self.location = location
        self._open_at = None  # private, set with set_hours()
        self._close_at = None  # private, set with set_hours()
        self.rooms = []  # rooms in this facility

    # check if facility is open for the whole time from start_at to end_at
    def is_available(self, start_at, end_at):
        begin_time = start_at.hour + start_at.minute / 60
        end_time = end_at.hour + end_at.minute / 60
        if begin_time < self._open_at:
            return False
        if end_time > self._close_at:
            return False
        return True

    # set the facility's opening/closing time.
    def set_hours(self, open_at, close_at):
        self._open_at = open_at
        self._close_at = close_at

    # search for rooms that are free from start_at to end_at,
    # fit at least min_capacity of people
    # and are at the given location.
    def find_available_rooms(self, start_at, end_at, min_capacity):
        available_rooms = []
        if  not self.is_available(start_at, end_at):
            return []
        for room in self.rooms:
            if not room.is_available(start_at, end_at):
                continue
            if room.capacity < min_capacity:
                continue
            available_rooms.append(room)

        return available_rooms

    # return facility's bookings between start_at and end_at
    def generate_usage_report(self, start_at, end_at):
        # QUESTION_LE Should 'generate_usage_report be renamed something else?
        # Because right now it's just returning the list of reservations.
        reservations = []
        for room in self.rooms:
            for reservation in room.reservations:
                if reservation.start_at < end_at and reservation.end_at > start_at:
                    reservations.append(reservation)


        return reservations

# physical room in a facility. never stops existing when booking ends,
# cycles back to Available.
class Room:
    # store details. reservations start empty.
    def __init__(self, room_id, capacity):
        self.room_id = room_id
        self.capacity = capacity
        self.reservations = []  # reservations for this room

    # check that no booking holds this room from start_at to end_at.
    # a booking holds the room if it's Pending, Approved or InProgress
    # and its times overlap. this is where we prevent double booking.
    def is_available(self, start_at, end_at):
        held_states = [
            ReservationStatus.PENDING,
            ReservationStatus.APPROVED,
            ReservationStatus.IN_PROGRESS,
        ]

        for reservation in self.reservations:
            if start_at < reservation.end_at and end_at > reservation.start_at:
                if reservation.status in held_states:
                    return False

        return True

    # find this room's Approved reservations whose start time has arrived
    # and move them to InProgress (Reserved -> In_Use).
    def start_booking(self):
        now = datetime.now()

        for reservation in self.reservations:
            if not reservation.status == ReservationStatus.APPROVED:
                continue
            if not reservation.start_at <= now:
                continue
            reservation.status = ReservationStatus.IN_PROGRESS

    # find this room's InProgress reservations whose end time has passed
    # and move them to Completed (slot goes back to Available).
    def end_booking(self):
        now = datetime.now()

        for reservation in self.reservations:
            if not reservation.status == ReservationStatus.IN_PROGRESS:
                continue
            if not reservation.end_at <= now:
                continue
            reservation.status = ReservationStatus.COMPLETED
        


# booking record. status track are here
class Reservation:
    # create a new reservation for a room. starts as Draft
    # details default to None so a Draft can be incomplete. 
    # QUESTION-LE: Shouldn't reservation keep track of the user,
    # to be able to send them notifications?
    # TODO Add user as member of Reservation
    def __init__(
        self,
        reservation_id,
        room,
        user=None,
        notifier=None,
        event_title=None,
        start_at=None,
        end_at=None,
        expected_attendance=None,
    ):
        self.reservation_id = reservation_id
        self.room = room  # the Room being reserved
        self.user = user
        self.notifier = notifier
        self.event_title = event_title
        self.start_at = start_at
        self.end_at = end_at
        self.expected_attendance = expected_attendance
        self.status = ReservationStatus.DRAFT  # private, starts in draft
        self.approvals = []  # approval history
        self.support_requests = []  # SupportRequests for this reservation

    # submit the request. if details are complete and room is free:
    # Draft -> Pending and user is notified.
    # if not, it stays Draft and show_validation_errors() runs.
    def send_request(self, start_at, end_at, event_title):
        if self.status != ReservationStatus.DRAFT: return

        self.start_at = start_at
        self.end_at = end_at
        self.event_title = event_title

        if not self.is_complete() or not self.check_availability():
            self.show_validation_errors()
            raise Exception("Incomplete reservations cannot be submitted for approval.")

        if self not in self.room.reservations:
            self.room.reservations.append(self)
        
        self.status = ReservationStatus.PENDING
        if self.notifier and self.user:
            self.notifier.notify_user(
                self.user,
                (f"Your reservation: {event_title} ({self.reservation_id}) in "
                f"{self.room} was submitted for approval.")
            )

    # change booking details. editing a Draft keeps it a Draft.
    # editing an Approved booking frees the room and sends it back to Draft
    # so it has to be submitted and Approved again.
    def edit(self, event_title=None, start_at=None, end_at=None, expected_attendance=None):
        valid_states = [
            ReservationStatus.DRAFT, ReservationStatus.PENDING, ReservationStatus.APPROVED
        ]

        if self.status not in valid_states:
            raise Exception("Invalid reservation state to edit")

        self.event_title = event_title if event_title is not None else self.event_title
        self.start_at = start_at if start_at is not None else self.start_at
        self.end_at = end_at if end_at is not None else self.end_at
        self.expected_attendance = expected_attendance if expected_attendance is not None else self.expected_attendance

        if self.status != ReservationStatus.DRAFT:
            self.status = ReservationStatus.DRAFT
            if self in self.room.reservations:
                self.room.reservations.remove(self)

    # check that room is free for this reservation's time. return bool
    def check_availability(self):
        if self.start_at is None or self.end_at is None:
            return False

        if self.room.is_available(self.start_at, self.end_at):
            return True

        return False

    # cancel a Pending/Approved booking: status goes to Cancelled.
    # room is freed, user notified.
    def request_cancel(self):
        if self.status not in [ReservationStatus.PENDING, ReservationStatus.APPROVED]:
            return

        self.status = ReservationStatus.CANCELLED
        if self.notifier is not None and self.user is not None:
            self.notifier.notify_user(
                self.user,
                f"Reservation {self.event_title} was cancelled."
            )

    # admin approves the request: Pending -> Approved
    # (the time slot now reads as Reserved). user notified.
    def approve_request(self):
        if self.status != ReservationStatus.PENDING:
            return

        self.status = ReservationStatus.APPROVED

        if self.notifier is not None and self.user is not None:
            self.notifier.notify_user(
                self.user,
                f"Booking {self.event_title} for room {self.room.room_id} was approved."
            )

    # admin rejects request: Pending -> Rejected
    # (this frees the time slot). user notified.
    def reject_request(self):
        if self.status != ReservationStatus.PENDING:
            return

        self.status = ReservationStatus.REJECTED

        if self.notifier is not None and self.user is not None:
            self.notifier.notify_user(
                self.user,
                f"Booking {self.event_title} for room {self.room.room_id} was rejected."
            )

    # throw away a draft that wasn't submitted? unsure if needed.
    def delete(self):
        if self.status != ReservationStatus.DRAFT:
            return

        if self in self.room.reservations:
            self.room.reservations.remove(self)

    # return current status
    def get_status(self):
        return self.status

    # check that all required details are filled in. return bool
    def is_complete(self):
        check = True

        try:
            check = True if len(str(self.event_title).strip()) > 0 else False
        except:
            return False

        check = check if self.start_at is not None else False
        check = check if self.end_at is not None else False
        check = check if self.expected_attendance is not None else False

        return check

    # tell user whats wrong after a failed submit (missing details or room taken)
    def show_validation_errors(self):
        errors = []

        try:
            if len(str(self.event_title).strip()) < 1:
                raise Exception()
        except:
            errors.append("Event title missing.")

        if self.start_at is None:
            errors.append("Start time missing.")

        if self.end_at is None:
            errors.append("End time missing.")

        if self.expected_attendance is None:
            errors.append("Expected attendance missing.")

        if self.start_at is not None and self.end_at is not None:
            if self.end_at <= self.start_at:
                errors.append("End time must be after start time.")
            if not self.check_availability():
                errors.append("Room unavailable.")
        
        return errors

    # attach an equipment, security, or event support request to booking.
    def request_support(self, support_type, details):
        support_request = SupportRequest(
            f"{self.reservation_id}-{len(self.support_requests)}",
            support_type,
            details
        )
        self.support_requests.append(support_request)
        return support_request

    # remind user about upcoming Approved booking.
    def send_reminder(self, user, notifier):
        notifier.notify_user(user, f"Reminder: {self.event_title} " f"in room {self.room.room_id} " f"on {self.start_at:%Y-%m-%d} " f"at {self.start_at:%H:%M}.")


# one approve/reject decision on a reservation. 
# belongs to a reservation and can't exist without it.
class Approval:
    # record decision, when it was made, any comments, etc. 
    def __init__(self, decision, decided_at, comments, reviewer):
        self.decision = decision  # an ApprovalOutcome
        self.decided_at = decided_at
        self.comments = comments
        self.reviewer = reviewer  # the user who made the decision


# one supportrequest attached to a reservation.
# just a record of what was asked for
class SupportRequest:
    # record request type and details (like "projector")
    def __init__(self, support_request_id, support_type, details):
        self.support_request_id = support_request_id
        self.support_type = support_type  # a SupportType
        self.details = details
