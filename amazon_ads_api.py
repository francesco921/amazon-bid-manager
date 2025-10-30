import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("AMAZON_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMAZON_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("AMAZON_REFRESH_TOKEN")

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
ADS_BASE_URL = "https://advertising-api.amazon.com"


def get_access_token_from_refresh():
    if not REFRESH_TOKEN:
        raise ValueError("AMAZON_REFRESH_TOKEN is missing in .env")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    r = requests.post(LWA_TOKEN_URL, data=data)
    r.raise_for_status()
    return r.json()["access_token"]


def list_profiles():
    access_token = get_access_token_from_refresh()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": CLIENT_ID,
    }
    r = requests.get(f"{ADS_BASE_URL}/v2/profiles", headers=headers)
    r.raise_for_status()
    return r.json()
