from dataclasses import dataclass
from typing import Dict, Optional

import requests

LOXONE_EPOCH_OFFSET = 1230768000


@dataclass
class LoxoneUserPayload:
    name: str
    user_state: int
    valid_from: int
    valid_until: int
    expiration_action: int
    usergroups: Optional[list]
    uuid: Optional[str] = None

    def to_json(self) -> dict:
        payload = {
            "name": self.name,
            "userState": self.user_state,
            "validFrom": self.valid_from,
            "validUntil": self.valid_until,
            "expirationAction": self.expiration_action,
        }
        if self.usergroups is not None:
            payload["usergroups"] = self.usergroups
        if self.uuid:
            payload["uuid"] = self.uuid
        return payload


class LoxoneClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)
        self.timeout = timeout

    def get_group_list(self) -> Dict[str, str]:
        resp = requests.get(
            f"{self.base_url}/jdev/sps/getgrouplist",
            auth=self.auth,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        # TODO: adapt parsing to actual Loxone response format.
        return {g["name"]: g["uuid"] for g in data.get("LL", {}).get("value", [])}

    def add_or_edit_user(self, payload: LoxoneUserPayload) -> dict:
        resp = requests.get(
            f"{self.base_url}/jdev/sps/addoredituser/{payload.to_json()}",
            auth=self.auth,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def update_user_access_code(self, user_uuid: str, access_code: str) -> dict:
        resp = requests.get(
            f"{self.base_url}/jdev/sps/updateuseraccesscode/{user_uuid}/{access_code}",
            auth=self.auth,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def to_loxone_epoch(unix_ts: int) -> int:
        return unix_ts - LOXONE_EPOCH_OFFSET

