# Data Flow Architecture

This document describes the data flow within the Portuguese Energy Price Tracker integration for Home Assistant.

## Architecture Diagram

```mermaid
flowchart TD
    %% User Interaction Layer
    USER[User/Automation] -->|Configure Integration| CONFIG_FLOW[Config Flow]
    USER -->|Call Service| REFRESH_SERVICE[refresh_data Service]
    USER -->|Change Provider| SELECT[select.active_energy_provider]

    %% Configuration Layer
    CONFIG_FLOW -->|Create Entry| SETUP[async_setup_entry]
    SETUP -->|Initialize| COORDINATOR[EnergyPriceCoordinator]
    SETUP -->|Create| PLATFORMS[Platform Setup]
    SETUP -->|Set Logger Level| LOGGER[Logger Configuration]
    SETUP -->|Register| REFRESH_SERVICE

    %% Coordinator Layer
    COORDINATOR -->|Schedule Updates| UPDATE_CYCLE[Update Cycle<br/>Every 5 minutes]
    UPDATE_CYCLE -->|_async_update_data| FETCH_LOGIC{Check Time}
    REFRESH_SERVICE -->|Force Update| FETCH_LOGIC

    %% Cache Decision Logic
    FETCH_LOGIC -->|After 1 PM| BYPASS_CACHE[Bypass Cache<br/>bypass_cache=True]
    FETCH_LOGIC -->|Before 1 PM| USE_CACHE[Use Cache<br/>bypass_cache=False]

    %% Data Fetching Layer
    BYPASS_CACHE -->|Today| FETCHER_TODAY[CSVDataFetcher.get_prices<br/>target_date=None]
    BYPASS_CACHE -->|Tomorrow| FETCHER_TOMORROW[CSVDataFetcher.get_prices<br/>target_date=tomorrow]
    USE_CACHE -->|Today| FETCHER_TODAY
    USE_CACHE -->|Tomorrow| FETCHER_TOMORROW

    %% CSV Fetcher Logic
    FETCHER_TODAY --> CACHE_CHECK{Cache<br/>Valid?}
    FETCHER_TOMORROW --> CACHE_CHECK

    CACHE_CHECK -->|Yes & !bypass| DISK_CACHE[Load from<br/>CSV Cache File]
    CACHE_CHECK -->|No or bypass| GITHUB[Fetch from GitHub<br/>CSV Repository]

    GITHUB -->|Success| PARSE_CSV[Parse CSV<br/>Calculate VAT]
    GITHUB -->|404 Error| GIT_HISTORY[Fetch from<br/>Git History]
    GIT_HISTORY -->|Success| PARSE_CSV
    GIT_HISTORY -->|Fail| RETURN_EMPTY[Return Empty Array]

    PARSE_CSV --> SAVE_CACHE[Save to<br/>CSV Cache File]
    SAVE_CACHE --> RETURN_DATA[Return Price Array]
    DISK_CACHE --> RETURN_DATA
    RETURN_EMPTY --> RETURN_DATA

    %% Data Processing
    RETURN_DATA -->|Combine| PROCESS[_process_prices<br/>Calculate min/max/current]
    PROCESS --> UPDATE_COORDINATOR[Update Coordinator Data]

    %% Platform Layer
    PLATFORMS -->|Create| PROVIDER_SENSORS[Provider-Specific Sensors<br/>e.g., sensor.g9_current_price]
    PLATFORMS -->|Create| ROUTING_SENSORS[ActiveProvider Routing Sensors<br/>e.g., sensor.active_provider_current_price]
    PLATFORMS -->|Create| SELECT

    %% Data Flow to Sensors
    UPDATE_COORDINATOR -->|Notify| PROVIDER_SENSORS
    UPDATE_COORDINATOR -->|Notify| ROUTING_SENSORS

    %% Routing Sensor Logic
    SELECT -->|State Change Event| ROUTING_UPDATE[Routing Sensor<br/>Update Callback]
    ROUTING_UPDATE -->|Find Provider| LOOKUP[Lookup Active Provider<br/>Coordinator]
    LOOKUP -->|Get Data| PROVIDER_DATA[Provider Coordinator Data]
    PROVIDER_DATA -->|Update State| ROUTING_SENSORS

    %% Final Output
    PROVIDER_SENSORS -->|Expose| HA_STATE[Home Assistant State Machine]
    ROUTING_SENSORS -->|Expose| HA_STATE
    SELECT -->|Expose| HA_STATE
    HA_STATE -->|Read| USER

    %% Style Definitions
    classDef userLayer fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef configLayer fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef coordLayer fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef fetchLayer fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef sensorLayer fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef cacheDecision fill:#fff9c4,stroke:#f57f17,stroke-width:3px

    class USER,SELECT,HA_STATE userLayer
    class CONFIG_FLOW,SETUP,LOGGER,PLATFORMS configLayer
    class COORDINATOR,UPDATE_CYCLE,REFRESH_SERVICE,PROCESS,UPDATE_COORDINATOR coordLayer
    class FETCHER_TODAY,FETCHER_TOMORROW,GITHUB,GIT_HISTORY,PARSE_CSV,SAVE_CACHE,DISK_CACHE fetchLayer
    class PROVIDER_SENSORS,ROUTING_SENSORS,ROUTING_UPDATE,LOOKUP,PROVIDER_DATA sensorLayer
    class FETCH_LOGIC,CACHE_CHECK,BYPASS_CACHE,USE_CACHE cacheDecision
```

