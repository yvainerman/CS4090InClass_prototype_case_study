#!/bin/python3
# console program for the Smart Campus Event & Facility Booking System.
# drafted some base imports here but these may change as you fill this out

from datetime import datetime
from enums import Role, ReservationStatus, SupportType
from models import User, Facility, Room, Reservation
from services import NotificationService, load_users, save_users

# helpers


# print the options as a list (1, 2, 3) and return the number the user types.
# prompt user until they type a valid option
def get_menu_choice(options):
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option}")
    while True:
        text = input("Choose an option: ").strip()
        if text.isdigit() and 1 <= int(text) <= len(options):
            return int(text)
        print(f"Enter a number from 1 to {len(options)}.")


# ask for a date and time (prompt for a consistent format) and return a datetime.
# so now u can call start_at = get_datetime("Start time") for example
def get_datetime(prompt):
    while True:
        text = input(prompt + " (YYYY-MM-DD HH:MM): ")
        try:
            return datetime.strptime(text, "%Y-%m-%d %H:%M")
        except ValueError:
            print("Invalid date/time. Example: 2026-10-12 14:30")


# build the starting facilities and their rooms (we should hard-code these)
# probs one facility for now
def create_sample_facilities():
    library = Facility("F001", "Curtis Laws Wilson Library", "North Campus")
    library.set_hours(8, 22) # open 8:00 to 22:00

    library.rooms.append(Room("G102", 20))  # small meeting room
    library.rooms.append(Room("G201", 40))  # classroom
    library.rooms.append(Room("G203", 120))  # event hall

    return [library]


# collect every reservation from every user (for admin screens).
def get_all_reservations(users):
    reservations = []
    for user in users:
        for reservation in user.reservations:
            reservations.append(reservation)
    return reservations


# start and end events based on the clock. call this right before showing any
# menu, so statuses are always up to date. for every booking in every room:
#   - Approved and the current time is at or after its start -> start it (In Progress)
#   - In Progress and the current time is at or after its end -> end it (Completed)
# use Room.start_booking(), end_booking()
def update_events(facilities):
    for facility in facilities:
        for room in facility.rooms:
            room.start_booking()
            room.end_booking()


# PIPELINE START HERE


# load users, create the facilities and the NotificationService, then loop:
#   1. Login
#   2. Register
#   3. Exit
# after login, users who can approve (user.is_authorized("approve")) go to
# show_admin_menu(); everyone else goes to show_user_menu().
# call update_events(facilities) each time before showing this menu.
def main():
    facilities = create_sample_facilities()
    users = load_users(facilities)  # needs facilities to relink saved bookings to rooms
    notifier = NotificationService()
 
    while True:
        update_events(facilities)
        print("\nSmart Campus Event & Facility Booking")
        choice = get_menu_choice(["Login", "Register", "Exit"])
 
        if choice == 1:
            user = login_screen(users)
            if user is None:
                continue
            if user.is_authorized("approve"):
                show_admin_menu(user, users, facilities, notifier)
            else:
                show_user_menu(user, facilities, notifier)
        elif choice == 2:
            register_screen(users)
        else:
            save_users(users)
            print("Exited")
            return


# ask for an email and return the matching user (None if DNE)
# use User.login()
def login_screen(users):
    email = input("Email: ").strip().lower()
    user = next((u for u in users if u.email.lower() ==email), None)
    if user is None:
        print("No account with that email. Choose Register to create one")
        return None
    if not user.login():
        print(f"{user.name} is already logged in.")
        return None
    print(f"Welcome, {user.name} ({user.role.value}).")
    return user


