"""Sensor platform for Energy Price Tracker integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EnergyPriceCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Energy Price Tracker sensor based on a config entry."""
    coordinator: EnergyPriceCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Provider-specific sensors
    sensors = [
        EnergyPriceCurrentSensor(coordinator, entry),
        EnergyPriceCurrentVATSensor(coordinator, entry),
        EnergyPriceTodayMaxSensor(coordinator, entry),
        EnergyPriceTodayMaxVATSensor(coordinator, entry),
        EnergyPriceTodayMinSensor(coordinator, entry),
        EnergyPriceTodayMinVATSensor(coordinator, entry),
        EnergyPriceTomorrowMaxSensor(coordinator, entry),
        EnergyPriceTomorrowMaxVATSensor(coordinator, entry),
        EnergyPriceTomorrowMinSensor(coordinator, entry),
        EnergyPriceTomorrowMinVATSensor(coordinator, entry),
        EnergyPriceTodayPricesSensor(coordinator, entry),
        EnergyPriceTomorrowPricesSensor(coordinator, entry),
        EnergyPriceAllPricesSensor(coordinator, entry),
    ]

    # Check if this is the first config entry to add generic routing sensors
    # These sensors are associated with the first entry to ensure they have a valid config_entry_id
    config_entries = hass.config_entries.async_entries(DOMAIN)
    is_first_entry = len(config_entries) > 0 and config_entries[0].entry_id == entry.entry_id

    if is_first_entry:
        _LOGGER.debug(f"Adding generic routing sensors linked to first config entry: {entry.entry_id}")
        # Add generic routing sensors - pass entry to link them to this config entry
        sensors.extend([
            ActiveProviderCurrentSensor(hass, entry),
            ActiveProviderCurrentVATSensor(hass, entry),
            ActiveProviderTodayMaxSensor(hass, entry),
            ActiveProviderTodayMaxVATSensor(hass, entry),
            ActiveProviderTodayMinSensor(hass, entry),
            ActiveProviderTodayMinVATSensor(hass, entry),
            ActiveProviderTomorrowMaxSensor(hass, entry),
            ActiveProviderTomorrowMaxVATSensor(hass, entry),
            ActiveProviderTomorrowMinSensor(hass, entry),
            ActiveProviderTomorrowMinVATSensor(hass, entry),
            ActiveProviderAllPricesSensor(hass, entry),
        ])

    async_add_entities(sensors)


class EnergyPriceBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Energy Price sensors."""

    def __init__(
        self,
        coordinator: EnergyPriceCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._sensor_type = sensor_type
        self._attr_has_entity_name = True

        # Build unique ID
        provider = entry.data["provider"]
        tariff = entry.data["tariff"]
        self._attr_unique_id = f"{DOMAIN}_{provider}_{tariff}_{sensor_type}".lower().replace(" ", "_")

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for grouping entities."""
        provider = self._entry.data["provider"]
        tariff = self._entry.data["tariff"]
        display_name = self._entry.data.get("display_name", f"{provider} {tariff}")

        # Create device identifier using provider+tariff slug
        device_id = f"{provider}_{tariff}".lower().replace(" ", "_")

        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": display_name,
            "manufacturer": "Portuguese Energy Price Tracker",
            "model": provider,
            "entry_type": "service",
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "provider": self._entry.data["provider"],
            "tariff": self._entry.data["tariff"],
            "display_name": self._entry.data.get("display_name", ""),
        }


class EnergyPriceCurrentSensor(EnergyPriceBaseSensor):
    """Sensor for current energy price (no VAT)."""

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "current_price")
        self._attr_name = "Current Price"
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return the current price."""
        if not self.coordinator.data:
            return None

        current_price = self.coordinator.data.get("current_price")
        if current_price is None:
            return None

        if current_price and "price" in current_price and current_price["price"] is not None:
            return round(float(current_price["price"]), 4)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes

        if self.coordinator.data:
            current_price = self.coordinator.data.get("current_price", {})
            if "period" in current_price:
                attrs["period"] = current_price["period"]

        return attrs


class EnergyPriceCurrentVATSensor(EnergyPriceBaseSensor):
    """Sensor for current energy price (with VAT)."""

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "current_price_vat")
        self._attr_name = "Current Price with VAT"
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return the current price with VAT."""
        if not self.coordinator.data:
            return None

        current_price = self.coordinator.data.get("current_price")
        if current_price is None:
            return None

        if current_price and "price_w_vat" in current_price and current_price["price_w_vat"] is not None:
            return round(float(current_price["price_w_vat"]), 4)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes
        attrs["vat_included"] = True

        if self.coordinator.data:
            current_price = self.coordinator.data.get("current_price", {})
            if "period" in current_price:
                attrs["period"] = current_price["period"]

        return attrs


