# Five-minute recording guide

## Before recording

1. Run `python3 main.py --reset-demo`, then `python3 main.py`.
2. Open `http://127.0.0.1:8000` and maximize the browser. Use a display size where the left navigation and cards fit.
3. Use the date picker’s default time (three days ahead, 14:00–15:00) or choose another future one-hour period within the facility's 08:00–22:00 hours. The seeded event is two days ahead, in G201 at 10:00–11:00.
4. Sign in with the demo cards. Password for both: `Miner2026!`.
5. Keep the two personas in mind: requester `student@mst.edu`, approver `approver@mst.edu`. Sign out between personas.

The demo data is generated relative to the machine’s local date/time when reset. No manually edited JSON fixture is needed.

## Recording sequence (target 4:45–5:00)

| Time | Screen and action | Narration / evidence |
|---|---|---|
| 0:00–0:25 | Login portal | Introduce Miner Space as a local prototype for the Smart Campus Event & Facility Booking case study. Point out the two demo personas and clarify that these are not university credentials. |
| 0:25–1:10 | Sign in as requester; open **Find a room**; search the default date/time with capacity 15. | Show room name and capacity, and explain that results use facility hours, group size, and current room requests. |
| 1:10–2:05 | Request G102 as “AI Showcase Planning” for 15 people. Return to search with the same room and time. | Show the Pending confirmation, then the absence of G102 in the second search. Explain that pending requests hold a slot in this prototype. If desired, briefly try attendance above capacity or an after-hours slot and show the validation message. |
| 2:05–3:05 | Sign out; sign in as approver; open **Approvals** and approve AI Showcase Planning. Then sign back in as requester and open **My reservations**. | Show the approver role, request details, status change, and requester notification. Note that decisions are stored as approval history. |
| 3:05–3:45 | As requester, add Equipment support: “Projector and two microphones.” | Show that the support request appears on the reservation. Clarify that the app records the need; it does not dispatch equipment. |
| 3:45–4:35 | Sign in as approver; run a usage report for a range that includes the event. | Show the report record and status. Mention that the report includes reservations with any status that overlap the selected range. |
| 4:35–5:00 | Return to overview or show the report summary. | Close with the five implemented flows and the prototype scope: local JSON persistence, demo-only accounts, and no integration with campus identity or room inventory. |

## Reset and recovery

- If the event is rejected or the wrong room/time is booked, run `python3 main.py --reset-demo` and refresh the browser. This resets the local demo data.
- If an account is signed out unexpectedly, sign in again using the appropriate demo card.
- If the web port is already in use, run `python3 main.py --port 8001` and open `http://127.0.0.1:8001`.
- The app writes its local data to ignored `booking_data.json`; do not include that runtime file in the submitted source archive.
