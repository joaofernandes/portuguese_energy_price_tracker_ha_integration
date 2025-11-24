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
    # Only create the select entity for the FIRST config entry (sorted by entry_id)
    # This ensures it's tied to the same entry as routing sensors
    all_entries = [e for e in hass.config_entries.async_entries(DOMAIN)]
    all_entries_sorted = sorted(all_entries, key=lambda e: e.entry_id)

    # Only create select entity if this is the first entry
    if not all_entries_sorted or entry.entry_id != all_entries_sorted[0].entry_id:
        _LOGGER.debug(f"Skipping select entity creation for entry {entry.entry_id} (not first entry)")
        return

    # Create the select entity tied to first config entry
    # If an orphaned entity exists in registry, Home Assistant will handle the cleanup
    # and properly bind this new instance to the config entry
    _LOGGER.info(f"Creating select entity linked to first config entry: {entry.entry_id}")
    select = ActiveProviderSelect(hass, entry)
    async_add_entities([select])


class ActiveProviderSelect(SelectEntity):
    """Select entity for choosing the active energy provider.

    This entity is tied to the first config entry to satisfy Home Assistant's
    requirement that config-entry-based integrations have entities with config_entry_id.
    """

    _attr_has_entity_name = False
    _attr_icon = "mdi:swap-horizontal"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = "active_provider"  # Simple unique_id, platform already provides domain context
        self._attr_name = "Active Energy Provider"
        self._attr_options = []
        self._attr_current_option = None

    @property
    def config_entry_id(self) -> str:
        """Return config entry ID (required for config-entry-based integrations)."""
        return self._entry.entry_id

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
