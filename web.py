"""Small standard-library HTTP adapter for the shared booking use cases."""

import json
import secrets
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from services import DomainError

STATIC_DIR = Path(__file__).parent / "static"


class BookingRequestHandler(BaseHTTPRequestHandler):
    server_version = "MinerBookingDemo/1.0"

    def log_message(self, format_string, *args):
        print(f"[web] {self.address_string()} - {format_string % args}")

    @property
    def service(self):
        return self.server.booking_service

    @property
    def sessions(self):
        return self.server.sessions

    def _send_json(self, payload, status=HTTPStatus.OK, headers=None):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if headers:
            for name, value in headers.items():
                self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise DomainError("Invalid request body.") from None
        if length > 32_768:
            raise DomainError("Request is too large.")
        if length == 0:
            return {}
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise DomainError("Request must contain valid JSON.") from None
        if not isinstance(payload, dict):
            raise DomainError("Request body must be a JSON object.")
        return payload

    def _user_id(self):
        cookie = SimpleCookie()
        cookie.load(self.headers.get("Cookie", ""))
        morsel = cookie.get("session")
        session_id = morsel.value if morsel else ""
        user_id = self.sessions.get(session_id)
        if not user_id:
            raise PermissionError("Please sign in to continue.")
        return user_id

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._send_file("index.html")
        if parsed.path.startswith("/static/"):
            return self._send_file(unquote(parsed.path.removeprefix("/static/")))
        try:
            query = parse_qs(parsed.query)
            if parsed.path == "/api/bootstrap":
                return self._send_json(
                    {
                        "facilities": self.service.list_facilities(),
                        "demo_accounts": [
                            {"label": "Student / requester", "email": "student@mst.edu"},
                            {"label": "Event approver", "email": "approver@mst.edu"},
                        ],
                    }
                )
            user_id = self._user_id()
            if parsed.path == "/api/me":
                return self._send_json({"user": self.service.get_user(user_id)})
            if parsed.path == "/api/dashboard":
                return self._send_json(self.service.dashboard(user_id))
            if parsed.path == "/api/facilities":
                return self._send_json({"facilities": self.service.list_facilities()})
            if parsed.path == "/api/search":
                return self._send_json(
                    {
                        "rooms": self.service.search_rooms(
                            self._first(query, "facility_id"),
                            self._first(query, "start_at"),
                            self._first(query, "end_at"),
                            self._first(query, "capacity"),
                        )
                    }
                )
            if parsed.path == "/api/reports":
                return self._send_json(
                    {
                        "reservations": self.service.usage_report(
                            user_id,
                            self._first(query, "facility_id"),
                            self._first(query, "start_at"),
                            self._first(query, "end_at"),
                        )
                    }
                )
            return self._send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
        except PermissionError as error:
            return self._send_json({"error": str(error)}, HTTPStatus.UNAUTHORIZED)
        except (DomainError, StopIteration) as error:
            message = str(error) or "The requested item could not be found."
            return self._send_json({"error": message}, HTTPStatus.BAD_REQUEST)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self._body()
            if parsed.path == "/api/login":
                user = self.service.authenticate(payload.get("email"), payload.get("password"))
                session_id = secrets.token_urlsafe(32)
                self.sessions[session_id] = user["user_id"]
                return self._send_json(
                    {"user": user},
                    headers={
                        "Set-Cookie": (
                            f"session={session_id}; HttpOnly; SameSite=Lax; Path=/"
                        )
                    },
                )
            if parsed.path == "/api/register":
                user = self.service.register(
                    payload.get("name"), payload.get("email"), payload.get("password")
                )
                session_id = secrets.token_urlsafe(32)
                self.sessions[session_id] = user["user_id"]
                return self._send_json(
                    {"user": user},
                    HTTPStatus.CREATED,
                    {
                        "Set-Cookie": (
                            f"session={session_id}; HttpOnly; SameSite=Lax; Path=/"
                        )
                    },
                )
            if parsed.path == "/api/logout":
                cookie = SimpleCookie()
                cookie.load(self.headers.get("Cookie", ""))
                morsel = cookie.get("session")
                if morsel:
                    self.sessions.pop(morsel.value, None)
                return self._send_json(
                    {"ok": True},
                    headers={"Set-Cookie": "session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"},
                )

            user_id = self._user_id()
            if parsed.path == "/api/reservations":
                reservation = self.service.create_reservation(user_id, payload)
                return self._send_json({"reservation": reservation}, HTTPStatus.CREATED)
            parts = [unquote(p) for p in parsed.path.strip("/").split("/")]
            if len(parts) == 4 and parts[:2] == ["api", "reservations"]:
                reservation_id, action = parts[2], parts[3]
                if action == "decision":
                    reservation = self.service.decide_reservation(
                        user_id, reservation_id, payload.get("decision"), payload.get("comments", "")
                    )
                    return self._send_json({"reservation": reservation})
                if action == "support":
                    reservation = self.service.add_support_request(
                        user_id,
                        reservation_id,
                        payload.get("support_type"),
                        payload.get("details"),
                    )
                    return self._send_json({"reservation": reservation})
                if action == "cancel":
                    reservation = self.service.cancel_reservation(user_id, reservation_id)
                    return self._send_json({"reservation": reservation})
            if len(parts) == 4 and parts[:2] == ["api", "facilities"] and parts[3] == "hours":
                facilities = self.service.update_facility_hours(
                    user_id, parts[2], payload.get("open_time"), payload.get("close_time")
                )
                return self._send_json({"facilities": facilities})
            return self._send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
        except PermissionError as error:
            return self._send_json({"error": str(error)}, HTTPStatus.UNAUTHORIZED)
        except DomainError as error:
            return self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def _send_file(self, name):
        if Path(name).name != name or name in {"", ".", ".."}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        path = STATIC_DIR / name
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        import mimetypes

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _first(query, key):
        values = query.get(key, [])
        return values[0] if values else None


def create_server(service, host="127.0.0.1", port=8000):
    server = ThreadingHTTPServer((host, port), BookingRequestHandler)
    server.booking_service = service
    server.sessions = {}
    return server


def serve(service, host="127.0.0.1", port=8000):
    server = create_server(service, host, port)
    print(f"Smart Campus Booking is ready at http://{host}:{server.server_port}")
    print("Demo sign-in: student@mst.edu or approver@mst.edu / Miner2026!")
    print("Press Ctrl+C to stop the local server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()
