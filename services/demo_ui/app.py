import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
IMG_DIR = Path("/img")
KONG_PROXY_URL = os.environ.get("KONG_PROXY_URL", "http://localhost:8000")
DEMO_LOGS_URL = os.environ.get("DEMO_LOGS_URL", "https://cloud.konghq.com")
DEMO_AUDIT_URL = os.environ.get("DEMO_AUDIT_URL", "https://cloud.konghq.com")
DOCKER_SOCKET_PATH = os.environ.get("DOCKER_SOCKET_PATH", "/var/run/docker.sock")
AD_PROTECTED_API_TENANT_ID = os.environ.get("AD_PROTECTED_API_TENANT_ID", "")
AD_PROTECTED_API_AUDIENCE = os.environ.get("AD_PROTECTED_API_AUDIENCE", "")
AD_CONSUMER1_CLIENT_ID = os.environ.get("AD_CONSUMER1_CLIENT_ID", "")
AD_CONSUMER1_SECRET = os.environ.get("AD_CONSUMER1_SECRET", "")
AD_CONSUMER2_CLIENT_ID = os.environ.get("AD_CONSUMER2_CLIENT_ID", "")
AD_CONSUMER2_SECRET = os.environ.get("AD_CONSUMER2_SECRET", "")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "kong-demo")
KEYCLOAK_CONSUMER1_CLIENT_ID = os.environ.get("KEYCLOAK_CONSUMER1_CLIENT_ID", "consumer-1")
KEYCLOAK_CONSUMER1_SECRET = os.environ.get("KEYCLOAK_CONSUMER1_SECRET", "consumer-1-secret")
KEYCLOAK_CONSUMER2_CLIENT_ID = os.environ.get("KEYCLOAK_CONSUMER2_CLIENT_ID", "consumer-2")
KEYCLOAK_CONSUMER2_SECRET = os.environ.get("KEYCLOAK_CONSUMER2_SECRET", "consumer-2-secret")
KEYCLOAK_INTERNAL_BASE_URL = os.environ.get("KEYCLOAK_INTERNAL_BASE_URL", "http://keycloak:8080")

SCENES = {
    "traffic-routing-header": {
        "id": "traffic-routing-header",
        "label": "Traffic and Routing: Header-Based Routing",
        "title": "Header-Based Routing",
        "services": [
            "svc-orders-header-east",
            "svc-orders-header-west",
            "svc-orders-header-missing-region",
        ],
        "routes": [
            "route-orders-header-east",
            "route-orders-header-west",
            "route-orders-header-catchall",
        ],
        "plugins": ["request-termination on route-orders-header-catchall"],
        "controlPlane": "Konnect control plane",
        "dataPlane": "Local hybrid data plane",
        "publicPath": "/orders",
        "routingHeader": "x-region",
        "architecture": [
            "Client requests enter the Kong data plane through a single public path.",
            "The local data plane receives its configuration from a Konnect-hosted control plane.",
            "Kong evaluates the x-region request header and forwards the request to the matching upstream service.",
        ],
    },
    "traffic-control-rate-limiting": {
        "id": "traffic-control-rate-limiting",
        "label": "Traffic Control: Rate Limiting",
        "title": "Service And Consumer Rate Limiting",
        "services": ["svc-orders-rate-anonymous", "svc-orders-rate-consumer"],
        "routes": ["route-orders-rate-anonymous", "route-orders-rate-consumer"],
        "plugins": [
            "rate-limiting-advanced on svc-orders-rate-anonymous",
            "key-auth on svc-orders-rate-consumer",
            "rate-limiting-advanced on consumer-gold",
            "rate-limiting-advanced on consumer-standard",
        ],
        "consumers": ["consumer-gold", "consumer-standard"],
        "controlPlane": "Konnect control plane",
        "dataPlane": "Local hybrid data plane",
        "publicPath": "/orders/rate/anonymous | /orders/rate/consumer",
        "routingHeader": "apikey",
        "architecture": [
            "Anonymous traffic is throttled by a service-level fixed-window policy with no consumer required.",
            "Consumer mode adds key-auth, resolves the Kong consumer, and applies a consumer-scoped fixed-window policy.",
            "The UI reads Kong response headers from the local data plane to show the active limit, remaining budget, and reset window.",
        ],
    },
    "resilience-failover-health-checks": {
        "id": "resilience-failover-health-checks",
        "label": "Resilience: Failover And Health Checks",
        "title": "Failover And Health Checks",
        "services": ["svc-orders-resilience-weighted", "svc-orders-circuit-breaker"],
        "routes": ["route-orders-resilience-weighted", "route-orders-circuit-breaker"],
        "upstreams": ["upstream-orders-weighted", "upstream-orders-circuit-breaker"],
        "plugins": ["Kong upstream active health checks", "Kong upstream passive health checks"],
        "controlPlane": "Konnect control plane",
        "dataPlane": "Local hybrid data plane",
        "publicPath": "/orders/resilience/weighted | /orders/resilience/circuit-breaker",
        "routingHeader": "none",
        "architecture": [
            "Weighted Load Balancing uses one Kong upstream with two targets weighted 30:70.",
            "Circuit Breaker uses one Kong upstream with two round-robin targets and both active and passive health checks.",
            "Stopping a backend container makes Kong mark that target unhealthy and remove it from load balancing until active checks recover it.",
        ],
        "scenarios": ["weighted-load-balancing", "circuit-breaker"],
    },
    "identity-azure-token-validation": {
        "id": "identity-azure-token-validation",
        "label": "Identity: Azure AD Token Validation",
        "title": "Azure AD Token Validation",
        "services": ["svc-orders-auth-azure"],
        "routes": ["route-orders-auth-azure"],
        "plugins": ["openid-connect on route-orders-auth-azure"],
        "controlPlane": "Konnect control plane",
        "dataPlane": "Local hybrid data plane",
        "publicPath": "/orders/auth/azure",
        "routingHeader": "authorization",
        "identityProvider": "Azure AD",
        "consumers": ["consumer-1", "consumer-2"],
        "architecture": [
            "The UI requests a client-credentials token from Azure AD and lets you edit it before sending.",
            "Kong validates the bearer token with the openid-connect plugin against Azure AD discovery and JWKS metadata.",
            "Kong maps the Azure AD appid claim to a Kong Consumer by custom_id.",
            "If authentication fails, Kong blocks the request before the protected API is reached.",
        ],
    },
    "identity-keycloak-authorization": {
        "id": "identity-keycloak-authorization",
        "label": "Identity: Keycloak Authorization",
        "title": "Keycloak Role Authorization",
        "services": ["svc-orders-auth-keycloak"],
        "routes": ["route-orders-auth-keycloak"],
        "plugins": ["openid-connect on route-orders-auth-keycloak"],
        "controlPlane": "Konnect control plane",
        "dataPlane": "Local hybrid data plane",
        "publicPath": "/orders/auth/keycloak",
        "routingHeader": "authorization",
        "identityProvider": "Keycloak",
        "consumers": ["consumer-1", "consumer-2"],
        "architecture": [
            "The UI requests a client-credentials token from Keycloak for the selected consumer and lets you edit it before sending.",
            "Kong validates the bearer token and authorizes access using the configured role claim from Keycloak.",
            "Kong maps the Keycloak azp claim to a Kong Consumer by custom_id.",
            "consumer-1 has the required role and consumer-2 does not, so authorization succeeds for one and fails for the other.",
        ],
    },
}

