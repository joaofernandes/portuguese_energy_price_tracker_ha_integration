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

from .const import CONF_ENABLE_DEBUG, DEFAULT_ENABLE_DEBUG, DOMAIN, SCAN_INTERVAL
from .csv_fetcher import CSVDataFetcher

_LOGGER = logging.getLogger(__name__)


def _set_logger_level(enable_debug: bool) -> None:
    """Set the logger level for the integration."""
    level = logging.DEBUG if enable_debug else logging.INFO
    _LOGGER.setLevel(level)

    # Also set level for csv_fetcher logger
    csv_fetcher_logger = logging.getLogger(f"{__name__.rsplit('.', 1)[0]}.csv_fetcher")
    csv_fetcher_logger.setLevel(level)

    # And for sensor logger
    sensor_logger = logging.getLogger(f"{__name__.rsplit('.', 1)[0]}.sensor")
    sensor_logger.setLevel(level)

    # And for select logger
    select_logger = logging.getLogger(f"{__name__.rsplit('.', 1)[0]}.select")
    select_logger.setLevel(level)

    _LOGGER.info(
        f"Debug logging {'enabled' if enable_debug else 'disabled'} for {DOMAIN}"
    )

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

    # DEBUG: Log migration entry details
    _LOGGER.info(f"[MIGRATION DEBUG] Starting migrations for entry_id: {entry.entry_id}")
    _LOGGER.info(f"[MIGRATION DEBUG] Current migration_version: {migration_version}")
    _LOGGER.info(f"[MIGRATION DEBUG] Entry data: {entry.data}")
    provider = entry.data.get("provider", "")
    tariff = entry.data.get("tariff", "")
    _LOGGER.info(f"[MIGRATION DEBUG] Provider: '{provider}', Tariff: '{tariff}'")
    _LOGGER.info(f"[MIGRATION DEBUG] Will check for migrations v1-v6")

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

    # Version 3: Clean up ALL ActiveProvider routing sensors to force recreation with config_entry_id (v2.2.7+)
    # Previous migrations didn't add config_entry_id property, so entities were still orphaned
    if migration_version < 3:
        _LOGGER.info("Running migration v3: Cleaning up ALL ActiveProvider routing sensors for recreation")

        # List of ActiveProvider routing sensor types
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

        all_routing_sensors = []

        # Find ALL ActiveProvider routing sensors regardless of config_entry_id
        for entity in entity_registry.entities.values():
            if entity.platform != DOMAIN or entity.domain != "sensor":
                continue

            # Check if this is an ActiveProvider routing sensor by unique_id pattern
            for sensor_type in routing_sensor_types:
                expected_unique_id = f"{DOMAIN}_active_provider_{sensor_type}"
                if entity.unique_id == expected_unique_id:
                    all_routing_sensors.append(entity.entity_id)
                    _LOGGER.info(
                        f"Found ActiveProvider sensor to clean: {entity.entity_id} "
                        f"(unique_id: {entity.unique_id}, config_entry_id: {entity.config_entry_id})"
                    )
                    break

        # Remove all routing sensors - they will be recreated with proper config_entry_id
        if all_routing_sensors:
            _LOGGER.info(f"Removing {len(all_routing_sensors)} ActiveProvider routing sensor(s) for clean recreation")
            for entity_id in all_routing_sensors:
                _LOGGER.info(f"Removing sensor: {entity_id}")
                entity_registry.async_remove(entity_id)
            _LOGGER.info("ActiveProvider routing sensors removed. They will be recreated with proper config_entry_id on next platform setup.")
        else:
            _LOGGER.debug("No ActiveProvider routing sensors found to clean")

        # Mark migration v3 as complete
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "migration_version": 3}
        )
        _LOGGER.info("Migration v3 complete")

    # Version 4: Fix select entity config_entry_id to match first config entry (v2.2.13+)
    # The select entity should be tied to the same entry as routing sensors (the first one)
    if migration_version < 4:
        _LOGGER.info("Running migration v4: Fixing select entity config_entry_id")

        # Find all config entries for this integration
        all_entries = [e for e in hass.config_entries.async_entries(DOMAIN)]
        if not all_entries:
            _LOGGER.warning("No config entries found for migration v4")
            # Mark migration as complete anyway to prevent re-running
            hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, "migration_version": 4}
            )
            return

        # Sort entries by entry_id to find the first one (same logic as sensor.py)
        all_entries_sorted = sorted(all_entries, key=lambda e: e.entry_id)
        first_entry_id = all_entries_sorted[0].entry_id

        _LOGGER.info(f"First config entry ID: {first_entry_id}")

        # Find the select entity with unique_id "active_provider"
        select_entity = None
        for entity in entity_registry.entities.values():
            if (entity.platform == DOMAIN and
                entity.domain == "select" and
                entity.unique_id == "active_provider"):
                select_entity = entity
                break

        if select_entity:
            current_entry_id = select_entity.config_entry_id
            if current_entry_id != first_entry_id:
                _LOGGER.info(
                    f"Updating select entity config_entry_id from {current_entry_id} to {first_entry_id}"
                )
                entity_registry.async_update_entity(
                    select_entity.entity_id,
                    config_entry_id=first_entry_id
                )
                _LOGGER.info("Select entity config_entry_id updated successfully")
            else:
                _LOGGER.debug(f"Select entity already has correct config_entry_id: {first_entry_id}")
        else:
            _LOGGER.warning("Select entity 'active_provider' not found in entity registry")

        # Mark migration v4 as complete
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "migration_version": 4}
        )
        _LOGGER.info("Migration v4 complete")

    # Version 5: Delete and recreate select entity with proper config_entry_id property (v2.2.14+)
    # Migration v4 updated the registry but the change didn't persist because the class
    # didn't have a config_entry_id property. Now we delete and recreate it properly.
    if migration_version < 5:
        _LOGGER.info("Running migration v5: Deleting old select entity for recreation")

        # Find the select entity
        select_entity = None
        for entity in entity_registry.entities.values():
            if (entity.platform == DOMAIN and
                entity.unique_id == "active_provider"):
                select_entity = entity
                break

        if select_entity:
            _LOGGER.info(f"Deleting select entity {select_entity.entity_id} to allow recreation with proper architecture")
            entity_registry.async_remove(select_entity.entity_id)
            _LOGGER.info("Select entity deleted - will be recreated by select platform with correct config_entry_id")
        else:
            _LOGGER.debug("Select entity not found in registry - will be created fresh by select platform")

        # Mark migration v5 as complete
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "migration_version": 5}
        )
        _LOGGER.info("Migration v5 complete")

    # Version 6: Delete provider sensors with old _vat suffix (v2.2.16+)
    # Provider sensors were using _vat suffix but should use _with_vat for consistency with routing sensors
    # This migration deletes old provider VAT sensors so they can be recreated with correct suffix.
    _LOGGER.info(f"[MIGRATION DEBUG] Checking migration v6 condition: migration_version ({migration_version}) < 6 = {migration_version < 6}")

    if migration_version < 6:
        _LOGGER.info("Running migration v6: Deleting provider sensors with old _vat suffix")

        # List of provider VAT sensor suffixes that need to be fixed
        old_suffixes = [
            "current_price_vat",
            "today_max_price_vat",
            "today_min_price_vat",
            "tomorrow_max_price_vat",
            "tomorrow_min_price_vat",
        ]

        deleted_count = 0
        provider = entry.data.get("provider", "")
        tariff = entry.data.get("tariff", "")

        _LOGGER.info(f"[MIGRATION DEBUG] Migration v6 - provider: '{provider}', tariff: '{tariff}'")
        _LOGGER.info(f"[MIGRATION DEBUG] Migration v6 - checking condition: provider and tariff = {bool(provider and tariff)}")

        # Only process provider entries (not the first entry which has routing sensors)
        if provider and tariff:
            _LOGGER.info(f"[MIGRATION DEBUG] Migration v6 - entering provider sensor deletion loop")
            for old_suffix in old_suffixes:
                # Build the old unique_id pattern for this provider's sensors
                old_unique_id = f"{DOMAIN}_{provider}_{tariff}_{old_suffix}".lower().replace(" ", "_")
                _LOGGER.info(f"[MIGRATION DEBUG] Migration v6 - searching for entity with unique_id: {old_unique_id}")

                found_entity = False
                for entity in entity_registry.entities.values():
                    if (entity.platform == DOMAIN and
                        entity.domain == "sensor" and
                        entity.unique_id == old_unique_id):
                        _LOGGER.info(f"Deleting provider sensor {entity.entity_id} with old unique_id: {old_unique_id}")
                        entity_registry.async_remove(entity.entity_id)
                        deleted_count += 1
                        found_entity = True
                        break

                if not found_entity:
                    _LOGGER.info(f"[MIGRATION DEBUG] Migration v6 - no entity found with unique_id: {old_unique_id}")

            if deleted_count > 0:
                _LOGGER.info(f"Deleted {deleted_count} provider sensor(s) with old _vat suffix - will be recreated with _with_vat suffix")
            else:
                _LOGGER.debug("No provider sensors with old _vat suffix found")

        # Mark migration v6 as complete
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "migration_version": 6}
        )
        _LOGGER.info("Migration v6 complete")
    else:
        _LOGGER.info(f"[MIGRATION DEBUG] Skipping migration v6 (migration_version={migration_version})")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Price Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Set debug logging level based on config
    enable_debug = entry.data.get(CONF_ENABLE_DEBUG, DEFAULT_ENABLE_DEBUG)
    _set_logger_level(enable_debug)

    # Run one-time migrations (version tracked per config entry)
    await _async_migrate_entities(hass, entry)

    coordinator = EnergyPriceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_update_options))

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


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # Merge options into entry data
    new_data = {**entry.data, **entry.options}

    # Update the config entry with merged data
    hass.config_entries.async_update_entry(entry, data=new_data, options={})

    # Update debug logging level if it changed
    enable_debug = new_data.get(CONF_ENABLE_DEBUG, DEFAULT_ENABLE_DEBUG)
    _set_logger_level(enable_debug)

    # Reload the entry to apply other changes
    await hass.config_entries.async_reload(entry.entry_id)


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

            # Fetch tomorrow's prices with smart cache bypass after 1 PM
            # After 1 PM, if tomorrow's data isn't available, we bypass cache
            # and try to fetch fresh data from GitHub until it's available
            now = datetime.now()
            tomorrow = now + timedelta(days=1)

            # Determine if we should bypass cache for tomorrow's data
            # Bypass if: current time >= 13:00 (1 PM)
            should_bypass_cache = now.hour >= 13

            if should_bypass_cache:
                _LOGGER.info(
                    f"[UPDATE] Time is after 1 PM ({now.strftime('%H:%M')}) - "
                    f"will bypass cache for tomorrow's data to ensure fresh fetch"
                )

            tomorrow_prices = await self.csv_fetcher.get_prices(
                provider=self.provider,
                tariff=self.tariff,
                vat_rate=self.vat,
                target_date=tomorrow,
                bypass_cache=should_bypass_cache,
            )
            _LOGGER.info(
                f"[UPDATE] Fetched {len(tomorrow_prices)} prices for TOMORROW ({tomorrow_date})"
                f"{' (cache bypassed)' if should_bypass_cache else ''}"
            )

            # Combine today and tomorrow prices
            all_prices = today_prices + tomorrow_prices
            _LOGGER.info(
                f"[UPDATE] Combined data for {self.display_name}: "
                f"Today={len(today_prices)}, Tomorrow={len(tomorrow_prices)}, Total={len(all_prices)}"
            )

            # Debug log if tomorrow's data is empty (no warning - sensors will use default values)
            if len(tomorrow_prices) == 0:
                _LOGGER.debug(
                    f"[UPDATE] No prices available for tomorrow ({tomorrow_date}). "
                    f"Tomorrow's sensors will use default values (typically 0 for prices, empty for arrays)."
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
