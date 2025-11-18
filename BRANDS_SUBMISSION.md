# Submitting to Home Assistant Brands Repository

To get the integration icon to load in Home Assistant (not just HACS), you need to submit to the brands repository.

**Domain**: `portuguese_energy_price_tracker`

## Steps to Submit

1. **Fork the repository**:
   - Go to: https://github.com/home-assistant/brands
   - Click "Fork" to create your own copy

2. **Add your icon files**:
   ```bash
   # Clone your fork
   git clone https://github.com/YOUR_USERNAME/brands.git
   cd brands

   # Create directory for custom integration
   mkdir -p custom_integrations/portuguese_energy_price_tracker

   # Copy your icons (use the ones from your integration)
   cp /path/to/icon.png custom_integrations/portuguese_energy_price_tracker/icon.png
   cp /path/to/icon@2x.png custom_integrations/portuguese_energy_price_tracker/icon@2x.png
   cp /path/to/icon.png custom_integrations/portuguese_energy_price_tracker/logo.png
   cp /path/to/icon@2x.png custom_integrations/portuguese_energy_price_tracker/logo@2x.png
   ```

3. **Icon requirements**:
   - PNG format
   - Transparent background
   - `icon.png`: 256x256 pixels
   - `icon@2x.png`: 512x512 pixels
   - `logo.png`: 256x256 pixels (same as icon)
   - `logo@2x.png`: 512x512 pixels (same as icon@2x)

4. **Commit and push**:
   ```bash
   git add custom_integrations/energy_price_tracker/
   git commit -m "Add icons for energy_price_tracker custom integration"
   git push origin main
   ```

5. **Create Pull Request**:
   - Go to your fork on GitHub
   - Click "Contribute" → "Open pull request"
   - Title: "Add icons for energy_price_tracker"
   - Description: "Adding brand icons for Portuguese Energy Price Tracker custom integration"

6. **Wait for approval**:
   - Brands team will review
   - May request changes (format, size, quality)
   - Once merged, icons will be available at `https://brands.home-assistant.io/energy_price_tracker/`

## Alternative: Use Current Setup

Your current setup works for HACS:
- Icons in repository root: ✅ HACS displays correctly
- Icons in integration dir: ✅ HA can use if cached properly
- Browser cache issues: Clear cache/hard refresh

## Why This Happens

- **Official integrations**: Load from `brands.home-assistant.io` CDN
- **Custom integrations**: Should load from local `custom_components/` but HA's frontend tries CDN first
- **HACS**: Bypasses this by using repository root icons directly

For now, your icons work in HACS. For full HA integration card icons, submit to brands repo.
