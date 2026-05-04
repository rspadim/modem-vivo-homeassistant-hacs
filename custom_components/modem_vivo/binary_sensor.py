from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import ModemVivoEntity


@dataclass(frozen=True, kw_only=True)
class ModemVivoBinarySensorEntityDescription(BinarySensorEntityDescription):
    value_path: tuple[str, ...]


BINARY_SENSORS = (
    ModemVivoBinarySensorEntityDescription(key="gpon_up", name="GPON", device_class=BinarySensorDeviceClass.CONNECTIVITY, value_path=("wan", "gpon_up")),
    ModemVivoBinarySensorEntityDescription(key="ppp_up", name="PPP", device_class=BinarySensorDeviceClass.CONNECTIVITY, value_path=("wan", "ppp_up")),
    ModemVivoBinarySensorEntityDescription(key="dhcp_enabled", name="DHCP", value_path=("lan", "dhcp_enabled")),
    ModemVivoBinarySensorEntityDescription(key="upnp_enabled", name="UPnP", value_path=("lan", "upnp_enabled")),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(ModemVivoBinarySensor(coordinator, description) for description in BINARY_SENSORS)


class ModemVivoBinarySensor(ModemVivoEntity, BinarySensorEntity):
    entity_description: ModemVivoBinarySensorEntityDescription

    def __init__(self, coordinator, description: ModemVivoBinarySensorEntityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_unique_id = f"modem_vivo_{coordinator.client.ip}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        value: Any = self.coordinator.data or {}
        for key in self.entity_description.value_path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return bool(value)
