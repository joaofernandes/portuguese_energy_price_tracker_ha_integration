# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **ApexCharts not updating when changing active provider**: Fixed routing sensors to force state refresh when select entity changes
  - Changed `_update_callback` to use `force_refresh=True` when `select.active_energy_provider` changes
  - Ensures Home Assistant notifies frontend about state updates even if values appear similar
  - ApexCharts and other UI components now receive immediate updates when switching providers
- **Active Provider (generic) sensors not working**: Fixed routing sensors not finding select entity
  - Changed unique_id lookup from `portuguese_energy_price_tracker_active_provider` to `active_provider`
  - Matches the select entity unique_id changed in v2.2.1
  - Routing sensors now properly find and work with the select entity

### Added

- **Enhanced logging for data fetch debugging**: Added detailed INFO-level logs to track today/tomorrow data fetching
  - Logs exact counts: "Fetched N prices for TODAY/TOMORROW"
  - Warns when tomorrow's data is empty (helps diagnose reload issues)
  - Better error logging with stack traces
  - Makes it clear when tomorrow's data is missing vs. successfully fetched
- **Automatic HACS installation**: Docker development container now auto-installs HACS on first startup
  - No manual installation needed - just `docker-compose up -d`
  - Checks for HACS presence and installs if missing
  - Uses `-o` flag for non-interactive overwrite during extraction
  - Extracts directly to `/config/custom_components/hacs` subdirectory
  - Maintains backward compatibility with manual installation script
- **Tomorrow's price data**: Complete 48-hour price data now available
  - **Three new sensors** for flexible data access:
    - `today_prices` - Today's data only with ALL fields (96 data points max)
    - `tomorrow_prices` - Tomorrow's data only with ALL fields (up to 96 data points)
    - `all_prices` - Combined 48-hour view (today + tomorrow, perfect for charts)
  - All sensors keep **ALL fields**: `datetime`, `interval`, `price`, `price_w_vat`, `market_price`, `tar_cost`
  - **No 16KB database warnings**: Uses `_unrecorded_attributes` to exclude `prices` from storage
    - Data remains fully available to frontend (charts, dashboards, automations)
    - Only excludes from long-term database storage to prevent size warnings
    - Better approach than field reduction - zero data loss
  - Enables better planning for next-day energy consumption
  - CSV source already contained tomorrow's data, now properly exposed
- Config entry removal handler (`async_remove_entry`) with proper logging
- Documentation for managing configurations (add, edit, delete) in README
- **Fully automated releases**: Every push to main now automatically creates a GitHub release
  - Auto-increments patch version (or uses manifest.json if changed)
  - Extracts changelog from [Unreleased] section
  - Creates tag and publishes release without manual intervention
- ApexCharts visualization examples for provider comparison in `examples/` directory

### Fixed

- **Select entity unique ID collision**: Fixed "ID active_provider already exists" error
  - Enhanced migration to find and remove orphaned entities from old domain
  - Now searches both current and old domain names
  - Scans for entities with no config_entry_id (orphaned)
  - Removes all duplicates before creating fresh select entity
- **Critical**: Fixed missing imports in sensor.py
  - Added missing `timedelta` import (fixed all_prices sensor crashes)
  - Added missing `entity_registry as er` import (fixed routing sensor crashes)
  - Resolves "NameError: name 'timedelta' is not defined" and "NameError: name 'er' is not defined"
  - All sensors now load correctly without import errors
- **Select entity initialization**: Fixed select entity not being created on restart
  - Changed setup logic to create entity on first config entry only
  - Prevents multiple setup attempts that were causing entity to stay unavailable
  - Routing sensors now properly detect when select entity becomes available
  - Handles "unavailable" state gracefully and updates when select becomes ready
- **Routing sensor entity lookup**: Fixed routing sensors not finding provider entities with special characters
  - Changed from string slugification to entity registry lookup
  - Now properly finds entities regardless of special characters (é, í, á, etc.)
  - Matches entities by config_entry_id and unique_id suffix pattern
  - Routing sensors now correctly display data from selected provider
- **Critical**: Fixed async/await error in CSV file saving
  - Changed `save_to_local()` from async to sync method
  - Fixed "object NoneType can't be used in 'await' expression" error
  - Resolves data fetching failures that prevented integration from loading price data
