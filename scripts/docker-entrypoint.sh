#!/bin/bash
set -e

# Docker Entrypoint Script
# Automatically installs HACS on first container startup if not already present

HACS_DIR="/config/custom_components/hacs"
HACS_VERSION="latest"

echo "=== Home Assistant Container Starting ==="

# Check if HACS is already installed
if [ ! -d "$HACS_DIR" ]; then
    echo ""
    echo "HACS not found. Installing automatically..."

    # Download HACS
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"

    if [ "$HACS_VERSION" = "latest" ]; then
        DOWNLOAD_URL="https://github.com/hacs/integration/releases/latest/download/hacs.zip"
    else
        DOWNLOAD_URL="https://github.com/hacs/integration/releases/download/${HACS_VERSION}/hacs.zip"
    fi

    echo "Downloading HACS from GitHub..."
    curl -L -s -o hacs.zip "$DOWNLOAD_URL"

    if [ $? -eq 0 ]; then
        echo "Extracting HACS..."
        mkdir -p "/config/custom_components/hacs"
        unzip -o -q hacs.zip -d "/config/custom_components/hacs"
        rm -rf "$TEMP_DIR"
        echo "✓ HACS installed successfully"
        echo ""
        echo "After Home Assistant starts:"
        echo "1. Go to Configuration → Integrations"
        echo "2. Click '+ Add Integration' and search for 'HACS'"
        echo "3. Follow the setup wizard to authenticate with GitHub"
        echo ""
    else
        echo "⚠ Warning: Failed to download HACS. Continuing without it."
        echo "You can install manually later using: ./scripts/install_hacs.sh"
        rm -rf "$TEMP_DIR"
    fi
else
    echo "✓ HACS already installed"
fi

echo "Starting Home Assistant..."
echo ""

# Execute the original Home Assistant entrypoint
exec /init
