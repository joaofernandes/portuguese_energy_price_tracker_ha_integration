"""Energy Price Tracker Integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import DOMAIN, SCAN_INTERVAL
from .csv_fetcher import CSVDataFetcher

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT]

# Service schema for data refresh with optional date
SERVICE_REFRESH_DATA = "refresh_data"
SERVICE_REFRESH_SCHEMA = vol.Schema({
    vol.Optional("date"): cv.date,  # Optional date in YYYY-MM-DD format
})


async def _async_migrate_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate entities and clean up duplicates (one-time upgrade)."""
    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)

    # Check if migration has already run
    migration_version = entry.data.get("migration_version", 0)

    # Version 1: Clean up duplicate select entities (v2.2.0+)
    if migration_version < 1:
        _LOGGER.info("Running migration v1: Cleaning up duplicate select entities")

        # List of unique_ids to search for and remove (both old and new formats)
        unique_ids_to_clean = [
            f"{DOMAIN}_active_provider",  # New format with domain prefix
            "active_provider",            # Old format without prefix
            "energy_price_tracker_active_provider",  # Very old format from previous domain
        ]

        # Also need to search in the old domain name
        old_domain = "energy_price_tracker"

        all_entities = []

        # Search in current DOMAIN
        for unique_id in unique_ids_to_clean:
            for platform in [Platform.SELECT, Platform.SENSOR]:
                entity_id = entity_registry.async_get_entity_id(platform, DOMAIN, unique_id)
                if entity_id:
                    all_entities.append((platform, entity_id, unique_id))

        # Also search in old domain (for orphaned entities)
        for unique_id in unique_ids_to_clean:
            for platform in [Platform.SELECT, Platform.SENSOR]:
                entity_id = entity_registry.async_get_entity_id(platform, old_domain, unique_id)
                if entity_id:
                    all_entities.append((platform, entity_id, unique_id))

        # Also find ANY orphaned select entities with matching entity_id pattern
        # This catches entities that lost their config_entry_id
        for entity in entity_registry.entities.values():
            if (
                entity.entity_id == "select.active_energy_provider" and
                entity.platform in [DOMAIN, old_domain] and
                entity.config_entry_id is None
            ):
                # This is an orphaned entity
                if not any(e[1] == entity.entity_id for e in all_entities):
                    all_entities.append((entity.platform, entity.entity_id, entity.unique_id))
                    _LOGGER.info(f"Found orphaned select entity: {entity.entity_id} (unique_id: {entity.unique_id})")

        # Remove all found entities - we'll create a fresh one
        if all_entities:
            _LOGGER.info(f"Found {len(all_entities)} select entity(ies) to clean up")
            for platform, entity_id, unique_id in all_entities:
                _LOGGER.info(f"Removing {platform} entity {entity_id} (unique_id: {unique_id})")
                entity_registry.async_remove(entity_id)
            _LOGGER.info("Select entity cleanup complete. New entity will be created on next platform setup.")
        else:
            _LOGGER.debug("No duplicate select entities found")

        # Mark migration v1 as complete
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "migration_version": 1}
        )
        _LOGGER.info("Migration v1 complete")

    # Version 2: Clean up orphaned ActiveProvider routing sensor entities (v2.2.5+)
    # These are the generic sensors that route to the active provider
    if migration_version < 2:
        _LOGGER.info("Running migration v2: Cleaning up orphaned ActiveProvider routing sensors")

        # List of ActiveProvider routing sensor types (all the generic sensors)
        routing_sensor_types = [
            "current_price",
            "current_price_with_vat",
            "today_max_price",
            "today_max_price_with_vat",
            "today_min_price",
            "today_min_price_with_vat",
            "tomorrow_max_price",
            "tomorrow_max_price_with_vat",
            "tomorrow_min_price",
            "tomorrow_min_price_with_vat",
            "all_prices",
        ]

        orphaned_sensors = []

        # Find all ActiveProvider routing sensors that might be orphaned
        # These sensors are created by the first config entry only, but might have
        # lost their config_entry_id or have incorrect unique_ids
        for entity in entity_registry.entities.values():
            if entity.platform != DOMAIN or entity.domain != "sensor":
                continue

            # Check if this is an ActiveProvider routing sensor by entity_id pattern
            if entity.entity_id.startswith("sensor.active_provider_"):
                # Check if it's one of our known routing sensors
                is_routing_sensor = False
                for sensor_type in routing_sensor_types:
                    expected_unique_id = f"{DOMAIN}_active_provider_{sensor_type}"
                    if entity.unique_id == expected_unique_id:
                        is_routing_sensor = True
                        break

                # If entity_id matches pattern but unique_id doesn't match expected format,
                # or if it has no config_entry_id, it's orphaned
                if not is_routing_sensor or entity.config_entry_id is None:
                    orphaned_sensors.append(entity.entity_id)
                    _LOGGER.info(
                        f"Found orphaned ActiveProvider sensor: {entity.entity_id} "
                        f"(unique_id: {entity.unique_id}, config_entry_id: {entity.config_entry_id})"
                    )

        # Remove all orphaned routing sensors
        if orphaned_sensors:
            _LOGGER.info(f"Found {len(orphaned_sensors)} orphaned ActiveProvider routing sensor(s) to clean up")
            for entity_id in orphaned_sensors:
                _LOGGER.info(f"Removing orphaned sensor: {entity_id}")
                entity_registry.async_remove(entity_id)
            _LOGGER.info("ActiveProvider routing sensor cleanup complete. Fresh sensors will be created on next platform setup.")
        else:
            _LOGGER.debug("No orphaned ActiveProvider routing sensors found")

        # Mark migration v2 as complete
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "migration_version": 2}
        )
        _LOGGER.info("Migration v2 complete")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Price Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Run one-time migrations (version tracked per config entry)
    await _async_migrate_entities(hass, entry)

    coordinator = EnergyPriceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register service for data refresh
    async def handle_refresh_data(call: ServiceCall):
        """Handle the refresh data service call."""
        target_date = call.data.get("date")
        if target_date:
            target_datetime = datetime.combine(target_date, datetime.min.time())
        else:
            target_datetime = None

        _LOGGER.info(
            f"[REFRESH] Starting data refresh "
            f"for {'all configured instances' if target_datetime is None else target_datetime.strftime('%Y-%m-%d')}"
        )

        # Count instances to refresh
        instances = [
            coord for coord in hass.data[DOMAIN].values()
            if isinstance(coord, EnergyPriceCoordinator)
        ]

        if not instances:
            _LOGGER.warning(f"[REFRESH] No configured instances found for data refresh")
            return

        _LOGGER.info(f"[REFRESH] Found {len(instances)} instance(s) to refresh data for")

        # Refresh for all configured instances
        success_count = 0
        failed_count = 0

        for coord in instances:
            try:
                _LOGGER.info(
                    f"[REFRESH] Processing instance: {coord.display_name} "
                    f"({coord.provider} - {coord.tariff})"
                )
                await coord.refresh_data(target_date=target_datetime, bypass_cache=True)
                success_count += 1
            except Exception as err:
                failed_count += 1
                _LOGGER.error(
                    f"[REFRESH] Failed to refresh data for {coord.display_name}: {err}"
                )

        date_msg = f" for {target_datetime.strftime('%Y-%m-%d')}" if target_datetime else ""
        _LOGGER.info(
            f"[REFRESH] Data refresh completed{date_msg}. "
            f"Success: {success_count}, Failed: {failed_count}"
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_DATA,
        handle_refresh_data,
        schema=SERVICE_REFRESH_SCHEMA,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    # Remove service if no more entries
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_REFRESH_DATA)

    return unload_ok


