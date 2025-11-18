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


async def _async_migrate_entities(hass: HomeAssistant) -> None:
    """Migrate entity unique IDs from old format to new format."""
    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)

    # Migration mappings: old unique_id -> new unique_id
    migrations = {
        # Select entity migration
        f"{DOMAIN}_active_provider": "active_provider",
        # Sensor migrations
        f"{DOMAIN}_active_provider_all_prices": "active_provider_all_prices",
        f"{DOMAIN}_active_provider_current_price": "active_provider_current_price",
        f"{DOMAIN}_active_provider_current_price_with_vat": "active_provider_current_price_with_vat",
        f"{DOMAIN}_active_provider_today_max_price": "active_provider_today_max_price",
        f"{DOMAIN}_active_provider_today_max_price_with_vat": "active_provider_today_max_price_with_vat",
        f"{DOMAIN}_active_provider_today_min_price": "active_provider_today_min_price",
        f"{DOMAIN}_active_provider_today_min_price_with_vat": "active_provider_today_min_price_with_vat",
    }

    for old_unique_id, new_unique_id in migrations.items():
        # Find entity with old unique ID
        entity_id = entity_registry.async_get_entity_id(Platform.SENSOR, DOMAIN, old_unique_id)
        if not entity_id:
            # Try select platform
            entity_id = entity_registry.async_get_entity_id(Platform.SELECT, DOMAIN, old_unique_id)

        if entity_id:
            _LOGGER.info(f"Migrating entity {entity_id} from unique_id '{old_unique_id}' to '{new_unique_id}'")
            entity_registry.async_update_entity(entity_id, new_unique_id=new_unique_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Price Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Migrate old entity unique IDs to new format (one-time migration)
    await _async_migrate_entities(hass)

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
        """Fetch data from GitHub CSV."""
        try:
            prices = await self.csv_fetcher.get_prices(
                provider=self.provider,
                tariff=self.tariff,
                vat_rate=self.vat,
                target_date=None,  # Today
                bypass_cache=False,
            )

            return self._process_prices(prices)

        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")

    async def refresh_data(self, target_date: datetime | None = None, bypass_cache: bool = False):
        """Refresh data for a specific date or today."""
        try:
            _LOGGER.info(
                f"[REFRESH] Fetching data for {self.display_name}: "
                f"{'today' if target_date is None else target_date.strftime('%Y-%m-%d')}"
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

            # If refreshing today's data, update the coordinator data
            if target_date is None or target_date.date() == dt_util.now().date():
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
            }

        # Find current price (first future or current time slot for TODAY only)
        current_price = None
        for price in prices:
            try:
                price_time = datetime.fromisoformat(price["datetime"])
                # Only consider today's prices
                if price_time.date() == today and price_time >= now:
                    current_price = price
                    break
            except (ValueError, KeyError):
                continue

        # If no future price found for today, use the last price from today
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

        return {
            "prices": prices,
            "current_price": current_price,
            "today_max_price": today_max,
            "today_min_price": today_min,
            "today_max_price_vat": today_max_vat,
            "today_min_price_vat": today_min_vat,
        }