# ask for name, email and role, create the User, and save it to users.json.
# use User.register(), save_users()
def register_screen(users):
    name = input("Name: ").strip()
    email = input("Email: ").strip().lower()
    if any(u.email.lower() == email for u in users):
        print("An account with that email already exists.")
        return None
 
    roles = list(Role)
    print("Role:")
    role = roles[get_menu_choice([r.value for r in roles]) - 1]
 
    user = User(next_user_id(users), name, email, role)
    try:
        user.register()
    except ValueError as error:
        print(f"Registration failed: {error}")
        return None
 
    users.append(user)
    save_users(users)
    print(f"Registered {user.name} as {user.role.value}. You can log in now.")
    return user

# ids like U1, U2, etc that never repeat even after users.json is reloaded
def next_user_id(users):
    numbers = [int(u.user_id[1:]) for u in users if u.user_id[1:].isdigit()]
    return f"U{max(numbers, default=0) + 1}"


# REGULAR USER (submits bookings) SCREENS


# loop this until the user picks Logout:
#   1. Search for a Room
#   2. View Facility Details
#   3. Reserve a Room
#   4. Edit a Booking
#   5. Cancel a Booking
#   6. View My Bookings
#   7. Request Equipment / Security / Event Support
#   8. View Upcoming Events
#   9. Logout
# use User.logout()
# call update_events(facilities) each time before showing this menu.
def show_user_menu(user, facilities, notifier):
    actions = [
        ("Search for a Room", lambda: search_rooms(facilities)),
        ("View Facility Details", lambda: view_facility_details(facilities)),
        ("Reserve a Room", lambda: reserve_room(user, facilities, notifier)),
        ("Edit a Booking", lambda: edit_booking(user, notifier)),
        ("Cancel a Booking", lambda: cancel_booking(user, notifier)),
        ("View My Bookings", lambda: view_my_bookings(user)),
        ("Request Equipment / Security / Event Support", lambda: request_support(user)),
        ("View Upcoming Events", lambda: show_upcoming_events(user)),
    ]
    run_menu(f"{user.name} ({user.role.value})", actions, user, facilities)

# ask for date, start/end time, minimum capacity and location to print free rooms
# use Facility.find_available_rooms()
def search_rooms(facilities):
    start_at = get_datetime("Please enter the starting date and time of your event")
    end_at = get_datetime("Please enter the ending date and time of your event")
    minimum_capacity = int(input("Please enter the minimum capacity you need for your reservation: "))
    building_name = input("Please enter the building name you are trying to reserve a room in: ").strip().lower()

    building_found = False
    rooms_found = False

    for facility in facilities:
        if facility.name.lower() != building_name:
            continue

        building_found = True
        available_rooms = facility.find_available_rooms(start_at, end_at, minimum_capacity)

        for room in available_rooms:
            print(f"{facility.name}: Room {room.room_id}, capacity {room.capacity}")
            rooms_found = True

    if not building_found:
        print("No building with that name found.")
    elif not rooms_found:
        print("No available rooms matching your requirements found.")


# let the user pick a facility and print its location, hours and rooms.
def view_facility_details(facilities):
    choice = get_menu_choice([facility.name for facility in facilities])
    facility: Facility
    facility = facilities[choice - 1]

    print(f"{facility.name} - {facility.location}")
    hours = facility.get_hours_formatted()
    print(f"Hours: {hours[0]} to {hours[1]}")

    for room in facility.rooms:
        print(f"Room {room.room_id}: capacity {room.capacity}")


