import os
import time
import requests

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
ADS_API_BASE_URL = "https://advertising-api.amazon.com"

CLIENT_ID = os.getenv("AMAZON_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMAZON_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("AMAZON_REFRESH_TOKEN")


class AmazonAdsClient:
    def __init__(self):
        self.access_token = None
        self.access_token_expiry = 0

    def refresh_access_token(self):
        # Se il token è ancora valido, lo riusa
        if self.access_token and time.time() < self.access_token_expiry - 60:
            return self.access_token

        data = {
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }
        resp = requests.post(LWA_TOKEN_URL, data=data)
        resp.raise_for_status()
        payload = resp.json()

        self.access_token = payload["access_token"]
        self.access_token_expiry = time.time() + payload.get("expires_in", 3600)
        return self.access_token

    def _headers(self, profile_id=None):
        token = self.refresh_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Amazon-Advertising-API-ClientId": CLIENT_ID,
        }
        # Se profilo specificato, aggiunge scope
        if profile_id is not None:
            headers["Amazon-Advertising-API-Scope"] = str(profile_id)
        return headers

    def list_profiles(self):
        url = f"{ADS_API_BASE_URL}/v2/profiles"
        resp = requests.get(url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_sp_campaigns(self, profile_id, states=("enabled", "paused")):
        """
        Legge le campagne Sponsored Products del profilo selezionato.
        """
        url = f"{ADS_API_BASE_URL}/sp/campaigns"
        params = {
            "stateFilter": ",".join(states),
        }
        resp = requests.get(url, headers=self._headers(profile_id), params=params)
        resp.raise_for_status()
        return resp.json()

    def get_sp_targets_for_campaign(self, profile_id, campaign_id):
        """
        Legge i target (keyword/ASIN, ecc.) di una singola campagna SP.
        """
        url = f"{ADS_API_BASE_URL}/sp/targets"
        params = {
            "campaignIdFilter": campaign_id,
        }
        resp = requests.get(url, headers=self._headers(profile_id), params=params)
        resp.raise_for_status()
        return resp.json()

    def update_sp_bids_for_campaign(
        self,
        profile_id,
        campaign_id,
        delta,
        direction="up",
        min_bid=None,
        max_bid=None,
    ):
        """
        Incrementa o decrementa i bid di tutti i target di una campagna SP.
        """
        targets = self.get_sp_targets_for_campaign(profile_id, campaign_id)

        updates = []
        preview_rows = []

        for t in targets:
            old_bid = t.get("bid")
            target_id = t.get("targetId") or t.get("keywordId")

            if old_bid is None or target_id is None:
                continue

            if direction == "up":
                new_bid = old_bid + delta
            else:
                new_bid = max(0, old_bid - delta)

            if min_bid is not None and min_bid > 0:
                new_bid = max(min_bid, new_bid)

            if max_bid is not None and max_bid > 0:
                new_bid = min(max_bid, new_bid)

            if new_bid != old_bid:
                updates.append(
                    {
                        "targetId": target_id,
                        "bid": new_bid,
                    }
                )
                preview_rows.append(
                    {
                        "targetId": target_id,
                        "old_bid": old_bid,
                        "new_bid": new_bid,
                    }
                )

        if not updates:
            return {
                "updated": 0,
                "preview": preview_rows,
                "api_response": None,
            }

        url = f"{ADS_API_BASE_URL}/sp/targets/bid"
        resp = requests.put(url, headers=self._headers(profile_id), json=updates)
        resp.raise_for_status()

        return {
            "updated": len(updates),
            "preview": preview_rows,
            "api_response": resp.json(),
        }

    def create_review_link(self, profile_id, manager_entity_id, region_code):
        """
        Crea il link di approvazione da inviare al cliente.
        """
        url = f"{ADS_API_BASE_URL}/v2/profiles/{profile_id}/authorization"
        data = {
            "clientId": CLIENT_ID,
            "entityId": manager_entity_id,
            "region": region_code
        }
        headers = self._headers(profile_id)
        resp = requests.post(url, headers=headers, json=data)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("approvalLink", "")
