from enums import ReservationStatus

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

    # sign up a new user so they can log in later
    # main.py should save this to users.json after registering
    def register(self):
        pass

    # log the user in. True if worked, False if not
    def login(self):
        pass

    # log user out (program goes back to start menu)
    def logout(self):
        pass

    # check if user's role is allowed to do an action like "approve". return bool.
    def is_authorized(self, action):
        pass

    # return approved bookings that haven't started yet.
    def view_upcoming_events(self):
        pass


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
        pass

    # set the facility's opening/closing time.
    def set_hours(self, open_at, close_at):
        pass

    # search for rooms that are free from start_at to end_at,
    # fit at least min_capacity of people
    # and are at the given location.
    # static: not tied to one facility, so it's called as
    # Facility.find_available_rooms(start_at, end_at, min_capacity, location)
    @staticmethod  # underlined (static) in the class diagram
    def find_available_rooms(start_at, end_at, min_capacity, location):
        pass

    # return facility's bookings between start_at and end_at
    def generate_usage_report(self, start_at, end_at):
        pass


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
        pass

    # find this room's Approved reservations whose start time has arrived
    # and move them to InProgress (Reserved -> In_Use).
    def start_booking(self):
        pass

    # find this room's InProgress reservations whose end time has passed
    # and move them to Completed (slot goes back to Available).
    def end_booking(self):
        pass


# booking record. status track are here
class Reservation:
    # create a new reservation for a room. starts as Draft
    # details default to None so a Draft can be incomplete. 
    def __init__(
        self,
        reservation_id,
        room,
        event_title=None,
        start_at=None,
        end_at=None,
        expected_attendance=None,
    ):
        self.reservation_id = reservation_id
        self.room = room  # the Room being reserved
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
        pass

    # change booking details. editing a Draft keeps it a Draft.
    # editing an Approved booking frees the room and sends it back to Draft
    # so it has to be submitted and Approved again.
    def edit(self):
        pass

    # check that room is free for this reservation's time. return bool
    def check_availability(self):
        pass

    # cancel a Pending/Approved booking: status goes to Cancelled.
    # room is freed, user notified.
    def request_cancel(self):
        pass

    # admin approves the request: Pending -> Approved
    # (the time slot now reads as Reserved). user notified.
    def approve_request(self):
        pass

    # admin rejects request: Pending -> Rejected
    # (this frees the time slot). user notified.
    def reject_request(self):
        pass

    # throw away a draft that wasn't submitted? unsure if needed.
    def delete(self):
        pass

    # return current status
    def get_status(self):
        pass

    # check that all required details are filled in. return bool
    def is_complete(self):
        pass

    # tell user whats wrong after a failed submit (missing details or room taken)
    def show_validation_errors(self):
        pass

    # attach an equipment, security, or event support request to booking.
    def request_support(self, support_type, details):
        pass

    # remind user about upcoming Approved booking.
    def send_reminder(self):
        pass


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