class EnergyPriceTodayMaxSensor(EnergyPriceBaseSensor):
    """Sensor for today's maximum energy price."""

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "today_max_price")
        self._attr_name = "Today's Maximum Price"
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return today's maximum price."""
        if not self.coordinator.data:
            return None

        today_max = self.coordinator.data.get("today_max_price")
        if today_max is not None:
            return round(float(today_max), 4)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes
        attrs["period"] = "today"
        attrs["last_update"] = datetime.now().isoformat()
        return attrs


class EnergyPriceTodayMaxVATSensor(EnergyPriceBaseSensor):
    """Sensor for today's maximum energy price with VAT."""

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "today_max_price_vat")
        self._attr_name = "Today's Maximum Price with VAT"
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return today's maximum price with VAT."""
        if not self.coordinator.data:
            return None

        today_max_vat = self.coordinator.data.get("today_max_price_vat")
        if today_max_vat is not None:
            return round(float(today_max_vat), 4)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes
        attrs["vat_included"] = True
        attrs["period"] = "today"
        attrs["last_update"] = datetime.now().isoformat()
        return attrs


class EnergyPriceTodayMinSensor(EnergyPriceBaseSensor):
    """Sensor for today's minimum energy price."""

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "today_min_price")
        self._attr_name = "Today's Minimum Price"
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return today's minimum price."""
        if not self.coordinator.data:
            return None

        today_min = self.coordinator.data.get("today_min_price")
        if today_min is not None:
            return round(float(today_min), 4)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes
        attrs["period"] = "today"
        attrs["last_update"] = datetime.now().isoformat()
        return attrs


class EnergyPriceTodayMinVATSensor(EnergyPriceBaseSensor):
    """Sensor for today's minimum energy price with VAT."""

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "today_min_price_vat")
        self._attr_name = "Today's Minimum Price with VAT"
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return today's minimum price with VAT."""
        if not self.coordinator.data:
            return None

        today_min_vat = self.coordinator.data.get("today_min_price_vat")
        if today_min_vat is not None:
            return round(float(today_min_vat), 4)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes
        attrs["vat_included"] = True
        attrs["period"] = "today"
        attrs["last_update"] = datetime.now().isoformat()
        return attrs


class EnergyPriceTomorrowMaxSensor(EnergyPriceBaseSensor):
    """Sensor for tomorrow's maximum energy price."""

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "tomorrow_max_price")
        self._attr_name = "Tomorrow Max Price"
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return tomorrow's maximum price."""
        if not self.coordinator.data:
            return None

        tomorrow_max = self.coordinator.data.get("tomorrow_max_price")
        if tomorrow_max is not None:
            return round(float(tomorrow_max), 4)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes
        attrs["period"] = "tomorrow"
        attrs["last_update"] = datetime.now().isoformat()
        return attrs


class EnergyPriceTomorrowMaxVATSensor(EnergyPriceBaseSensor):
    """Sensor for tomorrow's maximum energy price with VAT."""

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "tomorrow_max_price_vat")
        self._attr_name = "Tomorrow Max Price VAT"
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return tomorrow's maximum price with VAT."""
        if not self.coordinator.data:
            return None

        tomorrow_max_vat = self.coordinator.data.get("tomorrow_max_price_vat")
        if tomorrow_max_vat is not None:
            return round(float(tomorrow_max_vat), 4)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes
        attrs["vat_included"] = True
        attrs["period"] = "tomorrow"
        attrs["last_update"] = datetime.now().isoformat()
        return attrs