LATENCY_HEADERS = {
    "x-kong-proxy-latency",
    "x-kong-upstream-latency",
    "x-kong-response-latency",
}

RATE_LIMIT_KEYS = {
    "consumer-gold": "key-consumer-gold",
    "consumer-standard": "key-consumer-standard",
}

RATE_LIMIT_POLICIES = {
    "anonymous": {
        "route": "route-orders-rate-anonymous",
        "service": "svc-orders-rate-anonymous",
        "plugin": "rate-limiting-advanced on svc-orders-rate-anonymous",
        "window_seconds": 30,
        "plugin_scope": "svc-orders-rate-anonymous",
    },
    "consumer-standard": {
        "route": "route-orders-rate-consumer",
        "service": "svc-orders-rate-consumer",
        "plugin": "rate-limiting-advanced on consumer-standard",
        "window_seconds": 30,
        "plugin_scope": "consumer-standard",
    },
    "consumer-gold": {
        "route": "route-orders-rate-consumer",
        "service": "svc-orders-rate-consumer",
        "plugin": "rate-limiting-advanced on consumer-gold",
        "window_seconds": 30,
        "plugin_scope": "consumer-gold",
    },
}

RATE_LIMIT_EXECUTIONS = {}
RESILIENCE_WEIGHTED_COUNTS = {"orders-instance-1": 0, "orders-instance-2": 0}
RESILIENCE_INSTANCES = {
    "instance-1": {
        "label": "Service Instance 1",
        "container": "tcs-orders-instance-1",
        "service": "orders-instance-1",
        "target": "orders-instance-1:9201",
    },
    "instance-2": {
        "label": "Service Instance 2",
        "container": "tcs-orders-instance-2",
        "service": "orders-instance-2",
        "target": "orders-instance-2:9202",
    },
}


def shell_quote(value):
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def build_curl_command(url, headers):
    parts = ["curl", "-i", "-X", "GET"]
    for key, value in headers.items():
        parts.extend(["-H", shell_quote(f"{key}: {value}")])
    parts.append(shell_quote(url))
    return " ".join(parts)


def json_bytes(payload):
    return json.dumps(payload).encode("utf-8")


def sanitize_headers(headers):
    return {k: v for k, v in headers.items() if k.lower() not in LATENCY_HEADERS}


def normalize_detail_entities(items):
    return [[label, value if value not in (None, "") else "None"] for label, value in items]


