import sys
import unittest
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Make plusconnect importable when running from repo root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from plusconnect.clients.loxone import LoxoneClient, LoxoneUserPayload  # noqa: E402
from plusconnect.clients.previo_rest import PrevioRestClient  # noqa: E402
from plusconnect.clients.previo_xml import PrevioXmlClient  # noqa: E402
from plusconnect.services.sync_service import Reservation, SyncService  # noqa: E402


class FakeStateStore:
    def __init__(self):
        self.last_synced_at = None
        self.upserts = []

    def get_last_synced_at(self, hotel_id: str):
        return self.last_synced_at

    @staticmethod
    def compute_window(last_synced, overlap_minutes: int = 3):
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 5, 0)
        return {"modified_from": start, "modified_to": end}

    @staticmethod
    def compute_hash(reservation: Dict) -> str:
        return f"hash-{reservation.get('reservation_id')}"

    def get_reservation_state(self, hotel_id: str, reservation_id: str):
        return None

    def update_last_synced_at(self, hotel_id: str, ts: datetime):
        self.last_synced_at = ts

    def upsert_reservation_state(
        self, hotel_id: str, reservation_id: str, hash_value: str, loxone_uuid: Optional[str], status: str
    ):
        self.upserts.append((hotel_id, reservation_id, hash_value, loxone_uuid, status))


class FakePrevioXml(PrevioXmlClient):
    def __init__(self, reservations):
        self.reservations = reservations
        self.calls = []

    def search_reservations(self, modified_from: str, modified_to: str):
        self.calls.append((modified_from, modified_to))
        return self.reservations


class FakePrevioRest(PrevioRestClient):
    def __init__(self, pins: Dict[str, str]):
        self.pins = pins
        self.pin_calls = []

    def get_pin(self, reservation_id: str) -> str:
        self.pin_calls.append(reservation_id)
        return self.pins[reservation_id]


class FakeLoxone(LoxoneClient):
    def __init__(self, groups: Dict[str, str]):
        self.groups = groups
        self.add_edit_calls = []
        self.access_code_calls = []

    def get_group_list(self) -> Dict[str, str]:
        return self.groups

    def add_or_edit_user(self, payload: LoxoneUserPayload) -> dict:
        self.add_edit_calls.append(payload)
        return {"LL": {"value": {"uuid": "lox-user-123"}}}

    def update_user_access_code(self, user_uuid: str, access_code: str) -> dict:
        self.access_code_calls.append((user_uuid, access_code))
        return {"LL": {"code": 200}}


class SyncServiceTests(unittest.TestCase):
    def test_sync_fetches_pin_and_sets_access_code(self):
        reservations = [
            {
                "reservation_id": "abc",
                "room_name": "K1",
                "check_in": "2024-01-02T10:00:00",
                "check_out": "2024-01-03T10:00:00",
                "status": "confirmed",
            }
        ]
        fake_state = FakeStateStore()
        fake_previo_xml = FakePrevioXml(reservations)
        fake_previo_rest = FakePrevioRest({"abc": "123456"})
        fake_loxone = FakeLoxone({"K1": "uuid-k1"})

        service = SyncService(
            loxone=fake_loxone,
            previo_xml=fake_previo_xml,
            previo_rest=fake_previo_rest,
            state_store=fake_state,
            timezone="Europe/Prague",
            checkout_buffer_minutes=60,
            expiration_action=0,
            room_group_mapping={"K1": "uuid-k1"},
        )

        service.sync("moravskygrunt", overlap_minutes=0)

        self.assertEqual(fake_previo_xml.calls[0][0], "2024-01-01T12:00:00")
        self.assertEqual(fake_previo_xml.calls[0][1], "2024-01-01T12:05:00")
        self.assertEqual(fake_previo_rest.pin_calls, ["abc"])
        self.assertEqual(len(fake_loxone.add_edit_calls), 1)
        self.assertEqual(fake_loxone.add_edit_calls[0].usergroups, ["uuid-k1"])
        self.assertEqual(fake_loxone.access_code_calls[0][1], "123456")
        self.assertEqual(fake_state.upserts[0][0], "moravskygrunt")

    def test_sync_skips_pin_for_storno_and_no_access_code(self):
        reservations = [
            {
                "reservation_id": "st1",
                "room_name": "K2",
                "check_in": "2024-01-02T10:00:00",
                "check_out": "2024-01-03T10:00:00",
                "status": "storno",
            }
        ]
        fake_state = FakeStateStore()
        fake_previo_xml = FakePrevioXml(reservations)
        fake_previo_rest = FakePrevioRest({"st1": "should-not-be-used"})
        fake_loxone = FakeLoxone({"K2": "uuid-k2"})

        service = SyncService(
            loxone=fake_loxone,
            previo_xml=fake_previo_xml,
            previo_rest=fake_previo_rest,
            state_store=fake_state,
            timezone="Europe/Prague",
            checkout_buffer_minutes=60,
            expiration_action=0,
            room_group_mapping={"K2": "uuid-k2"},
        )

        service.sync("moravskygrunt", overlap_minutes=0)

        self.assertEqual(fake_previo_rest.pin_calls, [])
        self.assertEqual(fake_loxone.access_code_calls, [])
        self.assertEqual(fake_state.upserts[0][4], "storno")


if __name__ == "__main__":
    unittest.main()
