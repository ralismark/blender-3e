#!/usr/bin/env python3

"""
Handle global configuration relevant to the base layer only
"""

import logging
import yaml

_L = logging.getLogger(__name__)

with open("config.yaml") as config_file:
    CONFIG = yaml.load(config_file, Loader=yaml.FullLoader)

with open("secrets.yaml") as secrets_file:
    CONFIG["secrets"] = yaml.load(secrets_file, Loader=yaml.FullLoader)

def get(key: str):
    """
    Get a config key
    """
    head = CONFIG
    for seg in key.split("."):
        head = head[seg]
    return head
