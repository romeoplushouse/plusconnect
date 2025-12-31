import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import pytz
from datetime import timedelta

from ..clients.loxone import LoxoneClient, LoxoneUserPayload
from ..clients.previo_rest import PrevioRestClient
from ..clients.previo_xml import PrevioXmlClient
from .state_store import StateStore

LOG = logging.getLogger(__name__)


@dataclass
class Reservation:
    reservation_id: str
    room_name: str
    check_in: datetime
    check_out: datetime
    status: str
    pin: str


class SyncService:
    def __init__(
        self,
        loxone: LoxoneClient,
        previo_xml: PrevioXmlClient,
        previo_rest: PrevioRestClient,
        state_store: StateStore,
        timezone: str,
        checkout_buffer_minutes: int,
        expiration_action: int,
        room_group_mapping: Dict[str, str],
    ):
        self.loxone = loxone
        self.previo_xml = previo_xml
        self.previo_rest = previo_rest
        self.state_store = state_store
        self.timezone = pytz.timezone(timezone)
        self.checkout_buffer_minutes = checkout_buffer_minutes
        self.expiration_action = expiration_action
        self.room_group_mapping = room_group_mapping

    def sync(self, hotel_id: str, overlap_minutes: int = 3) -> None:
        last_synced_at = self.state_store.get_last_synced_at(hotel_id)
        window = self.state_store.compute_window(last_synced_at, overlap_minutes)
        LOG.info("Sync window %s -> %s", window["modified_from"], window["modified_to"])

        reservations_raw = self.previo_xml.search_reservations(
            window["modified_from"].isoformat(), window["modified_to"].isoformat()
        )
        LOG.info("Fetched %d reservations for processing", len(reservations_raw))
        for raw in reservations_raw:
            try:
                reservation = self._build_reservation(raw)
            except Exception as exc:  # noqa: BLE001 - we want to log and continue syncing
                LOG.exception("Skipping reservation due to parse error: %s", exc)
                continue
            self._process_reservation(hotel_id, reservation)

        self.state_store.update_last_synced_at(hotel_id, datetime.utcnow())

    def _build_reservation(self, raw: Dict) -> Reservation:
        reservation_id = self._pick(raw, ["reservation_id", "id", "resId"])
        if not reservation_id:
            raise ValueError("Missing reservation_id in reservation payload")

        check_in_raw = self._pick(
            raw, ["check_in", "checkIn", "arrival", "date_from", "from", "start"]
        )
        check_out_raw = self._pick(
            raw, ["check_out", "checkOut", "departure", "date_to", "to", "end"]
        )

        check_in = self._parse_datetime(check_in_raw)
        check_out = self._parse_datetime(check_out_raw)

        room_name = self._pick(raw, ["room_name", "room", "roomName", "roomCode", "unitName"], "")
        status = self._pick(raw, ["status", "state", "reservation_status"], default="confirmed")
        pin = raw.get("pin") or self.previo_rest.get_pin(reservation_id)

        return Reservation(
            reservation_id=str(reservation_id),
            room_name=str(room_name),
            check_in=check_in,
            check_out=check_out,
            status=status,
            pin=pin,
        )

    def _process_reservation(self, hotel_id: str, reservation: Reservation) -> None:
        state_hash = self.state_store.compute_hash(
            {
                "reservation_id": reservation.reservation_id,
                "room_name": reservation.room_name,
                "check_in": reservation.check_in.isoformat(),
                "check_out": reservation.check_out.isoformat(),
                "pin": reservation.pin,
                "status": reservation.status,
            }
        )
        current_state = self.state_store.get_reservation_state(
            hotel_id, reservation.reservation_id
        )
        if current_state and current_state.hash == state_hash:
            LOG.info("Reservation %s unchanged; skipping", reservation.reservation_id)
            return

        valid_from, valid_until = self._to_loxone_range(
            reservation.check_in, reservation.check_out
        )

        user_payload = LoxoneUserPayload(
            name=f"plusconnect {reservation.reservation_id}",
            user_state=4,
            valid_from=valid_from,
            valid_until=valid_until,
            expiration_action=self.expiration_action,
            usergroups=self._resolve_groups(reservation.room_name),
            uuid=current_state.loxone_uuid if current_state else None,
        )
        add_edit_resp = self.loxone.add_or_edit_user(user_payload)
        user_uuid = add_edit_resp.get("LL", {}).get("value", {}).get("uuid") or (
            current_state.loxone_uuid if current_state else None
        )

        if reservation.status.lower() == "storno":
            # TODO: optionally disable/delete user depending on expiration_action.
            LOG.info("Reservation %s cancelled; handled per policy", reservation.reservation_id)
        else:
            self._set_access_code(user_uuid, reservation)

        self.state_store.upsert_reservation_state(
            hotel_id,
            reservation.reservation_id,
            state_hash,
            user_uuid,
            reservation.status,
        )

    def _to_loxone_range(self, check_in: datetime, check_out: datetime) -> (int, int):
        check_in_local = self.timezone.localize(check_in)
        check_out_local = self.timezone.localize(check_out)
        valid_from_unix = int(check_in_local.timestamp())
        valid_until_unix = int(
            (check_out_local + timedelta(minutes=self.checkout_buffer_minutes)).timestamp()
        )
        return (
            self.loxone.to_loxone_epoch(valid_from_unix),
            self.loxone.to_loxone_epoch(valid_until_unix),
        )

    def _resolve_groups(self, room_name: str):
        if self.room_group_mapping:
            return [self.room_group_mapping.get(room_name)]
        # Fallback: fetch once and cache from Loxone group list.
        groups = self.loxone.get_group_list()
        if room_name in groups:
            return [groups[room_name]]
        return []

    def _set_access_code(self, user_uuid: Optional[str], reservation: Reservation) -> None:
        if not user_uuid:
            LOG.warning("Cannot set access code; missing user UUID for %s", reservation.reservation_id)
            return
        resp = self.loxone.update_user_access_code(user_uuid, reservation.pin)
        code = resp.get("LL", {}).get("code")
        if code == 201:
            LOG.warning("PIN collision (201) for %s, retrying with refreshed PIN", reservation.reservation_id)
            new_pin = self.previo_rest.get_pin(reservation.reservation_id)
            self.loxone.update_user_access_code(user_uuid, new_pin)
        elif code and code != 200:
            LOG.error("Unexpected response when setting PIN for %s: %s", reservation.reservation_id, resp)

    def _pick(self, raw: Dict, keys, default=None):
        for key in keys:
            if key in raw and raw[key] not in (None, ""):
                return raw[key]
        return default

    def _parse_datetime(self, value) -> datetime:
        if value is None:
            raise ValueError("Missing datetime value")
        if isinstance(value, datetime):
            dt = value
        else:
            normalized = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
        if dt.tzinfo:
            dt = dt.astimezone(self.timezone).replace(tzinfo=None)
        return dt
