import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT_DIR / ".runtime"
STATE_FILE = RUNTIME_DIR / "konnect_audit_state.json"
DESTINATION_NAME_PREFIX = "konnect-api-demo-audit"


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} must be set")
    return value


def api_json(method: str, url: str, token: str, payload: dict | None = None):
    request = urllib.request.Request(
        url,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def delete_resource(url: str, token: str):
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="DELETE")
    with urllib.request.urlopen(request, timeout=20):
        return


def derive_regional_api_base(default_base: str) -> str:
    cluster_server = os.environ.get("KONNECT_CLUSTER_SERVER_NAME", "")
    parts = cluster_server.split(".")
    if len(parts) >= 3:
        region = parts[1]
        if region:
            return f"https://{region}.api.konghq.com"
    return default_base


def main():
    token = require_env("KONNECT_TOKEN")
    public_url = require_env("KONNECT_AUDIT_PUBLIC_URL")
    shared_secret = require_env("KONNECT_AUDIT_SHARED_SECRET")
    global_api_base = os.environ.get("KONNECT_GLOBAL_API_BASE_URL", "https://global.api.konghq.com").rstrip("/")
    regional_api_base = derive_regional_api_base(
        os.environ.get("KONNECT_REGIONAL_API_BASE_URL", "https://us.api.konghq.com").rstrip("/")
    )
    endpoint = public_url.rstrip("/") + "/konnect/audit"
    destination_name = f"{DESTINATION_NAME_PREFIX}-{socket.gethostname().lower()}"

    RUNTIME_DIR.mkdir(exist_ok=True)

    previous_webhook = {}
    try:
        previous_webhook = api_json("GET", f"{regional_api_base}/v3/audit-log-webhook", token)
    except urllib.error.HTTPError:
        previous_webhook = {}

    try:
        destinations = api_json("GET", f"{global_api_base}/v3/audit-log-destinations", token)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Could not list audit log destinations: {exc}") from exc

    items = destinations.get("data") or destinations.get("items") or destinations.get("results") or []
    for destination in items:
        if str(destination.get("name", "")).startswith(DESTINATION_NAME_PREFIX):
            destination_id = destination.get("id")
            if destination_id:
                try:
                    delete_resource(f"{global_api_base}/v3/audit-log-destinations/{destination_id}", token)
                except urllib.error.HTTPError:
                    pass

    destination_payload = {
        "endpoint": endpoint,
        "authorization": shared_secret,
        "log_format": "json",
        "name": destination_name,
    }
    try:
        created_destination = api_json(
            "POST",
            f"{global_api_base}/v3/audit-log-destinations",
            token,
            destination_payload,
        )
    except urllib.error.HTTPError as exc:
        if exc.code != 409:
            raise
        destinations = api_json("GET", f"{global_api_base}/v3/audit-log-destinations", token)
        items = destinations.get("data") or destinations.get("items") or destinations.get("results") or []
        created_destination = next(
            (destination for destination in items if destination.get("name") == destination_name),
            None,
        )
        if created_destination is None:
            raise
    destination_id = created_destination["id"]

    api_json(
        "PATCH",
        f"{regional_api_base}/v3/audit-log-webhook",
        token,
        {
            "audit_log_destination_id": destination_id,
            "enabled": True,
        },
    )

    STATE_FILE.write_text(
        json.dumps(
            {
                "destination_id": destination_id,
                "destination_name": destination_name,
                "endpoint": endpoint,
                "previous_webhook": previous_webhook,
                "regional_api_base": regional_api_base,
                "global_api_base": global_api_base,
            },
            indent=2,
        )
    )

    print(json.dumps({"destination_id": destination_id, "endpoint": endpoint}, indent=2))


if __name__ == "__main__":
    main()
