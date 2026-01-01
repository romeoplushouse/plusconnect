from typing import Optional

import requests
from requests.auth import HTTPBasicAuth


class PrevioRestClient:
    def __init__(
        self,
        base_url: str,
        token: str = "",
        hotel_id: str = "",
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.hotel_id = hotel_id
        self.username = username
        self.password = password
        self.timeout = timeout

    def get_pin(self, reservation_id: str) -> str:
        """
        Fetch PIN for a reservation.
        Uses REST endpoint /rest/reservations/rooms/card-locking-keys with Basic Auth as per Previo docs.
        Fallback to bearer token if Basic credentials are not provided.
        """
        url = f"{self.base_url}/rest/reservations/rooms/card-locking-keys"
        params = {"reservationRoomId": reservation_id}
        headers = {"Content-Type": "application/json"}
        if self.hotel_id:
            headers["X-Previo-Hotel-ID"] = self.hotel_id

        auth = None
        if self.username and self.password:
            auth = HTTPBasicAuth(self.username, self.password)
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        resp = requests.get(url, params=params, headers=headers, auth=auth, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        # New response format contains list of keys; fallback to legacy "pin" field if present.
        if isinstance(data, dict):
            if "pin" in data:
                return str(data["pin"])
            keys = data.get("keys") or data.get("data") or []
            if isinstance(keys, dict):
                keys = list(keys.values())
            if keys:
                first = keys[0]
                if isinstance(first, dict):
                    for key_name in ("key", "code", "pin"):
                        if key_name in first and first[key_name] not in (None, ""):
                            return str(first[key_name])
        raise ValueError("PIN not found in Previo REST response")
