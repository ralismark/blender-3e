#!/usr/bin/env python3

import logging

_L = logging.getLogger(__name__)

_BOT = None

def setup(bot):
    _L.info("resolver has been initialised")
    global _BOT
    _BOT = bot

async def get_user(uid):
    return _BOT.get_user(uid)

async def get_channel(cid):
    return _BOT.get_channel(cid)