- **Icon display**: Moved icon files to repository root and converted to RGB format
  - Icons now display correctly in Home Assistant and HACS
  - Converted from RGBA to RGB to match Home Assistant icon standards
  - Added proper HACS configuration for icon loading
- **Duplicate unique ID**: Fixed entity unique_id collisions
  - Select entity: Changed from `active_provider` to `{domain}_active_provider`
  - Routing sensors: Changed from `active_provider_{type}` to `{domain}_active_provider_{type}`
  - Fixed migration mapping direction (was backwards, causing conflicts)
  - Prevents "ID already exists" errors when loading multiple config entries
  - All entities now create properly without unique ID warnings
- **Entity naming**: Simplified generic routing sensor entity IDs
  - Changed from `sensor.energy_price_tracker_active_provider_*` to `sensor.active_provider_*`
  - Select entity changed from `select.energy_price_tracker_active_provider` to `select.active_provider`
  - Cleaner, more intuitive entity names for automation and scripting
  - **Automatic migration**: Existing entities automatically migrate to new naming on update
  - Handles duplicate entities by removing conflicts before migration
- **Routing sensor availability**: Fixed entity mapping for generic `active_provider_*` sensors
  - Corrected display name to entity ID resolution
  - Generic sensors now properly route to provider+tariff combination
  - Fixes "unavailable" state for routing sensors

### Changed
- **IMPORTANT**: Removed hourly aggregation - now exposes native 15-minute intervals from CSV source
  - Increased data points from 24 to 96 per day (4 intervals per hour)
  - Provides higher granularity for accurate time-of-use optimization
  - No data loss from averaging - users see actual 15-minute pricing
- **Smart caching strategy**: Improved data persistence logic for better tomorrow's price availability
  - Today's data: Persisted to disk only when we have more complete data than existing cache
  - Tomorrow's data: Kept in memory cache, never overwrites more complete cached data
  - Smart overwrite protection: Only saves to disk if new data has more data points than existing
  - Past dates: Fetched from Git history only when explicitly requested
  - Coordinator now fetches both today and tomorrow in each update cycle
  - Ensures tomorrow's prices are always visible as soon as they're published upstream
- **Simplified configuration**: Removed options flow (configure/restore data menu)
  - VAT configuration remains at initial setup only (per provider/tariff)
  - Removed unnecessary post-configuration options menu
  - Removed historical data restore UI (data fetches automatically as needed)
- **Removed device grouping**: Each provider/tariff combination is now completely independent
  - Allows deleting individual tariffs without affecting other tariffs from same provider
  - Each config entry shows directly in integration list for easier management
  - No more nested device hierarchy - flat structure for better UX
