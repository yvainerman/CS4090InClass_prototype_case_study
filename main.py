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
    pass


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
    pass


# start and end events based on the clock. call this right before showing any
# menu, so statuses are always up to date. for every booking in every room:
#   - Approved and the current time is at or after its start -> start it (In Progress)
#   - In Progress and the current time is at or after its end -> end it (Completed)
# use Room.start_booking(), end_booking()
def update_events(facilities):
    pass


# PIPELINE START HERE


# load users, create the facilities and the NotificationService, then loop:
#   1. Login
#   2. Register
#   3. Exit
# after login, users who can approve (user.is_authorized("approve")) go to
# show_admin_menu(); everyone else goes to show_user_menu().
# call update_events(facilities) each time before showing this menu.
def main():
    pass


# ask for an email and return the matching user (None if DNE)
# use User.login()
def login_screen(users):
    pass


# ask for name, email and role, create the User, and save it to users.json.
# use User.register(), save_users()
def register_screen(users):
    pass


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
    pass


# ask for date, start/end time, minimum capacity and location to print free rooms
# use Facility.find_available_rooms()
def search_rooms(facilities):
    pass


# let the user pick a facility and print its location, hours and rooms.
def view_facility_details(facilities):
    pass


# pick a room, create a Draft reservation, fill in its details, and submit it.
# if submitting fails, show the errors and let the user try again or discard.
# use Reservation.send_request(), is_complete(), check_availability(),
# show_validation_errors(), delete(), Room.is_available()
def reserve_room(user, facilities, notifier):
    pass


# pick one of the user's Approved bookings, change its details, and resubmit it
# (it goes back to Draft and needs approval again).
# use Reservation.edit(), send_request()
def edit_booking(user, notifier):
    pass


# pick one of the user's Pending or Approved bookings and cancel it.
# use Reservation.request_cancel()
def cancel_booking(user, notifier):
    pass


# print each of the user's bookings with its status and any support requests.
# use Reservation.get_status()
def view_my_bookings(user):
    pass


# pick one of the user's Pending or Approved bookings, pick a type
#   1. Equipment
#   2. Security
#   3. Event Support
# and type the details (for example "projector and 2 microphones").
# it is saved on that booking as a SupportRequest.
# use Reservation.request_support()
def request_support(user):
    pass


# print the user's approved bookings that haven't happened yet.
# use User.view_upcoming_events()
def show_upcoming_events(user):
    pass


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
    pass


# show each Pending request (with support requests) and let the admin approve or reject it
# notify user who made booking of this change.
# use Reservation.approve_request(), reject_request(), NotificationService.notify_user()
def review_pending_requests(admin, users, notifier):
    pass


# pick a facility and set its opening and closing time.
# use Facility.set_hours(), Facility.is_available()
def set_facility_hours(facilities):
    pass


# send a reminder for every Approved booking.
# use Reservation.send_reminder()
def send_reminders(users, notifier):
    pass


# pick a facility and a date range, and print the bookings in that range.
# use Facility.generate_usage_report()
def show_usage_report(facilities):
    pass


if __name__ == "__main__":
    main()