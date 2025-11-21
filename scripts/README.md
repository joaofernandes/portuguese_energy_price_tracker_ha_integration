# Development Scripts

Automation scripts for development, testing, and release management of the Portuguese Energy Price Tracker integration.

## cleanup_select_entity.py

**⚠️ NOTE**: As of v2.2.0, the integration includes **automatic migration** that handles this cleanup on upgrade. This script is now primarily a **backup/troubleshooting tool** for edge cases.

### When to use

**Automatic Migration (v2.2.0+)**: When you upgrade from an earlier version to v2.2.0+, the integration automatically cleans up duplicate select entities. No manual action needed!

**This manual script is only needed if**:
1. You're already on v2.2.0+ and still have duplicates
2. The automatic migration didn't run or failed
3. You need to troubleshoot entity registry issues manually

If you see this error after upgrading to v2.2.0+:
```
Platform portuguese_energy_price_tracker does not generate unique IDs.
ID active_provider already exists - ignoring select.active_energy_provider
```

This script can manually remove the duplicates.

### Usage

**⚠️ IMPORTANT: Stop Home Assistant before running this script!**

```bash
# Dry run (preview changes without modifying)
python3 scripts/cleanup_select_entity.py /path/to/.storage/core.entity_registry

# Actually clean up duplicates
python3 scripts/cleanup_select_entity.py /path/to/.storage/core.entity_registry --apply
```

### What it does

1. ✅ Creates automatic backup of entity registry
2. ✅ Finds all select entities for this integration
3. ✅ Keeps the first one, removes duplicates
4. ✅ Saves cleaned registry

### Example

```bash
# Stop Home Assistant first!
cd /config
python3 scripts/cleanup_select_entity.py .storage/core.entity_registry

# Output:
# 📊 Found 2 select entity(ies):
#   - select.active_energy_provider
#   - select.active_energy_provider
#
# ⚠️  Found 2 duplicate select entities!
#    Will keep the first one and remove 1 duplicate(s)
#
# 🔍 DRY RUN - No changes will be made
#    Run with --apply to actually clean up the registry

# If everything looks good, apply the cleanup:
python3 scripts/cleanup_select_entity.py .storage/core.entity_registry --apply

# Then restart Home Assistant
```

### Alternative: Manual cleanup via UI

1. Go to **Settings → Devices & Services → Entities**
2. Search for "active energy provider"
3. Delete all instances
4. Restart Home Assistant
5. The entity will be recreated correctly on next startup

---

## prepare_release.py

Automated script to prepare a new release.

### What it does

1. ✅ Updates version in `manifest.json`
2. ✅ Moves changelog entries from `[Unreleased]` to new version section
3. ✅ Adds current date to the new version section
4. ✅ Validates version format (semantic versioning)
5. ✅ Provides clear next steps

### Usage

```bash
python scripts/prepare_release.py <version>
```

### Example

```bash
# Prepare version 2.0.1
python scripts/prepare_release.py 2.0.1

# Output:
# 🚀 Preparing release v2.0.1
#
# ✓ Updated manifest.json: 2.0.0 → 2.0.1
# ✓ Updated CHANGELOG.md with version 2.0.1
#
# ✅ Release preparation complete!
#
# Next steps:
# 1. Review the changes:
#    git diff
#
# 2. Commit the changes:
#    git add custom_components/energy_price_tracker/manifest.json CHANGELOG.md
#    git commit -m "Release v2.0.1"
#
# 3. Push to GitHub (this will trigger automatic release):
#    git push origin main
```

### Requirements

- Python 3.6+
- Git repository
- Active `[Unreleased]` section in `CHANGELOG.md` with content

### Workflow

1. **During development**: Add changes to `[Unreleased]` section in CHANGELOG.md

   ```markdown
   ## [Unreleased]

   ### Added
   - New feature

   ### Fixed
   - Bug fix
   ```

2. **When ready to release**: Run the script

   ```bash
   python scripts/prepare_release.py 2.0.1
   ```

