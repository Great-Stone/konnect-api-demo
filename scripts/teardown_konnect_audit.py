import json
import os
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT_DIR / ".runtime" / "konnect_audit_state.json"


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


def main():
    token = os.environ.get("KONNECT_TOKEN", "").strip()
    if not token or not STATE_FILE.exists():
        return

    state = json.loads(STATE_FILE.read_text())
    previous = state.get("previous_webhook") or {}
    regional_api_base = state.get("regional_api_base", "https://us.api.konghq.com").rstrip("/")
    global_api_base = state.get("global_api_base", "https://global.api.konghq.com").rstrip("/")
    destination_id = state.get("destination_id")

    try:
        if previous:
            payload = {
                "audit_log_destination_id": previous.get("audit_log_destination_id"),
                "enabled": bool(previous.get("enabled")),
            }
            api_json("PATCH", f"{regional_api_base}/v3/audit-log-webhook", token, payload)
        else:
            api_json(
                "PATCH",
                f"{regional_api_base}/v3/audit-log-webhook",
                token,
                {"audit_log_destination_id": destination_id, "enabled": False},
            )
    except urllib.error.HTTPError:
        pass

    if destination_id:
        try:
            delete_resource(f"{global_api_base}/v3/audit-log-destinations/{destination_id}", token)
        except urllib.error.HTTPError:
            pass

    STATE_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
