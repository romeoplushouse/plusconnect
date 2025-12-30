import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from mysql.connector import MySQLConnection


@dataclass
class ReservationState:
    reservation_id: str
    hash: str
    loxone_uuid: Optional[str]
    last_status: str
    updated_at: datetime


class StateStore:
    def __init__(self, conn: MySQLConnection):
        self.conn = conn

    def get_last_synced_at(self, hotel_id: str) -> Optional[datetime]:
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT last_synced_at FROM hotel_state WHERE hotel_id = %s", (hotel_id,)
        )
        row = cursor.fetchone()
        return row["last_synced_at"] if row else None

    def update_last_synced_at(self, hotel_id: str, ts: datetime) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO hotel_state (hotel_id, last_synced_at, created_at, updated_at)
            VALUES (%s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE last_synced_at = VALUES(last_synced_at), updated_at = NOW()
            """,
            (hotel_id, ts),
        )

    def get_reservation_state(self, hotel_id: str, reservation_id: str) -> Optional[ReservationState]:
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT reservation_id, hash, loxone_uuid, last_status, updated_at
            FROM reservations_state WHERE hotel_id = %s AND reservation_id = %s
            """,
            (hotel_id, reservation_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return ReservationState(
            reservation_id=row["reservation_id"],
            hash=row["hash"],
            loxone_uuid=row["loxone_uuid"],
            last_status=row["last_status"],
            updated_at=row["updated_at"],
        )

    def upsert_reservation_state(
        self,
        hotel_id: str,
        reservation_id: str,
        hash_value: str,
        loxone_uuid: Optional[str],
        status: str,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO reservations_state (hotel_id, reservation_id, hash, loxone_uuid, last_status, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE hash = VALUES(hash), loxone_uuid = VALUES(loxone_uuid), last_status = VALUES(last_status), updated_at = NOW()
            """,
            (hotel_id, reservation_id, hash_value, loxone_uuid, status),
        )

    @staticmethod
    def compute_hash(reservation: Dict) -> str:
        payload = (
            f"{reservation.get('reservation_id')}"
            f"{reservation.get('room_name')}"
            f"{reservation.get('check_in')}"
            f"{reservation.get('check_out')}"
            f"{reservation.get('pin')}"
            f"{reservation.get('status')}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_window(last_synced: Optional[datetime], overlap_minutes: int = 3) -> Dict[str, datetime]:
        now = datetime.now(timezone.utc)
        if last_synced is None:
            return {"modified_from": now - timedelta(minutes=5), "modified_to": now}
        return {
            "modified_from": last_synced - timedelta(minutes=overlap_minutes),
            "modified_to": now,
        }

