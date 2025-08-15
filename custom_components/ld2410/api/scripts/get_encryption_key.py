#!/usr/bin/env python3
import getpass
import sys

from ..ld2410 import LD2410Lock


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <device_mac> <username> [<password>]")
        sys.exit(1)

    password = getpass.getpass() if len(sys.argv) == 3 else sys.argv[3]

    try:
        result = LD2410Lock.retrieve_encryption_key(sys.argv[1], sys.argv[2], password)
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    print("Key ID: " + result["key_id"])
    print("Encryption key: " + result["encryption_key"])


if __name__ == "__main__":
    main()
