import os
import time
import requests

# Cache in memoria
_access_token = None
_token_expiry = 0

def get_access_token():
    global _access_token, _token_expiry

    # Se il token esiste ed è ancora valido, lo restituiamo
    if _access_token and time.time() < _token_expiry:
        return _access_token

    # Altrimenti rigeneriamo un nuovo access token
    client_id = os.getenv("AMAZON_CLIENT_ID")
    client_secret = os.getenv("AMAZON_CLIENT_SECRET")
    refresh_token = os.getenv("AMAZON_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise Exception("Variabili d'ambiente mancanti: controlla .env o secrets")

    token_url = "https://api.amazon.com/auth/o2/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    }

    response = requests.post(token_url, data=payload)
    response.raise_for_status()
    tokens = response.json()

    _access_token = tokens["access_token"]
    # Salviamo la scadenza con un margine di 5 minuti
    _token_expiry = time.time() + tokens["expires_in"] - 300

    return _access_token
