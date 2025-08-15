# LD2410 for Home Assistant
This project is an attempt at making a more up-to-date integration for HiLink LD2410 BLE devices

This is still a work in progress, not functional yet

# Main features

# Installation instructions
1. The esiest way to install the integration is using HACS. Just click the
   button bellow and follow the instructions:
   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=megarushing&repository=ha-ld2410) 

   Alternatively, you can go to HACS and: 

- a) Click on the 3 dots in the top right corner.
- b) Select "Custom repositories"
- c) Add the URL to this repository: https://github.com/megarushing/ha-ld2410.
- d) Select integration.
- e) Click the "ADD" button.

2. Navigate to Settings -> Devices & Services, the HA-LD2410 device should be auto-detected.
 
   If its not detected, go to Settings -> Devices & Services in Home Assistant and click the "Add Integration" button. Search for "HA-LD2410" and install it. Your device should appear in the list

# Known Issues

### Enabling debug logging
* Add the following to your configuration.yaml file then restart HA:
  ```
  logger:
    default: warn
    logs:
      custom_components.ld2410: debug

# Legal Notice
This integration is not built, maintained, provided or associated with HiLink.
