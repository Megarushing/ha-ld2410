# pyLD2410 [![codecov](https://codecov.io/gh/sblibs/pyLD2410/graph/badge.svg?token=TI027U5ISQ)](https://codecov.io/gh/sblibs/pyLD2410)

Library to control LD2410 IoT devices https://www.switch-bot.com/bot

## Obtaining encryption key for LD2410 Locks

Using the script `scripts/get_encryption_key.py` you can manually obtain locks encryption key.

Usage:

```shell
$ python3 get_encryption_key.py MAC USERNAME
Key ID: XX
Encryption key: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Where `MAC` is MAC address of the lock and `USERNAME` is your LD2410 account username, after that script will ask for your password.
If authentication succeeds then script should output your key id and encryption key.

## Examples:

#### WoLock (Lock-Pro)

Unlock:

```python
import asyncio
from ld2410.discovery import GetLD2410Devices
from ld2410.devices import lock
from ld2410.const import LD2410Model

BLE_MAC="XX:XX:XX:XX:XX:XX" # The MAC of your lock
KEY_ID="XX" # The key-ID of your encryption-key for your lock
ENC_KEY="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" # The encryption-key with key-ID "XX"
LOCK_MODEL=LD2410Model.LOCK_PRO # Your lock model (here we use the Lock-Pro)


async def main():
    wolock = await GetLD2410Devices().get_locks()
    await lock.LD2410Lock(
        wolock[BLE_MAC].device, KEY_ID, ENCRYPTION_KEY, model=LOCK_MODEL
    ).unlock()


asyncio.run(main())
```

Lock:

```python
import asyncio
from ld2410.discovery import GetLD2410Devices
from ld2410.devices import lock
from ld2410.const import LD2410Model

BLE_MAC="XX:XX:XX:XX:XX:XX" # The MAC of your lock
KEY_ID="XX" # The key-ID of your encryption-key for your lock
ENC_KEY="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" # The encryption-key with key-ID "XX"
LOCK_MODEL=LD2410Model.LOCK_PRO # Your lock model (here we use the Lock-Pro)


async def main():
    wolock = await GetLD2410Devices().get_locks()
    await lock.LD2410Lock(
        wolock[BLE_MAC].device, KEY_ID, ENCRYPTION_KEY, model=LOCK_MODEL
    ).lock()


asyncio.run(main())
```

#### WoCurtain (Curtain 3)

```python
import asyncio
from pprint import pprint
from ld2410 import GetLD2410Devices
from ld2410.devices import curtain


async def main():
    # get the BLE advertisement data of all ld2410 devices in the vicinity
    advertisement_data = await GetLD2410Devices().discover()

    for i in advertisement_data.values():
        pprint(i)
        print()  # print newline so that devices' data is separated visually

    # find your device's BLE address by inspecting the above printed debug logs, example below
    ble_address = "9915077C-C6FD-5FF6-27D3-45087898790B"
    # get the BLE device (via its address) and construct a curtain device
    ble_device = advertisement_data[ble_address].device
    curtain_device = curtain.LD2410Curtain(ble_device, reverse_mode=False)

    pprint(await curtain_device.get_device_data())
    pprint(await curtain_device.get_basic_info())
    await curtain_device.set_position(100)


if __name__ == "__main__":
    asyncio.run(main())
```
