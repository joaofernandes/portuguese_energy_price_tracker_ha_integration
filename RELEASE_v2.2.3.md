# Release v2.2.3 - Active Provider Sensors Fixed

## What Was Broken

In v2.2.1, we changed the select entity's unique_id from:
- `"portuguese_energy_price_tracker_active_provider"`
- To: `"active_provider"`

But we forgot to update [sensor.py:690](custom_components/portuguese_energy_price_tracker/sensor.py#L690), which was still looking for the old unique_id. This caused the **Active Provider (generic) routing sensors** to be unable to find the select entity, making them unavailable/non-clickable.

## What's Fixed

**v2.2.3** fixes the mismatch:
- Updated `_find_select_entity_id()` in sensor.py to search for `"active_provider"`
- Active Provider sensors now properly locate the select entity
- All routing sensors (current price, min, max, etc.) work correctly

## How to Update

### In HACS:
1. Go to **HACS > Integrations**
2. If HACS hasn't detected the update yet:
   - Click **⋮** (three dots) → **"Reload data"**
   - Wait a few seconds
3. Find **Portuguese Energy Price Tracker**
4. Click **Update** (should show v2.2.3)
5. **Restart Home Assistant** (required!)

### After Restart:

1. Go to **Settings > Devices & Services > Integrations**
2. Find **Portuguese Energy Price Tracker**
3. Should show **Version 2.2.3**
4. Click on it to verify all entities are accessible
5. Both provider-specific AND Active Provider (generic) sensors should work

## What to Check

After updating to v2.2.3:

### ✅ Select Entity Works
- `select.active_energy_provider` should be clickable
- Can change between providers

### ✅ Provider-Specific Sensors Work
- Example: `sensor.g9_bihorario_semanal_current_price`
- Shows data for that specific provider

### ✅ Active Provider Sensors Work (Fixed!)
- Example: `sensor.active_provider_current_price`
- Should now be **clickable and accessible**
- Shows data for whichever provider is selected
- Updates when you change the active provider

### ✅ Logs Show Data Fetch (from v2.2.2)
Check logs for:
```
[UPDATE] Starting data fetch for <provider> - Today: YYYY-MM-DD, Tomorrow: YYYY-MM-DD
[UPDATE] Fetched N prices for TODAY (YYYY-MM-DD)
[UPDATE] Fetched N prices for TOMORROW (YYYY-MM-DD)
[UPDATE] Combined data: Today=N, Tomorrow=N, Total=N
```

## Version History

- **v2.2.3** (current) - Fixed Active Provider sensors
- **v2.2.2** - Added enhanced logging for debugging
- **v2.2.1** - Fixed unique ID collision, simplified unique_id format
- **v2.2.0** - Previous release

## If Issues Persist

If Active Provider sensors still don't work after updating:

1. **Check Home Assistant logs** for errors
2. **Verify select entity exists**: Look for `select.active_energy_provider`
3. **Try removing and re-adding** the integration (last resort)

The fix is straightforward - just a one-line change to match the unique_id formats!
