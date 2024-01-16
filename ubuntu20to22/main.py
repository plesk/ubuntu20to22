#!/usr/bin/python3
# Copyright 2024. Plesk International GmbH. All rights reserved.

import sys

import pleskdistup.main
import pleskdistup.registry

import ubuntu20to22.upgrader

if __name__ == "__main__":
    pleskdistup.registry.register_upgrader(ubuntu20to22.upgrader.Ubuntu20to22Factory())
    sys.exit(pleskdistup.main.main())
