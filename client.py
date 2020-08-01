#!/usr/bin/env python3

"""
Main bot client
"""

import datetime
import logging
import logging.config
import random
import sys
import traceback

import discord
from discord.ext import commands

from base import config

if __name__ != "__main__":
    raise RuntimeError("client being imported")

_L = logging.getLogger(__name__)

bot = commands.Bot(command_prefix=commands.when_mentioned)

@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    """
    Handle errors from commands
    """
    # Un-nest
    error = getattr(error, 'original', error)

    async def report_to_owner():
        _L.error("exception from command %s", ctx.invoked_with, exc_info=error)
        exc_traceback = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        await (await bot.application_info()).owner.send(
            f"\u200bISE! {datetime.datetime.now()}\n```\n{exc_traceback} ```", delete_after=60)

    # Handle exceptions from user behaviour
    if isinstance(error, commands.CommandOnCooldown):
        hrs = error.retry_after // (60*60)
        mins = error.retry_after // 60 % 60
        secs = error.retry_after % 60
        timestr = "{}{}{:.3}s".format(
            f"{int(hrs)}hrs " if hrs else "",
            f"{int(mins)}mins " if mins else "",
            secs)
        await ctx.send(f"\u200b:timer: You need to wait **{timestr}**"
                       " before you can run this command again",
                       delete_after=min(30, error.retry_after))

    elif isinstance(error, commands.DisabledCommand):
        await ctx.send(f"\u200b`{ctx.command}` has been disabled", delete_after=10)

    # user_errs = (commands.UserInputError, commands.CommandNotFound, commands.CheckFailure)
    elif isinstance(error, commands.CommandError):
        await ctx.send(f"```fix\n{error}```", delete_after=10)

    elif isinstance(error, discord.Forbidden):
        try:
            await ctx.send(f"\u200b:no_entry: This bot is missing permissions (code {error.code})")
        # pylint: disable=bare-except
        except:
            await report_to_owner()

    else:
        await ctx.send("```diff\n-- 500 Internal Server Error --```", delete_after=60)
        await report_to_owner()


@bot.event
async def on_error(event, *args, **kwargs):
    """
    Handle error from event handler
    """
    _, exc, _ = sys.exc_info()
    _L.error("exception from handling event `%s`, args=%s kwargs=%s",
             event, args, kwargs, exc_info=sys.exc_info())
    if isinstance(exc, discord.errors.Forbidden):
        return # don't raise permission errors

    exc_traceback = "".join(traceback.format_exception(*sys.exc_info()))
    await (await bot.application_info()).owner.send(
        f"\u200bISE! {datetime.datetime.now()}\n```\n{exc_traceback}", delete_after=60)

bot.remove_command("help")
@bot.command("help")
async def help_message(ctx: commands.Context, *, command=None):
    """
    Show help about all commands.
    """

    if command is None:
        embed = discord.Embed(
            title="Help",
            description=(bot.description or "")
            )
        embed.set_footer(
            text="Run `help <command>` for information on a specific command."
            )

        for com in bot.commands:
            try:
                if com.hidden or not com.enabled or not await com.can_run(ctx):
                    continue
            except commands.CommandError:
                continue

            embed.add_field(
                name=com.name,
                value=com.short_doc or "_No description available_",
                inline=False
                )
    else:
        com = bot.get_command(command)
        if com is None:
            raise commands.CommandError("Command not found")

        embed = discord.Embed(
            title=f"Help on {com.qualified_name}"
            )
        embed.add_field(
            name="Usage",
            value=f"`{com.qualified_name} {com.signature}`",
            inline=False
            )
        embed.add_field(
            name="Description",
            value=com.help,
            inline=False
            )
        if com.aliases:
            embed.add_field(
                name="Aliases",
                value="\n".join(com.aliases),
                inline=False
                )

    await ctx.send(embed=embed)

#
# set up logger
#

logging.config.dictConfig(config.get('logging'))

#
# load fragments
#

for mod in config.get("discord.modules"):
    bot.load_extension(mod)

#
# start bot
#

random.seed()
bot.run(config.get("secrets.discord-token"))