# pick a room, create a Draft reservation, fill in its details, and submit it.
# if submitting fails, show the errors and let the user try again or discard.
# use Reservation.send_request(), is_complete(), check_availability(),
# show_validation_errors(), delete(), Room.is_available()
def reserve_room(user, facilities, notifier):
    rooms = []
    for facility in facilities:
        r = [room for room in facility.rooms]
        rooms.append((facility, r))

    pick = get_menu_choice([facility.name for facility, _ in rooms] + ["Back"])
    if pick == len(rooms) + 1: return
    facility: Facility
    facility, facility_rooms = rooms[pick - 1]

    labels = [f"Room {room.room_id} ({room.capacity})" for room in facility_rooms]
    pick = get_menu_choice(labels + ["Back"])
    if pick == len(facility_rooms) + 1: return
    room = facility_rooms[pick - 1]

    numbers = []
    for _, n in rooms:
        for existing in n:
            for reservation in existing.reservations:
                if reservation.reservation_id.isdigit():
                    numbers.append(int(reservation.reservation_id))

    numbers = max(numbers,default=0) + 1
    reservation = Reservation(f"{numbers}", room, user=user, notifier=notifier)
    user.reservations.append(reservation)
    room.reservations.append(reservation)

    while True:
        title = input("Event title: ").strip()
        start_at = get_datetime("Start time")
        end_at = get_datetime("End time")
        attendance_text = input("Expected attendance: ").strip()
        attendance = int(attendance_text) if attendance_text.isdigit() else None
        reservation.edit(event_title=title, start_at=start_at, end_at=end_at, expected_attendance=attendance)
        errors = []
        if attendance_text and attendance is None:
            errors.append("Expected attendance must be numerical.")
        if attendance is not None and attendance > room.capacity:
            errors.append("Expected attendance is over room capacity.")
        if end_at > start_at and not facility.is_available(start_at, end_at):
            errors.append(f"{facility.name} is closed during requested hours.")

        if not errors:
            try:
                reservation.send_request(start_at, end_at, title)
                return
            except Exception as e:
                errors.append(str(e))

        errors += reservation.show_validation_errors()
        print("Failure to submit reservation:")
        for error in errors:
            print(f"  - {error}")

        if get_menu_choice(["Edit", "Discard"]) == 2:
            reservation.delete()
            user.reservations.remove(reservation)
            print("Discarded.")
            return

# pick one of the user's Approved bookings, change its details, and resubmit it
# (it goes back to Draft and needs approval again).
# use Reservation.edit(), send_request()
def edit_booking(user, notifier):
    states_editable = [
        ReservationStatus.DRAFT, ReservationStatus.PENDING, ReservationStatus.APPROVED
    ]

    approved = []
    for reservation in user.reservations:
        if reservation.get_status() in states_editable:
            approved.append(reservation)

    if len(approved) == 0:
        print("You have no approved reservations to edit.")
        return

    menu = [f"{reservation.event_title} - in {reservation.room.room_id}" 
            for reservation in approved]
    pick = get_menu_choice(menu + ["Back"])
    if pick == len(menu) + 1:
        return
    reservation: Reservation = approved[pick - 1]
    room: Room = reservation.room

    while True:
        errors = []

        title = input(f"New title or leave empty: ").strip()
        if len(title) == 0: title = reservation.event_title
        start_at = get_datetime("New start time")
        end_at = get_datetime("New end time")
        attendance = input(f"New expected attendance or leave empty: ").strip()
        if len(attendance) == 0: attendance = reservation.expected_attendance
        elif attendance.isdigit():
            attendance = int(attendance)
        else:
            errors.append("Attendance must be a number.")

        if end_at <= start_at:
            errors.append("End time cannot be before start time.")
        if attendance > room.capacity:
            errors.append(f"Expected attendance exceeds room capacity {room.capacity}.")
        for other in room.reservations:
            if other is reservation or other.get_status() not in [
                ReservationStatus.PENDING,
                ReservationStatus.APPROVED,
                ReservationStatus.IN_PROGRESS
            ]:
                continue

            if start_at < other.end_at and end_at > other.start_at:
                errors.append("Room is occupied at the time.")
                break

        if not errors:
            break

        print("Failed to make change.")
        for error in errors:
            print(f"  - {error}")
        if get_menu_choice(["Edit", "Keep original booking"]) == 2:
            return

    reservation.user = user
    reservation.notifier = notifier
    try:
        reservation.edit(
            event_title=title, 
            start_at=start_at, 
            end_at=end_at, 
            expected_attendance=attendance
        )
    except Exception as e:
        print(str(e))
        return

    try:
        reservation.send_request(start_at, end_at, title)
        print("Updated successfully. Requesting approval.")
    except Exception as e:
        print(str(e))
        for error in reservation.show_validation_errors():
            print(f"  - {error}")


