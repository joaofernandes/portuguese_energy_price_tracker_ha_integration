#!/usr/bin/env python3
"""
Clean up duplicate select entities from the entity registry.

Run this script when Home Assistant is STOPPED to avoid conflicts.

Usage:
    python3 scripts/cleanup_select_entity.py /path/to/config/.storage/core.entity_registry
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def cleanup_select_entities(registry_path: str, dry_run: bool = True):
    """Remove duplicate select entities from registry."""

    registry_file = Path(registry_path)
    if not registry_file.exists():
        print(f"❌ Registry file not found: {registry_path}")
        return False

    # Create backup
    backup_path = registry_file.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')

    print(f"📄 Reading registry: {registry_path}")
    with open(registry_file, 'r') as f:
        data = json.load(f)

    entities = data.get("data", {}).get("entities", [])

    # Find all select entities for our integration
    select_entities = []
    select_indices = []

    for idx, entity in enumerate(entities):
        if (entity.get("platform") == "portuguese_energy_price_tracker" and
            entity.get("domain") == "select" and
            "active_provider" in entity.get("unique_id", "")):
            select_entities.append(entity)
            select_indices.append(idx)

    print(f"\n📊 Found {len(select_entities)} select entity(ies):")
    for entity in select_entities:
        print(f"  - {entity.get('entity_id')}")
        print(f"    Unique ID: {entity.get('unique_id')}")
        print(f"    Disabled: {entity.get('disabled_by')}")
        print()

    if len(select_entities) == 0:
        print("✓ No select entities found (nothing to clean up)")
        return True

    if len(select_entities) == 1:
        print("✓ Only one select entity exists (this is correct)")
        return True

    # Multiple entities found - remove all but the first
    print(f"⚠️  Found {len(select_entities)} duplicate select entities!")
    print(f"   Will keep the first one and remove {len(select_entities) - 1} duplicate(s)")

    if dry_run:
        print("\n🔍 DRY RUN - No changes will be made")
        print("   Run with --apply to actually clean up the registry")
        return True

    # Create backup before modifying
    print(f"\n💾 Creating backup: {backup_path}")
    with open(backup_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Remove duplicates (keep first, remove rest)
    indices_to_remove = sorted(select_indices[1:], reverse=True)

    print(f"\n🗑️  Removing {len(indices_to_remove)} duplicate(s)...")
    for idx in indices_to_remove:
        removed = entities.pop(idx)
        print(f"   Removed: {removed.get('entity_id')}")

    # Save modified registry
    print(f"\n💾 Saving cleaned registry...")
    with open(registry_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Cleanup complete!")
    print(f"   Backup saved to: {backup_path}")
    print(f"   Removed {len(indices_to_remove)} duplicate entity(ies)")
    print(f"   Kept: {select_entities[0].get('entity_id')}")
    print(f"\n⚠️  Restart Home Assistant to apply changes")

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 cleanup_select_entity.py <path_to_entity_registry> [--apply]")
        print("\nExample:")
        print("  python3 cleanup_select_entity.py /config/.storage/core.entity_registry")
        print("  python3 cleanup_select_entity.py /config/.storage/core.entity_registry --apply")
        sys.exit(1)

    registry_path = sys.argv[1]
    apply_changes = "--apply" in sys.argv

    if not apply_changes:
        print("=" * 60)
        print("DRY RUN MODE - No changes will be made")
        print("Add --apply flag to actually clean up the registry")
        print("=" * 60)
        print()

    success = cleanup_select_entities(registry_path, dry_run=not apply_changes)
    sys.exit(0 if success else 1)
