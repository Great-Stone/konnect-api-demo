#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


KONNECT_SERVER_URL = os.environ.get("KONNECT_SERVER_URL", "https://us.api.konghq.com").rstrip("/")
SYSTEM_TOKEN = os.environ.get("KONNECT_SYSTEM_TOKEN", "").strip()
KONG_PROXY_URL = os.environ.get("KONG_PROXY_URL", "http://localhost:8000").rstrip("/")
BOOTSTRAP_READY_TIMEOUT_SECONDS = int(os.environ.get("KONNECT_METERING_BOOTSTRAP_TIMEOUT_SECONDS", "90"))
BOOTSTRAP_READY_POLL_SECONDS = float(os.environ.get("KONNECT_METERING_BOOTSTRAP_POLL_SECONDS", "3"))

METER_SPECS = [
    {
        "key": "demo_api_requests_total",
        "name": "Demo API Requests",
        "event_type": "request",
        "aggregation": "count",
        "dimensions": {
            "method": "$.method",
            "route": "$.route",
        },
    },
]

CUSTOMER_SPECS = [
    {
        "key": "demo-acme-enterprise-consumer",
        "name": "Demo ACME Enterprise Consumer",
        "subject": "acme-enterprise-consumer",
    },
    {
        "key": "demo-department-engineering",
        "name": "Demo Department Engineering",
        "subject": "engineering",
    },
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
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv()
KONNECT_SERVER_URL = os.environ.get("KONNECT_SERVER_URL", KONNECT_SERVER_URL).rstrip("/")
SYSTEM_TOKEN = os.environ.get("KONNECT_SYSTEM_TOKEN", SYSTEM_TOKEN).strip()
KONG_PROXY_URL = os.environ.get("KONG_PROXY_URL", KONG_PROXY_URL).rstrip("/")


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
        if exc.code == 404 and method == "GET":
            return {}
        raise RuntimeError(f"{method} {path} failed with {exc.code}: {raw}") from exc


def ensure_meter(spec: dict) -> str:
    existing = api_request("GET", "/v3/openmeter/meters")
    items = existing.get("items") or existing.get("data") or []
    for item in items:
        if item.get("key") == spec["key"]:
            return "exists"
    api_request("POST", "/v3/openmeter/meters", spec)
    return "created"


def ensure_customer(spec: dict) -> str:
    existing = api_request("GET", "/v3/openmeter/customers")
    items = existing.get("items") or existing.get("data") or []
    for item in items:
        if item.get("key") == spec["key"]:
            current_subject_keys = (
                item.get("usageAttribution", {}).get("subjectKeys")
                or item.get("usage_attribution", {}).get("subject_keys")
                or []
            )
            expected_subject_keys = [spec["subject"]]
            if current_subject_keys == expected_subject_keys:
                return "exists"
            payload = {
                "name": spec["name"],
                "key": spec["key"],
                "usageAttribution": {"subjectKeys": expected_subject_keys},
            }
            customer_id = item.get("id") or spec["key"]
            api_request("PUT", f"/v3/openmeter/customers/{customer_id}", payload)
            return "updated"
    payload = {
        "name": spec["name"],
        "key": spec["key"],
        "usageAttribution": {"subjectKeys": [spec["subject"]]},
    }
    api_request("POST", "/v3/openmeter/customers", payload)
    return "created"


def emit_bootstrap_requests() -> list[dict]:
    requests = [
        {
            "url": f"{KONG_PROXY_URL}/orders/metering/consumer",
            "headers": {
                "Accept": "application/json",
                "apikey": "key-acme-enterprise-consumer",
                "x-request-id": "metering-bootstrap-consumer",
            },
        },
        {
            "url": f"{KONG_PROXY_URL}/orders/metering/tenant",
            "headers": {
                "Accept": "application/json",
                "x-department": "engineering",
                "x-request-id": "metering-bootstrap-tenant",
            },
        },
    ]
    results = []
    for item in requests:
        status = wait_for_bootstrap_route(item["url"], item["headers"])
        results.append({"url": item["url"], "status": status})
    return results


def issue_request(url: str, headers: dict[str, str]) -> int:
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            response.read()
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def wait_for_bootstrap_route(url: str, headers: dict[str, str]) -> int:
    deadline = time.time() + BOOTSTRAP_READY_TIMEOUT_SECONDS
    last_status = None
    while time.time() < deadline:
        status = issue_request(url, headers)
        last_status = status
        if status == 200:
            return status
        if status not in (404, 503, 504):
            return status
        time.sleep(BOOTSTRAP_READY_POLL_SECONDS)
    return last_status or 0


def main() -> int:
    require_env("KONNECT_SYSTEM_TOKEN", SYSTEM_TOKEN)

    meter_results = {spec["key"]: ensure_meter(spec) for spec in METER_SPECS}
    customer_results = {spec["key"]: ensure_customer(spec) for spec in CUSTOMER_SPECS}
    bootstrap_results = emit_bootstrap_requests()
    time.sleep(2)

    print(
        json.dumps(
            {
                "bootstrap_requests": bootstrap_results,
                "meters": meter_results,
                "customers": customer_results,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
