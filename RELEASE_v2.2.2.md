# Release v2.2.2 - Ready to Push

## What's Been Done

I've prepared v2.2.2 with the following changes:

### ✅ Changes Committed

1. **Enhanced logging in `__init__.py`**:
   - Added INFO-level logs for data fetch tracking
   - Shows exact counts: "Fetched N prices for TODAY/TOMORROW"
   - Warns when tomorrow's data is empty
   - Better error logging with stack traces

2. **Updated `manifest.json`**: Version bumped to 2.2.2

3. **Updated `CHANGELOG.md`**: Added release notes to `[Unreleased]` section

### 📝 Commit Created

```
commit 54b2fc1
v2.2.2: Add detailed logging for data fetch debugging

- Add INFO-level logs to track today/tomorrow data fetching
- Log exact counts: 'Fetched N prices for TODAY/TOMORROW'
- Add warning if tomorrow's data is empty
- Better error logging with stack traces
```

## How to Release

Since you have GitHub Actions set up for automated releases, just push:

```bash
git push origin main
```

The workflow will automatically:
1. ✅ Read version `2.2.2` from `manifest.json`
2. ✅ Extract changelog from `[Unreleased]` section
3. ✅ Create tag `v2.2.2`
4. ✅ Publish GitHub Release
5. ✅ HACS will pick up the new release

## After Pushing

### In HACS (on your Home Assistant)

1. Go to **HACS > Integrations**
2. Find **Portuguese Energy Price Tracker**
3. You should see "Update available: 2.2.2"
4. Click **Update**
5. **Restart Home Assistant**

### Check the Logs

After restart, look for these new log messages:

```
[UPDATE] Starting data fetch for <provider> - Today: 2025-11-21, Tomorrow: 2025-11-22
[UPDATE] Fetched 96 prices for TODAY (2025-11-21)
[UPDATE] Fetched 96 prices for TOMORROW (2025-11-22)
[UPDATE] Combined data: Today=96, Tomorrow=96, Total=192
```

If tomorrow's data is missing, you'll see:
```
[UPDATE] ⚠️  No prices found for tomorrow (2025-11-22)!
```

This will tell us exactly what's happening during reload.

## What This Fixes

### Issue 1: Unique ID Collision ✅
- **Fixed in v2.2.1** (included here)
- Enhanced migration removes all orphaned select entities
- No more "ID active_provider already exists" error

### Issue 2: Data Loading Debugging 🔍
- **New in v2.2.2**
- Detailed logs show exactly how many prices are fetched
- Makes it clear if tomorrow's data is missing vs. successfully loaded
- Helps diagnose why only today's data loads on reload

## Expected Outcome

After updating to v2.2.2 and reloading:
- ✅ No unique ID collision errors
- ✅ Clear logs showing data fetch status
- ✅ We can see if tomorrow's data is actually being fetched
- ✅ Easier to diagnose the "only today's data" issue

## Next Steps

1. **Push this commit**: `git push origin main`
2. **Wait for GitHub Actions** (usually < 1 minute)
3. **Update in HACS**
4. **Restart Home Assistant**
5. **Check logs** and share the `[UPDATE]` messages with me

This will give us the data we need to understand why only today's data loads!
