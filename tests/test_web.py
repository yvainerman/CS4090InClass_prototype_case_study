import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from services import BookingService
from web import create_server


class WebAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        service = BookingService(
            Path(self.temp_dir.name) / "web.json",
            now_fn=lambda: datetime(2026, 11, 13, 12, 0),
        )
        self.server = create_server(service, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.cookies = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def open(self, path, method="GET", payload=None):
        return self.call(self.client, path, method, payload)

    def call(self, client, path, method="GET", payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        return client.open(request, timeout=3)

    def test_login_dashboard_and_frontend_are_served(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.open("/api/dashboard")
        self.assertEqual(error.exception.code, 401)

        with self.open(
            "/api/login",
            "POST",
            {"email": "student@mst.edu", "password": "Miner2026!"},
        ) as response:
            self.assertEqual(response.status, 200)

        with self.open("/api/dashboard") as response:
            dashboard = json.load(response)
        self.assertEqual(dashboard["user"]["name"], "Jordan Lee")
        self.assertEqual(dashboard["facilities"][0]["name"], "Curtis Laws Wilson Library")

        with self.open("/") as response:
            self.assertIn(b"Miner Space", response.read())
        with self.open("/static/app.js") as response:
            self.assertIn(b"/api/reservations", response.read())

    def test_api_supports_the_full_recording_flow(self):
        approver_cookies = http.cookiejar.CookieJar()
        approver_client = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(approver_cookies)
        )
        self.call(
            self.client, "/api/login", "POST",
            {"email": "student@mst.edu", "password": "Miner2026!"},
        ).close()
        self.call(
            approver_client, "/api/login", "POST",
            {"email": "approver@mst.edu", "password": "Miner2026!"},
        ).close()

        search = "/api/search?facility_id=F001&start_at=2026-11-16T14%3A00&end_at=2026-11-16T15%3A00&capacity=15"
        with self.call(self.client, search) as response:
            rooms = json.load(response)["rooms"]
        self.assertIn("G102", {room["room_id"] for room in rooms})

        with self.call(
            self.client, "/api/reservations", "POST",
            {
                "facility_id": "F001", "room_id": "G102",
                "event_title": "AI Showcase Planning",
                "start_at": "2026-11-16T14:00", "end_at": "2026-11-16T15:00",
                "expected_attendance": 15,
            },
        ) as response:
            reservation_id = json.load(response)["reservation"]["reservation_id"]

        with self.assertRaises(urllib.error.HTTPError) as conflict:
            self.call(self.client, "/api/reservations", "POST", {
                "facility_id": "F001", "room_id": "G102",
                "event_title": "Overlapping event",
                "start_at": "2026-11-16T14:30", "end_at": "2026-11-16T15:30",
                "expected_attendance": 10,
            })
        self.assertEqual(conflict.exception.code, 400)
        conflict.exception.close()

        with self.call(
            approver_client,
            f"/api/reservations/{reservation_id}/decision",
            "POST",
            {"decision": "approve", "comments": "Approved for the demo."},
        ) as response:
            self.assertEqual(json.load(response)["reservation"]["status"], "Approved")

        with self.call(
            self.client,
            f"/api/reservations/{reservation_id}/support",
            "POST",
            {"support_type": "equipment", "details": "Projector and two microphones"},
        ) as response:
            updated = json.load(response)["reservation"]
            self.assertEqual(updated["support_requests"][0]["support_type"], "Equipment")

        report = (
            "/api/reports?facility_id=F001&start_at=2026-11-16T13%3A00"
            "&end_at=2026-11-16T16%3A00"
        )
        with self.call(approver_client, report) as response:
            records = json.load(response)["reservations"]
        self.assertIn(reservation_id, {item["reservation_id"] for item in records})

        with self.call(
            self.client,
            f"/api/reservations/{reservation_id}/cancel",
            "POST",
            {},
        ) as response:
            self.assertEqual(json.load(response)["reservation"]["status"], "Cancelled")


if __name__ == "__main__":
    unittest.main()
