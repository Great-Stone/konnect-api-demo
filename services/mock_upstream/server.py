import argparse
import json
import os
import socket
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


def build_handler(service_name: str, region: str, api_version: str = "", release_stage: str = ""):
    class UpstreamHandler(BaseHTTPRequestHandler):
        server_version = "MockUpstream/1.0"

        def _request_payload(self, method: str, body_text: str = ""):
            request_id = self.headers.get("x-request-id") or str(uuid.uuid4())
            query = {}
            path = self.path
            if "?" in self.path:
                path, query_string = self.path.split("?", 1)
                query = {
                    key: values if len(values) > 1 else values[0]
                    for key, values in parse_qs(query_string, keep_blank_values=True).items()
                }
            return {
                "service": service_name,
                "region": region,
                "api_version": api_version or None,
                "release_stage": release_stage or None,
                "handled_by": f"{region}-cluster",
                "path": path,
                "query": query,
                "method": method,
                "request_id": request_id,
                "host": socket.gethostname(),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "content_type": self.headers.get("Content-Type", ""),
                "content_length": self.headers.get("Content-Length", "0"),
                "body": body_text,
            }

        def _send_json(self, status: int, payload: dict, request_id: str):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("x-upstream-service", service_name)
            self.send_header("x-upstream-region", region)
            self.send_header("x-request-id", request_id)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                payload = {
                    "service": service_name,
                    "region": region,
                    "status": "healthy",
                }
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            payload = self._request_payload("GET")
            self._send_json(200, payload, payload["request_id"])

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", "0") or "0")
            body_text = self.rfile.read(content_length).decode("utf-8", errors="replace") if content_length > 0 else ""
            payload = self._request_payload("POST", body_text)
            self._send_json(200, payload, payload["request_id"])

        def log_message(self, fmt, *args):
            print(
                json.dumps(
                    {
                        "service": service_name,
                        "region": region,
                        "client": self.address_string(),
                        "message": fmt % args,
                    }
                )
            )

    return UpstreamHandler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--api-version", default="")
    parser.add_argument("--release-stage", default="")
    args = parser.parse_args()

    handler = build_handler(args.service, args.region, args.api_version, args.release_stage)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print(
        json.dumps(
            {
                "message": "mock upstream ready",
                "service": args.service,
                "region": args.region,
                "api_version": args.api_version,
                "release_stage": args.release_stage,
                "port": args.port,
                "pid": os.getpid(),
            }
        )
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
