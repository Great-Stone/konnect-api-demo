import argparse
import json
import os
import socket
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def build_handler(service_name: str, region: str):
    class UpstreamHandler(BaseHTTPRequestHandler):
        server_version = "MockUpstream/1.0"

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

            request_id = self.headers.get("x-request-id") or str(uuid.uuid4())
            payload = {
                "service": service_name,
                "region": region,
                "handled_by": f"{region}-cluster",
                "path": self.path,
                "method": "GET",
                "request_id": request_id,
                "host": socket.gethostname(),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("x-upstream-service", service_name)
            self.send_header("x-upstream-region", region)
            self.end_headers()
            self.wfile.write(body)

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
    args = parser.parse_args()

    handler = build_handler(args.service, args.region)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print(
        json.dumps(
            {
                "message": "mock upstream ready",
                "service": args.service,
                "region": args.region,
                "port": args.port,
                "pid": os.getpid(),
            }
        )
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
