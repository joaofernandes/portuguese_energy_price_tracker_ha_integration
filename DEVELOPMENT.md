# Development Guide

This guide explains how to set up a local development environment for the Portuguese Energy Price Tracker integration.

## Prerequisites

- Docker and Docker Compose installed
- Git

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration.git
   cd portuguese_energy_price_tracker_ha_integration
   ```

2. **Start the development environment**:
   ```bash
   docker-compose up -d
   ```

3. **Access Home Assistant**:
   - Open http://localhost:8123
   - Complete the onboarding process
   - The integration is automatically available in Settings → Devices & Services

4. **View logs**:
   ```bash
   # Follow all logs
   docker-compose logs -f

   # View integration-specific logs
   docker-compose logs -f | grep energy_price_tracker
   ```

5. **Stop the environment**:
   ```bash
   docker-compose down
   ```

## Development Workflow

### Making Changes

1. **Edit code** in `custom_components/energy_price_tracker/`
2. **Restart Home Assistant** to load changes:
   ```bash
   docker-compose restart
   ```

   Or use the UI: Developer Tools → YAML → Restart

3. **Check logs** for errors:
   ```bash
   docker-compose logs -f homeassistant
   ```

### Testing Changes

1. **Add a provider configuration**:
   - Go to Settings → Devices & Services
   - Click "+ ADD INTEGRATION"
   - Search for "Portuguese Energy Price Tracker"
   - Configure a provider (e.g., G9, Galp, etc.)

2. **Verify entities are created**:
   - Go to Developer Tools → States
   - Search for entities:
     - Provider-specific: `sensor.{provider}_{tariff}_current_price`
     - Generic routing: `sensor.active_provider_current_price`
     - Select: `select.active_provider`

3. **Test routing sensors**:
   - Change the active provider using `select.active_provider`
   - Verify generic sensors update to reflect the selected provider
   - Check that prices are correct

4. **Enable debug logging** (already configured in `dev_config/configuration.yaml`):
   ```yaml
   logger:
     logs:
       custom_components.energy_price_tracker: debug
   ```

### Debugging

#### View Integration Logs

Debug logs are enabled by default in the dev environment. Look for:

```
Looking for coordinator with display_name: ...
Found coordinator with display_name: ...
Matched! Built entity_id: ...
```

#### Check Entity Registry

```bash
# Enter container
docker exec -it energy_price_tracker_dev bash

# Check entity registry
cd /config/.storage
cat core.entity_registry | jq '.data.entities[] | select(.platform=="energy_price_tracker")'
```

#### Test Data Refresh

Use the service call in Developer Tools → Services:

```yaml
service: energy_price_tracker.refresh_data
data:
  date: "2025-11-18"  # Optional: specific date
```

### Common Issues

#### Integration Not Loading

1. Check logs: `docker-compose logs -f`
2. Verify Python syntax: No errors in logs
3. Restart: `docker-compose restart`

#### Entities Not Appearing

1. Check if integration is loaded: Settings → Devices & Services
2. View entity registry: Developer Tools → States
3. Check logs for errors during entity creation

#### Routing Sensors Unavailable

1. Verify `select.active_provider` has a valid value
2. Check debug logs for entity mapping messages
3. Ensure provider-specific sensors exist and are available

## File Structure

```
.
├── custom_components/energy_price_tracker/  # Integration source code
│   ├── __init__.py                          # Setup and coordinator
│   ├── sensor.py                            # Sensor entities
│   ├── select.py                            # Select entity
│   ├── config_flow.py                       # Configuration UI
│   └── manifest.json                        # Integration metadata
├── dev_config/                              # Development HA config
│   └── configuration.yaml                   # HA configuration
├── docker-compose.yml                       # Docker setup
└── DEVELOPMENT.md                           # This file
```

## Tips

### Fast Iteration

For quick testing without full restart:

1. **Reload integration**:
   - Settings → Devices & Services
   - Click "..." on integration
   - Click "Reload"

2. **Restart Core** (faster than full restart):
   - Developer Tools → YAML → Quick Reload → Restart

### Clean Start

To start fresh with clean state:

```bash
# Stop and remove containers/volumes
docker-compose down -v

# Remove dev_config (except configuration.yaml)
rm -rf dev_config/.storage dev_config/*.db* dev_config/*.log

# Start again
docker-compose up -d
```

### Persistent Testing Data

The `dev_config/` directory persists between restarts:
- Configuration
- Entity registry
- State history
- Logs

This allows you to test upgrades and migrations without losing data.

## Testing Scenarios

### Test Entity Migration

1. Start with an old version (checkout old commit)
2. Configure the integration
3. Stop HA
4. Update to new version (checkout new commit)
5. Restart HA
6. Verify migration logs and entity renaming

### Test Multiple Providers

1. Add multiple provider configurations
2. Verify `select.active_provider` shows all options
3. Test switching between providers
4. Verify routing sensors update correctly

### Test Edge Cases

1. **No providers configured**: Verify graceful handling
2. **Provider unavailable**: Check error handling
3. **Network issues**: Test offline behavior with cached data
4. **Invalid configuration**: Verify validation in config flow

## Contributing

When submitting changes:

1. Test locally using this development environment
2. Verify all entities work correctly
3. Check logs for warnings or errors
4. Ensure migration works for existing users
5. Update CHANGELOG.md with your changes

## Troubleshooting

### Container Won't Start

```bash
# Check container status
docker-compose ps

# View container logs
docker-compose logs homeassistant

# Rebuild container
docker-compose up -d --build
```

### Permission Issues

```bash
# Fix permissions on dev_config
sudo chown -R $USER:$USER dev_config
```

### Port 8123 Already in Use

```bash
# Stop other HA instances
docker ps | grep homeassistant
docker stop <container_id>

# Or change port in docker-compose.yml:
ports:
  - "8124:8123"  # Use different port
```

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Integration Development](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Integration Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index/)
