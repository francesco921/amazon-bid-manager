import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("AMAZON_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMAZON_CLIENT_SECRET")
REDIRECT_URI = os.getenv("AMAZON_REDIRECT_URI")

TOKEN_URL = "https://api.amazon.com/auth/o2/token"


def exchange_code(code: str):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    r = requests.post(TOKEN_URL, data=data)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    auth_code = input("Paste the ?code=... value: ").strip()
    tokens = exchange_code(auth_code)

    print("\n--- RESPONSE FROM AMAZON ---")
    print(tokens)
    print("----------------------------\n")

    print("access_token:", tokens.get("access_token"))
    print("refresh_token:", tokens.get("refresh_token"))

    refresh_token = tokens.get("refresh_token")
    if refresh_token:
        print("\n✅ Copy this line into your .env file:\n")
        print(f"AMAZON_REFRESH_TOKEN={refresh_token}")
    else:
        print("\n⚠️  No refresh_token received. Check that the code is valid and not expired.")
