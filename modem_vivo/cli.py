from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .client import VivoModemClient


def load_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect status from Vivo/GVT modem")
    parser.add_argument("--config", default="config.json", help="JSON config path")
    parser.add_argument("--ip")
    parser.add_argument("--usuario")
    parser.add_argument("--senha")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    ip = args.ip or os.getenv("VIVO_MODEM_IP") or config.get("ip")
    usuario = args.usuario or os.getenv("VIVO_MODEM_USUARIO") or config.get("usuario")
    senha = args.senha or os.getenv("VIVO_MODEM_SENHA") or config.get("senha")

    missing = [name for name, value in {"ip": ip, "usuario": usuario, "senha": senha}.items() if not value]
    if missing:
        raise SystemExit(f"Missing config values: {', '.join(missing)}")

    client = VivoModemClient(ip=ip, usuario=usuario, senha=senha)
    print(json.dumps(client.collect_status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