- CSV cache files are now properly shared between all providers (date-based naming)
- Cache files are NOT deleted when removing a provider (as they're shared by all instances)
- Simplified GitHub Actions validation to only use Hassfest (removed HACS-specific checks)
- Updated documentation to reflect custom repository approach
- Streamlined release process with automation (no manual tagging needed)

## [2.0.0] - 2025-11-17

### Changed
- **BREAKING**: Complete rewrite to fetch data directly from GitHub CSV instead of intermediate API
- Changed data source from `energy.bogos.me` API to direct GitHub CSV access
- Improved data reliability with direct source access
- Updated SCAN_INTERVAL to 5 minutes (300 seconds) for better responsiveness

### Added
- **New**: Generic routing sensors with `active_provider` prefix for seamless provider switching
  - `sensor.active_provider_current_price` and `sensor.active_provider_current_price_with_vat`
  - `sensor.active_provider_today_max_price` and `sensor.active_provider_today_max_price_with_vat`
  - `sensor.active_provider_today_min_price` and `sensor.active_provider_today_min_price_with_vat`
  - `sensor.active_provider_all_prices`
- **New**: `select.energy_price_tracker_active_provider` for provider selection
  - Automatically populated with all configured provider instances
  - Generic sensors route to selected provider without template configuration
- Direct CSV fetching from GitHub with retry logic and exponential backoff
- Local file caching system for offline access (1-hour cache TTL)
- Historical data support via Git commit history
- UTF-8 BOM handling for proper CSV parsing
- Timezone-aware datetime handling throughout the integration
- `energy_price_tracker.refresh_data` service with optional date parameter
- Better error handling and logging for debugging

### Fixed
- **Critical**: Fixed timezone comparison error preventing integration from loading
  - Changed `datetime.now()` to `dt_util.now()` for timezone-aware comparisons
- **Critical**: Fixed 23:00 hour data gap that showed missing data in charts
  - Root cause: API changed to 15-minute intervals causing compatibility issues
  - Solution: Direct CSV parsing with proper hourly aggregation
- **Critical**: Fixed recorder warning about attribute size exceeding 16KB
  - Modified `AllPricesSensor` to store only today's prices instead of all historical data
  - Reduced database storage requirements significantly
- **Critical**: Fixed ESS Smart Battery Charging automation template errors
  - Stripped timezone info from datetime strings in sensor attributes
  - Ensures compatibility with existing automations expecting naive datetime format
- Improved NaN handling in CSV data (gracefully skips invalid rows)
- Better error messages for missing or invalid data

### Removed
- Removed dependency on intermediate API endpoint
- Removed `restore_historical_data` service (replaced by `refresh_data` with date parameter)
- Removed manual template sensor configuration requirement (now built into integration)

### Performance
- Reduced network requests: 1 per hour (cached) vs 1 every 5 minutes (old API)
- Smaller response size: ~50 KB (compressed CSV) vs ~192 KB (old API JSON)
- Fallback to local cache if offline
- Minimal disk space usage: ~500 KB per day for local cache

### Credits
- **Data Source**: Special thanks to **[Tiago Felícia](https://github.com/tiagofelicia)** for maintaining the comprehensive Portuguese energy price dataset at [tiagofelicia.github.io](https://github.com/tiagofelicia/tiagofelicia.github.io). This integration would not be possible without his dedication to collecting and providing accurate hourly energy price data for the Portuguese community.

## [1.1.0] - 2025-11-14

### Added
- Initial public release
- Support for multiple Portuguese energy providers
- Config flow for easy UI-based setup
- Basic sensors for current price, min/max prices
- All prices sensor with full data array
- VAT configuration support

### Fixed
- Minor bug fixes in config flow validation
- Improved error handling

## [1.0.0] - 2025-11-13

### Added
- Initial integration development
- Basic API integration with energy.bogos.me
- Provider and tariff selection
- Current price sensors
- Today's min/max price sensors

---

## Migration Guide

### From v1.x to v2.0

**No breaking changes for users:**
- Sensor entity names remain unchanged
- Sensor attributes remain compatible
- Existing automations continue to work

**What's different:**
1. Data source changed from API to direct CSV (more reliable)
2. Service `restore_historical_data` removed
   - Use `refresh_data` with `date` parameter instead
3. 23:00 hour data gap is fixed
4. Better performance with local caching

**Update steps:**
1. Update integration via HACS or manually
2. Restart Home Assistant
3. Verify sensors update correctly (check Developer Tools → States)
4. If using old `restore_historical_data` service, update automations to use `refresh_data`

**Example service call migration:**

```yaml
# OLD (v1.x) - No longer works
service: energy_price_tracker.restore_historical_data
data:
  provider: "Coopérnico GO"
  tariff: "BIHORARIO_SEMANAL"
  start_date: "2025-11-01"
  end_date: "2025-11-16"

# NEW (v2.0) - Fetch specific date
service: energy_price_tracker.refresh_data
data:
  date: "2025-11-16"  # Single day only
```

---

## Roadmap

### Planned Features
- [ ] Add support for more Portuguese energy providers
- [ ] Weekly/monthly price statistics sensors
- [ ] Price forecast integration with weather data
- [ ] Energy cost calculator helper
- [ ] Lovelace card for price visualization
- [ ] Multi-language support (PT, EN)

### Under Consideration
- [ ] Custom scan interval configuration via UI
- [ ] Price alerts and notifications
- [ ] Integration with Home Assistant Energy Dashboard
- [ ] Historical data export to CSV
- [ ] API rate limiting configuration

---

## Support

For issues, questions, or feature requests:
- [GitHub Issues](https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration/issues)
- [GitHub Discussions](https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration/discussions)
