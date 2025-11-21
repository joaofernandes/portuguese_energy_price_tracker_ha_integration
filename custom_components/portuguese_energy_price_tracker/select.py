"""Select platform for Energy Price Tracker integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Energy Price Tracker select entity."""
    # Only create the select entity once across all config entries
    # Check if we already have a select entity by checking the entity registry
    entity_reg = er.async_get(hass)
    select_unique_id = f"{DOMAIN}_active_provider"

    # Check if select entity already exists in the registry
    existing_entity_id = entity_reg.async_get_entity_id("select", DOMAIN, select_unique_id)

    if existing_entity_id:
        _LOGGER.debug(f"Select entity already exists in registry ({existing_entity_id}), skipping creation")
        return

    # Create the select entity (only on first config entry setup)
    _LOGGER.debug(f"Creating select entity with unique_id: {select_unique_id}")
    select = ActiveProviderSelect(hass)
    async_add_entities([select])


class ActiveProviderSelect(SelectEntity):
    """Select entity for choosing the active energy provider."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:swap-horizontal"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the select entity."""
        self._hass = hass
        self._attr_unique_id = f"{DOMAIN}_active_provider"
        self._attr_name = "Active Energy Provider"
        self._attr_options = []
        self._attr_current_option = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to Home Assistant."""
        await super().async_added_to_hass()
        # Update options when entity is added
        await self._update_options()

        # Listen for config entry changes to update options
        @callback
        def _entry_changed(event=None):
            """Update options when config entries change."""
            self.hass.async_create_task(self._update_options())

        # Subscribe to config entry updates
        self.async_on_remove(
            self._hass.bus.async_listen("config_entry_discovered", _entry_changed)
        )

    @callback
    async def _update_options(self) -> None:
        """Update available provider options from all configured entries."""
        options = []

        # Get all coordinator instances
        if DOMAIN in self._hass.data:
            for entry_id, coordinator in self._hass.data[DOMAIN].items():
                if hasattr(coordinator, "display_name"):
                    # Use display name as option
                    display_name = coordinator.display_name
                    _LOGGER.debug(f"Select: Found coordinator with display_name='{display_name}' (provider={coordinator.provider}, tariff={coordinator.tariff})")
                    if display_name and display_name not in options:
                        options.append(display_name)

        # Handle empty configuration gracefully
        if not options:
            self._attr_options = ["No providers configured"]
            self._attr_current_option = "No providers configured"
            _LOGGER.warning(
                "No energy providers configured. Please add a provider via "
                "Settings > Devices & Services > Add Integration"
            )
        else:
            self._attr_options = sorted(options)
            # Set current option to first if not set or if previous selection no longer exists
            if not self._attr_current_option or self._attr_current_option not in self._attr_options:
                self._attr_current_option = self._attr_options[0]

        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Change the selected provider."""
        if option in self._attr_options:
            self._attr_current_option = option
            self.async_write_ha_state()
            _LOGGER.info(f"Active energy provider changed to: {option}")
        else:
            _LOGGER.warning(f"Invalid provider option selected: {option}")

    @property
    def current_option(self) -> str | None:
        """Return the currently selected provider."""
        return self._attr_current_option

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "available_providers": len(self._attr_options),
            "integration": DOMAIN,
        }
