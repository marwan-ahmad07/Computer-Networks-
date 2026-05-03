from __future__ import annotations

# HTTP server running on top of the custom ReliableUDP transport.
#
# Limitation mapping summary:
# - HTTP/1.0 server behavior.
# - Required methods: GET and POST only.
# - Required statuses: OK and NOT FOUND.

import argparse
from pathlib import Path

from .http import build_response, parse_request, resolve_path
from .reliable_udp import ReliableUDP


class Http10Server:
    def __init__(
        self,
        host: str,
        port: int,
        root_dir: str,
        *,
        loss_rate: float = 0.0,
        corruption_rate: float = 0.0,
        timeout: float = 1.0,
        seed: int | None = None,
    ) -> None:
        # Root directory that GET reads from and POST writes to.
        self.root = Path(root_dir)
        # Transport object that provides reliability over UDP.
        self.transport = ReliableUDP(
            (host, port),
            timeout=timeout,
            loss_rate=loss_rate,
            corruption_rate=corruption_rate,
            seed=seed,
        )

    def serve_forever(self) -> None:
        # Wait for one client handshake, then process requests in a loop.
        print(f"[HTTP] Serving files from {self.root.resolve()}")
        client_addr, _ = self.transport.accept()
        print(f"[HTTP] Client connected from {client_addr}")
        try:
            while True:
                # Receive complete HTTP request bytes from reliable transport.
                raw_request = self.transport.recv_message()
                request = parse_request(raw_request)
                response = self._handle_request(request)
                # Send HTTP response bytes through reliable transport.
                self.transport.send_message(response)
        except (ConnectionError, OSError, KeyboardInterrupt):
            print("[HTTP] Server shutting down")
        finally:
            self.transport.close()

    def _handle_request(self, request) -> bytes:
        # Limitation: only GET and POST are required.
        method = request.method.upper()
        if method not in {"GET", "POST"}:
            # Required NOT FOUND family response in unsupported scenarios.
            return build_response(404, "NOT FOUND", b"Unsupported method")

        try:
            # Secure path resolution blocks traversal outside root.
            target = resolve_path(self.root, request.path)
        except ValueError:
            return build_response(404, "NOT FOUND", b"Invalid path")

        if method == "GET":
            # GET returns file bytes when file exists.
            if not target.exists() or not target.is_file():
                return build_response(404, "NOT FOUND", b"File not found")
            body = target.read_bytes()
            # Required OK response for successful GET.
            return build_response(200, "OK", body, {"Content-Type": "application/octet-stream"})

        # POST writes body to file and confirms with 200 OK.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(request.body)
        message = f"Stored {len(request.body)} bytes at {target.name}".encode("utf-8")
        return build_response(200, "OK", message, {"Content-Type": "text/plain; charset=utf-8"})


def main() -> None:
    # CLI entrypoint for running HTTP/1.0 server over ReliableUDP.
    parser = argparse.ArgumentParser(description="HTTP/1.0 server over ReliableUDP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--root", default=".")
    parser.add_argument("--loss", type=float, default=0.0)
    parser.add_argument("--corruption", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    server = Http10Server(
        args.host,
        args.port,
        args.root,
        loss_rate=args.loss,
        corruption_rate=args.corruption,
        timeout=args.timeout,
        seed=args.seed,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
