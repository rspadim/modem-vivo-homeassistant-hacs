from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import ModemVivoEntity


def path_value(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


@dataclass(frozen=True, kw_only=True)
class ModemVivoSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[ModemVivoSensorEntityDescription, ...] = (
    ModemVivoSensorEntityDescription(key="public_ipv4", translation_key="public_ipv4", name="IP público IPv4", value_fn=lambda d: path_value(d, "wan.ipv4_address")),
    ModemVivoSensorEntityDescription(key="gpon_status", translation_key="gpon_status", name="Status GPON", value_fn=lambda d: path_value(d, "wan.gpon_status")),
    ModemVivoSensorEntityDescription(key="gpon_serial", translation_key="gpon_serial", name="Serial GPON", value_fn=lambda d: path_value(d, "wan.gpon_serial")),
    ModemVivoSensorEntityDescription(key="ppp_uptime", translation_key="ppp_uptime", name="Uptime PPP", device_class=SensorDeviceClass.DURATION, native_unit_of_measurement="s", value_fn=lambda d: path_value(d, "wan.ppp_uptime_seconds")),
    ModemVivoSensorEntityDescription(key="optical_tx", translation_key="optical_tx", name="Potência óptica TX", native_unit_of_measurement="dBm", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: path_value(d, "wan.optical_power_dbm.tx")),
    ModemVivoSensorEntityDescription(key="optical_rx", translation_key="optical_rx", name="Potência óptica RX", native_unit_of_measurement="dBm", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: path_value(d, "wan.optical_power_dbm.rx")),
    ModemVivoSensorEntityDescription(key="ethernet_rx_mbps", translation_key="ethernet_rx_mbps", name="Ethernet RX", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: path_value(d, "rates.totals.ethernet_rx_mbps")),
    ModemVivoSensorEntityDescription(key="ethernet_tx_mbps", translation_key="ethernet_tx_mbps", name="Ethernet TX", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: path_value(d, "rates.totals.ethernet_tx_mbps")),
    ModemVivoSensorEntityDescription(key="wifi_rx_mbps", translation_key="wifi_rx_mbps", name="Wi-Fi RX", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: path_value(d, "rates.totals.wifi_rx_mbps")),
    ModemVivoSensorEntityDescription(key="wifi_tx_mbps", translation_key="wifi_tx_mbps", name="Wi-Fi TX", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: path_value(d, "rates.totals.wifi_tx_mbps")),
    ModemVivoSensorEntityDescription(key="lan_hosts_active", translation_key="lan_hosts_active", name="Hosts ativos", state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: sum(1 for h in d.get("lan", {}).get("hosts", []) if h.get("active"))),
    ModemVivoSensorEntityDescription(key="dhcp_lease", translation_key="dhcp_lease", name="DHCP lease", device_class=SensorDeviceClass.DURATION, native_unit_of_measurement="min", value_fn=lambda d: path_value(d, "lan.lease_minutes")),
    ModemVivoSensorEntityDescription(key="wifi_2g_channel", translation_key="wifi_2g_channel", name="Canal Wi-Fi 2.4 GHz", value_fn=lambda d: path_value(d, "wifi.channel_2g")),
    ModemVivoSensorEntityDescription(key="wifi_5g_channel", translation_key="wifi_5g_channel", name="Canal Wi-Fi 5 GHz", value_fn=lambda d: path_value(d, "wifi.channel_5g")),
    ModemVivoSensorEntityDescription(key="wifi_2g_tx_power", translation_key="wifi_2g_tx_power", name="Potência Wi-Fi 2.4 GHz", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: path_value(d, "wifi.tx_power_2g_percent")),
    ModemVivoSensorEntityDescription(key="wifi_5g_tx_power", translation_key="wifi_5g_tx_power", name="Potência Wi-Fi 5 GHz", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: path_value(d, "wifi.tx_power_5g_percent")),
)

for iface in ("eth1", "eth2", "eth3", "eth4"):
    SENSORS += (
        ModemVivoSensorEntityDescription(key=f"{iface}_rx_bytes", name=f"{iface} RX bytes", native_unit_of_measurement=UnitOfInformation.BYTES, state_class=SensorStateClass.TOTAL_INCREASING, value_fn=lambda d, iface=iface: path_value(d, f"statistics.ethernet.{iface}.rx_bytes")),
        ModemVivoSensorEntityDescription(key=f"{iface}_tx_bytes", name=f"{iface} TX bytes", native_unit_of_measurement=UnitOfInformation.BYTES, state_class=SensorStateClass.TOTAL_INCREASING, value_fn=lambda d, iface=iface: path_value(d, f"statistics.ethernet.{iface}.tx_bytes")),
        ModemVivoSensorEntityDescription(key=f"{iface}_rx_mbps", name=f"{iface} RX", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d, iface=iface: path_value(d, f"rates.ethernet.{iface}.rx_mbps")),
        ModemVivoSensorEntityDescription(key=f"{iface}_tx_mbps", name=f"{iface} TX", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d, iface=iface: path_value(d, f"rates.ethernet.{iface}.tx_mbps")),
    )

for iface in ("wl0", "wl1"):
    SENSORS += (
        ModemVivoSensorEntityDescription(key=f"{iface}_rx_bytes", name=f"{iface} RX bytes", native_unit_of_measurement=UnitOfInformation.BYTES, state_class=SensorStateClass.TOTAL_INCREASING, value_fn=lambda d, iface=iface: path_value(d, f"statistics.wifi.{iface}.rx_bytes")),
        ModemVivoSensorEntityDescription(key=f"{iface}_tx_bytes", name=f"{iface} TX bytes", native_unit_of_measurement=UnitOfInformation.BYTES, state_class=SensorStateClass.TOTAL_INCREASING, value_fn=lambda d, iface=iface: path_value(d, f"statistics.wifi.{iface}.tx_bytes")),
        ModemVivoSensorEntityDescription(key=f"{iface}_rx_mbps", name=f"{iface} RX", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d, iface=iface: path_value(d, f"rates.wifi.{iface}.rx_mbps")),
        ModemVivoSensorEntityDescription(key=f"{iface}_tx_mbps", name=f"{iface} TX", native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND, state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d, iface=iface: path_value(d, f"rates.wifi.{iface}.tx_mbps")),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(ModemVivoSensor(coordinator, description) for description in SENSORS)


class ModemVivoSensor(ModemVivoEntity, SensorEntity):
    entity_description: ModemVivoSensorEntityDescription

    def __init__(self, coordinator, description: ModemVivoSensorEntityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_unique_id = f"modem_vivo_{coordinator.client.ip}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})
