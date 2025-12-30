import time
from dataclasses import dataclass
from typing import Dict

import requests


@dataclass
class ServiceHealth:
    status: str
    latency_ms: float
    detail: str = ""


class HealthChecker:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def check_endpoint(self, url: str, auth=None) -> ServiceHealth:
        started = time.time()
        try:
            resp = requests.get(url, auth=auth, timeout=self.timeout)
            latency = (time.time() - started) * 1000
            return ServiceHealth(
                status="ok" if resp.ok else "error",
                latency_ms=latency,
                detail=str(resp.status_code),
            )
        except Exception as exc:
            latency = (time.time() - started) * 1000
            return ServiceHealth(status="error", latency_ms=latency, detail=str(exc))