class EnergyPriceTomorrowMinSensor(EnergyPriceBaseSensor):
    """Sensor for tomorrow's minimum energy price."""

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "tomorrow_min_price")
        self._attr_name = "Tomorrow Min Price"
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return tomorrow's minimum price."""
        if not self.coordinator.data:
            return None

        tomorrow_min = self.coordinator.data.get("tomorrow_min_price")
        if tomorrow_min is not None:
            return round(float(tomorrow_min), 4)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes
        attrs["period"] = "tomorrow"
        attrs["last_update"] = datetime.now().isoformat()
        return attrs


class EnergyPriceTomorrowMinVATSensor(EnergyPriceBaseSensor):
    """Sensor for tomorrow's minimum energy price with VAT."""

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "tomorrow_min_price_vat")
        self._attr_name = "Tomorrow Min Price VAT"
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return tomorrow's minimum price with VAT."""
        if not self.coordinator.data:
            return None

        tomorrow_min_vat = self.coordinator.data.get("tomorrow_min_price_vat")
        if tomorrow_min_vat is not None:
            return round(float(tomorrow_min_vat), 4)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes
        attrs["vat_included"] = True
        attrs["period"] = "tomorrow"
        attrs["last_update"] = datetime.now().isoformat()
        return attrs


class EnergyPriceTodayPricesSensor(EnergyPriceBaseSensor):
    """Sensor containing today's price datapoints with ALL fields."""

    _unrecorded_attributes = frozenset({"prices"})

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "today_prices")
        self._attr_name = "Today Prices"
        self._attr_icon = "mdi:calendar-today"

    @property
    def native_value(self) -> int:
        """Return the count of today's price points."""
        if not self.coordinator.data:
            return 0

        from homeassistant.util import dt as dt_util
        prices = self.coordinator.data.get("prices", [])
        today = dt_util.now().date()

        today_prices = [p for p in prices if datetime.fromisoformat(p["datetime"]).date() == today]
        return len(today_prices)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return today's price datapoints with ALL fields preserved."""
        from homeassistant.util import dt as dt_util

        attrs = super().extra_state_attributes

        if self.coordinator.data:
            all_prices = self.coordinator.data.get("prices", [])
            now = dt_util.now()
            today = now.date()

            today_prices = []
            for p in all_prices:
                dt_obj = datetime.fromisoformat(p["datetime"])
                if dt_obj.date() == today:
                    # Keep ALL fields - no data loss
                    today_prices.append({
                        "datetime": p["datetime"],
                        "interval": p["interval"],
                        "price": p["price"],
                        "price_w_vat": p["price_w_vat"],
                        "market_price": p["market_price"],
                        "tar_cost": p["tar_cost"],
                    })

            attrs["prices"] = today_prices
            attrs["data_points"] = len(today_prices)
            attrs["last_update"] = datetime.now().isoformat()

            if today_prices:
                attrs["first_timestamp"] = today_prices[0]["datetime"]
                attrs["last_timestamp"] = today_prices[-1]["datetime"]

        return attrs


class EnergyPriceTomorrowPricesSensor(EnergyPriceBaseSensor):
    """Sensor containing tomorrow's price datapoints with ALL fields."""

    _unrecorded_attributes = frozenset({"prices"})

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "tomorrow_prices")
        self._attr_name = "Tomorrow Prices"
        self._attr_icon = "mdi:calendar-arrow-right"

    @property
    def native_value(self) -> int:
        """Return the count of tomorrow's price points."""
        if not self.coordinator.data:
            return 0

        from homeassistant.util import dt as dt_util
        prices = self.coordinator.data.get("prices", [])
        tomorrow = (dt_util.now() + timedelta(days=1)).date()

        tomorrow_prices = [p for p in prices if datetime.fromisoformat(p["datetime"]).date() == tomorrow]
        return len(tomorrow_prices)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return tomorrow's price datapoints with ALL fields preserved."""
        from homeassistant.util import dt as dt_util

        attrs = super().extra_state_attributes

        if self.coordinator.data:
            all_prices = self.coordinator.data.get("prices", [])
            now = dt_util.now()
            tomorrow = (now + timedelta(days=1)).date()

            tomorrow_prices = []
            for p in all_prices:
                dt_obj = datetime.fromisoformat(p["datetime"])
                if dt_obj.date() == tomorrow:
                    # Keep ALL fields - no data loss
                    tomorrow_prices.append({
                        "datetime": p["datetime"],
                        "interval": p["interval"],
                        "price": p["price"],
                        "price_w_vat": p["price_w_vat"],
                        "market_price": p["market_price"],
                        "tar_cost": p["tar_cost"],
                    })

            attrs["prices"] = tomorrow_prices
            attrs["data_points"] = len(tomorrow_prices)
            attrs["last_update"] = datetime.now().isoformat()

            if tomorrow_prices:
                attrs["first_timestamp"] = tomorrow_prices[0]["datetime"]
                attrs["last_timestamp"] = tomorrow_prices[-1]["datetime"]

        return attrs


