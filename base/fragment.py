#!/usr/bin/env python3

import asyncio
import logging

from discord.ext import commands

_L = logging.getLogger(__name__)

async def is_admin_or_owner(ctx: commands.Context):
    """
    Check if the person running the command is an admin or the owner
    """
    if await ctx.bot.is_owner(ctx.author):
        return True
    perms = ctx.channel.permissions_for(ctx.author)
    return perms.administrator

class Fragment(commands.GroupMixin):
    """
    An interface to the actual bot
    """

    def __init__(self):
        commands.GroupMixin.__init__(self)
        self.events = []
        self.tasks = []
        self.bot = None

    def __call__(self, bot: commands.Bot):
        self.setup(bot)

    def setup(self, bot: commands.Bot):
        """
        Attach a fragment to a bot
        """
        _L.debug("Fragment.setup: bot=%s; %d commands, %d events",
                 bot, len(self.commands), len(self.events))

        self.bot = bot

        for com in self.commands:
            bot.add_command(com)

        for func, name in self.events:
            if name == "task":
                bot.loop.create_task(func())
            else:
                bot.add_listener(func, name)

    def listen(self, name=None):
        """
        Decorator - set the event handler. If name is "task", then attach as
        task.
        """
        def decorate(func):
            if name == "task" and not asyncio.iscoroutinefunction(func):
                orig = func
                async def afunc(bot):
                    orig(bot)
                func = afunc
            self.events.append((func, name))
        return decorate

    def task(self, func):
        """
        Specialisation of listen to create an async task
        """
        return self.listen("task")(func)