def docker_api_request(method, path, body=b""):
    if not os.path.exists(DOCKER_SOCKET_PATH):
        raise FileNotFoundError(DOCKER_SOCKET_PATH)

    request = (
        f"{method} {path} HTTP/1.1\r\n"
        "Host: docker\r\n"
        "Connection: close\r\n"
        f"Content-Length: {len(body)}\r\n"
        "\r\n"
    ).encode("utf-8") + body

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(DOCKER_SOCKET_PATH)
        sock.sendall(request)
        response = bytearray()
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            response.extend(chunk)
    finally:
        sock.close()

    header_bytes, _, body_bytes = bytes(response).partition(b"\r\n\r\n")
    header_lines = header_bytes.decode("utf-8", errors="replace").split("\r\n")
    status_code = int(header_lines[0].split(" ")[1])
    headers = {}
    for line in header_lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    if headers.get("transfer-encoding", "").lower() == "chunked":
        decoded = bytearray()
        remaining = body_bytes
        while remaining:
            line, _, remaining = remaining.partition(b"\r\n")
            if not line:
                break
            size = int(line.decode("utf-8"), 16)
            if size == 0:
                break
            decoded.extend(remaining[:size])
            remaining = remaining[size + 2 :]
        body_bytes = bytes(decoded)

    parsed_body = {}
    if body_bytes:
        try:
            parsed_body = json.loads(body_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            parsed_body = {"raw": body_bytes.decode("utf-8", errors="replace")}
    return {"status": status_code, "headers": headers, "body": parsed_body}


def docker_container_status(container_name):
    response = docker_api_request("GET", f"/containers/{container_name}/json")
    if response["status"] != 200:
        return {"status": "unknown", "running": False}
    state = response["body"].get("State", {})
    return {
        "status": state.get("Status", "unknown"),
        "running": bool(state.get("Running")),
    }


def set_container_state(container_name, action):
    action_path = "/start" if action == "start" else "/stop?t=1"
    response = docker_api_request("POST", f"/containers/{container_name}{action_path}")
    return response["status"] in {204, 304}


def get_resilience_instance_states():
    states = {}
    for instance_id, meta in RESILIENCE_INSTANCES.items():
        try:
            states[instance_id] = {
                "label": meta["label"],
                "service": meta["service"],
                **docker_container_status(meta["container"]),
            }
        except Exception as exc:  # noqa: BLE001
            states[instance_id] = {
                "label": meta["label"],
                "service": meta["service"],
                "status": f"error: {exc}",
                "running": False,
            }
    return states


def parse_response_body(raw_body):
    if not raw_body:
        return {}
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return {"raw": raw_body}


def parse_int(value):
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def extract_rate_limit_metrics(headers):
    metrics = {"limit": None, "remaining": None, "reset": None, "retry_after": None}
    for key, value in headers.items():
        lower_key = key.lower()
        if "ratelimit" not in lower_key and lower_key != "retry-after":
            continue
        parsed = parse_int(value)
        if parsed is None:
            continue
        if lower_key == "retry-after":
            metrics["retry_after"] = parsed
        elif "remaining" in lower_key and metrics["remaining"] is None:
            metrics["remaining"] = parsed
        elif "reset" in lower_key and metrics["reset"] is None:
            metrics["reset"] = parsed
        elif "limit" in lower_key and metrics["limit"] is None:
            metrics["limit"] = parsed
    return metrics


def update_execution_counter(counter_key, limit, remaining, reset_seconds, response_status):
    now = time.time()
    state = RATE_LIMIT_EXECUTIONS.get(counter_key)
    if state and now >= state["window_expires_at"]:
        state = None

    if limit is not None and remaining is not None and response_status != 429:
        execution_count = max(limit - remaining, 0)
    elif state:
        execution_count = state["execution_count"] + 1
    elif limit is not None:
        execution_count = limit + 1 if response_status == 429 else 1
    else:
        execution_count = 1

    window_expires_at = now + max(reset_seconds or 0, 0)
    RATE_LIMIT_EXECUTIONS[counter_key] = {
        "execution_count": execution_count,
        "window_expires_at": window_expires_at,
        "window_started_at": window_expires_at - max(reset_seconds or 0, 0),
    }
    return execution_count, max(int(round(window_expires_at - now)), 0), window_expires_at


def build_rate_limit_expected_outcome(mode, consumer, window_seconds, limit):
    scope = "Anonymous requests" if mode == "anonymous" else f"{consumer} requests"
    blocked_request = (limit or 0) + 1 if limit is not None else "the next blocked request"
    return (
        f"{scope} should pass through Kong for requests 1-{limit} in each {window_seconds}-second fixed window. "
        f"Request {blocked_request} should return 429 until the window resets."
    )


def request_through_kong(url, headers):
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_body = resp.read().decode("utf-8")
            return {
                "status": resp.status,
                "headers": sanitize_headers({k.lower(): v for k, v in resp.headers.items()}),
                "body": parse_response_body(raw_body),
            }
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8") if exc.fp else ""
        return {
            "status": exc.code,
            "headers": sanitize_headers({k.lower(): v for k, v in exc.headers.items()}),
            "body": parse_response_body(raw_body),
        }


def post_form(url, form_data):
    body = urllib.parse.urlencode(form_data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_body = resp.read().decode("utf-8")
            return {"status": resp.status, "headers": {k.lower(): v for k, v in resp.headers.items()}, "body": json.loads(raw_body)}
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8") if exc.fp else ""
        parsed = parse_response_body(raw_body)
        return {"status": exc.code, "headers": {k.lower(): v for k, v in exc.headers.items()}, "body": parsed}


def build_bearer_headers(token):
    headers = {"Accept": "application/json", "x-request-id": str(uuid.uuid4())}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def kong_identity_consumer_name(idp_name, consumer_label):
    if idp_name == "Azure AD":
        return f"azure-ad-{consumer_label}"
    if idp_name == "Keycloak":
        return f"keycloak-{consumer_label}"
    return consumer_label


def consumer_mapping_description(idp_name):
    if idp_name == "Azure AD":
        return "appid claim -> Kong Consumer custom_id"
    if idp_name == "Keycloak":
        return "azp claim -> Kong Consumer custom_id"
    return "No consumer mapping"


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "TcsKongDemo/1.0"

    def do_HEAD(self):
        if (
            self.path == "/"
            or self.path == "/favicon.ico"
            or self.path.startswith("/static/")
            or self.path.startswith("/img/")
        ):
            self.serve_static(head_only=True)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_GET(self):
        if self.path == "/api/config":
            self.respond_json(
                {
                    "sceneOptions": [
                        {"id": scene["id"], "label": scene["label"]} for scene in SCENES.values()
                    ],
                    "scenes": SCENES,
                    "links": {"logs": DEMO_LOGS_URL, "audit": DEMO_AUDIT_URL},
                }
            )
            return
        if self.path == "/api/scenes/resilience/status":
            self.respond_json({"instances": get_resilience_instance_states()})
            return

        if (
            self.path == "/"
            or self.path == "/favicon.ico"
            or self.path.startswith("/static/")
            or self.path.startswith("/img/")
        ):
            self.serve_static()
            return

        self.respond_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if self.path == "/api/scenes/header-routing/run":
            self.handle_run_header_routing()
            return
        if self.path == "/api/scenes/header-routing/reset":
            self.respond_json({"ok": True})
            return
        if self.path == "/api/scenes/rate-limiting/run":
            self.handle_run_rate_limiting()
            return
        if self.path == "/api/scenes/rate-limiting/reset":
            self.respond_json({"ok": True})
            return
        if self.path == "/api/scenes/resilience/run":
            self.handle_run_resilience()
            return
        if self.path == "/api/scenes/resilience/reset":
            self.handle_reset_resilience()
            return
        if self.path == "/api/scenes/resilience/instance":
            self.handle_resilience_instance()
            return
        if self.path == "/api/scenes/identity/azure/token":
            self.handle_generate_azure_token()
            return
        if self.path == "/api/scenes/identity/azure/run":
            self.handle_run_identity_azure()
            return
        if self.path == "/api/scenes/identity/keycloak/token":
            self.handle_generate_keycloak_token()
            return
        if self.path == "/api/scenes/identity/keycloak/run":
            self.handle_run_identity_keycloak()
            return

        self.respond_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def handle_run_header_routing(self):
        scene = SCENES["traffic-routing-header"]
        body = self.read_json()
        region = body.get("region", "")
        header_value = region if region in {"east", "west"} else ""
        request_id = str(uuid.uuid4())

        target_url = f"{KONG_PROXY_URL}/orders"
        request_headers = {"Accept": "application/json", "x-request-id": request_id}
        if header_value:
            request_headers["x-region"] = header_value

        response = request_through_kong(target_url, request_headers)
        response_body = response["body"]
        response_status = response["status"]
        route_state = "unmatched"
        route_matched = None
        plugin_applied = None
        error_message = None

        if response_status == 200:
            route_state = "matched"
            route_matched = (
                "route-orders-header-east" if header_value == "east" else "route-orders-header-west"
            )
        elif response_status == 400 and response_body.get("policy") == "orders-header-missing-region-policy":
            route_state = "policy"
            route_matched = "route-orders-header-catchall"
            plugin_applied = "request-termination"
            error_message = "Kong applied the missing-header policy route."
        else:
            error_message = "No Kong route matched the supplied header."

        selected_service = response_body.get("service")
        selected_region = response_body.get("region")
        kong_service_matched = None
        if header_value == "east":
            kong_service_matched = "svc-orders-header-east"
        elif header_value == "west":
            kong_service_matched = "svc-orders-header-west"
        elif route_state == "policy":
            kong_service_matched = "svc-orders-header-missing-region"

        payload = {
            "scene": scene["id"],
            "sceneDetails": scene,
            "requestPreview": [
                ("Method", "GET"),
                ("Path", "/orders"),
                ("Header", f"x-region: {header_value}" if header_value else "x-region: <missing>"),
            ],
            "expectedOutcome": (
                "Orders East should receive the request."
                if header_value == "east"
                else "Orders West should receive the request."
                if header_value == "west"
                else "Kong should apply the catch-all policy route and return a guided missing-header response."
            ),
            "actualOutcome": [
                ("Kong Route", route_matched or "No match"),
                ("Kong Service", kong_service_matched or "No match"),
                ("Backend Service", selected_service or "No backend"),
                ("Status", str(response_status or 502)),
            ],
            "result": {
                "status": response_status or 502,
                "routeState": route_state,
                "routeMatched": route_matched,
                "kongServiceMatched": kong_service_matched,
                "pluginApplied": plugin_applied,
                "selectedService": selected_service,
                "selectedRegion": selected_region,
                "error": error_message,
                "responseBody": response_body,
                "responseHeaders": response["headers"],
            },
            "consoleView": {
                "request": {
                    "method": "GET",
                    "endpoint": "/orders",
                    "headers": request_headers,
                    "body": None,
                },
                "response": {
                    "status": response_status or 502,
                    "headers": response["headers"],
                    "body": response_body,
                },
            },
            "detailView": {
                "entities": normalize_detail_entities(
                    [
                        ("Kong Route", route_matched or "No match"),
                        ("Kong Service", kong_service_matched or "No match"),
                        ("Kong Plugin", f"{plugin_applied} on {route_matched}" if plugin_applied else "None"),
                        ("Actual Service Name", selected_service or "No backend service"),
                    ]
                ),
                "curl": build_curl_command(target_url, request_headers),
                "response": {
                    "status": response_status or 502,
                    "headers": response["headers"],
                    "body": response_body,
                },
            },
            "topology": {
                "labels": {
                    "client": ("Client", "Web Caller", "GET /orders"),
                    "kong": ("Gateway", "Kong Data Plane", "Header routing policy"),
                    "east": ("Upstream", "Orders East", "x-region: east"),
                    "west": ("Upstream", "Orders West", "x-region: west"),
                },
                "nodes": {
                    "kong": "active" if route_state != "unmatched" else "error",
                    "east": "active" if selected_region == "east" else "idle",
                    "west": "active" if selected_region == "west" else "idle",
                },
                "connectors": {
                    "clientKong": "active",
                    "kongEast": "active" if selected_region == "east" else ("error" if route_state == "unmatched" else "idle"),
                    "kongWest": "active" if selected_region == "west" else ("error" if route_state == "unmatched" else "idle"),
                },
                "statusKong": "Kong Matched Route" if route_state == "matched" else "Kong Applied Policy" if route_state == "policy" else "Kong Rejected Request",
                "statusKongClass": "success" if route_state != "unmatched" else "error",
                "statusRoute": "Route: East" if selected_region == "east" else "Route: West" if selected_region == "west" else "Policy Route" if route_state == "policy" else "No Route Match",
                "statusRouteClass": "success" if route_state != "unmatched" else "error",
            },
            "architecture": scene["architecture"],
        }
        self.respond_json(payload)

    def handle_run_rate_limiting(self):
        scene = SCENES["traffic-control-rate-limiting"]
        body = self.read_json()
        mode = body.get("mode", "anonymous")
        consumer = body.get("consumer", "consumer-standard")

        path = "/orders/rate/anonymous" if mode == "anonymous" else "/orders/rate/consumer"
        target_url = f"{KONG_PROXY_URL}{path}"
        request_headers = {"Accept": "application/json"}
        if mode == "consumer":
            request_headers["apikey"] = RATE_LIMIT_KEYS.get(consumer, RATE_LIMIT_KEYS["consumer-standard"])

        policy_key = "anonymous" if mode == "anonymous" else consumer
        policy = RATE_LIMIT_POLICIES[policy_key]
        window_seconds = policy["window_seconds"]
        route_name = policy["route"]
        service_name = policy["service"]
        plugin_detail = policy["plugin"]

        req_headers = dict(request_headers)
        req_headers["x-request-id"] = str(uuid.uuid4())
        response = request_through_kong(target_url, req_headers)
        response_body = response["body"] if isinstance(response["body"], dict) else {}
        rate_metrics = extract_rate_limit_metrics(response["headers"])
        limit = rate_metrics["limit"]
        remaining = rate_metrics["remaining"]
        reset_seconds = rate_metrics["reset"] or rate_metrics["retry_after"] or 0
        execution_key = f"{mode}:{consumer if mode == 'consumer' else 'anonymous'}"
        execution_count, seconds_until_reset, window_expires_at = update_execution_counter(
            execution_key,
            limit,
            remaining,
            reset_seconds,
            response["status"],
        )
        next_blocked_request = limit + 1 if limit is not None else None
        backend_service = response_body.get("service", "orders-east")
        final_status = response["status"]
        current_window_text = f"{window_seconds}-second fixed window"

        expected_outcome = build_rate_limit_expected_outcome(mode, consumer, window_seconds, limit)

        payload = {
            "scene": scene["id"],
            "sceneDetails": scene,
            "requestPreview": [
                ("Method", "GET"),
                ("Path", path),
                ("Mode", mode),
                ("Consumer", consumer if mode == "consumer" else "none"),
                ("Window", current_window_text),
            ],
            "expectedOutcome": expected_outcome,
            "actualOutcome": [
                ("Mode", mode),
                ("Kong Consumer", consumer if mode == "consumer" else "none"),
                ("Kong Route", route_name),
                ("Kong Service", service_name),
                ("Kong Plugin", plugin_detail),
                ("Backend Service", backend_service),
                ("Execution Count", str(execution_count)),
                ("Window", current_window_text),
                ("Limit", str(limit) if limit is not None else "unknown"),
                ("Remaining", str(remaining) if remaining is not None else "unknown"),
                ("Next Blocked Request", str(next_blocked_request) if next_blocked_request is not None else "unknown"),
                ("Reset In", f"{seconds_until_reset}s"),
                ("Final Status", str(final_status)),
            ],
            "result": {
                "status": final_status,
                "routeState": "throttled" if final_status == 429 else "matched",
                "routeMatched": route_name,
                "kongServiceMatched": service_name,
                "pluginApplied": policy["plugin_scope"],
                "selectedService": backend_service,
                "selectedRegion": "allowed" if final_status != 429 else None,
                "executionCount": execution_count,
                "limit": limit,
                "remaining": remaining,
                "resetSeconds": seconds_until_reset,
                "windowExpiresAt": window_expires_at,
                "windowSeconds": window_seconds,
                "responseBody": response["body"],
                "responseHeaders": response["headers"],
            },
            "consoleView": {
                "request": {
                    "method": "GET",
                    "endpoint": path,
                    "headers": req_headers,
                    "body": None,
                },
                "response": {
                    "status": final_status,
                    "headers": response["headers"],
                    "body": response["body"],
                },
            },
            "detailView": {
                "entities": normalize_detail_entities(
                    [
                        ("Kong Route", route_name),
                        ("Kong Service", service_name),
                        ("Kong Plugin", plugin_detail),
                        ("Kong Consumer", consumer if mode == "consumer" else "None"),
                        ("Actual Service Name", backend_service),
                    ]
                ),
                "curl": build_curl_command(target_url, req_headers),
                "response": {
                    "status": final_status,
                    "headers": response["headers"],
                    "body": response["body"],
                },
            },
            "topology": {
                "labels": {
                    "client": ("Client", "API Caller", f"Mode: {mode}"),
                    "kong": ("Gateway", "Kong Data Plane", f"{limit or '?'} requests per {window_seconds}s"),
                    "east": ("Backend", "Orders API", f"Status: {final_status}"),
                    "west": ("Policy Window", "Fixed Window Counter", f"Request {execution_count}, reset in {seconds_until_reset}s"),
                },
                "nodes": {
                    "kong": "error" if final_status == 429 else "active",
                    "east": "active",
                    "west": "static",
                },
                "connectors": {
                    "clientKong": "active",
                    "kongEast": "active",
                    "kongWest": "hidden",
                },
                "statusKong": "Kong Throttled Request" if final_status == 429 else "Kong Allowed Request",
                "statusKongClass": "error" if final_status == 429 else "success",
                "statusRoute": (
                    f"Request {execution_count} throttled"
                    if final_status == 429
                    else f"Request {execution_count} of {limit or '?'}"
                ),
                "statusRouteClass": "error" if final_status == 429 else "success",
            },
            "architecture": scene["architecture"],
        }
        self.respond_json(payload)

    def handle_run_resilience(self):
        scene = SCENES["resilience-failover-health-checks"]
        body = self.read_json()
        scenario = body.get("scenario", "weighted-load-balancing")
        scenario = scenario if scenario in {"weighted-load-balancing", "circuit-breaker"} else "weighted-load-balancing"

        path = (
            "/orders/resilience/weighted"
            if scenario == "weighted-load-balancing"
            else "/orders/resilience/circuit-breaker"
        )
        route_name = (
            "route-orders-resilience-weighted"
            if scenario == "weighted-load-balancing"
            else "route-orders-circuit-breaker"
        )
        service_name = (
            "svc-orders-resilience-weighted"
            if scenario == "weighted-load-balancing"
            else "svc-orders-circuit-breaker"
        )
        upstream_name = (
            "upstream-orders-weighted"
            if scenario == "weighted-load-balancing"
            else "upstream-orders-circuit-breaker"
        )

        req_headers = {"Accept": "application/json", "x-request-id": str(uuid.uuid4())}
        target_url = f"{KONG_PROXY_URL}{path}"
        response = request_through_kong(target_url, req_headers)
        response_body = response["body"] if isinstance(response["body"], dict) else {}
        response_status = response["status"]
        backend_service = response_body.get("service")
        instance_states = get_resilience_instance_states()

        if response_status == 200 and backend_service in RESILIENCE_WEIGHTED_COUNTS and scenario == "weighted-load-balancing":
            RESILIENCE_WEIGHTED_COUNTS[backend_service] += 1

        if scenario == "weighted-load-balancing":
            expected_outcome = (
                "Kong should distribute requests across the two healthy targets using the configured 30:70 weights."
            )
            east_subtitle = f"Weight 30 | observed {RESILIENCE_WEIGHTED_COUNTS['orders-instance-1']}"
            west_subtitle = f"Weight 70 | observed {RESILIENCE_WEIGHTED_COUNTS['orders-instance-2']}"
            status_kong = "Weighted Policy Applied" if response_status == 200 else "Weighted Route Failed"
            status_route = (
                f"Selected: {backend_service}" if response_status == 200 else f"HTTP {response_status}"
            )
        else:
            healthy_instances = [key for key, value in instance_states.items() if value["running"]]
            expected_outcome = (
                "Kong should round robin across both targets while healthy, then remove an unhealthy target from rotation and reroute traffic to the healthy target."
            )
            east_subtitle = "Healthy" if instance_states["instance-1"]["running"] else "Unhealthy / removed"
            west_subtitle = "Healthy" if instance_states["instance-2"]["running"] else "Unhealthy / removed"
            if response_status == 200 and len(healthy_instances) == 1:
                status_kong = "Circuit Open: Failed Over"
                status_route = f"Traffic rerouted to {backend_service}"
            elif response_status == 200:
                status_kong = "Round Robin Healthy"
                status_route = f"Selected: {backend_service}"
            else:
                status_kong = "No Healthy Targets"
                status_route = f"HTTP {response_status}"

        selected_instance = None
        for instance_id, meta in RESILIENCE_INSTANCES.items():
            if meta["service"] == backend_service:
                selected_instance = instance_id
                break

        payload = {
            "scene": scene["id"],
            "sceneDetails": scene,
            "requestPreview": [
                ("Method", "GET"),
                ("Path", path),
                ("Scenario", "Weighted Load Balancing" if scenario == "weighted-load-balancing" else "Circuit Breaker"),
                ("Strategy", "30:70 weighted" if scenario == "weighted-load-balancing" else "Round robin with active + passive health checks"),
            ],
            "expectedOutcome": expected_outcome,
            "instanceStates": instance_states,
            "result": {
                "status": response_status,
                "routeMatched": route_name,
                "kongServiceMatched": service_name,
                "upstreamMatched": upstream_name,
                "selectedService": backend_service,
                "selectedInstance": selected_instance,
                "responseBody": response["body"],
                "responseHeaders": response["headers"],
                "scenario": scenario,
                "weightedCounts": dict(RESILIENCE_WEIGHTED_COUNTS),
            },
            "consoleView": {
                "request": {
                    "method": "GET",
                    "endpoint": path,
                    "headers": req_headers,
                    "body": None,
                },
                "response": {
                    "status": response_status,
                    "headers": response["headers"],
                    "body": response["body"],
                },
            },
            "detailView": {
                "entities": normalize_detail_entities(
                    [
                        ("Kong Route", route_name),
                        ("Kong Service", service_name),
                        ("Kong Upstream", upstream_name),
                        ("Kong Target Selected", RESILIENCE_INSTANCES[selected_instance]["target"] if selected_instance else "None"),
                        ("Actual Service Name", backend_service or "None"),
                    ]
                ),
                "curl": build_curl_command(target_url, req_headers),
                "response": {
                    "status": response_status,
                    "headers": response["headers"],
                    "body": response["body"],
                },
            },
            "topology": {
                "labels": {
                    "client": ("Client", "API Caller", "GET resilience route"),
                    "kong": (
                        "Gateway",
                        "Kong Data Plane",
                        "30:70 weighted" if scenario == "weighted-load-balancing" else "Round robin + health checks",
                    ),
                    "east": ("Target", "Service Instance 1", east_subtitle),
                    "west": ("Target", "Service Instance 2", west_subtitle),
                },
                "nodes": {
                    "kong": "error" if response_status >= 500 else "active",
                    "east": "active" if selected_instance == "instance-1" else ("error" if not instance_states["instance-1"]["running"] else None),
                    "west": "active" if selected_instance == "instance-2" else ("error" if not instance_states["instance-2"]["running"] else None),
                },
                "connectors": {
                    "clientKong": "active",
                    "kongEast": "active" if selected_instance == "instance-1" else ("error" if not instance_states["instance-1"]["running"] else None),
                    "kongWest": "active" if selected_instance == "instance-2" else ("error" if not instance_states["instance-2"]["running"] else None),
                },
                "statusKong": status_kong,
                "statusKongClass": "error" if response_status >= 500 else "success",
                "statusRoute": status_route,
                "statusRouteClass": "error" if response_status >= 500 else "success",
            },
            "architecture": scene["architecture"],
        }
        self.respond_json(payload)

    def handle_reset_resilience(self):
        for meta in RESILIENCE_INSTANCES.values():
            try:
                set_container_state(meta["container"], "start")
            except Exception:  # noqa: BLE001
                pass
        RESILIENCE_WEIGHTED_COUNTS["orders-instance-1"] = 0
        RESILIENCE_WEIGHTED_COUNTS["orders-instance-2"] = 0
        self.respond_json({"ok": True, "instances": get_resilience_instance_states()})

    def handle_resilience_instance(self):
        body = self.read_json()
        instance_id = body.get("instance")
        action = body.get("action")
        meta = RESILIENCE_INSTANCES.get(instance_id)
        if meta is None or action not in {"start", "stop"}:
            self.respond_json({"error": "Invalid resilience instance request"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            set_container_state(meta["container"], action)
            self.respond_json({"ok": True, "instances": get_resilience_instance_states()})
        except Exception as exc:  # noqa: BLE001
            self.respond_json(
                {"error": f"Failed to {action} {instance_id}: {exc}", "instances": get_resilience_instance_states()},
                status=HTTPStatus.BAD_GATEWAY,
            )

    def handle_generate_azure_token(self):
        body = self.read_json()
        consumer = body.get("consumer", "consumer-1")
        client_id = AD_CONSUMER1_CLIENT_ID if consumer == "consumer-1" else AD_CONSUMER2_CLIENT_ID
        client_secret = AD_CONSUMER1_SECRET if consumer == "consumer-1" else AD_CONSUMER2_SECRET
        token_url = f"https://login.microsoftonline.com/{AD_PROTECTED_API_TENANT_ID}/oauth2/v2.0/token"
        response = post_form(
            token_url,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": f"{AD_PROTECTED_API_AUDIENCE}/.default",
                "grant_type": "client_credentials",
            },
        )
        self.respond_json(
            {
                "token": response["body"].get("access_token", ""),
                "tokenResponse": response["body"],
                "idp": "Azure AD",
                "consumer": consumer,
            },
            status=response["status"],
        )

    def handle_generate_keycloak_token(self):
        body = self.read_json()
        consumer = body.get("consumer", "consumer-1")
        client_id = KEYCLOAK_CONSUMER1_CLIENT_ID if consumer == "consumer-1" else KEYCLOAK_CONSUMER2_CLIENT_ID
        client_secret = KEYCLOAK_CONSUMER1_SECRET if consumer == "consumer-1" else KEYCLOAK_CONSUMER2_SECRET
        token_url = f"{KEYCLOAK_INTERNAL_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
        response = post_form(
            token_url,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
        )
        self.respond_json(
            {
                "token": response["body"].get("access_token", ""),
                "tokenResponse": response["body"],
                "idp": "Keycloak",
                "consumer": consumer,
            },
            status=response["status"],
        )

    def handle_run_identity_azure(self):
        scene = SCENES["identity-azure-token-validation"]
        body = self.read_json()
        token = body.get("token", "").strip()
        payload = self.build_identity_payload(
            scene=scene,
            path="/orders/auth/azure",
            token=token,
            idp_name="Azure AD",
            route_name="route-orders-auth-azure",
            service_name="svc-orders-auth-azure",
            plugin_name="openid-connect on route-orders-auth-azure",
            consumer_label=body.get("consumer", "consumer-1"),
            allowed_role=None,
        )
        self.respond_json(payload)

    def handle_run_identity_keycloak(self):
        scene = SCENES["identity-keycloak-authorization"]
        body = self.read_json()
        token = body.get("token", "").strip()
        consumer = body.get("consumer", "consumer-1")
        payload = self.build_identity_payload(
            scene=scene,
            path="/orders/auth/keycloak",
            token=token,
            idp_name="Keycloak",
            route_name="route-orders-auth-keycloak",
            service_name="svc-orders-auth-keycloak",
            plugin_name="openid-connect on route-orders-auth-keycloak",
            consumer_label=consumer,
            allowed_role=os.environ.get("KEYCLOAK_ALLOWED_ROLE", "api-access"),
        )
        self.respond_json(payload)

    def build_identity_payload(
        self,
        *,
        scene,
        path,
        token,
        idp_name,
        route_name,
        service_name,
        plugin_name,
        consumer_label,
        allowed_role,
    ):
        req_headers = build_bearer_headers(token)
        target_url = f"{KONG_PROXY_URL}{path}"
        response = request_through_kong(target_url, req_headers)
        response_body = response["body"] if isinstance(response["body"], dict) else {}
        response_status = response["status"]
        selected_service = response_body.get("service")
        kong_consumer = kong_identity_consumer_name(idp_name, consumer_label)
        consumer_mapping = consumer_mapping_description(idp_name)

        if response_status == 200:
            route_state = "authorized"
            error_message = None
        elif response_status == 403:
            route_state = "forbidden"
            error_message = "Authorization failed. Kong denied the token based on policy."
        else:
            route_state = "unauthorized"
            error_message = "Authentication failed. Kong rejected the token."

        expected_outcome = (
            "Kong should validate the Azure AD token and forward the request only when the token is valid."
            if scene["id"] == "identity-azure-token-validation"
            else "consumer-1 should be authorized while consumer-2 should be denied based on the role claim."
        )

        return {
            "scene": scene["id"],
            "sceneDetails": scene,
            "requestPreview": [
                ("Method", "GET"),
                ("Path", path),
                ("Identity Provider", idp_name),
                ("Token", "Bearer token in Authorization header"),
            ],
            "expectedOutcome": expected_outcome,
            "result": {
                "status": response_status,
                "routeState": route_state,
                "routeMatched": route_name,
                "kongServiceMatched": service_name,
                "pluginApplied": plugin_name,
                "selectedService": selected_service,
                "responseBody": response["body"],
                "responseHeaders": response["headers"],
                "consumer": consumer_label,
                "idp": idp_name,
            },
            "consoleView": {
                "request": {
                    "method": "GET",
                    "endpoint": path,
                    "headers": req_headers,
                    "body": None,
                },
                "response": {
                    "status": response_status,
                    "headers": response["headers"],
                    "body": response["body"],
                },
            },
            "detailView": {
                "entities": normalize_detail_entities(
                    [
                        ("Kong Route", route_name),
                        ("Kong Service", service_name),
                        ("Kong Plugin", plugin_name),
                        ("Kong Consumer", kong_consumer),
                        ("Consumer Mapping", consumer_mapping),
                        ("Identity Provider", idp_name),
                        ("Consumer", consumer_label),
                        ("Required Role", allowed_role or "None"),
                        ("Actual Service Name", selected_service or "No upstream call"),
                    ]
                ),
                "curl": build_curl_command(target_url, req_headers),
                "response": {
                    "status": response_status,
                    "headers": response["headers"],
                    "body": response["body"],
                },
            },
            "topology": {
                "labels": {
                    "client": ("Client", "Token Caller", "Bearer token supplied"),
                    "kong": ("Gateway", "Kong Data Plane", "openid-connect validation"),
                    "east": ("Protected API", "Orders API", "Reached" if response_status == 200 else "Not reached"),
                    "west": (
                        "Identity Provider",
                        idp_name,
                        "Validated",
                    ),
                },
                "nodes": {
                    "kong": "active" if response_status == 200 else "error",
                    "east": "active" if response_status == 200 else None,
                    "west": "active",
                },
                "connectors": {
                    "clientKong": "active",
                    "kongWest": "active",
                    "kongEast": "active" if response_status == 200 else None,
                },
                "statusKong": "Kong Authorized Request" if response_status == 200 else "Kong Rejected Request",
                "statusKongClass": "success" if response_status == 200 else "error",
                "statusRoute": (
                    "Token validated"
                    if response_status == 200
                    else "Authorization denied"
                    if response_status == 403
                    else "Authentication failed"
                ),
                "statusRouteClass": "success" if response_status == 200 else "error",
            },
            "architecture": scene["architecture"],
            "errorMessage": error_message,
        }

    def serve_static(self, head_only=False):
        if self.path == "/":
            candidate = STATIC_DIR / "index.html"
        elif self.path == "/favicon.ico":
            candidate = IMG_DIR / "image.png"
        elif self.path.startswith("/img/"):
            candidate = IMG_DIR / Path(self.path).name
        else:
            candidate = STATIC_DIR / self.path.removeprefix("/static/")
        if not candidate.exists() or not candidate.is_file():
            self.respond_json({"error": "Static asset not found"}, status=HTTPStatus.NOT_FOUND)
            return

        if candidate.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif candidate.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif candidate.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif candidate.suffix == ".svg":
            content_type = "image/svg+xml"
        elif candidate.suffix == ".png":
            content_type = "image/png"
        else:
            content_type = "application/octet-stream"

        raw = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if not head_only:
            self.wfile.write(raw)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def respond_json(self, payload, status=HTTPStatus.OK):
        raw = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        print(json.dumps({"client": self.address_string(), "message": fmt % args}))


def main():
    host = os.environ.get("DEMO_HOST", "0.0.0.0")
    port = int(os.environ.get("DEMO_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), DemoHandler)
    print(json.dumps({"message": "demo UI ready", "host": host, "port": port}))
    server.serve_forever()


if __name__ == "__main__":
    main()
