# Release Scripts

Automation scripts for managing releases of the Portuguese Energy Price Tracker integration.

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
