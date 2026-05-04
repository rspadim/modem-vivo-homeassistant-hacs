from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any

import requests


def _decode_login_field(value: str) -> str:
    """Apply the modem login obfuscation used by /js/tools.js."""
    return "".join(chr(ord(char) ^ 0x1F) for char in value)


def _extract_var(html: str, name: str) -> str | None:
    match = re.search(rf"var\s+{re.escape(name)}\s*=\s*'([^']*)'", html)
    return match.group(1) if match else None


def _extract_int_var(html: str, name: str) -> int | None:
    value = _extract_var(html, name)
    if value is None:
        match = re.search(rf"var\s+{re.escape(name)}\s*=\s*parseInt\(([^)]*)\)", html)
        if match:
            expression = match.group(1).strip().strip("'")
            if "/" in expression:
                left, right = expression.split("/", 1)
                try:
                    return int(int(left.strip()) / int(right.strip()))
                except ValueError:
                    return None
            value = expression
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _extract_html_decode_var(html: str, name: str) -> str | None:
    match = re.search(rf"var\s+{re.escape(name)}\s*=\s*htmlDecode\('([^']*)'\)", html)
    return match.group(1) if match else None


SENSITIVE_VAR_PARTS = (
    "pass",
    "password",
    "psk",
    "key",
    "session",
    "user",
    "ddns",
    "pw",
)


def _is_sensitive_var(name: str) -> bool:
    lowered = name.lower()
    return any(part in lowered for part in SENSITIVE_VAR_PARTS)


def _extract_public_vars(html: str) -> dict[str, str]:
    """Extract plain/htmlDecode JS vars, excluding obvious secrets."""
    result: dict[str, str] = {}
    patterns = (
        r"var\s+([A-Za-z0-9_]+)\s*=\s*'([^']*)'\s*;",
        r"var\s+([A-Za-z0-9_]+)\s*=\s*htmlDecode\('([^']*)'\)\s*;",
        r"var\s+([A-Za-z0-9_]+)\s*=\s*parseInt\('?(\d+)'?(?:/\d+)?\)\s*;",
    )
    for pattern in patterns:
        for name, value in re.findall(pattern, html):
            if _is_sensitive_var(name):
                continue
            result[name] = value
    return result


