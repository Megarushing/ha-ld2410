# LD2410 for Home Assistant

Integration for HiLink **LD2410** Bluetooth Low Energy (BLE) mmWave radar sensors.
This integration allows Home Assistant to interface directly with LD2410 devices over Bluetooth.

## Features
- Real-time motion and occupancy detection using the LD2410 radar.
- Distance and energy measurements for moving and stationary targets.
- Per-gate energy sensors for detailed zone analysis.

## Recommended Setup

For best results, 
- Use an [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html) to connect your LD2410 to Home Assistant.
- Use firmware version 2.44.24073110 or higher on your LD2410 device. 
  - If your device has an older firmware, you can update it using the HLKRadarTool app on [Android](https://play.google.com/store/apps/details?id=com.hlk.hlkradartool&hl=en) or [iOS](https://apps.apple.com/us/app/hlkradartool/id1638651152).
- If you ever run into issues, you can reset to factory defaults by connecting and disconnecting power from the device 5 times.

## Entities

🏠 **Occupancy** – overall presence state combining motion and static data. Use this sensor for automations; it clears only when both motion and static detection are absent.

🏃 **Motion** – turns on when movement is detected, making it ideal for instant motion-triggered automations.

🧍 **Static** – indicates a stationary presence so lights or HVAC can remain active even after motion stops.

🔌 **OUT pin** – reports the current state of the device’s hardware output pin for wiring diagnostics.

📏 **Detect distance** – distance at which a target is detected (cm); helps tune sensor placement.

🌞 **Photo sensor** – onboard light level (0‑255) for integrating ambient light into automations.

🎯 **Motion gate energy sensors (0‑8)** – energy level of each motion gate (0‑100%); inspect these to fine‑tune motion zones.

🧊 **Static gate energy sensors (0‑8)** – energy level of each static gate (0‑100%); with them its possible to detect presence in individual spots of a room.

📡 **Moving distance** – distance to the closest moving target (cm).

📍 **Still distance** – distance to the closest stationary target (cm).

⚡ **Moving energy** – strongest gate energy of a moving target, indicating motion intensity.

🔋 **Still energy** – strongest gate energy of a stationary target.

📈 **Max motion gate** – index of latest motion gate currently activated, default is 8, meaning 9 total gates.

📊 **Max still gate** – index of latest still gate currently activated, default is 8, meaning 9 total gates.

🏷️ **Firmware version** – version of the firmware running on the device; include when reporting issues.

📅 **Firmware build date** – build date of the installed firmware.

🖼️ **Frame type** – shows whether the sensor is sending basic or engineering frames. The integration automatically upgrades to engineering when possible

📶 **Bluetooth signal** – RSSI strength; move the device closer if the value is weak.

🔑 **New password** – text field for entering a new Bluetooth password. The password must be exactly six printable ASCII characters.

🔄 **Change password** – button that applies the password from *New password* and reboots the device.

🤖 **Auto sensitivities** – button to calibrate gate sensitivities automatically. Leave the room before clicking it, keep it empty for 10 seconds during calibration.

💾 **Save sensitivities** – button to store current gate sensitivities in the config entry. Useful for playing around with calibration without missing the sweet spot.

📥 **Load sensitivities** – button to restore previously saved gate sensitivities to the device.

♻️ **Reboot device** – button to reboot the device.

🎚️ **Motion gate sensitivity sliders (MG0–MG8)** – sets the motion sensitivity for each gate, the lower the slider the easier it gets activated.

🎛️ **Static gate sensitivity sliders (SG0–SG8)** – number entities to set static sensitivity for each gate, the lower the slider the easier it gets activated.

⏱️ **Absence delay** – number of seconds to wait before occupancy clears, preventing false absence.

🕯️ **Light function** – when enabled the OUT pin will only be activated if the photo sensor reading is (dimmer than/brighter than) *Light sensitivity* .

🌗 **Light sensitivity** – threshold for the photo sensor (0‑255) when using the light function.

📐 **Distance resolution** – select detection resolution (0.75m or 0.20m); the higher the resolution, more distant targets are detected.

📤 **OUT level** – select the default level of the OUT pin (usually low becoming high when activated / usually high becoming low when activated).

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

## Note on recorder
Some sensors update several times per second. They are **disabled by default**. If you enable them, exclude them from the recorder, or they will fill your database. Real example: six devices with `Last frame` enabled wrote 3.7 million rows in 7 days, 38% of the whole database.

Add this to your `configuration.yaml`, then restart Home Assistant. Replace `hlk_ld2410_e5f6` with the entity id prefix of your device (lowercase; it changes if you rename the device):

```yaml
recorder:
  exclude:
    entity_globs:
      # Safe for every device: these names are unique to this integration
      - sensor.*_gate_?_energy      # 18 per-gate energy sensors
      - sensor.*_last_frame         # updates on every received frame
      # Generic names: scope them to your device so other integrations are not affected
      - sensor.hlk_ld2410_e5f6_*_distance
      - sensor.hlk_ld2410_e5f6_*_energy
      - sensor.hlk_ld2410_e5f6_photo_sensor
      - sensor.hlk_ld2410_e5f6_frame_type
```

To stop recording a whole device instead, use one glob per entity domain:

```yaml
recorder:
  exclude:
    entity_globs:
      - "*.hlk_ld2410_e5f6_*"
```

Notes:
- `exclude: domains: [ld2410]` does **not** work. Recorder domains are entity domains such as `sensor` or `binary_sensor`, not integrations.
- Excluding an entity does not delete rows it already wrote. To remove them, call `recorder.purge` with `apply_filter: true`.
- Recorder changes need a Home Assistant restart.

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
Before registering issues, please enable debug logging to help diagnose problems and paste your logs in it.
Add the following to your `configuration.yaml` file then restart Home Assistant:

```yaml
logger:
  default: warn
  logs:
    custom_components.ld2410: debug
```

# Legal Notice
This integration is not built, maintained, provided or associated with HiLink.

