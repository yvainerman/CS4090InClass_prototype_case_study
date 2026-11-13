#!/usr/bin/env python3
"""Launch the browser app, or use --tui for the terminal interface."""

import argparse

from services import BookingService
from tui import run_tui
from web import serve


def main():
    parser = argparse.ArgumentParser(description="Smart Campus Event & Facility Booking demo")
    parser.add_argument("--tui", action="store_true", help="use the terminal interface")
    parser.add_argument("--reset-demo", action="store_true", help="restore the repeatable demo data and exit")
    parser.add_argument("--host", default="127.0.0.1", help="local bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="web server port (default: 8000)")
    args = parser.parse_args()

    service = BookingService()
    if args.reset_demo:
        service.reset_demo()
        print("Demo data reset. Sign-in: student@mst.edu or approver@mst.edu / Miner2026!")
        return
    if args.tui:
        run_tui(service)
    else:
        serve(service, args.host, args.port)


if __name__ == "__main__":
    main()
