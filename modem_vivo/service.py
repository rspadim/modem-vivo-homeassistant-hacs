from __future__ import annotations

import argparse
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import sleep
from typing import Any

from .cli import load_config
from .client import VivoModemClient
from .rates import RateCalculator

LOG = logging.getLogger(__name__)


class SharedState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.status: dict[str, Any] = {"ok": False, "error": "not collected yet"}

    def set(self, status: dict[str, Any]) -> None:
        with self.lock:
            self.status = status

    def get(self) -> dict[str, Any]:
        with self.lock:
            return dict(self.status)


def poll_loop(client: VivoModemClient, state: SharedState, interval: int) -> None:
    calculator = RateCalculator()
    while True:
        try:
            status = client.collect_status()
            enriched = calculator.add_sample(status)
            enriched["ok"] = True
            state.set(enriched)
            LOG.info("Collected modem status")
        except Exception as exc:  # noqa: BLE001 - service must keep running
            LOG.exception("Failed to collect modem status")
            state.set({"ok": False, "error": str(exc)})
        sleep(interval)


def make_handler(state: SharedState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib API
            if self.path not in ("/", "/status"):
                self.send_response(404)
                self.end_headers()
                return

            body = json.dumps(state.get(), ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: Any) -> None:
            LOG.info("%s - %s", self.address_string(), fmt % args)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Vivo modem local HTTP status service")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    config = load_config(Path(args.config))
    ip = os.getenv("VIVO_MODEM_IP") or config.get("ip")
    usuario = os.getenv("VIVO_MODEM_USUARIO") or config.get("usuario")
    senha = os.getenv("VIVO_MODEM_SENHA") or config.get("senha")
    if not ip or not usuario or not senha:
        raise SystemExit("Missing ip, usuario or senha")

    state = SharedState()
    client = VivoModemClient(ip=ip, usuario=usuario, senha=senha)
    thread = threading.Thread(target=poll_loop, args=(client, state, args.interval), daemon=True)
    thread.start()

    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    LOG.info("Serving on http://%s:%s/status", args.host, args.port)
    server.serve_forever()


if __name__ == "__main__":
    main()
