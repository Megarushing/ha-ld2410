# LD2410 for Home Assistant

Integration for HiLink **LD2410** Bluetooth Low Energy (BLE) mmWave radar sensors.
This integration allows Home Assistant to interface directly with LD2410 devices over Bluetooth.

## Recommended Setup

For best results, use an [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html) to connect your LD2410 to Home Assistant.

## Features
- Real-time motion and occupancy detection using the LD2410 radar.
- Distance and energy measurements for moving and stationary targets.
- Per-gate energy sensors for detailed zone analysis.

## Sensors
### Binary sensors
- **Occupancy** – overall presence state combining motion and static data.
  - We recommend using this sensor for automations as it aggregates both motion and static presence.
- **Motion** – active when movement is detected.
- **Static** – indicates a stationary presence.

### Numeric sensors
- **Detect distance** – distance at which a target is detected (cm).
- **Photo Sensor** – photo sensor value (0-255).
- **Motion Gates** – Energy level of individual motion gates (0-100%)
- **Static Gates** – Energy level of individual static gates (0-100%)

### Diagnostic sensors

- **Moving distance** – distance to the closest moving target (cm).
- **Still distance** – distance to the closest stationary target (cm).
- **Moving energy** – strongest gate energy of moving target.
- **Still energy** – strongest gate energy of stationary targets.
- **Max motion gate** – index of latest motion gate.
- **Max still gate** – index of latest still gate.
- **Firmware version** – device firmware version.
- **Firmware build date** – build date of the installed firmware.
- **Frame type** – type of uplink frames (basic or engineering).
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

3. Before making your Pull Request, run the linters and tests:

   ```bash
   ruff check . --fix
   ruff format .
   pytest
   ```

## Known Issues
- The integration may not work with some LD2410 devices due to firmware differences. If you encounter issues, please open an issue on GitHub with details about your device and firmware version.

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

