# Miner Space — Smart Campus Booking

A local demonstration app for the Smart Campus Event & Facility Booking case study. It has a Missouri S&T-inspired green-and-gold web interface, a terminal interface, and one shared application/service layer. Both interfaces use the same validation, reservation, approval, support, and reporting logic.

## Run it

Requires Python 3.9 or newer. No third-party packages are needed.

```bash
python3 main.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Stop the app with Ctrl+C. The web server binds to localhost by default.

The terminal UI is available with:

```bash
python3 main.py --tui
```

Restore the repeatable demonstration data at any time with:

```bash
python3 main.py --reset-demo
```

The demo data is stored in the ignored `booking_data.json` file beside the source. It is separate from the legacy `users.json` file and is excluded from Git.

## Demo sign-in

| Persona | Email | Password |
|---|---|---|
| Student requester | `student@mst.edu` | `Miner2026!` |
| Event approver | `approver@mst.edu` | `Miner2026!` |

Both demo cards can autofill the login form. New accounts can be registered as requesters; the public registration form does not grant approver access.

## Five video flows

Reset demo data immediately before recording so the walkthrough is predictable. Use the same event request to connect the five steps:

1. **Find an available space.** Sign in as `student@mst.edu`. In **Find a room**, use the next available future date (the form defaults to three days ahead), a one-hour time between 08:00 and 22:00, and capacity 15. Show the room options with room IDs, names, and capacities.
2. **Submit and prevent a double booking.** Request G102 for “AI Showcase Planning,” attendance 15, using the search time. Show the Pending confirmation. Run the same room/time search again; G102 should no longer appear because pending requests hold the slot. Optionally submit an over-capacity or out-of-hours request to show a useful validation error.
3. **Approve and notify.** Sign out and sign in as `approver@mst.edu`. Open **Approvals**, review AI Showcase Planning, and approve it. Return to the student account and show the Approved status and notification.
4. **Attach event support.** As the requester, open **My reservations** and add an Equipment request such as “Projector and two microphones.” Show it attached to the event.
5. **Run a usage report.** Sign in as the approver, open **Usage reports**, choose a range covering the booking, and run the report. Point out that the report includes all reservation statuses and selects bookings that overlap the range.

Use the seeded “Miner Makers Meetup” booking to demonstrate a pre-existing approved event or use it to show occupied room search results. The sample booking is scheduled relative to the day demo data is reset.

## Behavior and demo assumptions

- Pending, approved, and in-progress requests occupy their room/time interval; time intervals that only touch at their boundaries do not overlap.
- Requests must start in the future, fit within one day’s facility hours, and fit the room’s capacity. Default library hours are 08:00–22:00.
- Only Event Approver and System Administrator personas can review requests, change facility hours, or run reports. New registration creates a requester account.
- Requesters can cancel pending or approved reservations; cancellation releases the slot. Editing a submitted reservation is not included. Support requests are recorded on a reservation; the prototype does not fulfill them.
- Usage reports include every reservation status. They use interval overlap, rather than requiring the event to be completely contained within the report range.
- Authentication is classroom-demo authentication only. Demo credentials are published in this README; this is not connected to Missouri S&T identity services and is not production-ready.

## Validation

Run the focused automated tests with:

```bash
python3 -m unittest discover -s tests -v
```
