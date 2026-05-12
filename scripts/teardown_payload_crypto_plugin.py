import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT_DIR / ".runtime" / "payload_crypto_plugin_state.json"
PLUGIN_NAME = "payload-crypto-demo"
SSL_CONTEXT = ssl._create_unverified_context()


def delete_resource(url: str, token: str):
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="DELETE",
    )
    with urllib.request.urlopen(request, timeout=20, context=SSL_CONTEXT):
        return


def main():
    token = os.environ.get("KONNECT_TOKEN", "").strip()
    if not token or not STATE_FILE.exists():
        return

    state = json.loads(STATE_FILE.read_text())
    regional_api_base = state["regional_api_base"].rstrip("/")
    control_plane_id = state["control_plane_id"]
    route_id = state.get("route_id")
    plugin_id = state.get("plugin_id")
    base = f"{regional_api_base}/v2/control-planes/{control_plane_id}/core-entities"

    if route_id and plugin_id:
        try:
            delete_resource(f"{base}/routes/{route_id}/plugins/{plugin_id}", token)
        except urllib.error.HTTPError:
            pass

    try:
        delete_resource(f"{base}/plugin-schemas/{PLUGIN_NAME}", token)
    except urllib.error.HTTPError:
        pass

    STATE_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
