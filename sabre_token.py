"""Get a Sabre REST sessionless (OAuth v2) token.

Usage:
    pip install requests
    # PowerShell:  $env:SABRE_PASSWORD = "<password from My Account > Applications>"
    # bash:        export SABRE_PASSWORD="<password>"
    python sabre_token.py            # fetch a token
    python sabre_token.py --selftest # verify the base64 recipe, no network/password
"""
import base64, os, sys

# Your Developer Hub Application credentials (My Account > Applications).
# User ID is shown in plain text there; password is the secret -> pass via env var.
# Set SABRE_USER_ID in .env (My Account > Applications). Format: V1:<id>:DEVCENTER:EXT
USER_ID = os.environ.get("SABRE_USER_ID", "V1:YOUR_USER_ID:DEVCENTER:EXT")

# DEVCENTER credentials are for the certification (test) environment.
TOKEN_URL = "https://api.cert.platform.sabre.com/v2/auth/token"


def basic_auth(user_id: str, password: str) -> str:
    """Sabre v2 recipe: base64( base64(userID) : base64(password) )."""
    b1 = base64.b64encode(user_id.encode()).decode()
    b2 = base64.b64encode(password.encode()).decode()
    return base64.b64encode(f"{b1}:{b2}".encode()).decode()


def get_token() -> str:
    """Fetch a sessionless bearer token. Needs SABRE_PASSWORD env var."""
    password = os.environ.get("SABRE_PASSWORD")
    if not password:
        sys.exit("Set SABRE_PASSWORD (copy it from My Account > Applications, eye icon)")
    import requests
    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": "Basic " + basic_auth(USER_ID, password),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _selftest():
    # Known example from Sabre's "Get a Token" docs (userID "V1:userid:group:domain", pw "12345")
    expected = "VmpFNmRYTmxjbWxrT21keWIzVndPbVJ2YldGcGJnPT06TVRJek5EVT0="
    assert basic_auth("V1:userid:group:domain", "12345") == expected, "base64 recipe mismatch"
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    print(get_token())
