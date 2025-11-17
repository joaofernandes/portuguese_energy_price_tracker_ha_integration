# Release Process

Quick reference for creating new releases of the Portuguese Energy Price Tracker integration.

## Quick Start

```bash
# 1. Make your changes and update CHANGELOG.md [Unreleased] section
# 2. Run release script
python scripts/prepare_release.py 2.0.1

# 3. Review, commit, and push
git diff
git add custom_components/energy_price_tracker/manifest.json CHANGELOG.md
git commit -m "Release v2.0.1"
git push origin main

# 4. GitHub Actions automatically creates the release! 🎉
```

## Detailed Steps

### 1. During Development

Add all changes to the `[Unreleased]` section in `CHANGELOG.md`:

```markdown
## [Unreleased]

### Added
- New sensor for peak hours
- Support for new provider

### Fixed
- Fixed timezone issue
- Corrected VAT calculation

### Changed
- Improved error messages
- Updated data refresh interval
```

### 2. Prepare Release

Run the automated release script:

```bash
python scripts/prepare_release.py 2.0.1
```

The script will:
- ✅ Update `manifest.json` with new version
- ✅ Move `[Unreleased]` changes to new version section
- ✅ Add today's date to the version header
- ✅ Clear the `[Unreleased]` section

### 3. Review Changes

```bash
git diff
```

Check that:
- `manifest.json` version is correct
- `CHANGELOG.md` has new version section with proper date
- All unreleased changes moved to new version
- New `[Unreleased]` section is empty

### 4. Commit and Push

```bash
git add custom_components/energy_price_tracker/manifest.json CHANGELOG.md
git commit -m "Release v2.0.1"
git push origin main
```

### 5. Automated Release

The GitHub Action (`.github/workflows/release.yml`) will automatically:

1. **Detect** version change in `manifest.json`
2. **Create** git tag (e.g., `v2.0.1`)
3. **Extract** changelog for this version
4. **Create** GitHub release with:
   - Tag: `v2.0.1`
   - Title: `v2.0.1`
   - Description: Changelog + installation instructions
5. **Publish** release

**Timeline:** Usually completes within 1-2 minutes after push.

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (2.X.0): New features (backwards compatible)
- **PATCH** (2.0.X): Bug fixes (backwards compatible)

### Examples

```bash
# Patch release (bug fixes)
python scripts/prepare_release.py 2.0.1

# Minor release (new features)
python scripts/prepare_release.py 2.1.0

# Major release (breaking changes)
python scripts/prepare_release.py 3.0.0
```

## Changelog Format

Use these standard sections in `[Unreleased]`:

- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Features that will be removed
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security fixes

### Example

```markdown
## [Unreleased]

### Added
- Support for G9 Smart Dynamic provider
- New `all_prices` sensor with complete price array

### Fixed
- Fixed timezone handling for DST transitions
- Corrected VAT calculation for bi-tariff rates

### Changed
- Improved error messages for API failures
- Updated documentation with new examples
```

## Troubleshooting

### Script fails: "No [Unreleased] section found"

**Solution:** Add the section to CHANGELOG.md:

```markdown
## [Unreleased]

### Fixed
- Your changes here
```

### Script fails: "[Unreleased] section is empty"

**Solution:** Add at least one change:

```markdown
## [Unreleased]

### Changed
- Updated documentation
```

### Release not created on GitHub

**Check:**
1. GitHub Actions are enabled (Settings → Actions)
2. Push went to `main` branch
3. `manifest.json` actually changed
4. Check Actions tab for workflow status

### Need to fix a release

If you need to fix an already-created release:

```bash
# Delete the tag locally and remotely
git tag -d v2.0.1
git push origin :refs/tags/v2.0.1

# Delete the GitHub release manually (via GitHub UI)

# Fix the issues, then run release script again
python scripts/prepare_release.py 2.0.1
```

## Manual Release (Fallback)

If automation fails, create release manually:

```bash
# 1. Update files manually
# Edit custom_components/energy_price_tracker/manifest.json
# Edit CHANGELOG.md

# 2. Commit
git add custom_components/energy_price_tracker/manifest.json CHANGELOG.md
git commit -m "Release v2.0.1"

# 3. Create and push tag
git tag -a v2.0.1 -m "Release v2.0.1"
git push origin main
git push origin v2.0.1

# 4. Create release manually on GitHub
# Go to: https://github.com/joaofernandes/portuguese_energy_price_tracker_ha_integration/releases/new
# - Choose tag: v2.0.1
# - Title: v2.0.1
# - Description: Copy from CHANGELOG.md
# - Click "Publish release"
```

## HACS Updates

Once a release is created:

1. **HACS automatically detects** new releases
2. **Users see update available** in HACS
3. **Users can update** with one click

No additional steps needed!

## Resources

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Releases Documentation](https://docs.github.com/en/repositories/releasing-projects-on-github)
