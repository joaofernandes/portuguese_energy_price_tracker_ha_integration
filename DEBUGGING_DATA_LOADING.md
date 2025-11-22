# Debugging: "Only Today's Data Loads" Issue

## Problem Description

When reloading or installing a new version of the integration at 21h (when tomorrow's data should be available), only today's data is loaded into the sensors.

## Investigation

### Expected Behavior

The `_async_update_data()` method should:
1. Fetch today's prices from GitHub CSV
2. Fetch tomorrow's prices from the same CSV (contains both days)
3. Combine both into a single list
4. Process and update sensors with both days' data

### Code Flow

```python
async def _async_update_data(self):
    # Step 1: Fetch today
    today_prices = await self.csv_fetcher.get_prices(target_date=None)

    # Step 2: Fetch tomorrow
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_prices = await self.csv_fetcher.get_prices(target_date=tomorrow)

    # Step 3: Combine
    all_prices = today_prices + tomorrow_prices

    # Step 4: Process
    return self._process_prices(all_prices)
```

## Changes Made (v2.2.1)

### Enhanced Logging

Added detailed INFO-level logging to track exactly what's happening:

1. **Start of fetch**: Logs today's and tomorrow's dates
2. **After today fetch**: Logs how many prices were found for today
3. **After tomorrow fetch**: Logs how many prices were found for tomorrow
4. **After combining**: Logs the totals (today + tomorrow + combined)
5. **Warning if empty**: If tomorrow_prices is empty, logs a warning

### Log Messages to Look For

```
[UPDATE] Starting data fetch for <provider> - Today: YYYY-MM-DD, Tomorrow: YYYY-MM-DD
[UPDATE] Fetched N prices for TODAY (YYYY-MM-DD)
[UPDATE] Fetched N prices for TOMORROW (YYYY-MM-DD)
[UPDATE] Combined data: Today=N, Tomorrow=N, Total=N
```

If tomorrow's data is missing:
```
[UPDATE] ⚠️  No prices found for tomorrow (YYYY-MM-DD)!
         Tomorrow's sensors will show 'Unknown'. This may be normal if tomorrow's
         data hasn't been published yet (usually available after 13:00 CET).
```

## Testing Instructions

1. **Deploy v2.2.1** to your Home Assistant instance
2. **Reload the integration** at a time when tomorrow's data should be available (after 13:00 CET)
3. **Check the logs** immediately after reload:
   ```bash
   # In Home Assistant
   Settings > System > Logs
   # Or via command line:
   tail -f /config/home-assistant.log | grep "\[UPDATE\]"
   ```

4. **Look for the log messages** above to see:
   - How many prices were fetched for today
   - How many prices were fetched for tomorrow
   - Whether tomorrow_prices is 0 (empty)

## Possible Root Causes

If tomorrow_prices shows 0 in the logs:

### 1. GitHub CSV Doesn't Contain Tomorrow's Data Yet
- **Symptom**: `Fetched 0 prices for TOMORROW`
- **Cause**: Data publisher hasn't updated the CSV file yet
- **Solution**: Wait until after 13:00 CET, then reload or wait for next update cycle

### 2. CSV Parsing Issue
- **Symptom**: `Fetched 0 prices for TOMORROW` but CSV file exists and has data
- **Cause**: Bug in date parsing or filtering logic in `csv_fetcher.py`
- **Solution**: Check `get_prices()` and `parse_csv()` methods

### 3. Caching Issue
- **Symptom**: First reload shows 0, subsequent reloads show correct data
- **Cause**: Cached CSV from before tomorrow's data was published
- **Solution**: Use `bypass_cache=True` during first refresh or clear cache directory

### 4. Timezone Issue
- **Symptom**: Tomorrow's date calculation is incorrect
- **Cause**: Mismatch between HA timezone and CSV timezone
- **Solution**: Check timezone handling in date comparisons

## Next Steps

After deploying and checking logs:

1. **If tomorrow_prices = 0**:
   - Check what time the CSV is actually updated on GitHub
   - Verify the CSV contains tomorrow's date at all
   - Check if date parsing is working correctly

2. **If tomorrow_prices > 0 but sensors still show Unknown**:
   - Issue is in `_process_prices()` method
   - Check how tomorrow's min/max values are calculated

3. **If logs show correct counts but UI shows old data**:
   - Entity state may not be updating properly
   - Check sensor update mechanism

## Manual Test

You can manually trigger a refresh with:
```yaml
# In Developer Tools > Services
service: portuguese_energy_price_tracker.refresh_data
```

This will bypass cache and fetch fresh data from GitHub.
