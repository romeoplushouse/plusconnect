import requests


class PrevioRestClient:
    def __init__(self, base_url: str, token: str, hotel_id: str = "", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.hotel_id = hotel_id
        self.timeout = timeout

    def get_pin(self, reservation_id: str) -> str:
        """
        Fetch PIN for a reservation.
        Expects response: {"pin": "123456"}
        """
        # TODO: add correct endpoint path/params based on Previo REST docs.
        url = f"{self.base_url}/pin/{reservation_id}"
        params = {}
        if self.hotel_id:
            params["hotelId"] = self.hotel_id
        resp = requests.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["pin"]
