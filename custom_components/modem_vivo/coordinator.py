from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import VivoModemClient
from .const import CONF_IP, CONF_SENHA, CONF_USUARIO, DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN
from .rates import RateCalculator

LOGGER = logging.getLogger(__name__)


class ModemVivoDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.client = VivoModemClient(
            ip=entry.data[CONF_IP],
            usuario=entry.data[CONF_USUARIO],
            senha=entry.data[CONF_SENHA],
        )
        self.rate_calculator = RateCalculator()
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            status = await self.hass.async_add_executor_job(self.client.collect_status)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
        return self.rate_calculator.add_sample(status)
