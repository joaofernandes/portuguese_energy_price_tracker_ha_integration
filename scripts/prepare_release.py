#!/usr/bin/env python3
"""Prepare a new release.

This script:
1. Updates the version in manifest.json
2. Moves changelog entries from [Unreleased] to the new version section
3. Creates a git commit with the changes
4. Provides instructions for pushing

Usage:
    python scripts/prepare_release.py <version>

Example:
    python scripts/prepare_release.py 2.0.1
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def update_manifest(version: str, manifest_path: Path) -> bool:
    """Update version in manifest.json."""
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        old_version = manifest.get('version', 'unknown')
        manifest['version'] = version

        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            f.write('\n')

        print(f"✓ Updated manifest.json: {old_version} → {version}")
        return True
    except Exception as e:
        print(f"✗ Error updating manifest.json: {e}")
        return False


def update_changelog(version: str, changelog_path: Path) -> bool:
    """Move [Unreleased] section to new version section in CHANGELOG.md."""
    try:
        with open(changelog_path, 'r') as f:
            content = f.read()

        # Check if there's an Unreleased section with content
        unreleased_pattern = r'## \[Unreleased\]\s*\n(.*?)(?=\n## \[|$)'
        unreleased_match = re.search(unreleased_pattern, content, re.DOTALL)

        if not unreleased_match:
            print("✗ No [Unreleased] section found in CHANGELOG.md")
            return False

        unreleased_content = unreleased_match.group(1).strip()

        if not unreleased_content or unreleased_content == "":
            print("✗ [Unreleased] section is empty. Add changes to CHANGELOG.md first.")
            return False

        # Create new version section
        today = datetime.now().strftime("%Y-%m-%d")
        new_version_section = f"""## [{version}] - {today}

{unreleased_content}

"""

        # Replace [Unreleased] section with empty one and add new version section
        new_unreleased = "## [Unreleased]\n\n"

        # Find the position after [Unreleased] section
        content = re.sub(
            r'## \[Unreleased\]\s*\n.*?(?=\n## \[)',
            new_unreleased + new_version_section,
            content,
            count=1,
            flags=re.DOTALL
        )

        with open(changelog_path, 'w') as f:
            f.write(content)

        print(f"✓ Updated CHANGELOG.md with version {version}")
        return True
    except Exception as e:
        print(f"✗ Error updating CHANGELOG.md: {e}")
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/prepare_release.py <version>")
        print("Example: python scripts/prepare_release.py 2.0.1")
        sys.exit(1)

    version = sys.argv[1].lstrip('v')  # Remove 'v' prefix if present

    # Validate version format (semantic versioning)
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        print(f"✗ Invalid version format: {version}")
        print("  Version must follow semantic versioning: MAJOR.MINOR.PATCH (e.g., 2.0.1)")
        sys.exit(1)

    print(f"\n🚀 Preparing release v{version}\n")

    # Paths
    root = Path(__file__).parent.parent
    manifest_path = root / "custom_components/energy_price_tracker/manifest.json"
    changelog_path = root / "CHANGELOG.md"

    # Update files
    manifest_ok = update_manifest(version, manifest_path)
    changelog_ok = update_changelog(version, changelog_path)

    if not (manifest_ok and changelog_ok):
        print("\n✗ Release preparation failed")
        sys.exit(1)

    print("\n✅ Release preparation complete!\n")
    print("Next steps:")
    print(f"1. Review the changes:")
    print(f"   git diff")
    print(f"\n2. Commit the changes:")
    print(f"   git add custom_components/energy_price_tracker/manifest.json CHANGELOG.md")
    print(f"   git commit -m \"Release v{version}\"")
    print(f"\n3. Push to GitHub (this will trigger automatic release):")
    print(f"   git push origin main")
    print(f"\n4. The GitHub Action will automatically:")
    print(f"   - Create tag v{version}")
    print(f"   - Create GitHub release with changelog")
    print(f"   - Publish the release")


if __name__ == "__main__":
    main()
