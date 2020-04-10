#!/usr/bin/env python3

import logging

import discord
from discord.ext import commands

from base import fragment, settings

setup = fragment.Fragment()
_L = logging.getLogger(__name__)

class LogSettings(settings.SettingBase):
    async def impl_show(self, target: discord.Message) -> str:
        _L.info("impl_show: user=%s channel=%s", target.author, target.channel)
        return f"impl_show user={target.author} channel={target.channel}"

    async def impl_get(self, target: discord.Message) -> type(None):
        _L.info("impl_get: user=%s channel=%s", target.author, target.channel)
        return None

    async def impl_set(self, value: str, target: discord.Message, context: list):
        _L.info("impl_set: value=%s user=%s channel=%s [%s]",
                value, target.author, target.channel, context)

ls = settings.ServerChannelSetting(
        name="test",
        description="This is a test lmao",
        parse=int,
        deser=int)
