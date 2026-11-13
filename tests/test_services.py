import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from services import BookingService, DomainError


NOW = datetime(2026, 11, 13, 12, 0)


class BookingServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_file = Path(self.temp_dir.name) / "demo.json"
        self.service = BookingService(self.data_file, now_fn=lambda: NOW)
        self.student = self.service.authenticate("student@mst.edu", "Miner2026!")
        self.approver = self.service.authenticate("approver@mst.edu", "Miner2026!")

    def tearDown(self):
        self.temp_dir.cleanup()

    def request_payload(self, **overrides):
        payload = {
            "facility_id": "F001",
            "room_id": "G102",
            "event_title": "AI Showcase Planning",
            "start_at": "2026-11-16T14:00",
            "end_at": "2026-11-16T15:00",
            "expected_attendance": 15,
        }
        payload.update(overrides)
        return payload

    def test_search_filters_capacity_and_pending_requests_hold_a_room(self):
        rooms = self.service.search_rooms(
            "F001", "2026-11-16T14:00", "2026-11-16T15:00", 30
        )
        self.assertEqual({room["room_id"] for room in rooms}, {"G201", "G203"})

        self.service.create_reservation(self.student["user_id"], self.request_payload())
        rooms = self.service.search_rooms(
            "F001", "2026-11-16T14:00", "2026-11-16T15:00", 15
        )
        self.assertNotIn("G102", {room["room_id"] for room in rooms})

        touching_interval = self.service.search_rooms(
            "F001", "2026-11-16T15:00", "2026-11-16T16:00", 15
        )
        self.assertIn("G102", {room["room_id"] for room in touching_interval})

    def test_reservation_rejects_bad_time_capacity_and_overlap(self):
        with self.assertRaisesRegex(DomainError, "future"):
            self.service.create_reservation(
                self.student["user_id"], self.request_payload(start_at="2026-11-13T11:00")
            )
        with self.assertRaisesRegex(DomainError, "capacity"):
            self.service.create_reservation(
                self.student["user_id"],
                self.request_payload(expected_attendance=21),
            )
        with self.assertRaisesRegex(DomainError, "facility hours"):
            self.service.create_reservation(
                self.student["user_id"],
                self.request_payload(start_at="2026-11-16T21:30", end_at="2026-11-16T22:30"),
            )

        self.service.create_reservation(self.student["user_id"], self.request_payload())
        with self.assertRaisesRegex(DomainError, "already requested"):
            self.service.create_reservation(
                self.student["user_id"],
                self.request_payload(event_title="Conflicting request"),
            )

    def test_approval_support_notifications_and_persistence(self):
        created = self.service.create_reservation(
            self.student["user_id"], self.request_payload()
        )
        supported = self.service.add_support_request(
            self.student["user_id"], created["reservation_id"], "equipment",
            "Projector and two microphones",
        )
        self.assertEqual(supported["support_requests"][0]["support_type"], "Equipment")

        result = self.service.decide_reservation(
            self.approver["user_id"], created["reservation_id"], "approve", "Looks good."
        )
        self.assertEqual(result["status"], "Approved")
        self.assertEqual(result["approvals"][0]["comments"], "Looks good.")
        student_dashboard = self.service.dashboard(self.student["user_id"])
        self.assertIn("approved", student_dashboard["notifications"][0]["message"])

        reloaded = BookingService(self.data_file, now_fn=lambda: NOW)
        persisted = reloaded.dashboard(self.student["user_id"])["reservations"]
        event = next(item for item in persisted if item["reservation_id"] == created["reservation_id"])
        self.assertEqual(event["status"], "Approved")
        self.assertEqual(event["support_requests"][0]["details"], "Projector and two microphones")
        self.assertEqual(event["approvals"][0]["reviewer_name"], "Morgan Chen")

    def test_reports_use_overlapping_range_and_are_role_protected(self):
        event = self.service.create_reservation(self.student["user_id"], self.request_payload())
        self.service.decide_reservation(self.approver["user_id"], event["reservation_id"], "reject")
        report = self.service.usage_report(
            self.approver["user_id"], "F001", "2026-11-16T14:30", "2026-11-16T16:00"
        )
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]["status"], "Rejected")
        with self.assertRaisesRegex(DomainError, "Only an event approver"):
            self.service.usage_report(
                self.student["user_id"], "F001", "2026-11-16T00:00", "2026-11-17T00:00"
            )

    def test_facility_hours_cannot_conflict_with_active_reservations(self):
        with self.assertRaisesRegex(DomainError, "active reservations"):
            self.service.update_facility_hours(
                self.approver["user_id"], "F001", "08:00", "09:00"
            )
        updated = self.service.update_facility_hours(
            self.approver["user_id"], "F001", "07:30", "22:30"
        )
        self.assertEqual(updated[0]["open_time"], "07:30")

    def test_requester_can_cancel_and_release_a_pending_room(self):
        created = self.service.create_reservation(
            self.student["user_id"], self.request_payload()
        )
        cancelled = self.service.cancel_reservation(
            self.student["user_id"], created["reservation_id"]
        )
        self.assertEqual(cancelled["status"], "Cancelled")
        rooms = self.service.search_rooms(
            "F001", "2026-11-16T14:00", "2026-11-16T15:00", 15
        )
        self.assertIn("G102", {room["room_id"] for room in rooms})

    def test_registration_creates_requester_and_rejects_short_password(self):
        with self.assertRaisesRegex(DomainError, "at least 8"):
            self.service.register("New Miner", "new@mst.edu", "short")
        created = self.service.register("New Miner", "new@mst.edu", "a-secure-demo")
        self.assertFalse(created["can_approve"])
        self.assertEqual(
            self.service.authenticate("new@mst.edu", "a-secure-demo")["user_id"],
            created["user_id"],
        )


if __name__ == "__main__":
    unittest.main()
