"""Smoke-test: call the Agentic Hotels Rates API with a token.

    export SABRE_PASSWORD='<password>'
    python sabre_hotel_rates.py

A 200/4xx with a JSON body means your token is accepted by the Agentic API.
A 403/401 means this endpoint needs higher-tier (PCC/EPR) credentials.
"""
import requests
from sabre_token import get_token

URL = "https://api.cert.platform.sabre.com/v1/hotels/getHotelRates"

# hotelCode is a placeholder from the docs — we're testing ACCESS, not real rates.
body = {
    "checkInDate": "2026-08-21",
    "checkOutDate": "2026-08-23",
    "hotelCode": "123456789",
    "numberOfAdults": 2,
    "numberOfChildren": 0,
}

resp = requests.post(
    URL,
    headers={"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"},
    json=body,
)
print("status:", resp.status_code)
print(resp.text[:1500])
