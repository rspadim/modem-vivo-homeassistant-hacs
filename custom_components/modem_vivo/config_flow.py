from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import CONF_IP, CONF_SENHA, CONF_USUARIO, DEFAULT_IP, DEFAULT_SENHA, DEFAULT_USUARIO, DOMAIN


class ModemVivoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input["ip"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"Modem Vivo {user_input['ip']}", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_IP, default=DEFAULT_IP): str,
                vol.Required(CONF_USUARIO, default=DEFAULT_USUARIO): str,
                vol.Required(CONF_SENHA, default=DEFAULT_SENHA): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
