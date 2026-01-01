#!/usr/bin/env python3
"""
CLI entrypoint for multi-hotel sync.

Usage:
  python sync.py --config ../../secret/<hotel>/config/config.yaml --db-config ../../secret/<hotel>/config/db.yaml --hotel-id <hotel_id>
"""

import argparse
import logging
from datetime import datetime

from plusconnect.clients.loxone import LoxoneClient
from plusconnect.clients.previo_rest import PrevioRestClient
from plusconnect.clients.previo_xml import PrevioXmlClient
from plusconnect.config import DbConfig, load_db_config, load_hotel_config, resolve_config_path
from plusconnect.db import db_session
from plusconnect.services.state_store import StateStore
from plusconnect.services.sync_service import SyncService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
LOG = logging.getLogger("sync")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PlusConnect sync")
    parser.add_argument("--config", required=True, help="Path to hotel config YAML")
    parser.add_argument("--db-config", required=True, help="Path to DB config YAML")
    parser.add_argument("--hotel-id", help="Hotel ID to sync; if not set, sync all")
    parser.add_argument("--overlap", type=int, default=3, help="Overlap minutes for modified window")
    return parser.parse_args()


def main():
    args = parse_args()
    hotel_cfg_path = resolve_config_path(args.config)
    db_cfg = load_db_config(args.db_config)
    hotels = load_hotel_config(hotel_cfg_path)
    target_hotels = [h for h in hotels if not args.hotel_id or h.hotel_id == args.hotel_id]
    if not target_hotels:
        raise SystemExit("No matching hotels found for provided hotel-id")

    for hotel in target_hotels:
        LOG.info("Starting sync for hotel %s", hotel.hotel_id)
        with db_session(db_cfg) as state:
            store = StateStore(state.connection)
            loxone_client = LoxoneClient(
                base_url=hotel.loxone.base_url,
                username=hotel.loxone.username,
                password=hotel.loxone.password,
            )
            previo_xml = PrevioXmlClient(
                base_url=hotel.previo_xml.base_url,
                username=hotel.previo_xml.username,
                password=hotel.previo_xml.password,
                hotel_id=hotel.previo_hotel_id,
            )
            previo_rest = PrevioRestClient(
                base_url=hotel.previo_rest.base_url,
                token=hotel.previo_rest.token,
                username=hotel.previo_rest.username,
                password=hotel.previo_rest.password,
                hotel_id=hotel.previo_hotel_id,
            )
            sync_service = SyncService(
                loxone=loxone_client,
                previo_xml=previo_xml,
                previo_rest=previo_rest,
                state_store=store,
                timezone=hotel.timezone,
                checkout_buffer_minutes=hotel.checkout_buffer_minutes,
                expiration_action=hotel.expiration_action,
                room_group_mapping=hotel.room_group_mapping,
            )
            sync_service.sync(hotel.hotel_id, overlap_minutes=args.overlap)
        LOG.info("Finished sync for hotel %s", hotel.hotel_id)


if __name__ == "__main__":
    main()
