# Portuguese Energy Price Tracker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/joaofernandes/portuguese_energy_price_tracker_ha_integration.svg)](https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration/releases)
[![License](https://img.shields.io/github/license/joaofernandes/portuguese_energy_price_tracker_ha_integration.svg)](LICENSE)

A Home Assistant custom integration that tracks real-time electricity prices for Portuguese energy providers. Get hourly energy prices from multiple providers including Coopérnico GO, G9 Smart Dynamic, and Alfa Power Index.

## Features

- **Real-time Energy Prices**: Fetches hourly electricity prices directly from GitHub CSV data source
- **Multiple Providers**: Supports various Portuguese energy providers and tariff options
- **Current & Historical Data**: Access current prices, today's min/max, and full price arrays
- **Bi-tariff Support**: Compatible with Bi-horário Diário and Bi-horário Semanal tariffs
- **VAT Flexibility**: Configurable VAT rate (default 23%) with automatic price calculations
- **Smart Caching**: 1-hour cache with local file fallback for offline reliability
- **Manual Refresh Service**: Force data updates with optional historical date lookup
- **Low Resource Usage**: Efficient CSV parsing with minimal memory footprint

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration`
6. Select category: "Integration"
7. Click "Add"
8. Find "Portuguese Energy Price Tracker" in HACS and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub releases](https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration/releases)
2. Extract the `energy_price_tracker` folder to your `custom_components` directory
3. Restart Home Assistant

## Configuration

### Via UI

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Portuguese Energy Price Tracker"
4. Follow the configuration flow:
   - **Provider**: Select your energy provider (e.g., Coopérnico GO, G9 Smart Dynamic)
   - **Tariff**: Choose your tariff plan (e.g., BIHORARIO_SEMANAL, SIMPLES)
   - **Display Name**: Custom name for this configuration (optional)
   - **VAT Rate**: VAT percentage (default: 23)

### Multiple Providers

You can add multiple instances for different providers or tariffs. Each instance creates its own set of sensors with unique entity IDs based on the provider and tariff.

## Sensors Created

The integration creates two types of sensors:

1. **Provider-Specific Sensors**: Created for each configured provider/tariff instance
2. **Generic Routing Sensors**: Automatically route to the active provider (selected via `select.energy_price_tracker_active_provider`)

### Generic Routing Sensors (Active Provider)

These sensors automatically reflect the currently selected provider's data. Use these in your automations and dashboards for seamless provider switching:

- **Active Provider Current Price** - `sensor.active_provider_current_price`
  - Current electricity price from the selected provider

- **Active Provider Current Price with VAT** - `sensor.active_provider_current_price_with_vat`
  - Current price including VAT from the selected provider

- **Active Provider Today Max Price** - `sensor.active_provider_today_max_price`
- **Active Provider Today Max Price with VAT** - `sensor.active_provider_today_max_price_with_vat`
- **Active Provider Today Min Price** - `sensor.active_provider_today_min_price`
- **Active Provider Today Min Price with VAT** - `sensor.active_provider_today_min_price_with_vat`

- **Active Provider All Prices** - `sensor.active_provider_all_prices`
  - Complete price array with all attributes from the selected provider

**Provider Selection:**
- **Active Energy Provider** - `select.energy_price_tracker_active_provider`
  - Select which provider's data to use in generic sensors
  - Options are automatically populated from configured instances

### Provider-Specific Sensors

For each configured instance, the integration creates the following sensors:

#### Price Sensors (with and without VAT)

- **Current Price** - `sensor.{provider}_{tariff}_current_price`
  - Current electricity price for the active time slot
  - Updates every hour based on pricing schedule

- **Current Price with VAT** - `sensor.{provider}_{tariff}_current_price_with_vat`
  - Current price including configured VAT rate

### Min/Max Sensors

- **Today's Maximum Price** - `sensor.{provider}_{tariff}_today_s_maximum_price`
- **Today's Maximum Price with VAT** - `sensor.{provider}_{tariff}_today_s_maximum_price_with_vat`
- **Today's Minimum Price** - `sensor.{provider}_{tariff}_today_s_minimum_price`
- **Today's Minimum Price with VAT** - `sensor.{provider}_{tariff}_today_s_minimum_price_with_vat`

### All Prices Sensor

- **All Prices** - `sensor.{provider}_{tariff}_all_prices`
  - Contains complete price array for today in attributes
  - State shows count of available price points
  - Attributes include:
    - `prices`: Array of today's hourly prices
    - `data_points_today`: Number of prices for today
    - `data_points_total`: Total prices cached
    - `first_timestamp`: First price timestamp
    - `last_timestamp`: Last price timestamp

## Services

### `energy_price_tracker.refresh_data`

Manually refresh energy price data from the source.

**Parameters:**
- `date` (optional): Specific date to fetch data for (YYYY-MM-DD format)
  - If not specified, fetches today's data
  - Always bypasses cache

**Examples:**

```yaml
# Refresh today's data
service: energy_price_tracker.refresh_data

# Fetch historical data for specific date
service: energy_price_tracker.refresh_data
data:
  date: "2025-11-16"
```

## Data Source

This integration fetches data directly from:
- **Source**: [GitHub CSV Repository](https://github.com/tiagofelicia/tiagofelicia.github.io)
- **File**: `data/precos-horarios.csv`
- **Update Frequency**: CSV is typically updated daily with next-day prices
- **Integration Refresh**: Every 5 minutes (configurable via SCAN_INTERVAL)

## Supported Providers & Tariffs

### Coopérnico GO
- Simples
- Bi-horário - Ciclo Diário
- Bi-horário - Ciclo Semanal

### G9 Smart Dynamic
- Simples
- Bi-horário - Ciclo Diário
- Bi-horário - Ciclo Semanal

### Alfa Power Index BTN
- Simples
- Bi-horário - Ciclo Diário
- Bi-horário - Ciclo Semanal

*Note: Provider and tariff availability depends on the CSV data source.*

## Advanced Usage

### Automation Examples

#### Charge Battery When Price is Low

```yaml
automation:
  - alias: "Charge Battery - Low Price"
    trigger:
      - platform: numeric_state
        entity_id: sensor.coopernico_energy_data_current_price_with_vat
        below: 0.15  # EUR/kWh
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.battery_charger
```

#### Notify When Peak Price is Coming

```yaml
automation:
  - alias: "Alert - Peak Price Soon"
    trigger:
      - platform: template
        value_template: >
          {% set current = states('sensor.coopernico_energy_data_current_price_with_vat') | float %}
          {% set max_price = states('sensor.coopernico_energy_data_today_s_maximum_price_with_vat') | float %}
          {{ current >= (max_price * 0.9) }}
    action:
      - service: notify.mobile_app
        data:
          message: "Peak electricity price in effect: {{ current }} EUR/kWh"
```

## Troubleshooting

### Sensors Show "Unknown"

**Possible causes:**
- No data available for today yet (CSV updated daily)
- GitHub source is temporarily unavailable
- Local cache is empty

**Solutions:**
1. Check logs: `Settings → System → Logs` (search for "energy_price_tracker")
2. Manually refresh: Call `energy_price_tracker.refresh_data` service
3. Verify GitHub source is accessible: https://raw.githubusercontent.com/tiagofelicia/tiagofelicia.github.io/main/data/precos-horarios.csv

### High Database Size Warning

If you see warnings about sensor attributes exceeding 16KB:
- This is normal for the `all_prices` sensor
- The integration automatically filters to today's prices only
- Older versions stored more data; update to latest version

### Integration Not Loading

**Check for:**
1. Timezone comparison errors → Update to latest version (fixed in v2.0.0)
2. Missing dependencies → Restart Home Assistant
3. Configuration errors → Check Configuration → Integrations

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Credits

- **Data Source**: [Tiago Felícia's Price Data](https://github.com/tiagofelicia/tiagofelicia.github.io)
- **CSV Format**: Maintained by the Portuguese energy community
- **Integration**: Built for Home Assistant community

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

## Support

- **Issues**: [GitHub Issues](https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration/discussions)
- **Home Assistant Community**: [Community Forum Thread](https://community.home-assistant.io)

---

**Disclaimer**: This integration relies on third-party data sources. Price accuracy and availability depend on the upstream CSV data provider. Always verify prices with your energy provider's official sources.
