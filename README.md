# LD2410 for Home Assistant

Integration for HiLink **LD2410** Bluetooth Low Energy (BLE) mmWave radar sensors.
This integration allows Home Assistant to interface directly with LD2410 devices over Bluetooth.

## Recommended Setup

For best results, use an [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html) to connect your LD2410 to Home Assistant.

## Features
- Real-time motion and occupancy detection using the LD2410 radar.
- Distance and energy measurements for moving and stationary targets.
- Per-gate energy sensors for detailed zone analysis.

## Entities

🏠 **Occupancy** – overall presence state combining motion and static data. Use this sensor for automations; it clears only when both motion and static detection are absent.

🏃 **Motion** – turns on when movement is detected, making it ideal for instant motion-triggered actions.

🧍 **Static** – indicates a stationary presence so lights or HVAC can remain active even after motion stops.

🔌 **OUT pin** – reports the current state of the device’s hardware output pin for wiring diagnostics.

📏 **Detect distance** – distance at which a target is detected (cm); helps tune sensor placement.

🌞 **Photo sensor** – onboard light level (0‑255) for integrating ambient light into automations.

🎯 **Motion gate energy sensors (0‑8)** – energy level of each motion gate (0‑100%); inspect these to fine‑tune motion zones.

🧊 **Static gate energy sensors (0‑8)** – energy level of each static gate (0‑100%); useful for adjusting static presence sensitivity.

📡 **Moving distance** – distance to the closest moving target (cm).

📍 **Still distance** – distance to the closest stationary target (cm).

⚡ **Moving energy** – strongest gate energy of a moving target, indicating motion intensity.

🔋 **Still energy** – strongest gate energy of a stationary target.

📈 **Max motion gate** – index of the gate with highest motion energy; helpful when debugging sensitivity.

📊 **Max still gate** – index of the gate with highest static energy.

🏷️ **Firmware version** – version of the firmware running on the device; include when reporting issues.

📅 **Firmware build date** – build date of the installed firmware.

🖼️ **Frame type** – shows whether the sensor sends basic or engineering frames.

📶 **Bluetooth signal** – RSSI strength; move the device closer if the value is weak.

🔑 **New password** – text field for entering a new Bluetooth password. The password must be exactly six printable ASCII characters.

🔄 **Change password** – button that applies the password from *New password* and reboots the device. Fails if the password is not six ASCII characters.

🤖 **Auto sensitivities** – button to calibrate gate sensitivities automatically. Keep the room empty for 10 seconds during calibration.

💾 **Save sensitivities** – button to store current gate sensitivities in the config entry.

📥 **Load sensitivities** – button to restore previously saved gate sensitivities to the device.

🎚️ **Motion gate sensitivity sliders (MG0–MG8)** – number entities to set motion sensitivity for each gate.

🎛️ **Static gate sensitivity sliders (SG0–SG8)** – number entities to set static sensitivity for each gate.

⏱️ **Absence delay** – numeric value (0‑65535 seconds) before occupancy clears, preventing false absence.

🌗 **Light sensitivity** – threshold for the photo sensor (0‑255) that controls when the device considers it dark.

📐 **Distance resolution** – select entity to choose detection resolution (0.75 m or 0.20 m).

🕯️ **Light function** – select how the photo sensor affects the OUT pin (off, dimmer than, or brighter than).

📤 **OUT level** – select the default level of the OUT pin (low or high).

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

