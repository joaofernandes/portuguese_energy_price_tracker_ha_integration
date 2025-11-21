# Dashboard Examples

This directory contains example Lovelace dashboards for visualizing energy price data from the Portuguese Energy Price Tracker integration.

## Prerequisites

- **ApexCharts Card** installed via HACS Frontend
  - Go to HACS → Frontend → Search for "ApexCharts Card" → Install
  - Repository: https://github.com/RomRider/apexcharts-card

## Available Examples

### [energy_price_comparison.yaml](energy_price_comparison.yaml)

A comprehensive dashboard comparing two energy providers side-by-side.

**Features:**
- 24-hour price comparison line chart (stepline)
- Price difference visualization (area chart with color thresholds)
- Daily statistics (min/avg/max) for both providers
- Real-time "Now" indicator
- Automatic data extraction from sensor attributes

**Dashboard Sections:**
1. **Main Comparison Chart** - Overlays both providers' prices
2. **Price Difference Chart** - Shows Coopernico minus G9 with color coding:
   - Green: Coopernico is cheaper
   - Yellow: Break-even
   - Red: Coopernico is more expensive
3. **Daily Statistics** - Min/Avg/Max prices for each provider

## Installation

### Option 1: Manual Dashboard (Recommended for Testing)

1. Copy the dashboard content from `energy_price_comparison.yaml`
2. In Home Assistant, go to **Settings → Dashboards**
3. Click **Add Dashboard** → **New dashboard from scratch**
4. Name it "Energy Price Comparison"
5. Click the ⋮ menu → **Edit Dashboard** → **Raw configuration editor**
6. Paste the content and save

### Option 2: YAML Dashboard Mode

If you use YAML mode for dashboards:

1. Copy `energy_price_comparison.yaml` to your Home Assistant config:
   ```bash
   cp energy_price_comparison.yaml /config/dashboards/
   ```

2. Add to your `configuration.yaml`:
   ```yaml
   lovelace:
     mode: storage
     dashboards:
       energy-price-comparison:
         mode: yaml
         title: Energy Price Comparison
         icon: mdi:chart-line
         show_in_sidebar: true
         filename: dashboards/energy_price_comparison.yaml
   ```

3. Restart Home Assistant

## Customization

### Using Different Sensors

Replace the sensor entity IDs with your own:

```yaml
series:
  - entity: sensor.YOUR_PROVIDER_1_all_prices
    name: Provider 1
    color: '#2196F3'

  - entity: sensor.YOUR_PROVIDER_2_all_prices
    name: Provider 2
    color: '#FF9800'
```

### Finding Your Sensor Names

Your sensors follow this pattern:
```
sensor.<provider>_<tariff>_all_prices
```

Examples:
- `sensor.coopernico_base_bi_horario_ciclo_semanal_all_prices`
- `sensor.g9_bihorario_semanal_all_prices`
- `sensor.edp_comercial_simples_all_prices`

Use **Developer Tools → States** to find your exact sensor names.

### Changing Time Range

Modify the `graph_span` parameter:

```yaml
graph_span: 24h    # Show 24 hours
graph_span: 48h    # Show 2 days
graph_span: 7d     # Show 1 week
```

### Adjusting Colors

Change the color codes in the series:

```yaml
series:
  - entity: sensor.coopernico_base_bi_horario_ciclo_semanal_all_prices
    color: '#2196F3'  # Blue
    # Other popular colors:
    # '#4CAF50' - Green
    # '#FF9800' - Orange
    # '#F44336' - Red
    # '#9C27B0' - Purple
    # '#00BCD4' - Cyan
```

### Adding More Providers

To compare 3+ providers, duplicate the series block:

```yaml
series:
  - entity: sensor.provider_1_all_prices
    name: Provider 1
    color: '#2196F3'

  - entity: sensor.provider_2_all_prices
    name: Provider 2
    color: '#FF9800'

  - entity: sensor.provider_3_all_prices
    name: Provider 3
    color: '#4CAF50'
```

## Data Structure

The dashboard uses the `all_prices` sensor which contains an array of price objects in its attributes:

