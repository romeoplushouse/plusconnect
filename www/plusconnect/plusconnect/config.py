import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class LoxoneConfig:
    base_url: str
    username: str
    password: str


@dataclass
class PrevioXmlConfig:
    base_url: str
    username: str
    password: str


@dataclass
class PrevioRestConfig:
    base_url: str
    token: str = ""
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class HotelConfig:
    hotel_id: str
    previo_hotel_id: str
    timezone: str
    checkout_buffer_minutes: int
    expiration_action: int
    loxone: LoxoneConfig
    previo_xml: PrevioXmlConfig
    previo_rest: PrevioRestConfig
    room_group_mapping: Dict[str, str]


@dataclass
class DbConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_hotel_config(path: str) -> List[HotelConfig]:
    raw = load_yaml(path)
    hotels = []
    for item in raw.get("hotels", []):
        hotels.append(
            HotelConfig(
                hotel_id=item["id"],
                previo_hotel_id=str(item.get("previo_hotel_id", "")),
                timezone=item.get("timezone", "Europe/Prague"),
                checkout_buffer_minutes=item.get("checkout_buffer_minutes", 60),
                expiration_action=item.get("expiration_action", 0),
                loxone=LoxoneConfig(**item["loxone"]),
                previo_xml=PrevioXmlConfig(**item["previo"]["xml"]),
                previo_rest=PrevioRestConfig(**item["previo"]["rest"]),
                room_group_mapping=item.get("room_group_mapping", {}),
            )
        )
    return hotels


def load_db_config(path: str) -> DbConfig:
    raw = load_yaml(path)
    return DbConfig(
        host=raw["host"],
        port=int(raw.get("port", 3306)),
        user=raw["user"],
        password=raw["password"],
        database=raw["database"],
    )


def resolve_config_path(config_path: str) -> Path:
    path = Path(config_path)
    if path.is_file():
        return path
    resolved = Path(__file__).resolve().parent
    candidate = resolved / config_path
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"Config file not found at {config_path}")