# pick one of the user's Pending or Approved bookings and cancel it.
# use Reservation.request_cancel()
def cancel_booking(user, notifier):
    cancellable = []
    for reservation in user.reservations:
        if reservation.get_status() in [ReservationStatus.PENDING, ReservationStatus.APPROVED]:
            cancellable.append(reservation)
    if not cancellable:
        print("You have nothing to cancel.")
        return

    choices = [f"{res.event_title} - {res.room.room_id}" for res in cancellable]
    pick = get_menu_choice(choices + ["Back"])
    if pick == len(choices) + 1:
        return

    reservation: Reservation = cancellable[pick-1]
    reservation.request_cancel()


# print each of the user's bookings with its status and any support requests.
# use Reservation.get_status()
def view_my_bookings(user):
    if not user.reservations:
        print("You have no bookings.")
        return

    res: Reservation
    for res in user.reservations:
        print(f"\n{res.reservation_id}: {res.event_title or 'untitled'}")
        print(f"  Room: {res.room.room_id}")
        print(f"  Start: {res.start_at or 'No time listed'}")
        print(f"  End: {res.end_at or 'No time listed'}")
        print(f"  Attendance: {res.expected_attendance or 'No time listed'}")
        print(f"  Status: {res.get_status().value}")
        if res.support_requests:
            for sup in res.support_requests:
                print(f"  Support Request: {sup.support_type.value} - {sup.details}")
        else:
            print(f"  Support: None requested")


# pick one of the user's Pending or Approved bookings, pick a type
#   1. Equipment
#   2. Security
#   3. Event Support
# and type the details (for example "projector and 2 microphones").
# it is saved on that booking as a SupportRequest.
# use Reservation.request_support()
def request_support(user):
    reses = []
    for reservation in user.reservations:
        if reservation.get_status() in [ReservationStatus.PENDING, ReservationStatus.APPROVED]:
            reses.append(reservation)
    if not reses:
        print("You have nothing to cancel.")
        return

    choices = [f"{res.event_title} - {res.room.room_id}" for res in reses]
    pick = get_menu_choice(choices + ["Back"])
    if pick == len(choices) + 1:
        return

    reservation: Reservation = reses[pick-1]

    _types = list(SupportType)
    print("Requested support type:")
    support_type = _types[get_menu_choice([typ.value for typ in _types]) - 1]

    details = input("Details (for example 'projector and 2 microphones'): ").strip()
    while not details:
        details = input("Please enter details: ").strip()

    reservation.request_support(support_type, details)
    print(f"A request for {support_type.value} was made for event \"{reservation.event_title}\".")


# print the user's approved bookings that haven't happened yet.
# use User.view_upcoming_events()
def show_upcoming_events(user):
    events = user.view_upcoming_events()
    if not events:
        print("You have no upcoming approved events.")
        return
    print("Your upcoming events:")
    for r in events:
        print(f"  {r.start_at:%Y-%m-%d %H:%M}-{r.end_at:%H:%M}  {r.event_title}  "
              f"(room {r.room.room_id}, {r.expected_attendance} people)")


# ADMIN (approves bookings) SCREENS


# loop this until the admin picks Logout:
#   1. Review Pending Requests
#   2. Set Facility Hours
#   3. Send Reminders
#   4. Usage Report
#   5. Logout
# use User.logout()
# call update_events(facilities) each time before showing this menu.
def show_admin_menu(admin, users, facilities, notifier):
    actions = [
        ("Review Pending Requests", lambda: review_pending_requests(admin, users, notifier)),
        ("Set Facility Hours", lambda: set_facility_hours(facilities)),
        ("Send Reminders", lambda: send_reminders(users, notifier)),
        ("Usage Report", lambda: show_usage_report(facilities)),
    ]
    run_menu(f"Admin: {admin.name} ({admin.role.value})", actions, admin, facilities)

