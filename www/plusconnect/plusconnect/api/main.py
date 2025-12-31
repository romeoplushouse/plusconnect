"""
Lightweight API skeleton for dashboard consumption.
Requires FastAPI + Uvicorn. Endpoints are placeholders and should be wired to DB.
"""

from typing import List

from fastapi import Depends, FastAPI, HTTPException

from ..config import DbConfig, load_db_config
from ..db import db_session

app = FastAPI(title="PlusConnect Dashboard API")


def get_db(cfg: DbConfig = Depends(lambda: load_db_config("db.yaml"))):
    # In production, inject path via environment or CLI.
    with db_session(cfg) as state:
        yield state.connection


@app.get("/health/{hotel_id}")
def health(hotel_id: str, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT hotel_id, loxone_status, previo_xml_status, previo_rest_status,
               loxone_latency_ms, previo_xml_latency_ms, previo_rest_latency_ms,
               checked_at
        FROM service_health
        WHERE hotel_id = %s
        ORDER BY checked_at DESC
        LIMIT 1
        """,
        (hotel_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No health record found")
    row["checked_at"] = row["checked_at"].isoformat()
    return row


@app.get("/runs/{hotel_id}")
def runs(hotel_id: str, limit: int = 20, db=Depends(get_db)):
    safe_limit = max(1, min(limit, 500))
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, started_at, finished_at, status, processed, changed, errors_count, message
        FROM sync_runs
        WHERE hotel_id = %s
        ORDER BY started_at DESC
        LIMIT %s
        """,
        (hotel_id, safe_limit),
    )
    rows = cursor.fetchall()
    runs: List[dict] = []
    for row in rows:
        row["started_at"] = row["started_at"].isoformat()
        row["finished_at"] = row["finished_at"].isoformat() if row["finished_at"] else None
        runs.append(row)
    return {"hotel_id": hotel_id, "runs": runs, "limit": safe_limit}


@app.get("/logs/{hotel_id}")
def logs(hotel_id: str, limit: int = 50, db=Depends(get_db)):
    safe_limit = max(1, min(limit, 1000))
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, timestamp, level, source, code, reservation_id, message
        FROM sync_logs
        WHERE hotel_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
        """,
        (hotel_id, safe_limit),
    )
    rows = cursor.fetchall()
    log_rows: List[dict] = []
    for row in rows:
        row["timestamp"] = row["timestamp"].isoformat()
        log_rows.append(row)
    return {"hotel_id": hotel_id, "logs": log_rows, "limit": safe_limit}
