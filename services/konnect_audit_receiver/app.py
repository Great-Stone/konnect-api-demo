import gzip
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = os.environ.get("AUDIT_RECEIVER_HOST", "0.0.0.0")
PORT = int(os.environ.get("AUDIT_RECEIVER_PORT", "8090"))
SHARED_SECRET = os.environ.get("AUDIT_SHARED_SECRET", "konnect-audit-demo-secret")
LOKI_PUSH_URL = os.environ.get("AUDIT_LOKI_PUSH_URL", "http://localhost:3100/loki/api/v1/push")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_event_time_ns(value: str | None) -> str:
    if not value:
        return str(time.time_ns())
    try:
        normalized = value.replace("Z", "+00:00")
        return str(int(datetime.fromisoformat(normalized).timestamp() * 1_000_000_000))
    except ValueError:
        return str(time.time_ns())


def detect_event_category(event: dict) -> str:
    name = str(event.get("name") or "")
    if name.startswith("Authn."):
        return "authentication"
    if name.startswith("Authz."):
        return "authorization"
    if event.get("act") or event.get("request"):
        return "access"
    return "unknown"


def sanitize_label(value) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    cleaned = []
    for char in text.lower():
        if char.isalnum():
            cleaned.append(char)
        elif char in {"-", "_", ".", "/"}:
            cleaned.append("_")
    normalized = "".join(cleaned).strip("_")
    return normalized or "unknown"


def extract_target_kind(request_path: str) -> str:
    if not request_path:
        return "unknown"
    trimmed = request_path.split("?", 1)[0].strip("/")
    parts = [part for part in trimmed.split("/") if part]
    try:
        control_plane_index = parts.index("control-planes")
    except ValueError:
        return "unknown"
    tail = parts[control_plane_index + 2 :]
    if not tail:
        return "control_plane"
    if tail[0] == "core-entities" and len(tail) >= 2:
        return sanitize_label(tail[1])
    return sanitize_label(tail[0])


def is_control_plane_change(event: dict) -> bool:
    method = str(event.get("act") or "").upper()
    request_path = str(event.get("request") or "")
    if method not in {"POST", "PATCH", "PUT", "DELETE"}:
        return False
    return "/control-planes/" in request_path


def format_labels(labels: dict[str, str]) -> str:
    segments = [f'{key}="{value}"' for key, value in sorted(labels.items())]
    return "{" + ",".join(segments) + "}"


def push_events_to_loki(events: list[dict]) -> None:
    streams = []
    for event in events:
        labels = {
            "service_name": "konnect-audit-webhook",
            "log_type": "konnect_audit",
            "event_category": sanitize_label(event.get("event_category")),
            "control_plane_change": "true" if event.get("control_plane_change") else "false",
            "principal_id": sanitize_label(event.get("principal_id")),
            "request_method": sanitize_label(event.get("act")),
            "target_kind": sanitize_label(event.get("target_kind")),
            "status": sanitize_label(event.get("status")),
            "granted": sanitize_label(event.get("granted")),
        }
        streams.append(
            {
                "stream": labels,
                "values": [[event["event_ts_ns"], json.dumps(event, separators=(",", ":"))]],
            }
        )

    payload = json.dumps({"streams": streams}).encode("utf-8")
    request = urllib.request.Request(
        LOKI_PUSH_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10):
        return


class AuditHandler(BaseHTTPRequestHandler):
    server_version = "KonnectAuditReceiver/1.0"

    def do_GET(self):
        if self.path == "/health":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
            return

        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()

    def do_POST(self):
        if self.path != "/konnect/audit":
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
            return

        authorization = self.headers.get("Authorization", "")
        if authorization != SHARED_SECRET:
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.end_headers()
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.end_headers()
            return

        payload = self.rfile.read(content_length)
        encoding = (self.headers.get("Content-Encoding") or "").lower()
        if "gzip" in encoding or encoding == "application/gzip":
            payload = gzip.decompress(payload)

        lines = [line.strip() for line in payload.decode("utf-8", errors="replace").splitlines() if line.strip()]
        events = []

        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                event = {"raw_line": line}

            event_category = detect_event_category(event)
            control_plane_change = is_control_plane_change(event)
            target_kind = extract_target_kind(str(event.get("request") or ""))

            normalized = {
                **event,
                "_konnect_raw": event,
                "_receiver": {
                    "received_at": iso_now(),
                    "event_category": event_category,
                    "control_plane_change": control_plane_change,
                    "target_kind": target_kind,
                },
                "event_category": event_category,
                "control_plane_change": control_plane_change,
                "target_kind": target_kind,
                "event_ts_ns": parse_event_time_ns(event.get("event_ts")),
                "principal_id": event.get("principal_id") or "unknown",
                "act": event.get("act") or event.get("action") or "unknown",
                "status": event.get("status") if event.get("status") is not None else "unknown",
                "granted": event.get("granted") if event.get("granted") is not None else "unknown",
            }
            events.append(normalized)

        try:
            if events:
                push_events_to_loki(events)
        except urllib.error.HTTPError as exc:
            self.send_response(HTTPStatus.BAD_GATEWAY)
            self.end_headers()
            self.wfile.write(f"Loki rejected audit payload: {exc}".encode("utf-8"))
            return
        except urllib.error.URLError as exc:
            self.send_response(HTTPStatus.BAD_GATEWAY)
            self.end_headers()
            self.wfile.write(f"Could not reach Loki: {exc}".encode("utf-8"))
            return

        self.send_response(HTTPStatus.ACCEPTED)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"accepted": len(events)}).encode("utf-8"))

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")


def main():
    server = ThreadingHTTPServer((HOST, PORT), AuditHandler)
    print(f"Konnect audit receiver listening on {HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
