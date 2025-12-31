import logging
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

import requests

LOG = logging.getLogger(__name__)


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
        payload = self._with_defaults({"modifiedFrom": modified_from, "modifiedTo": modified_to})
        resp = requests.post(
            f"{self.base_url}/Hotel.searchReservations",
            data=payload,
            auth=self.auth,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return self._parse_reservations_response(resp)

    def get_room_kinds(self) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/Hotel.getRoomKinds",
            data=self._with_defaults({}),
            auth=self.auth,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return self._parse_room_kinds_response(resp)

    def _with_defaults(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = {
            "login": self.auth[0],
            "password": self.auth[1],
            "hotelId": self.hotel_id,
            **{k: v for k, v in payload.items() if v is not None},
        }
        return data

    def _parse_reservations_response(self, response: requests.Response) -> List[Dict[str, Any]]:
        content = response.text.strip()
        if not content:
            return []

        if "json" in response.headers.get("Content-Type", "") or content.startswith("{"):
            data = response.json()
            raw_reservations = data.get("reservations") or data.get("Reservation") or data.get("data") or []
            if isinstance(raw_reservations, dict):
                raw_reservations = list(raw_reservations.values())
            return [r for r in (self._normalize_reservation(item) for item in raw_reservations) if r]

        if not content.lstrip().startswith("<"):
            snippet = content[:200].replace("\n", " ")
            raise ValueError(
                f"Unexpected response format (status {response.status_code}, content-type "
                f"{response.headers.get('Content-Type')}): {snippet}"
            )

        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as exc:
            LOG.error(
                "Failed to parse Previo XML response (status %s, content-type %s): %s",
                response.status_code,
                response.headers.get("Content-Type"),
                exc,
            )
            raise ValueError(f"Invalid XML from Previo: {exc}") from exc
        reservations: List[Dict[str, Any]] = []
        for res_el in root.findall(".//reservation"):
            res_data = {child.tag: (child.text or "").strip() for child in res_el}
            normalized = self._normalize_reservation(res_data)
            if normalized:
                reservations.append(normalized)
        return reservations

    def _normalize_reservation(self, raw: Any) -> Optional[Dict[str, Any]]:
        data: Dict[str, Any] = {}
        if isinstance(raw, dict):
            data.update(raw)

        # Pull common nested structures up to the top-level.
        if isinstance(data.get("room"), dict):
            data.setdefault("room_name", data["room"].get("name") or data["room"].get("code"))
        if isinstance(data.get("accommodationUnit"), dict):
            unit = data["accommodationUnit"]
            data.setdefault("room_name", unit.get("name") or unit.get("code"))

        def pick(keys, default=None):
            for key in keys:
                if key in data and data[key] not in (None, ""):
                    return data[key]
            return default

        reservation_id = pick(["reservation_id", "reservationId", "id", "resId"])
        if not reservation_id:
            return None

        return {
            "reservation_id": str(reservation_id),
            "room_name": pick(["room_name", "roomName", "room", "roomCode", "unitName"], ""),
            "check_in": pick(["check_in", "checkIn", "arrival", "date_from", "from", "start"]),
            "check_out": pick(["check_out", "checkOut", "departure", "date_to", "to", "end"]),
            "status": pick(["status", "state", "reservation_status"], ""),
            "pin": pick(["pin", "access_code", "code"]),
        }

    def _parse_room_kinds_response(self, response: requests.Response) -> Dict[str, Any]:
        content = response.text.strip()
        if not content:
            return {}

        if "json" in response.headers.get("Content-Type", "") or content.startswith("{"):
            data = response.json()
            return data.get("roomKinds") or data.get("data") or {}

        root = ElementTree.fromstring(content)
        result: Dict[str, Any] = {}
        for kind in root.findall(".//roomKind"):
            uuid = None
            name = None
            for child in kind:
                if child.tag in ("uuid", "id") and child.text:
                    uuid = child.text.strip()
                if child.tag == "name" and child.text:
                    name = child.text.strip()
            if uuid and name:
                result[uuid] = name
        return result
