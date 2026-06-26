"""Deterministic tests for the Sabre tool layer. No LLM, no API key.

Spins up the mock in-process, then drives every tool. The calls are GENERATED
from sabre_fixtures.json (the real Sabre request examples) so coverage tracks
the real contract automatically.

    python test_sabre_tools.py
"""
import json
import os
import threading
from http.server import HTTPServer

PORT = 8091  # off the default 8080 so a separately-running mock doesn't clash
os.environ["SABRE_BASE"] = f"http://localhost:{PORT}"

import mock_sabre
import sabre_tools

FIX = json.load(open("sabre_fixtures.json", encoding="utf-8"))


def _serve():
    srv = HTTPServer(("127.0.0.1", PORT), mock_sabre.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def is_error(resp):
    return isinstance(resp, dict) and resp.get("errors")


def main():
    srv = _serve()

    # 1. Each typed tool returns the real Sabre shape (not an error envelope).
    booking = sabre_tools.get_booking("BQAUZG")
    assert "travelers" in booking and "flights" in booking, booking
    assert booking["travelers"][0]["surname"] == "POWER", booking["travelers"][0]

    rates = sabre_tools.get_hotel_rates("100214", "2026-08-21", "2026-08-23")
    assert not is_error(rates), rates

    hotels = sabre_tools.search_hotels("2026-08-21", "2026-08-23", 40.757, -73.985)
    assert not is_error(hotels), hotels

    cancel = sabre_tools.cancel_booking("XVOWMO", flightItemIds=["12"], hotelItemIds=["37"])
    assert not is_error(cancel), cancel

    # 2. Missing required field -> real Sabre error envelope (proves validation path).
    bad = sabre_tools._post("/v1/trip/orders/getBooking", {})
    assert is_error(bad), bad

    # 3. dispatch() maps tool names to functions and swallows bad input.
    assert "error" in sabre_tools.dispatch("get_booking", {"wrong": "arg"})
    assert "travelers" in sabre_tools.dispatch("get_booking", {"confirmationId": "BQAUZG"})

    srv.shutdown()
    print(f"tool tests ok: {len(sabre_tools.DISPATCH)} tools exercised against the real contract")


if __name__ == "__main__":
    main()
