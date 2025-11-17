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
    CONF_INCLUDE_VAT,
    CONF_PROVIDER,
    CONF_TARIFF,
    CONF_VAT,
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
        return EnergyPriceTrackerOptionsFlow()


class EnergyPriceTrackerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Energy Price Tracker."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["configure", "restore_data"],
        )

    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle configuration options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Update config entry
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_DISPLAY_NAME: user_input.get(
                        CONF_DISPLAY_NAME, self.config_entry.data[CONF_DISPLAY_NAME]
                    ),
                    CONF_VAT: user_input.get(CONF_VAT, self.config_entry.data.get(CONF_VAT, DEFAULT_VAT)),
                    CONF_INCLUDE_VAT: user_input.get(CONF_INCLUDE_VAT, self.config_entry.data.get(CONF_INCLUDE_VAT, DEFAULT_INCLUDE_VAT)),
                },
            )
            return self.async_create_entry(title="", data={})

        # Build options schema
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DISPLAY_NAME,
                    default=self.config_entry.data.get(CONF_DISPLAY_NAME, ""),
                ): cv.string,
                vol.Optional(
                    CONF_VAT,
                    default=self.config_entry.data.get(CONF_VAT, DEFAULT_VAT),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
                vol.Optional(
                    CONF_INCLUDE_VAT,
                    default=self.config_entry.data.get(CONF_INCLUDE_VAT, DEFAULT_INCLUDE_VAT),
                ): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="configure",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_restore_data(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle historical data restore."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Extract year and month from the date string (YYYY-MM format)
            from datetime import datetime

            date_str = user_input["restore_date"]
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m")
                year = date_obj.year
                month = date_obj.month
            except ValueError:
                _LOGGER.error(f"Invalid date format: {date_str}")
                errors["base"] = "restore_failed"
                year = None
                month = None

            if year and month:
                try:
                    # Call the service to restore data
                    await self.hass.services.async_call(
                        "energy_price_tracker",
                        "restore_historical_data",
                        {"year": year, "month": month},
                        blocking=True,
                    )
                    return self.async_create_entry(
                        title="",
                        data={},
                    )
                except Exception as err:
                    _LOGGER.error(f"Error restoring historical data: {err}")
                    errors["base"] = "restore_failed"

        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m")

        # Build restore data schema with text input for YYYY-MM format
        data_schema = vol.Schema(
            {
                vol.Required("restore_date", default=current_date): cv.string,
            }
        )

        return self.async_show_form(
            step_id="restore_data",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "provider": self.config_entry.data["provider"],
                "tariff": self.config_entry.data["tariff"],
            },
        )
