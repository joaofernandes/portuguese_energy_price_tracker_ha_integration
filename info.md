# Portuguese Energy Price Tracker

Track real-time electricity prices for Portuguese energy providers directly in Home Assistant.

## Key Features

⚡ **Real-time Prices** - Hourly electricity prices from multiple Portuguese providers
📊 **Complete Data** - Current price, today's min/max, and full price arrays
🔄 **Smart Caching** - 1-hour cache with offline fallback for reliability
🏷️ **Multi-Provider** - Supports Coopérnico GO, G9 Smart Dynamic, Alfa Power Index
💰 **Flexible VAT** - Configurable VAT rates with automatic calculations
⏱️ **Bi-Tariff Ready** - Compatible with Bi-horário Diário and Semanal tariffs

## Quick Start

1. **Install via HACS** (or manually)
2. **Add Integration** via Settings → Devices & Services
3. **Select Provider** and tariff plan
4. **Use Sensors** in your automations and dashboards

## What You Get

Each configured provider creates sensors for:
- Current electricity price (with/without VAT)
- Today's maximum price (for peak detection)
- Today's minimum price (for optimal charging)
- Complete hourly price array (for advanced automations)

## Example Use Cases

- **Smart Charging**: Charge EV or battery when prices are low
- **Load Shifting**: Run appliances during cheap hours
- **Cost Tracking**: Monitor your energy costs in real-time
- **Price Alerts**: Get notified when peak prices arrive
- **Energy Optimization**: Integrate with solar/battery systems

## Data Source

Fetches directly from trusted Portuguese energy price data hosted on GitHub. Updated daily with next-day prices.

## Support

- Provider coverage across Portugal
- Hourly price updates
- Historical data access
- Manual refresh service
- Reliable offline caching

Perfect for smart home energy management and cost optimization!
