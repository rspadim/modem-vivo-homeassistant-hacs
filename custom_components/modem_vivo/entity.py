from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ModemVivoDataUpdateCoordinator


class ModemVivoEntity(CoordinatorEntity[ModemVivoDataUpdateCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ModemVivoDataUpdateCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.client.ip}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.client.ip)},
            "name": "Modem Vivo",
            "manufacturer": "Vivo",
            "model": "RTF8225VW",
            "configuration_url": f"http://{coordinator.client.ip}/",
        }
