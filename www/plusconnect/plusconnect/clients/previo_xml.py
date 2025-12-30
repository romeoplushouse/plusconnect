from typing import Any, Dict, List

import requests


class PrevioXmlClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        hotel_id: str = "",
        timeout: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)
        self.hotel_id = hotel_id
        self.timeout = timeout

    def search_reservations(self, modified_from: str, modified_to: str) -> List[Dict[str, Any]]:
        """
        Call Hotel.searchReservations and return parsed reservations.
        `modified_from` / `modified_to` should be ISO strings expected by Previo.
        """
        # TODO: Implement XML payload/response parsing according to Previo docs.
        raise NotImplementedError

    def get_room_kinds(self) -> Dict[str, Any]:
        # TODO: Implement Hotel.getRoomKinds if needed for metadata.
        raise NotImplementedError
