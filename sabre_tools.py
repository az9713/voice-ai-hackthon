"""Sabre tools for the voice agent: thin HTTP wrappers + Claude tool schemas.

Each function POSTs to SABRE_BASE (the mock at localhost, or real Sabre later).
The same code path works against both — only SABRE_BASE + the token differ.
"""
import os
import requests


def _base():
    return os.environ.get("SABRE_BASE", "http://localhost:8080")


def _token():
    base = _base()
    if "localhost" in base or "127.0.0.1" in base:
        return "MOCK-TOKEN"
    from sabre_token import get_token  # real cert token (needs SABRE_PASSWORD)
    return get_token()


def _post(path, body):
    r = requests.post(_base() + path,
                      headers={"Authorization": f"Bearer {_token()}",
                               "Content-Type": "application/json"},
                      json=body, timeout=30)
    return r.json() if r.text else {}


# --- tool implementations (real Sabre Agentic paths) ---
def get_booking(confirmationId):
    return _post("/v1/trip/orders/getBooking", {"confirmationId": confirmationId})


def cancel_booking(confirmationId, flightItemIds=None, hotelItemIds=None):
    body = {"confirmationId": confirmationId}
    if flightItemIds:
        body["flights"] = [{"itemId": str(i)} for i in flightItemIds]
    if hotelItemIds:
        body["hotels"] = [{"itemId": str(i)} for i in hotelItemIds]
    return _post("/v1/trip/orders/cancelBooking", body)


def search_hotels(checkInDate, checkOutDate, latitude, longitude,
                  numberOfAdults=2, radiusInMiles=5, currencyCode="USD"):
    return _post("/v1/hotels/hotelSearch", {
        "currencyCode": currencyCode, "radiusInMiles": radiusInMiles,
        "checkInDate": checkInDate, "checkOutDate": checkOutDate,
        "numberOfAdults": numberOfAdults, "latitude": latitude, "longitude": longitude,
    })


def get_hotel_rates(hotelCode, checkInDate, checkOutDate, numberOfAdults=2, currencyCode="USD"):
    return _post("/v1/hotels/getHotelRates", {
        "currencyCode": currencyCode, "checkInDate": checkInDate, "checkOutDate": checkOutDate,
        "hotelCode": hotelCode, "numberOfAdults": numberOfAdults, "numberOfChildren": 0,
    })


DISPATCH = {
    "get_booking": get_booking,
    "cancel_booking": cancel_booking,
    "search_hotels": search_hotels,
    "get_hotel_rates": get_hotel_rates,
}


def dispatch(name, args):
    """Run a tool by name; never raise into the agent loop."""
    try:
        return DISPATCH[name](**args)
    except Exception as e:  # surface to the model so it can recover
        return {"error": f"{type(e).__name__}: {e}"}


# --- Claude tool schemas (what the model sees) ---
TOOLS = [
    {
        "name": "get_booking",
        "description": "Look up a traveler's booking (PNR) by its confirmation ID. "
                       "Call this first whenever the user references their trip, flight, or hotel.",
        "input_schema": {
            "type": "object",
            "properties": {
                "confirmationId": {"type": "string", "description": "The 6-char Sabre record locator, e.g. BQAUZG"},
            },
            "required": ["confirmationId"],
        },
    },
    {
        "name": "cancel_booking",
        "description": "Cancel specific flight and/or hotel segments on a booking. "
                       "Only call after the user has clearly confirmed they want to cancel. "
                       "Use the itemId values from get_booking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "confirmationId": {"type": "string"},
                "flightItemIds": {"type": "array", "items": {"type": "string"},
                                  "description": "itemIds of flight segments to cancel"},
                "hotelItemIds": {"type": "array", "items": {"type": "string"},
                                 "description": "itemIds of hotel segments to cancel"},
            },
            "required": ["confirmationId"],
        },
    },
    {
        "name": "search_hotels",
        "description": "Find available hotels near a lat/long for a date range. Use to rebook a stay.",
        "input_schema": {
            "type": "object",
            "properties": {
                "checkInDate": {"type": "string", "description": "YYYY-MM-DD"},
                "checkOutDate": {"type": "string", "description": "YYYY-MM-DD"},
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "numberOfAdults": {"type": "integer"},
            },
            "required": ["checkInDate", "checkOutDate", "latitude", "longitude"],
        },
    },
    {
        "name": "get_hotel_rates",
        "description": "Get nightly rates for a specific hotel (by hotelCode) and date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hotelCode": {"type": "string"},
                "checkInDate": {"type": "string", "description": "YYYY-MM-DD"},
                "checkOutDate": {"type": "string", "description": "YYYY-MM-DD"},
                "numberOfAdults": {"type": "integer"},
            },
            "required": ["hotelCode", "checkInDate", "checkOutDate"],
        },
    },
]
