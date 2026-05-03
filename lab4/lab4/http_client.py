from __future__ import annotations

# HTTP client running on top of the custom ReliableUDP transport.
#
# Limitation mapping summary:
# - Sends HTTP/1.0 GET/POST requests.
# - Uses reliable transport that handles timeout/retransmission/checksum rules.

import argparse
import sys

from .http import build_request, parse_response
from .reliable_udp import ReliableUDP


class Http10Client:
    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout: float = 1.0,
        loss_rate: float = 0.0,
        corruption_rate: float = 0.0,
        seed: int | None = None,
    ) -> None:
        # Transport object handles handshake, ACKs, retransmission, and checksums.
        self.transport = ReliableUDP(
            timeout=timeout,
            loss_rate=loss_rate,
            corruption_rate=corruption_rate,
            seed=seed,
        )
        # Remote server endpoint.
        self.remote = (host, port)

    def connect(self) -> None:
        # Start client-side handshake with server.
        self.transport.connect(self.remote)

    def request(self, method: str, path: str, body: bytes = b"") -> str:
        # Build HTTP request bytes and send through reliable UDP.
        request = build_request(method, path, body)
        self.transport.send_message(request)
        # Receive and parse HTTP response.
        response = parse_response(self.transport.recv_message())
        return self.format_response(response)

    @staticmethod
    def format_response(response) -> str:
        # Pretty string output for terminal/debug console.
        body_text = response.body.decode("utf-8", errors="replace")
        lines = [f"{response.version} {response.status_code} {response.reason}"]
        for key, value in response.headers.items():
            lines.append(f"{key}: {value}")
        lines.append("")
        lines.append(body_text)
        return "\n".join(lines)

    def close(self) -> None:
        # Gracefully close transport connection (FIN path inside transport).
        self.transport.close()


def main() -> None:
    # CLI entrypoint for HTTP/1.0 client operations.
    # Limitation: only GET and POST are allowed.
    parser = argparse.ArgumentParser(description="HTTP/1.0 client over ReliableUDP")
    parser.add_argument("method", choices=["GET", "POST"])
    parser.add_argument("path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--body", default="")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--loss", type=float, default=0.0)
    parser.add_argument("--corruption", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    client = Http10Client(
        args.host,
        args.port,
        timeout=args.timeout,
        loss_rate=args.loss,
        corruption_rate=args.corruption,
        seed=args.seed,
    )
    try:
        client.connect()
        output = client.request(args.method, args.path, args.body.encode("utf-8"))
        print(output)
    except (ConnectionError, TimeoutError, OSError) as exc:
        print(f"[HTTP CLIENT] {exc}")
        raise SystemExit(1) from exc
    finally:
        client.close()


if __name__ == "__main__":
    main()