```json
{
  "prices": [
    {
      "datetime": "2025-01-19T00:00:00+00:00",
      "interval": "[00:00-00:15[",
      "price": 0.12345,
      "price_w_vat": 0.15184,
      "market_price": 0.08000,
      "tar_cost": 0.04345
    },
    ...
  ]
}
```

The `data_generator` extracts this data and formats it for ApexCharts:

```javascript
data_generator: |
  return entity.attributes.prices.map((item) => {
    return [new Date(item.datetime).getTime(), item.price_w_vat];
  });
```

You can use any of these fields:
- `item.price` - Price without VAT
- `item.price_w_vat` - Price with VAT (most common)
- `item.market_price` - OMIE market price only
- `item.tar_cost` - Regulated tariff cost only

## Troubleshooting

### "Custom element doesn't exist: apexcharts-card"

**Solution**: Install ApexCharts Card via HACS Frontend, then clear browser cache (Ctrl+F5)

### Dashboard shows "Entity not found"

**Solution**:
1. Check entity ID exists in **Developer Tools → States**
2. Verify the integration has fetched data (check sensor attributes)
3. Wait 5 minutes for first data fetch

### Chart is empty

**Solution**:
1. Verify sensor has `prices` attribute with data
2. Check browser console for JavaScript errors (F12)
3. Ensure `prices` array has at least one entry

### Prices showing as "0" or "NaN"

**Solution**:
1. Check if CSV source has valid data for your provider/tariff
2. Verify VAT rate is configured correctly
3. Check integration logs for parsing errors

## Advanced Examples

### Show Only Peak Hours (18:00-22:00)

```yaml
series:
  - entity: sensor.coopernico_base_bi_horario_ciclo_semanal_all_prices
    name: Peak Hours Only
    data_generator: |
      return entity.attributes.prices
        .filter((item) => {
          const hour = new Date(item.datetime).getHours();
          return hour >= 18 && hour < 22;
        })
        .map((item) => {
          return [new Date(item.datetime).getTime(), item.price_w_vat];
        });
```

### Calculate Hourly Average (from 15-min intervals)

```yaml
series:
  - entity: sensor.coopernico_base_bi_horario_ciclo_semanal_all_prices
    name: Hourly Average
    data_generator: |
      const prices = entity.attributes.prices;
      const hourly = {};

      prices.forEach((item) => {
        const hour = new Date(item.datetime).getHours();
        if (!hourly[hour]) hourly[hour] = [];
        hourly[hour].push(item.price_w_vat);
      });

      return Object.entries(hourly).map(([hour, values]) => {
        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        const date = new Date();
        date.setHours(hour, 0, 0, 0);
        return [date.getTime(), avg];
      });
```

### Show Market Price vs Final Price Breakdown

```yaml
series:
  - entity: sensor.coopernico_base_bi_horario_ciclo_semanal_all_prices
    name: Market Price (OMIE)
    type: area
    color: '#4CAF50'
    data_generator: |
      return entity.attributes.prices.map((item) => {
        return [new Date(item.datetime).getTime(), item.market_price];
      });

  - entity: sensor.coopernico_base_bi_horario_ciclo_semanal_all_prices
    name: Tariff Cost
    type: area
    color: '#FF9800'
    data_generator: |
      return entity.attributes.prices.map((item) => {
        return [new Date(item.datetime).getTime(), item.tar_cost];
      });

  - entity: sensor.coopernico_base_bi_horario_ciclo_semanal_all_prices
    name: Final Price (with VAT)
    type: line
    stroke_width: 3
    color: '#F44336'
    data_generator: |
      return entity.attributes.prices.map((item) => {
        return [new Date(item.datetime).getTime(), item.price_w_vat];
      });
```

## Contributing

Have a cool dashboard example? Submit a PR with your YAML file and description!

## Support

For issues with:
- **This integration**: https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration/issues
- **ApexCharts Card**: https://github.com/RomRider/apexcharts-card/issues
- **Home Assistant**: https://community.home-assistant.io/
