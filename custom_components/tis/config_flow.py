from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_PORT


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for TIS."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        # Lazy import so any voluptuous issues show up clearly in logs
        import voluptuous as vol

        if user_input is not None:
            return self.async_create_entry(
                title=f"TIS {user_input.get('host', '')}".strip(),
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required("host", default=DEFAULT_HOST): str,
                vol.Required("port", default=DEFAULT_PORT): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
