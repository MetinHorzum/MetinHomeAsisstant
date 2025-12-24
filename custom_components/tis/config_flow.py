from __future__ import annotations

import ipaddress
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_PORT

def _default_broadcast(host: str) -> str:
    # 192.168.1.200 -> 192.168.1.255 (common /24)
    try:
        ip = ipaddress.IPv4Address(host)
        octets = str(ip).split(".")
        return ".".join(octets[:3] + ["255"])
    except Exception:
        return "255.255.255.255"

class TisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title=f"TIS {user_input['host']}", data=user_input)

        schema = vol.Schema(
            {
                vol.Required("host", default=DEFAULT_HOST): str,
                vol.Required("port", default=DEFAULT_PORT): int,
                vol.Optional("broadcast", default=_default_broadcast(DEFAULT_HOST)): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
