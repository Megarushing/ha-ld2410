# LD2410 for Home Assistant
Integration for HiLink LD2410 BLE mmWave radar devices.

## Features
- Real-time motion and occupancy detection using the LD2410 radar.
- Distance and energy measurements for moving and stationary targets.
- Per-gate energy sensors for detailed zone analysis.
- Diagnostic sensors reporting firmware information and Bluetooth signal strength.

## Sensors
### Binary sensors
- **Motion** – active when movement is detected.
- **Static** – indicates a stationary presence.
- **Occupancy** – overall presence state combining motion and static data.

### Diagnostic sensors
- **Moving distance** – distance to the closest moving target (cm).
- **Moving energy** – signal strength of moving targets.
- **Still distance** – distance to the closest stationary target (cm).
- **Still energy** – signal strength of stationary targets.
- **Detect distance** – distance at which a target is detected (cm).
- **Max moving gate** – gate index with strongest moving target.
- **Max still gate** – gate index with strongest stationary target.
- **Moving/Still gate energy 0‑8** – energy value for each radar gate.
- **Firmware version** – device firmware version.
- **Firmware build date** – build date of the installed firmware.
- **Frame type** – last reported frame type.
- **Bluetooth signal** – RSSI of the device.

## Installation instructions
1. The easiest way to install the integration is using HACS. Click the button below and follow the instructions:  
   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=megarushing&repository=ha-ld2410)

   Alternatively, you can go to HACS and:
   - a) Click on the 3 dots in the top right corner.
   - b) Select "Custom repositories".
   - c) Add the URL to this repository: https://github.com/megarushing/ha-ld2410.
   - d) Select integration.
   - e) Click the "ADD" button.

2. Navigate to **Settings → Devices & Services**; the HA-LD2410 device should be auto-detected.  
   If it's not detected, click the **Add Integration** button, search for "HA-LD2410", and install it. Your device should appear in the list.

## Contributing
Contributions are welcome! To set up the development environment:

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install the development requirements:

   ```bash
   pip install -r requirements.dev.txt
   ```

3. Before committing, run the linters and tests:

   ```bash
   ruff check . --fix
   ruff format .
   pytest
   ```

## Known Issues
### Enabling debug logging
Add the following to your `configuration.yaml` file then restart Home Assistant:

```yaml
logger:
  default: warn
  logs:
    custom_components.ld2410: debug
```

# Legal Notice
This integration is not built, maintained, provided or associated with HiLink.