class EnergyPriceAllPricesSensor(EnergyPriceBaseSensor):
    """Sensor containing all price datapoints fetched from API.

    This sensor excludes the 'prices' attribute from recorder to avoid 16KB database limit.
    All data remains available to frontend (charts, dashboards) but won't be stored in history.
    """

    _unrecorded_attributes = frozenset({"prices"})

    def __init__(self, coordinator: EnergyPriceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "all_prices")
        self._attr_name = "All Prices"
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self) -> int:
        """Return the count of available price points."""
        if not self.coordinator.data:
            return 0

        prices = self.coordinator.data.get("prices", [])
        return len(prices)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return today and tomorrow's price datapoints with ALL fields preserved.

        The 'prices' attribute is excluded from recorder (see __init__.py) to avoid
        16KB database limit while keeping all data available to frontend for charts.
        """
        from homeassistant.util import dt as dt_util

        attrs = super().extra_state_attributes

        if self.coordinator.data:
            all_prices = self.coordinator.data.get("prices", [])

            # Filter to show today + tomorrow (48-hour window)
            now = dt_util.now()
            today = now.date()
            tomorrow = (now + timedelta(days=1)).date()

            visible_prices = []
            today_count = 0
            tomorrow_count = 0

            for p in all_prices:
                dt_obj = datetime.fromisoformat(p["datetime"])
                if dt_obj.date() == today:
                    # Keep ALL fields - no data loss
                    visible_prices.append({
                        "datetime": p["datetime"],
                        "interval": p["interval"],
                        "price": p["price"],
                        "price_w_vat": p["price_w_vat"],
                        "market_price": p["market_price"],
                        "tar_cost": p["tar_cost"],
                    })
                    today_count += 1
                elif dt_obj.date() == tomorrow:
                    # Keep ALL fields for tomorrow too
                    visible_prices.append({
                        "datetime": p["datetime"],
                        "interval": p["interval"],
                        "price": p["price"],
                        "price_w_vat": p["price_w_vat"],
                        "market_price": p["market_price"],
                        "tar_cost": p["tar_cost"],
                    })
                    tomorrow_count += 1

            attrs["prices"] = visible_prices
            attrs["data_points_today"] = today_count
            attrs["data_points_tomorrow"] = tomorrow_count
            attrs["data_points_total"] = len(all_prices)
            attrs["last_update"] = datetime.now().isoformat()

            # Add first and last timestamp for visible data
            if visible_prices:
                attrs["first_timestamp"] = visible_prices[0]["datetime"]
                attrs["last_timestamp"] = visible_prices[-1]["datetime"]

        return attrs


# ============================================================================
# GENERIC ROUTING SENSORS (Route to active provider)
# ============================================================================


class ActiveProviderBaseSensor(SensorEntity):
    """Base class for active provider routing sensors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, sensor_type: str, name: str) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._entry = entry
        self._sensor_type = sensor_type
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_active_provider_{sensor_type}"
        self._attr_has_entity_name = False
        self._attr_should_poll = False

    @property
    def config_entry_id(self) -> str:
        """Return the config entry ID this entity belongs to."""
        return self._entry.entry_id

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info to link sensor to the config entry's device."""
        # Link to the first provider's device to maintain connection
        return {
            "identifiers": {(DOMAIN, f"{DOMAIN}_routing_sensors")},
            "name": "Active Energy Provider (Routing Sensors)",
            "manufacturer": "Portuguese Energy Price Tracker",
            "model": "Routing Sensors",
            "entry_type": "service",
        }

    def _find_select_entity_id(self) -> str | None:
        """Find the integration's select entity, handling potential naming conflicts."""
        # Try exact match first
        select_entity_id = "select.active_energy_provider"
        if self._hass.states.get(select_entity_id):
            return select_entity_id

        # If not found, search for our select entity with unique_id
        entity_reg = er.async_get(self._hass)
        for entity in entity_reg.entities.values():
            if (entity.platform == DOMAIN and
                entity.domain == "select" and
                entity.unique_id == "active_provider"):  # Fixed: was f"{DOMAIN}_active_provider"
                _LOGGER.debug(f"Found integration select entity at: {entity.entity_id}")
                return entity.entity_id

        _LOGGER.warning("Could not find integration select entity")
        return None

    def _get_active_provider_entity(self, suffix: str) -> str | None:
        """Get the entity ID for the active provider's sensor."""
        # Get active provider from select entity
        select_entity_id = self._find_select_entity_id()
        if not select_entity_id:
            return None

        active_provider = self._hass.states.get(select_entity_id)

        if not active_provider or not active_provider.state or active_provider.state in ["unknown", "unavailable"]:
            _LOGGER.debug(f"Active provider select entity not ready (state={active_provider.state if active_provider else 'None'})")
            return None

        selected_display_name = active_provider.state

        # Handle empty configuration case
        if selected_display_name == "No providers configured":
            _LOGGER.debug(f"No providers configured")
            return None

        # Find the coordinator matching this display name
        if DOMAIN not in self._hass.data:
            _LOGGER.debug(f"Domain {DOMAIN} not in hass.data")
            return None

        _LOGGER.debug(f"Looking for coordinator with display_name: {selected_display_name}")
        for entry_id, coordinator in self._hass.data[DOMAIN].items():
            if hasattr(coordinator, "display_name"):
                _LOGGER.debug(f"  Found coordinator with display_name: {coordinator.display_name}")
                if coordinator.display_name == selected_display_name:
                    # Found the matching coordinator
                    # Instead of building entity_id, look it up in entity registry
                    # The unique_id format is: f"{DOMAIN}_{slug}_{suffix}"
                    # where slug comes from provider/tariff combination

                    entity_reg = er.async_get(self._hass)

                    # Search for entity with matching unique_id pattern
                    for entity in entity_reg.entities.values():
                        if (entity.platform == DOMAIN and
                            entity.unique_id and
                            entity.unique_id.endswith(f"_{suffix}") and
                            entity.config_entry_id == entry_id):
                            _LOGGER.debug(f"Matched! Found entity_id: {entity.entity_id}")
                            return entity.entity_id

                    _LOGGER.warning(f"Found coordinator but no matching entity for suffix '{suffix}'")
                    return None

        _LOGGER.warning(f"No coordinator found matching display_name: {selected_display_name}")
        return None

    async def async_added_to_hass(self) -> None:
        """Subscribe to provider sensor and select changes."""
        await super().async_added_to_hass()

        @callback
        def _update_callback(event):
            """Update when provider changes or provider sensor updates."""
            # Force refresh when select entity changes to ensure charts update
            # This is critical for ApexCharts and other UI components that watch attributes
            entity_id = event.data.get("entity_id")

            if entity_id == "select.active_energy_provider":
                old_state = event.data.get("old_state")
                new_state = event.data.get("new_state")

                # Only force refresh if the state actually changed
                if old_state and new_state and old_state.state != new_state.state:
                    _LOGGER.info(
                        f"[ROUTING] Active provider changed from '{old_state.state}' to '{new_state.state}' - "
                        f"forcing state refresh for {self._attr_name}"
                    )
                    self.async_schedule_update_ha_state(force_refresh=True)
                    return

            # For all other state changes, just schedule normal update
            self.async_schedule_update_ha_state(force_refresh=False)

        # Subscribe to all state changes (we'll filter for our select entity dynamically)
        self.async_on_remove(
            self._hass.bus.async_listen("state_changed", _update_callback)
        )

        # Trigger initial state update
        self.async_schedule_update_ha_state(force_refresh=True)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        entity_id = self._get_active_provider_entity("current_price")
        # Sensor is available only if we have a valid provider entity
        return entity_id is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        select_entity_id = "select.active_energy_provider"
        active_provider_state = self._hass.states.get(select_entity_id)

        attrs = {
            "active_provider": active_provider_state.state if active_provider_state else None,
            "integration": DOMAIN,
        }

        # Add helpful message when no providers configured
        if active_provider_state and active_provider_state.state == "No providers configured":
            attrs["info"] = "Please configure a provider via Settings > Devices & Services"

        return attrs


class ActiveProviderCurrentSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's current price (no VAT)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "current_price", "Active Provider Current Price")
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return the current price from active provider."""
        entity_id = self._get_active_provider_entity("current_price")
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None


class ActiveProviderCurrentVATSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's current price with VAT."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "current_price_with_vat", "Active Provider Current Price with VAT")
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return the current price with VAT from active provider."""
        entity_id = self._get_active_provider_entity("current_price_vat")
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None


class ActiveProviderTodayMaxSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's today max price."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "today_max_price", "Active Provider Today Max Price")
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return today's max price from active provider."""
        entity_id = self._get_active_provider_entity("today_max_price")
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None


class ActiveProviderTodayMaxVATSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's today max price with VAT."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "today_max_price_with_vat", "Active Provider Today Max Price with VAT")
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return today's max price with VAT from active provider."""
        entity_id = self._get_active_provider_entity("today_max_price_vat")
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None


class ActiveProviderTodayMinSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's today min price."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "today_min_price", "Active Provider Today Min Price")
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return today's min price from active provider."""
        entity_id = self._get_active_provider_entity("today_min_price")
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None


class ActiveProviderTodayMinVATSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's today min price with VAT."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "today_min_price_with_vat", "Active Provider Today Min Price with VAT")
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return today's min price with VAT from active provider."""
        entity_id = self._get_active_provider_entity("today_min_price_vat")
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None


class ActiveProviderAllPricesSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's all prices."""

    _unrecorded_attributes = frozenset({"prices"})

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "all_prices", "Active Provider All Prices")
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self) -> int:
        """Return the count of price points from active provider."""
        entity_id = self._get_active_provider_entity("all_prices")
        if not entity_id:
            return 0

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return int(state.state)
            except (ValueError, TypeError):
                return 0
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes including prices array."""
        attrs = super().extra_state_attributes

        entity_id = self._get_active_provider_entity("all_prices")
        if entity_id:
            state = self._hass.states.get(entity_id)
            if state and state.attributes:
                # Copy prices and metadata from provider sensor
                if "prices" in state.attributes:
                    attrs["prices"] = state.attributes["prices"]
                if "data_points_today" in state.attributes:
                    attrs["data_points_today"] = state.attributes["data_points_today"]
                if "data_points_total" in state.attributes:
                    attrs["data_points_total"] = state.attributes["data_points_total"]
                if "first_timestamp" in state.attributes:
                    attrs["first_timestamp"] = state.attributes["first_timestamp"]
                if "last_timestamp" in state.attributes:
                    attrs["last_timestamp"] = state.attributes["last_timestamp"]

        return attrs


class ActiveProviderTomorrowMaxSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's tomorrow max price."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "tomorrow_max_price", "Active Provider Tomorrow Max Price")
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return tomorrow's max price from active provider."""
        entity_id = self._get_active_provider_entity("tomorrow_max_price")
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None


class ActiveProviderTomorrowMaxVATSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's tomorrow max price with VAT."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "tomorrow_max_price_with_vat", "Active Provider Tomorrow Max Price with VAT")
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return tomorrow's max price with VAT from active provider."""
        entity_id = self._get_active_provider_entity("tomorrow_max_price_vat")
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None


class ActiveProviderTomorrowMinSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's tomorrow min price."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "tomorrow_min_price", "Active Provider Tomorrow Min Price")
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return tomorrow's min price from active provider."""
        entity_id = self._get_active_provider_entity("tomorrow_min_price")
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None


class ActiveProviderTomorrowMinVATSensor(ActiveProviderBaseSensor):
    """Generic sensor for active provider's tomorrow min price with VAT."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, "tomorrow_min_price_with_vat", "Active Provider Tomorrow Min Price with VAT")
        self._attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self) -> float | None:
        """Return tomorrow's min price with VAT from active provider."""
        entity_id = self._get_active_provider_entity("tomorrow_min_price_vat")
        if not entity_id:
            return None

        state = self._hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None
