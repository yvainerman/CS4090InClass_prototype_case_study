"""Terminal UI adapter; all booking rules remain in BookingService."""

from getpass import getpass

from services import DomainError


def _read_datetime(prompt):
    return input(f"{prompt} (YYYY-MM-DD HH:MM): ").strip()


def _choose(options, prompt="Choose"):
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {option}")
    answer = input(f"{prompt}: ").strip()
    if not answer.isdigit() or not 1 <= int(answer) <= len(options):
        raise DomainError("Choose one of the listed options.")
    return int(answer) - 1


def _show_reservation(reservation):
    print(
        f"{reservation['event_title']} | {reservation['room_id']} | "
        f"{reservation['start_at'].replace('T', ' ')} | {reservation['status']}"
    )


def _user_actions(service, user_id, facilities):
    print("\n1. Search rooms  2. Request a room  3. My bookings  4. Request support  5. Logout")
    choice = input("Choose: ").strip()
    if choice == "1":
        facility = facilities[_choose([f["name"] for f in facilities], "Facility")]
        start, end = _read_datetime("Start"), _read_datetime("End")
        rooms = service.search_rooms(
            facility["facility_id"], start, end, input("Minimum capacity: ").strip()
        )
        print("\nAvailable rooms:" if rooms else "\nNo rooms match those requirements.")
        for room in rooms:
            print(f"  {room['room_id']} — {room['room_name']} (capacity {room['capacity']})")
    elif choice == "2":
        facility = facilities[_choose([f["name"] for f in facilities], "Facility")]
        room = facility["rooms"][_choose(
            [f"{r['room_id']} — {r['name']} ({r['capacity']})" for r in facility["rooms"]],
            "Room",
        )]
        result = service.create_reservation(
            user_id,
            {
                "facility_id": facility["facility_id"],
                "room_id": room["room_id"],
                "event_title": input("Event title: "),
                "start_at": _read_datetime("Start"),
                "end_at": _read_datetime("End"),
                "expected_attendance": input("Expected attendance: "),
            },
        )
        print(f"Submitted {result['reservation_id']} for approval.")
    elif choice == "3":
        for reservation in service.dashboard(user_id)["reservations"]:
            _show_reservation(reservation)
            for support in reservation["support_requests"]:
                print(f"  {support['support_type']}: {support['details']}")
    elif choice == "4":
        eligible = [
            item for item in service.dashboard(user_id)["reservations"]
            if item["status"] in {"Pending", "Approved"}
        ]
        if not eligible:
            print("You need a pending or approved reservation before requesting support.")
            return True
        index = _choose([item["event_title"] for item in eligible], "Reservation")
        kind = _choose(["Equipment", "Security", "Event support"], "Support type")
        service.add_support_request(
            user_id,
            eligible[index]["reservation_id"],
            ["equipment", "security", "event_support"][kind],
            input("Describe the request: "),
        )
        print("Support request attached to the event.")
    elif choice == "5":
        return False
    else:
        raise DomainError("Choose 1, 2, 3, 4, or 5.")
    return True


def _approver_actions(service, user_id, facilities):
    print("\n1. Review pending  2. Usage report  3. Logout")
    choice = input("Choose: ").strip()
    if choice == "1":
        pending = service.dashboard(user_id)["pending_requests"]
        if not pending:
            print("There are no pending requests.")
            return True
        for index, item in enumerate(pending, start=1):
            print(f"{index}. ", end="")
            _show_reservation(item)
        index = _choose([r["event_title"] for r in pending], "Review request")
        decision = _choose(["Approve", "Reject"], "Decision")
        result = service.decide_reservation(
            user_id, pending[index]["reservation_id"], "approve" if decision == 0 else "reject"
        )
        print(f"Request {result['status'].lower()}. The requester has been notified.")
    elif choice == "2":
        facility = facilities[_choose([f["name"] for f in facilities], "Facility")]
        start, end = _read_datetime("Report start"), _read_datetime("Report end")
        report = service.usage_report(user_id, facility["facility_id"], start, end)
        print(f"\n{len(report)} booking(s), including every status:")
        for item in report:
            _show_reservation(item)
    elif choice == "3":
        return False
    else:
        raise DomainError("Choose 1, 2, or 3.")
    return True


def run_tui(service):
    print("Smart Campus Event & Facility Booking — terminal mode")
    print("Demo accounts: student@mst.edu / approver@mst.edu — password Miner2026!")
    while True:
        print("\n1. Sign in  2. Register requester account  3. Exit")
        choice = input("Choose: ").strip()
        if choice == "3":
            return
        try:
            if choice == "1":
                user = service.authenticate(input("Email: "), getpass("Password: "))
            elif choice == "2":
                user = service.register(
                    input("Name: "), input("Email: "), getpass("Password (8+ characters): ")
                )
            else:
                raise DomainError("Choose 1, 2, or 3.")
            print(f"\nWelcome, {user['name']} ({user['role']}).")
            facilities = service.list_facilities()
            keep_going = True
            while keep_going:
                try:
                    if user["can_approve"]:
                        keep_going = _approver_actions(service, user["user_id"], facilities)
                    else:
                        keep_going = _user_actions(service, user["user_id"], facilities)
                except DomainError as error:
                    print(f"Cannot complete that action: {error}")
        except DomainError as error:
            print(f"Sign-in failed: {error}")


if __name__ == "__main__":
    from services import BookingService

    run_tui(BookingService())
