#!/usr/bin/env python3

import logging

import discord
from discord.ext import commands

from . import fragment
from .settings import _SETTINGS, ArgError

frag = fragment.Fragment()
_L = logging.getLogger(__name__)

@frag.group(pass_context=True)
@commands.check(fragment.is_admin_or_owner)
async def settings(ctx: commands.Context):
    """
    List available settings and their value in this current channel.

    setting/arg=1/arg=2
    """
    if ctx.invoked_subcommand is None:
        _L.debug("command settings: %d items", len(_SETTINGS))
        embed = discord.Embed(title="Available settings", description=f"{len(_SETTINGS)} available")

        for key, value in _SETTINGS.items():
            embed.add_field(name=key, value=(value.description or "no description"), inline=False)

        await ctx.send(embed=embed)

@settings.command("here")
@commands.check(fragment.is_admin_or_owner)
async def setting_here(ctx, name: str):
    """
    Show the value of setting `name` for all relevant contexts.
    """
    if name not in _SETTINGS:
        raise commands.BadArgument(message=f"`{name}` is not a valid name")
    setting = _SETTINGS[name]
    embed = discord.Embed(title=name, description=await setting.show(ctx))
    await ctx.send(embed=embed)

@settings.command("set")
@commands.check(fragment.is_admin_or_owner)
async def settings_set(ctx, option: str, *, value=None):
    """
    Set a configuration option.
    """
    bits = option.split("/")
    name = bits[0]
    args = [s.split("=", 1) for s in bits[1:]]
    args = [s[0] if len(s) == 1 else tuple(s) for s in args]

    if name not in _SETTINGS:
        raise commands.BadArgument(message=f"`{name}` is not a valid name")
    setting = _SETTINGS[name]

    try:
        await setting.impl_set(value, ctx.message, args)
    except ArgError as e:
        await ctx.send("\u200b❎ " + str(e))
    else:
        await ctx.message.add_reaction("✅")

def setup(bot):
    from . import resolver

    frag.setup(bot)
    resolver.setup(bot)
