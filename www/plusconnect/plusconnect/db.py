import contextlib
from dataclasses import dataclass
from typing import Generator, Optional

import mysql.connector
from mysql.connector import MySQLConnection

from .config import DbConfig


@dataclass
class DbState:
    connection: MySQLConnection


def create_connection(cfg: DbConfig) -> MySQLConnection:
    return mysql.connector.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        autocommit=False,
    )


@contextlib.contextmanager
def db_session(cfg: DbConfig) -> Generator[DbState, None, None]:
    conn: Optional[MySQLConnection] = None
    try:
        conn = create_connection(cfg)
        yield DbState(connection=conn)
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

