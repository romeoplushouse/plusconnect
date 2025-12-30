"""
Lightweight API skeleton for dashboard consumption.
Requires FastAPI + Uvicorn. Endpoints are placeholders and should be wired to DB.
"""

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
    # TODO: read from service_health table
    return {"hotel_id": hotel_id, "loxone": "unknown", "previo": "unknown"}


@app.get("/runs/{hotel_id}")
def runs(hotel_id: str, limit: int = 20, db=Depends(get_db)):
    # TODO: query sync_runs
    return {"hotel_id": hotel_id, "runs": [], "limit": limit}


@app.get("/logs/{hotel_id}")
def logs(hotel_id: str, limit: int = 50, db=Depends(get_db)):
    # TODO: query sync_logs with pagination/filter
    return {"hotel_id": hotel_id, "logs": [], "limit": limit}