3. **Review and commit**: Check the changes and commit

   ```bash
   git diff
   git add custom_components/energy_price_tracker/manifest.json CHANGELOG.md
   git commit -m "Release v2.0.1"
   ```

4. **Push to GitHub**: Trigger automatic release

   ```bash
   git push origin main
   ```

5. **Automatic release**: The GitHub Action will:
   - Create tag `v2.0.1`
   - Extract changelog for this version
   - Create GitHub release with description
   - Make it available via HACS

## Troubleshooting

### "No [Unreleased] section found"

Make sure your CHANGELOG.md has an `[Unreleased]` section:

```markdown
## [Unreleased]

### Added
- Something new
```

### "[Unreleased] section is empty"

Add your changes to the `[Unreleased]` section before running the script:

```markdown
## [Unreleased]

### Fixed
- Fixed issue with...
```

### "Invalid version format"

Use semantic versioning format: `MAJOR.MINOR.PATCH`

- ✅ Valid: `2.0.1`, `1.2.3`, `3.0.0`
- ❌ Invalid: `2.0`, `v2.0.1`, `2.0.1-beta`

### GitHub Action not triggering

Make sure:
1. You pushed to the `main` branch
2. The `manifest.json` file changed
3. GitHub Actions are enabled in repository settings
4. You have proper permissions

---

## Automatic HACS Installation

The Docker development container **automatically installs HACS** on first startup if not already present.

### How it works

1. ✅ Container checks for HACS on startup
2. ✅ If missing, downloads latest HACS release from GitHub
3. ✅ Extracts HACS to `/config/custom_components/hacs`
4. ✅ Starts Home Assistant with HACS ready

### First time setup

```bash
# Just start the container - HACS installs automatically
docker-compose up -d

# Watch the startup logs to see HACS installation
docker logs -f portuguese_energy_price_tracker_dev
```

## install_hacs.sh

Manual HACS installation script (backup option if automatic installation fails).

### Usage

```bash
# Make sure the container is running
docker-compose up -d

# Run the installation script manually
./scripts/install_hacs.sh
```

### What it does

1. ✅ Checks if the Home Assistant container is running
2. ✅ Downloads the latest HACS release from GitHub
3. ✅ Extracts HACS to `dev_config/custom_components/hacs`
4. ✅ Restarts the Home Assistant container

### After installation

1. Wait for Home Assistant to restart (30-60 seconds)
2. Open http://localhost:8123
3. Navigate to **Configuration → Integrations**
4. Click **+ Add Integration** and search for **HACS**
5. Follow the setup wizard to authenticate with GitHub
6. Once HACS is configured, add custom repositories:
   - Go to **HACS → Integrations**
   - Click the **three dots menu → Custom repositories**
   - Add: `joaofernandes/portuguese_energy_price_tracker_ha_integration`
   - Category: **Integration**
   - Click **Add**

### Requirements

- Docker and docker-compose installed
- `curl` and `unzip` utilities available
- Container name: `portuguese_energy_price_tracker_dev`

### Troubleshooting

#### HACS doesn't appear after installation

```bash
# Check container logs
docker logs -f portuguese_energy_price_tracker_dev

# Restart the container manually
docker restart portuguese_energy_price_tracker_dev

# Verify HACS files exist
ls -la dev_config/custom_components/hacs/
```

#### Need to reinstall HACS

```bash
# Remove existing HACS installation
rm -rf dev_config/custom_components/hacs

# Run the install script again
./scripts/install_hacs.sh
```

### Development Workflow with HACS

Once HACS is installed, you can test the integration in a more realistic environment:

1. **Install via HACS**: Add the repository and install through HACS UI
2. **Development Testing**: The integration is already mounted directly via docker-compose
3. **Live Updates**: Changes to files are reflected immediately (may need HA restart)

**Note**: The direct mount in docker-compose.yml takes precedence over HACS installations, so you can develop and test simultaneously.
