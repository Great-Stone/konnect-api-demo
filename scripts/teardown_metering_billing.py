#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


KONNECT_SERVER_URL = os.environ.get("KONNECT_SERVER_URL", "https://us.api.konghq.com").rstrip("/")
SYSTEM_TOKEN = os.environ.get("KONNECT_SYSTEM_TOKEN", "").strip()

METER_KEYS = [
    "demo_api_requests_total",
]

CUSTOMER_KEYS = [
    "demo-acme-enterprise-consumer",
    "demo-department-engineering",
    "demo-consumer-metering",
    "demo-tenant-acme",
]


def load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_env(name: str, value: str) -> str:
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def api_request(method: str, path: str, payload: dict | None = None) -> dict | list:
    token = require_env("KONNECT_SYSTEM_TOKEN", SYSTEM_TOKEN)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{KONNECT_SERVER_URL}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            return {}
        raise RuntimeError(f"{method} {path} failed with {exc.code}: {raw}") from exc


def list_customers() -> list[dict]:
    existing = api_request("GET", "/v3/openmeter/customers")
    return existing.get("items") or existing.get("data") or []


def list_meters() -> list[dict]:
    existing = api_request("GET", "/v3/openmeter/meters")
    return existing.get("items") or existing.get("data") or []


def delete_customer(customer_id: str) -> str:
    api_request("DELETE", f"/v3/openmeter/customers/{customer_id}")
    return "deleted"


def delete_meter(meter_id: str) -> str:
    api_request("DELETE", f"/v3/openmeter/meters/{meter_id}")
    return "deleted"


def main() -> int:
    load_dotenv()
    global KONNECT_SERVER_URL, SYSTEM_TOKEN
    KONNECT_SERVER_URL = os.environ.get("KONNECT_SERVER_URL", KONNECT_SERVER_URL).rstrip("/")
    SYSTEM_TOKEN = os.environ.get("KONNECT_SYSTEM_TOKEN", SYSTEM_TOKEN).strip()
    require_env("KONNECT_SYSTEM_TOKEN", SYSTEM_TOKEN)

    customer_results: dict[str, str] = {}
    meter_results: dict[str, str] = {}

    target_customer_keys = set(CUSTOMER_KEYS)
    for customer in list_customers():
        key = customer.get("key")
        if key in target_customer_keys:
            customer_id = customer.get("id") or key
            customer_results[key] = delete_customer(customer_id)

    target_meter_keys = set(METER_KEYS)
    for meter in list_meters():
        key = meter.get("key")
        if key in target_meter_keys:
            meter_id = meter.get("id") or key
            meter_results[key] = delete_meter(meter_id)

    print(json.dumps({"customers": customer_results, "meters": meter_results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
