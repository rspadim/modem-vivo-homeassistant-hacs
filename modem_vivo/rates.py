from __future__ import annotations

from copy import deepcopy
from time import time
from typing import Any


def _rate_bps(current_bytes: int, previous_bytes: int, elapsed_seconds: float) -> float:
    if elapsed_seconds <= 0 or current_bytes < previous_bytes:
        return 0.0
    return (current_bytes - previous_bytes) * 8 / elapsed_seconds


def _format_rates(current: dict[str, Any], previous: dict[str, Any] | None, elapsed: float | None) -> dict[str, Any]:
    if previous is None or elapsed is None:
        return {"ready": False, "elapsed_seconds": None, "ethernet": {}, "wifi": {}, "totals": {}}

    result: dict[str, Any] = {
        "ready": True,
        "elapsed_seconds": elapsed,
        "ethernet": {},
        "wifi": {},
        "totals": {
            "ethernet_rx_bps": 0.0,
            "ethernet_tx_bps": 0.0,
            "wifi_rx_bps": 0.0,
            "wifi_tx_bps": 0.0,
        },
    }

    for group in ("ethernet", "wifi"):
        current_group = current.get("statistics", {}).get(group, {})
        previous_group = previous.get("statistics", {}).get(group, {})
        for iface, counters in current_group.items():
            old = previous_group.get(iface)
            if not old:
                continue
            rx_bps = _rate_bps(counters["rx_bytes"], old["rx_bytes"], elapsed)
            tx_bps = _rate_bps(counters["tx_bytes"], old["tx_bytes"], elapsed)
            result[group][iface] = {
                "rx_bps": rx_bps,
                "tx_bps": tx_bps,
                "rx_mbps": rx_bps / 1_000_000,
                "tx_mbps": tx_bps / 1_000_000,
            }
            result["totals"][f"{group}_rx_bps"] += rx_bps
            result["totals"][f"{group}_tx_bps"] += tx_bps

    for key, value in list(result["totals"].items()):
        result["totals"][key.replace("_bps", "_mbps")] = value / 1_000_000

    return result


class RateCalculator:
    def __init__(self) -> None:
        self._previous_status: dict[str, Any] | None = None
        self._previous_time: float | None = None

    def add_sample(self, status: dict[str, Any]) -> dict[str, Any]:
        now = time()
        elapsed = None if self._previous_time is None else now - self._previous_time
        rates = _format_rates(status, self._previous_status, elapsed)

        enriched = deepcopy(status)
        enriched["rates"] = rates

        self._previous_status = deepcopy(status)
        self._previous_time = now
        return enriched