## Component Descriptions

### User Interaction Layer
- **User/Automation**: Home Assistant users or automations that interact with the integration
- **Config Flow**: UI-based configuration for adding/editing providers
- **select.active_energy_provider**: Dropdown to select which provider's data to display in routing sensors

### Configuration Layer
- **async_setup_entry**: Initializes the integration when a config entry is loaded
- **Logger Configuration**: Sets DEBUG or INFO level based on user's "Enable Debug Logging" option
- **Platform Setup**: Creates sensor and select platforms

### Coordinator Layer
- **EnergyPriceCoordinator**: DataUpdateCoordinator that manages data fetching and updates
- **Update Cycle**: Runs every 5 minutes (SCAN_INTERVAL) to fetch fresh data
- **Check Time**: After 1 PM, uses `bypass_cache=True` for tomorrow's data to ensure fresh fetch
- **_process_prices**: Calculates current price, today's min/max, tomorrow's min/max

### Data Fetching Layer
- **CSVDataFetcher**: Handles fetching and caching CSV data from GitHub
- **Cache Check**: Verifies if cached data exists and is valid (< 1 hour old)
- **GitHub CSV Repository**: Primary data source for current prices
- **Git History**: Fallback for historical data when CSV file doesn't exist yet
- **CSV Cache File**: Disk cache stored in `custom_components/portuguese_energy_price_tracker/data/`

### Sensor Layer
- **Provider-Specific Sensors**: Direct sensors for each configured provider (e.g., `sensor.g9_current_price`)
- **ActiveProvider Routing Sensors**: Generic sensors that automatically route to the active provider's data
- **Routing Update Callback**: Listens for select entity state changes and forces sensor updates

## Data Flow Scenarios

### Normal Update Cycle (Before 1 PM)
1. Coordinator triggers update every 5 minutes
2. Fetches today's data with cache (if valid)
3. Fetches tomorrow's data with cache (if valid)
4. Combines data and updates all sensors
5. Routing sensors read from active provider's coordinator

### Smart Cache Bypass (After 1 PM)
1. Coordinator detects time >= 13:00
2. Fetches today's data with cache (if valid)
3. **Bypasses cache** for tomorrow's data, always tries GitHub
4. Continues retrying fresh fetch until tomorrow's data is available
5. Once available, data is cached and normal behavior resumes

### Provider Switch via select.active_energy_provider
1. User changes select entity value
2. Select entity fires state_changed event
3. Routing sensors receive event in `_update_callback`
4. Routing sensors call `force_refresh=True` to notify frontend
5. Sensors look up new provider's coordinator data
6. ApexCharts and UI components receive update notifications

### Manual Refresh via Service
1. User calls `portuguese_energy_price_tracker.refresh_data`
2. Service handler iterates all coordinators
3. Each coordinator fetches with `bypass_cache=True`
4. Optional: specific date can be requested for historical lookup
5. Updates only affect coordinator data if date == today

## Caching Strategy

### Memory Cache
- Stores in-progress fetch operations to prevent duplicate requests
- Cleared after data is successfully fetched

### Disk Cache
- CSV files stored per date: `prices_YYYY-MM-DD.csv`
- Valid for 1 hour after creation
- Shared between all provider/tariff instances
- Not deleted when providers are removed (shared resource)

### Cache Bypass Logic
```python
# After 1 PM, always try to fetch fresh data for tomorrow
should_bypass_cache = datetime.now().hour >= 13

tomorrow_prices = await csv_fetcher.get_prices(
    target_date=tomorrow,
    bypass_cache=should_bypass_cache  # True after 1 PM
)
```

## Sensor Update Propagation

```
Coordinator Data Change
    ↓
Provider-Specific Sensors Updated (immediate)
    ↓
Select Entity Changed (if user switches provider)
    ↓
state_changed Event Fired
    ↓
Routing Sensors _update_callback
    ↓
force_refresh=True
    ↓
Frontend Notified
    ↓
ApexCharts/UI Components Re-render
```

## Key Design Decisions

1. **Smart Cache Bypass**: Only after 1 PM to reduce GitHub API calls while ensuring timely data availability
2. **Routing Sensors**: Allow seamless provider switching without reconfiguring dashboards/automations
3. **Shared CSV Cache**: Reduces redundant fetches across multiple provider instances
4. **Git History Fallback**: Provides historical data access for dates without published CSV files
5. **Force Refresh on Select Change**: Ensures UI updates even when numeric values appear similar between providers
6. **Debug Logging Option**: Users can enable detailed logging without editing configuration.yaml

## Error Handling

### CSV Fetch Failures
- GitHub 404 → Try Git history
- Git history fail → Return empty array
- Sensors display `None` or `Unknown`

### Empty Tomorrow Data
- Before 1 PM: Normal, uses cache or returns empty
- After 1 PM: Retries fresh fetch every 5 minutes until available
- Sensors for tomorrow show `None` until data arrives

### Coordinator Errors
- Logged with stack trace
- Raises `UpdateFailed` to prevent bad data
- Retries on next update cycle
