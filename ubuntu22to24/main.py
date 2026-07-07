#!/usr/bin/python3
# Copyright 2024. Plesk International GmbH. All rights reserved.

import sys

import pleskdistup.main
import pleskdistup.registry

import ubuntu22to24.upgrader

if __name__ == "__main__":
    pleskdistup.registry.register_upgrader(ubuntu22to24.upgrader.Ubuntu22to24Factory())
    sys.exit(pleskdistup.main.main())
