# Routing Sensors Fix - Troubleshooting Guide

## Current Status

The ActiveProvider routing sensors (`sensor.active_provider_*`) are reporting:
> "This entity is no longer being provided by the portuguese_energy_price_tracker integration"

## What's Implemented

The code currently HAS the proper fix:

1. **`config_entry_id` property** (line 680-682 in sensor.py) ✅
2. **Migration v3** to clean up old sensors (lines 187-254 in __init__.py) ✅
3. **Proper initialization** with entry parameter (lines 56-71 in sensor.py) ✅
4. **Device grouping** for routing sensors (lines 685-694 in sensor.py) ✅
5. **Force update flag** to ensure state changes (line 678 in sensor.py) ✅

## Why Sensors Show as "No Longer Provided"

This happens when:
1. Migration v3 removes old routing sensors
2. But new sensors haven't been created yet
3. OR the sensors exist but Home Assistant hasn't recognized them yet

## Required Steps to Fix

### Step 1: Complete Restart (Not Just Reload)
```bash
# In Home Assistant:
# Settings > System > Restart Home Assistant
# (NOT just "Reload integration")
```

**Why**: Integration reload doesn't always trigger entity recreation. A full HA restart ensures all entities are properly registered.

### Step 2: Verify Migration Ran
After restart, check logs for:
```
Running migration v3: Cleaning up ALL ActiveProvider routing sensors for recreation
Removing X ActiveProvider routing sensor(s) for clean recreation
Migration v3 complete
```

### Step 3: Verify Sensors Were Created
Check logs for:
```
Adding generic routing sensors linked to first config entry: <entry_id>
```

### Step 4: Check Entity Registry
The routing sensors should appear with:
- **unique_id**: `portuguese_energy_price_tracker_active_provider_current_price` (etc.)
- **config_entry_id**: Same as your FIRST provider's entry ID
- **device**: "Active Energy Provider (Routing Sensors)"

## If Still Not Working

### Option A: Manual Entity Cleanup
1. Go to Settings > Devices & Services > Integrations
2. Find "Portuguese Energy Price Tracker"
3. Click on each "Active Provider" sensor showing the error
4. Click "Delete" to remove them
5. Restart Home Assistant
6. Sensors should be recreated automatically

### Option B: Remove and Re-add First Provider
1. Note which provider was added FIRST (check creation date)
2. Remove that provider configuration
3. Re-add it (it will become the "first" again)
4. Routing sensors will be created with new config_entry_id
5. All other providers remain unaffected

### Option C: Nuclear Option - Remove All and Re-add
1. Remove ALL provider configurations
2. Restart Home Assistant
3. Add providers back one by one
4. First one added will host the routing sensors

## Architecture Explanation

### Why Tied to First Entry?

Home Assistant requires config-entry-based integrations to have entities tied to config entries. The routing sensors:

- **Must** have a `config_entry_id` (HA requirement)
- **Are shared** across all providers (not provider-specific)
- **Solution**: Tie to the first provider entry as a "host"

### What If First Provider Is Removed?

The routing sensors will become orphaned and show the "no longer provided" error. This is a known limitation. Solutions:

1. Don't remove the first provider (remove others instead)
2. OR remove all providers and re-add them
3. OR implement a synthetic "system" config entry (complex, not done yet)

## Current Code Status

- ✅ All necessary code is implemented
- ✅ Migration v3 is active and working
- ✅ Sensors have proper config_entry_id property
- ✅ Force update flag added for state propagation
- ⚠️ Requires full HA restart, not just integration reload
- ⚠️ Sensors tied to first provider entry (architectural limitation)

## Future Improvements

Potential solutions for full independence:

1. **Synthetic Config Entry**: Create a hidden "system" entry just for routing sensors
2. **Helper Entity Registry**: Use HA's helper entity system instead of config entry entities
3. **MQTT Integration Pattern**: Use a different integration pattern that allows global entities

These would require significant architectural changes and are not implemented in v2.2.7/v2.2.8.

## Testing Checklist

- [ ] Full Home Assistant restart completed
- [ ] Migration v3 log messages appear
- [ ] Sensor creation log messages appear
- [ ] Routing sensors appear in entity registry
- [ ] Routing sensors show values (not "unavailable")
- [ ] `select.active_energy_provider` is working
- [ ] Changing active provider updates routing sensor values
- [ ] Provider-specific sensors still working

## Need More Help?

Enable debug logging:
1. Go to Settings > Devices & Services
2. Find Portuguese Energy Price Tracker
3. Click Configure on any provider
4. Enable "Enable Debug Logging"
5. Check Home Assistant logs for detailed information