def _parse_enet_status(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    ports = []
    for item in raw.split("|"):
        parts = item.split(",")
        if len(parts) != 3:
            continue
        index, interface, status = parts
        ports.append(
            {
                "index": int(index) if index.isdigit() else index,
                "interface": interface,
                "connected": status == "1",
            }
        )
    return ports


def _parse_optical_power(value: str | None) -> dict[str, float]:
    if not value:
        return {}
    result: dict[str, float] = {}
    for item in value.split(";"):
        if not item or ":" not in item:
            continue
        key, raw_value = item.split(":", 1)
        try:
            result[key.lower()] = float(raw_value.replace("dBm", "").strip())
        except ValueError:
            continue
    return result


def _parse_lan_hosts(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        rows = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return []

    hosts: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 10:
            continue
        hosts.append(
            {
                "active": row[0] == "1",
                "hostname": row[1] or None,
                "ipv4": row[3] if row[3] != "0.0.0.0" else None,
                "connection": row[4] if row[4] != "NONE" else None,
                "manageable": row[5] == "yes",
                "mac": row[6],
                "port": row[7],
                "address_type": row[8],
                "ipv6": row[9] if row[9] != "::" else None,
            }
        )
    return hosts


def _parse_interface_stats(raw: str | None) -> dict[str, dict[str, int]]:
    if not raw:
        return {}
    stats: dict[str, dict[str, int]] = {}
    fields = (
        "rx_packets",
        "rx_bytes",
        "rx_errors",
        "rx_discards",
        "tx_packets",
        "tx_bytes",
        "tx_errors",
        "tx_discards",
    )
    for iface_raw in raw.split("/"):
        parts = iface_raw.split(",")
        if len(parts) != 9:
            continue
        iface = parts[0]
        try:
            values = [int(value) for value in parts[1:]]
        except ValueError:
            continue
        stats[iface] = dict(zip(fields, values, strict=True))
    return stats


def _parse_associated_wifi_clients(raw: str | None) -> list[dict[str, str]]:
    if not raw:
        return []
    clients = []
    for item in raw.split("/"):
        if not item or "," not in item:
            continue
        mac, uptime = item.split(",", 1)
        clients.append({"mac": mac, "uptime": uptime})
    return clients


@dataclass(slots=True)
class VivoModemClient:
    ip: str
    usuario: str
    senha: str
    timeout: int = 10
    base_url: str = field(init=False)
    session: requests.Session = field(init=False)

    def __post_init__(self) -> None:
        self.base_url = f"http://{self.ip}"
        self.session = requests.Session()

    def login(self) -> None:
        self.session.get(f"{self.base_url}/", timeout=self.timeout)
        response = self.session.post(
            f"{self.base_url}/cgi-bin/te_acceso_router.cgi",
            data={
                "curWebPage": "/index.asp",
                "loginUsername": _decode_login_field(self.usuario),
                "loginPassword": _decode_login_field(self.senha),
            },
            timeout=self.timeout,
            allow_redirects=True,
        )
        response.raise_for_status()

        if "Falha no login" in response.text or "invalid" in response.url.lower():
            raise RuntimeError("Login failed")

    def get_page(self, page: str) -> str:
        response = self.session.get(f"{self.base_url}/{page}", timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def collect_status(self) -> dict[str, Any]:
        self.login()
        status_html = self.get_page("index_cliente.asp")
        about_html = self.get_page("about-power-box.asp")
        lan_html = self.get_page("settings-local-network.asp")
        stats_html = self.get_page("device-management-statistics.asp")
        wifi_html = self.get_page("settings-wireless-network-u.asp")

        lan_hosts_raw_match = re.search(r"var\s+lanHostList\s*=\s*(\[.*?\]);", status_html)
        lan_hosts_raw = lan_hosts_raw_match.group(1) if lan_hosts_raw_match else None

        return {
            "modem": {
                "ip": self.ip,
                "model": self._extract_table_value(about_html, "Modelo"),
                "software_version": self._extract_table_value(about_html, "Software"),
                "hardware_version": self._extract_table_value(about_html, "Hardware"),
                "wan_mac": self._extract_table_value(about_html, "MAC da WAN"),
                "lan_mac": self._extract_table_value(about_html, "MAC da LAN"),
                "gvt_mode": _extract_var(status_html, "gvtMode"),
            },
            "wan": {
                "gpon_up": _extract_var(status_html, "gponUp") == "1",
                "gpon_status": _extract_var(status_html, "gponStatus") or _extract_var(stats_html, "gponSt"),
                "ppp_up": _extract_var(status_html, "pppStatus") == "1",
                "ppp_uptime_seconds": _extract_int_var(status_html, "pppUptime"),
                "ipv4_address": _extract_var(status_html, "pppIpv4Address"),
                "ipv4_gateway": _extract_var(status_html, "pppIpv4Gateway"),
                "dns4": (_extract_var(status_html, "dns4") or "").split(",") if _extract_var(status_html, "dns4") else [],
                "ipv6_address": _extract_var(status_html, "pppIpv6Address"),
                "ipv6_gateway": _extract_var(status_html, "pppIpv6Gateway"),
                "optical_power_dbm": _parse_optical_power(_extract_var(status_html, "opticalPower") or _extract_var(stats_html, "opticalPower")),
                "gpon_serial": _extract_var(stats_html, "gponSn"),
            },
            "lan": {
                "ip": _extract_var(lan_html, "lanIp"),
                "mask": _extract_var(lan_html, "lanMask"),
                "dhcp_enabled": _extract_var(lan_html, "dhcpEnbl") == "1",
                "dhcp_start": _extract_var(lan_html, "dhcpStart"),
                "dhcp_end": _extract_var(lan_html, "dhcpEnd"),
                "dhcp_dns": (_extract_var(lan_html, "dhcpDns") or "").split(",") if _extract_var(lan_html, "dhcpDns") else [],
                "lease_minutes": _extract_int_var(lan_html, "leaseTime"),
                "upnp_enabled": _extract_var(lan_html, "uPNP") == "1",
                "ethernet_ports": _parse_enet_status(_extract_var(status_html, "enetStatus")),
                "hosts": _parse_lan_hosts(lan_hosts_raw),
            },
            "wifi": {
                "ssid_2g": _extract_html_decode_var(wifi_html, "wlSsid") or _extract_var(status_html, "wlSsid_main0"),
                "enabled_2g": _extract_var(wifi_html, "wlEnbl") == "1" or _extract_var(status_html, "wlEnbl_main0") == "1",
                "channel_2g": _extract_var(wifi_html, "wlCurrentChannel") or _extract_var(status_html, "wlCurrentChannel_main0"),
                "bssid_2g": _extract_var(wifi_html, "wlBssid"),
                "ssid_5g": _extract_html_decode_var(wifi_html, "ssid_1") or _extract_var(status_html, "wlSsid_main1"),
                "enabled_5g": _extract_var(status_html, "wlEnbl_main1") == "1",
                "channel_5g": _extract_var(status_html, "wlCurrentChannel_main1"),
                "tx_power_2g_percent": _extract_int_var(stats_html, "wlan2dot4GTxPower"),
                "tx_power_5g_percent": _extract_int_var(stats_html, "wlan5GTxPower"),
                "clients_2g": _parse_associated_wifi_clients(_extract_var(stats_html, "wlan2dot4GAssociatedList")),
                "clients_5g": _parse_associated_wifi_clients(_extract_var(stats_html, "wlan5GAssociatedList")),
            },
            "statistics": {
                "ethernet": _parse_interface_stats(_extract_var(stats_html, "ethIntfSts")),
                "wifi": _parse_interface_stats(_extract_var(stats_html, "wlanIntfSts")),
            },
            "raw_public_vars": {
                "index_cliente": _extract_public_vars(status_html),
                "about_power_box": _extract_public_vars(about_html),
                "local_network": _extract_public_vars(lan_html),
                "statistics": _extract_public_vars(stats_html),
                "wireless": _extract_public_vars(wifi_html),
            },
        }

    @staticmethod
    def _extract_table_value(html: str, label: str) -> str | None:
        pattern = rf"<strong>[^<]*{re.escape(label)}[^<]*:</strong></td><td>([^<]*)</td>"
        match = re.search(pattern, html, re.IGNORECASE)
        return match.group(1).strip() if match else None