async def async_remove_entry(_hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry.

    Note: CSV cache files are shared between all providers/tariffs and are
    date-based (prices_YYYY-MM-DD.csv), so they are NOT deleted when a
    provider is removed. They will be cleaned up naturally as they age.
    """
    _LOGGER.info(
        f"Removed config entry for {entry.data.get('provider')} - "
        f"{entry.data.get('tariff')} ({entry.title})"
    )


class EnergyPriceCoordinator(DataUpdateCoordinator):
    """Class to manage fetching energy price data from GitHub CSV."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.provider = entry.data["provider"]
        self.tariff = entry.data["tariff"]
        self.display_name = entry.data.get("display_name", f"{self.provider} {self.tariff}")
        self.vat = entry.data.get("vat", 23)
        self.include_vat = entry.data.get("include_vat", True)

        # Initialize CSV fetcher
        session = async_get_clientsession(hass)
        data_dir = Path(hass.config.config_dir) / "custom_components" / DOMAIN / "data"
        self.csv_fetcher = CSVDataFetcher(session, data_dir)

        super().__init__(
            hass,
            _LOGGER,
            name=f"Energy Price Tracker - {self.display_name}",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    async def _async_update_data(self):
        """Fetch data from GitHub CSV (both today and tomorrow)."""
        try:
            # Validate csv_fetcher is initialized
            if self.csv_fetcher is None:
                raise ValueError("CSV fetcher not initialized")

            if not hasattr(self.csv_fetcher, 'get_prices'):
                raise ValueError(f"CSV fetcher has no get_prices method. Type: {type(self.csv_fetcher)}")

            today_date = datetime.now().date()
            tomorrow_date = (datetime.now() + timedelta(days=1)).date()

            _LOGGER.info(
                f"[UPDATE] Starting data fetch for {self.display_name} - "
                f"Today: {today_date}, Tomorrow: {tomorrow_date}"
            )

            # Fetch today's prices
            today_prices = await self.csv_fetcher.get_prices(
                provider=self.provider,
                tariff=self.tariff,
                vat_rate=self.vat,
                target_date=None,  # Today
                bypass_cache=False,
            )
            _LOGGER.info(f"[UPDATE] Fetched {len(today_prices)} prices for TODAY ({today_date})")

            # Fetch tomorrow's prices
            tomorrow = datetime.now() + timedelta(days=1)
            tomorrow_prices = await self.csv_fetcher.get_prices(
                provider=self.provider,
                tariff=self.tariff,
                vat_rate=self.vat,
                target_date=tomorrow,
                bypass_cache=False,
            )
            _LOGGER.info(f"[UPDATE] Fetched {len(tomorrow_prices)} prices for TOMORROW ({tomorrow_date})")

            # Combine today and tomorrow prices
            all_prices = today_prices + tomorrow_prices
            _LOGGER.info(
                f"[UPDATE] Combined data for {self.display_name}: "
                f"Today={len(today_prices)}, Tomorrow={len(tomorrow_prices)}, Total={len(all_prices)}"
            )

            if len(tomorrow_prices) == 0:
                _LOGGER.warning(
                    f"[UPDATE] ⚠️  No prices found for tomorrow ({tomorrow_date})! "
                    f"Tomorrow's sensors will show 'Unknown'. This may be normal if tomorrow's "
                    f"data hasn't been published yet (usually available after 13:00 CET)."
                )

            return self._process_prices(all_prices)

        except Exception as err:
            _LOGGER.error(f"[UPDATE] Error fetching data for {self.display_name}: {err}", exc_info=True)
            raise UpdateFailed(f"Error fetching data: {err}")

    async def refresh_data(self, target_date: datetime | None = None, bypass_cache: bool = False):
        """Refresh data for a specific date or today (and tomorrow if refreshing today)."""
        try:
            # If refreshing today (target_date is None), fetch both today and tomorrow
            if target_date is None:
                _LOGGER.info(
                    f"[REFRESH] Fetching data for {self.display_name}: today and tomorrow"
                )

                # Fetch today's prices
                today_prices = await self.csv_fetcher.get_prices(
                    provider=self.provider,
                    tariff=self.tariff,
                    vat_rate=self.vat,
                    target_date=None,  # Today
                    bypass_cache=bypass_cache,
                )

                # Fetch tomorrow's prices
                tomorrow = datetime.now() + timedelta(days=1)
                tomorrow_prices = await self.csv_fetcher.get_prices(
                    provider=self.provider,
                    tariff=self.tariff,
                    vat_rate=self.vat,
                    target_date=tomorrow,
                    bypass_cache=bypass_cache,
                )

                # Combine today and tomorrow prices
                all_prices = today_prices + tomorrow_prices

                _LOGGER.info(
                    f"[REFRESH] Successfully fetched {len(today_prices)} price entries for today, "
                    f"{len(tomorrow_prices)} for tomorrow (total: {len(all_prices)}) for {self.display_name}"
                )

                # Update coordinator data with combined prices
                self.async_set_updated_data(self._process_prices(all_prices))

            else:
                # Refreshing a specific date
                _LOGGER.info(
                    f"[REFRESH] Fetching data for {self.display_name}: "
                    f"{target_date.strftime('%Y-%m-%d')}"
                )

                prices = await self.csv_fetcher.get_prices(
                    provider=self.provider,
                    tariff=self.tariff,
                    vat_rate=self.vat,
                    target_date=target_date,
                    bypass_cache=bypass_cache,
                )

                _LOGGER.info(
                    f"[REFRESH] Successfully fetched {len(prices)} price entries for {self.display_name}"
                )

                # Only update coordinator if refreshing today
                if target_date.date() == dt_util.now().date():
                    self.async_set_updated_data(self._process_prices(prices))

        except Exception as err:
            _LOGGER.error(
                f"[REFRESH] Failed to refresh data for {self.display_name}: {err}",
                exc_info=True
            )
            raise

    def _process_prices(self, prices: list[dict]) -> dict:
        """Process price data and calculate current/today's min/max."""
        if not prices:
            _LOGGER.warning(
                f"No price data found for {self.provider} - {self.tariff}. "
                f"All sensors will show 'Unknown'."
            )
            return {
                "prices": [],
                "current_price": None,
                "today_max_price": None,
                "today_min_price": None,
                "today_max_price_vat": None,
                "today_min_price_vat": None,
                "tomorrow_max_price": None,
                "tomorrow_min_price": None,
                "tomorrow_max_price_vat": None,
                "tomorrow_min_price_vat": None,
            }

        # Get today's date (timezone-aware)
        now = dt_util.now()
        today = now.date()

        # Filter today's prices
        today_prices = []
        today_prices_vat = []

        for p in prices:
            try:
                price_time = datetime.fromisoformat(p["datetime"])
                if price_time.date() == today:
                    if p.get("price") is not None:
                        today_prices.append(float(p["price"]))
                    if p.get("price_w_vat") is not None:
                        today_prices_vat.append(float(p["price_w_vat"]))
            except (ValueError, KeyError):
                continue

        # If no data for today, return None for all sensors
        if not today_prices:
            _LOGGER.warning(
                f"No price data found for today ({today}) for {self.provider} - {self.tariff}. "
                f"All sensors will show 'Unknown'."
            )
            return {
                "prices": prices,
                "current_price": None,
                "today_max_price": None,
                "today_min_price": None,
                "today_max_price_vat": None,
                "today_min_price_vat": None,
                "tomorrow_max_price": None,
                "tomorrow_min_price": None,
                "tomorrow_max_price_vat": None,
                "tomorrow_min_price_vat": None,
            }

        # Find current price (the period that contains the current time)
        # Price periods are 15 minutes: [HH:MM - HH:MM+15[
        current_price = None
        for price in prices:
            try:
                price_time = datetime.fromisoformat(price["datetime"])
                # Only consider today's prices
                if price_time.date() == today:
                    # Check if current time falls within this price period
                    # Period is [price_time, price_time + 15 minutes[
                    period_end = price_time + timedelta(minutes=15)
                    if price_time <= now < period_end:
                        current_price = price
                        break
            except (ValueError, KeyError):
                continue

        # If no matching period found (edge case), use the last price from today
        if not current_price:
            for price in reversed(prices):
                try:
                    price_time = datetime.fromisoformat(price["datetime"])
                    if price_time.date() == today:
                        current_price = price
                        break
                except (ValueError, KeyError):
                    continue

        # Calculate today's max/min
        today_max = max(today_prices) if today_prices else None
        today_min = min(today_prices) if today_prices else None
        today_max_vat = max(today_prices_vat) if today_prices_vat else None
        today_min_vat = min(today_prices_vat) if today_prices_vat else None

        # Filter tomorrow's prices
        tomorrow = (now + timedelta(days=1)).date()
        tomorrow_prices = []
        tomorrow_prices_vat = []

        for p in prices:
            try:
                price_time = datetime.fromisoformat(p["datetime"])
                if price_time.date() == tomorrow:
                    if p.get("price") is not None:
                        tomorrow_prices.append(float(p["price"]))
                    if p.get("price_w_vat") is not None:
                        tomorrow_prices_vat.append(float(p["price_w_vat"]))
            except (ValueError, KeyError):
                continue

        # Calculate tomorrow's max/min
        tomorrow_max = max(tomorrow_prices) if tomorrow_prices else None
        tomorrow_min = min(tomorrow_prices) if tomorrow_prices else None
        tomorrow_max_vat = max(tomorrow_prices_vat) if tomorrow_prices_vat else None
        tomorrow_min_vat = min(tomorrow_prices_vat) if tomorrow_prices_vat else None

        return {
            "prices": prices,
            "current_price": current_price,
            "today_max_price": today_max,
            "today_min_price": today_min,
            "today_max_price_vat": today_max_vat,
            "today_min_price_vat": today_min_vat,
            "tomorrow_max_price": tomorrow_max,
            "tomorrow_min_price": tomorrow_min,
            "tomorrow_max_price_vat": tomorrow_max_vat,
            "tomorrow_min_price_vat": tomorrow_min_vat,
        }
