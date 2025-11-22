# Migration System

## Automatic Entity Cleanup (v2.2.0+)

Starting with version 2.2.0, the integration includes an **automatic migration system** that runs once per config entry when the integration loads.

### How It Works

The migration system uses **version tracking** stored in each config entry's data to ensure migrations only run once:

```python
migration_version = entry.data.get("migration_version", 0)
```

### Migration v1: Duplicate Select Entity Cleanup

**Problem Solved**: In versions prior to 2.2.0, the select entity could be registered multiple times (once per config entry), causing this error:

```
Platform portuguese_energy_price_tracker does not generate unique IDs.
ID active_provider already exists - ignoring select.active_energy_provider
```

**Solution**: Migration v1 automatically removes ALL existing select entities from the registry when upgrading to v2.2.0+. The integration then creates a fresh, single select entity using the improved entity registry detection.

### Migration Process

When you upgrade to v2.2.0:

1. **First config entry loads**:
   - Migration v1 runs
   - Finds and removes all existing select entities
   - Marks migration v1 as complete (stores `migration_version: 1` in config entry data)
   - Creates fresh select entity with proper checks

2. **Second config entry loads**:
   - Checks if migration v1 already ran (yes)
   - Skips migration (already complete)
   - Detects existing select entity via entity registry
   - Skips creation (entity already exists)

3. **Subsequent restarts**:
   - Migration never runs again (version tracking prevents it)
   - Entity registry checks prevent duplicate creation

### Log Messages

Successful migration shows these logs:

```
INFO: Running migration v1: Cleaning up duplicate select entities
INFO: Removing select entity select.active_energy_provider for cleanup
INFO: Select entity cleanup complete. New entity will be created on next platform setup.
INFO: Migration v1 complete
DEBUG: Creating select entity with unique_id: portuguese_energy_price_tracker_active_provider
DEBUG: Select entity already exists in registry (select.active_energy_provider), skipping creation
```

### Benefits

- ✅ **Automatic**: No manual intervention required
- ✅ **Safe**: Runs once per config entry, never repeats
- ✅ **Clean**: Removes old problematic entities
- ✅ **Persistent**: Version tracking survives restarts
- ✅ **Extensible**: New migrations can be added with version checks

### Adding Future Migrations

To add a new migration in the future:

```python
# Version 2: Future migration example
if migration_version < 2:
    _LOGGER.info("Running migration v2: ...")
    # Migration logic here
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, "migration_version": 2}
    )
    _LOGGER.info("Migration v2 complete")
```

### Manual Cleanup Script

For systems that cannot wait for the automatic migration (or need manual intervention), the `scripts/cleanup_select_entity.py` script is still available for direct entity registry cleanup.

See [scripts/README.md](scripts/README.md) for usage instructions.
