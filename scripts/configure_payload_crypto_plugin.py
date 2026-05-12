import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT_DIR / ".runtime"
STATE_FILE = RUNTIME_DIR / "payload_crypto_plugin_state.json"
PLUGIN_NAME = "payload-crypto-demo"
ROUTE_NAME = "route-orders-payload-crypto"
SCHEMA_PATH = ROOT_DIR / "kong_plugins" / "kong" / "plugins" / PLUGIN_NAME / "schema.lua"
SSL_CONTEXT = ssl._create_unverified_context()


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} must be set")
    return value


def derive_regional_api_base(default_base: str) -> str:
    cluster_server = os.environ.get("KONNECT_CLUSTER_SERVER_NAME", "")
    parts = cluster_server.split(".")
    if len(parts) >= 3 and parts[1]:
        return f"https://{parts[1]}.api.konghq.com"
    return default_base


def api_json(method: str, url: str, token: str, payload: dict | None = None):
    request = urllib.request.Request(
        url,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20, context=SSL_CONTEXT) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            raise
        raise SystemExit(f"{method} {url} failed with {exc.code}: {error_body}") from exc


def api_get_or_none(url: str, token: str):
    try:
        return api_json("GET", url, token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def main():
    token = require_env("KONNECT_TOKEN")
    control_plane_id = require_env("KONNECT_CP_ID")
    helper_url = os.environ.get("PAYLOAD_CRYPTO_HELPER_URL", "http://crypto-helper:8092").strip()
    regional_api_base = derive_regional_api_base(
        os.environ.get("KONNECT_REGIONAL_API_BASE_URL", "https://us.api.konghq.com").rstrip("/")
    )
    control_plane_base = f"{regional_api_base}/v2/control-planes/{control_plane_id}/core-entities"
    schema_lua = SCHEMA_PATH.read_text("utf-8")

    RUNTIME_DIR.mkdir(exist_ok=True)

    schema_url = f"{control_plane_base}/plugin-schemas/{PLUGIN_NAME}"
    existing_schema = api_get_or_none(schema_url, token)
    if existing_schema is None:
        api_json("POST", f"{control_plane_base}/plugin-schemas", token, {"lua_schema": schema_lua})
    elif existing_schema.get("lua_schema") != schema_lua:
        api_json("PUT", schema_url, token, {"lua_schema": schema_lua})

    routes = api_json("GET", f"{control_plane_base}/routes?size=1000", token)
    route_items = routes.get("data") or routes.get("items") or []
    route = next((item for item in route_items if item.get("name") == ROUTE_NAME), None)
    if route is None:
        raise SystemExit(f"Could not find route {ROUTE_NAME}")

    route_id = route["id"]
    plugins_url = f"{control_plane_base}/routes/{route_id}/plugins"
    plugins = api_json("GET", f"{plugins_url}?size=1000", token)
    plugin_items = plugins.get("data") or plugins.get("items") or []
    existing_plugin = next((item for item in plugin_items if item.get("name") == PLUGIN_NAME), None)
    plugin_payload = {
        "name": PLUGIN_NAME,
        "config": {
            "helper_url": helper_url,
            "algorithm": "AES/CBC/PKCS5Padding",
        },
    }
    if existing_plugin is None:
        created = api_json("POST", plugins_url, token, plugin_payload)
        plugin_id = created["id"]
    else:
        plugin_id = existing_plugin["id"]
        api_json("PUT", f"{plugins_url}/{plugin_id}", token, plugin_payload)

    STATE_FILE.write_text(
        json.dumps(
            {
                "regional_api_base": regional_api_base,
                "control_plane_id": control_plane_id,
                "route_id": route_id,
                "plugin_id": plugin_id,
            },
            indent=2,
        )
    )
    print(json.dumps({"route_id": route_id, "plugin_id": plugin_id}, indent=2))


if __name__ == "__main__":
    main()