# this has it as a shared loop for the user and admin menus so the logout is always the last option
# also it saves after every action
def run_menu(title, actions, user, facilities):
    labels = [label for label, _ in actions] + ["Logout"]
    while True:
        update_events(facilities)
        print(f"\n--- {title} ---")
        choice = get_menu_choice(labels)
        if choice == len(labels):
            user.logout()
            print("Logged out.")
            return
        _, action = actions[choice - 1]
        action()

# show each Pending request (with support requests) and let the admin approve or reject it
# notify user who made booking of this change.
# use Reservation.approve_request(), reject_request(), NotificationService.notify_user()
def review_pending_requests(admin, users, notifier):
    pending_found = False

    user: User
    for user in users:
        reservation: Reservation
        for reservation in user.reservations:
            if reservation.get_status() != ReservationStatus.PENDING:
                continue

            pending_found = True
            print(f"\nRequester: {user.name}")
            print(f"Event: {reservation.event_title}")
            print(f"Room: {reservation.room.room_id}")
            print(f"Start: {reservation.start_at}")
            print(f"End: {reservation.end_at}")
            print(f"Expected attendance: {reservation.expected_attendance}")

            for support in reservation.support_requests:
                print(f"Support: {support.support_type.value}: {support.details}")

            choice = get_menu_choice(["Approve", "Reject", "Skip"])
            if choice == 1:
                reservation.approve_request()
                notifier.notify_user(user, f"Your reservation for {reservation.event_title} was approved.")
            elif choice == 2:
                reservation.reject_request()
                notifier.notify_user(user, f"Your reservation for {reservation.event_title} was rejected.")

    if not pending_found:
        print("No pending requests.") 

# pick a facility and set its opening and closing time.
# use Facility.set_hours(), Facility.is_available()
def set_facility_hours(facilities):
    choice = get_menu_choice([facility.name for facility in facilities])
    facility = facilities[choice - 1]

    opening = datetime.strptime(input("Opening time (HH:MM): ").strip(), "%H:%M")
    closing = datetime.strptime(input("Closing time (HH:MM): ").strip(), "%H:%M")

    open_at = opening.hour + opening.minute / 60
    close_at = closing.hour + closing.minute / 60

    facility.set_hours(open_at, close_at)
    print( f"{facility.name} hours updated to {opening:%H:%M}-{closing:%H:%M}.")



# send a reminder for every Approved booking.
# use Reservation.send_reminder()
def send_reminders(users, notifier):
    now = datetime.now()
    reminders_sent = 0

    for user in users:
        for reservation in user.view_upcoming_events(now):
            reservation.send_reminder(user, notifier)
            reminders_sent += 1

    if reminders_sent == 0:
        print("No upcoming approved bookings to remind users about.")
    else:
        print(f"Sent {reminders_sent} reminder(s).") 


# pick a facility and a date range, and print the bookings in that range.
# use Facility.generate_usage_report()
def show_usage_report(facilities):
    choice = get_menu_choice([facility.name for facility in facilities])
    facility = facilities[choice - 1]

    start_at = get_datetime("Report starting date and time")
    end_at = get_datetime("Report ending date and time")

    reservations = facility.generate_usage_report(start_at, end_at)

    print(f"\nUsage report for {facility.name}")
    for reservation in reservations:
        print(f"\nReservation: {reservation.reservation_id}")
        print(f"Event: {reservation.event_title}")
        print(f"Room: {reservation.room.room_id}")
        print(f"Start: {reservation.start_at:%Y-%m-%d %H:%M}")
        print(f"End: {reservation.end_at:%Y-%m-%d %H:%M}")
        print(f"Expected attendance: {reservation.expected_attendance}")
        print(f"Status: {reservation.status.value}")


if __name__ == "__main__":
    main()
