"""Config flow for Energy Price Tracker integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_DISPLAY_NAME,
    CONF_ENABLE_DEBUG,
    CONF_INCLUDE_VAT,
    CONF_PROVIDER,
    CONF_TARIFF,
    CONF_VAT,
    DEFAULT_ENABLE_DEBUG,
    DEFAULT_INCLUDE_VAT,
    DEFAULT_VAT,
    DOMAIN,
    PROVIDERS,
    TARIFF_NAMES,
)

_LOGGER = logging.getLogger(__name__)


class EnergyPriceTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energy Price Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._provider: str | None = None
        self._tariff: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - select provider."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._provider = user_input[CONF_PROVIDER]
            return await self.async_step_tariff()

        # Build provider selection schema
        provider_list = list(PROVIDERS.keys())

        data_schema = vol.Schema(
            {
                vol.Required(CONF_PROVIDER): vol.In(provider_list),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "provider_count": str(len(provider_list)),
            },
        )

    async def async_step_tariff(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the tariff selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._tariff = user_input[CONF_TARIFF]
            return await self.async_step_options()

        # Get available tariffs for selected provider
        if self._provider and self._provider in PROVIDERS:
            tariff_list = PROVIDERS[self._provider]["tariffs"]
        else:
            return self.async_abort(reason="invalid_provider")

        # Build tariff selection schema with friendly names
        tariff_options = {
            tariff: TARIFF_NAMES.get(tariff, tariff) for tariff in tariff_list
        }

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TARIFF): vol.In(tariff_options),
            }
        )

        return self.async_show_form(
            step_id="tariff",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "provider": self._provider,
                "tariff_count": str(len(tariff_list)),
            },
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle optional configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Build final config
            config_data = {
                CONF_PROVIDER: self._provider,
                CONF_TARIFF: self._tariff,
                CONF_DISPLAY_NAME: user_input.get(
                    CONF_DISPLAY_NAME, f"{self._provider} {TARIFF_NAMES.get(self._tariff, self._tariff)}"
                ),
                CONF_VAT: user_input.get(CONF_VAT, DEFAULT_VAT),
                CONF_INCLUDE_VAT: user_input.get(CONF_INCLUDE_VAT, DEFAULT_INCLUDE_VAT),
                CONF_ENABLE_DEBUG: user_input.get(CONF_ENABLE_DEBUG, DEFAULT_ENABLE_DEBUG),
            }

            # Check for duplicate entries
            await self.async_set_unique_id(
                f"{config_data[CONF_PROVIDER]}_{config_data[CONF_TARIFF]}"
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=config_data[CONF_DISPLAY_NAME],
                data=config_data,
            )

        # Build options schema
        default_name = f"{self._provider} {TARIFF_NAMES.get(self._tariff, self._tariff)}"

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_DISPLAY_NAME, default=default_name): cv.string,
                vol.Optional(CONF_VAT, default=DEFAULT_VAT): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=100)
                ),
                vol.Optional(CONF_INCLUDE_VAT, default=DEFAULT_INCLUDE_VAT): cv.boolean,
                vol.Optional(CONF_ENABLE_DEBUG, default=DEFAULT_ENABLE_DEBUG): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="options",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "provider": self._provider,
                "tariff": TARIFF_NAMES.get(self._tariff, self._tariff),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update config entry with new options
            return self.async_create_entry(title="", data=user_input)

        # Get current values
        current_vat = self.config_entry.data.get(CONF_VAT, DEFAULT_VAT)
        current_include_vat = self.config_entry.data.get(
            CONF_INCLUDE_VAT, DEFAULT_INCLUDE_VAT
        )
        current_enable_debug = self.config_entry.data.get(
            CONF_ENABLE_DEBUG, DEFAULT_ENABLE_DEBUG
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_VAT,
                        default=current_vat,
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
                    vol.Optional(
                        CONF_INCLUDE_VAT,
                        default=current_include_vat,
                    ): cv.boolean,
                    vol.Optional(
                        CONF_ENABLE_DEBUG,
                        description={"suggested_value": current_enable_debug},
                    ): cv.boolean,
                }
            ),
        )

