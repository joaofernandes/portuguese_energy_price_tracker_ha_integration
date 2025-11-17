# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-11-17

### Changed
- **BREAKING**: Complete rewrite to fetch data directly from GitHub CSV instead of intermediate API
- Changed data source from `energy.bogos.me` API to direct GitHub CSV access
- Improved data reliability with direct source access
- Changed from 15-minute intervals to hourly aggregated prices
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
- Automatic hourly aggregation from 15-minute CSV intervals
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
