#!/usr/bin/env python3

import abc
import logging
import typing

import discord
from discord.ext import commands

from . import resolver, sql

_L = logging.getLogger(__name__)

_SETTINGS = dict()

class ArgError(Exception):
    pass

TargetType = typing.Union[commands.Context, discord.Message]
ContextType = typing.List[typing.Union[str, typing.Tuple[str, str]]]

class SettingBase(abc.ABC):
    """
    A base class for settings
    """

    def __init__(self, *,
                 name: str,
                 description: typing.Optional[str] = None,
                 default=None,
                 **kwargs):
        super().__init__(**kwargs)
        _L.info("registering scoped setting: name=%s -> %r", name, self)

        self.name = name
        self.description = description or ""
        self.default = default

        _SETTINGS[name] = self

    @abc.abstractmethod
    async def impl_show(self, target: discord.Message) -> str:
        """
        The implementation should return a string identifying all options set
        for this target. This is intended for user/admin use.
        """

    async def show(
            self,
            target: TargetType
        ) -> str:
        """
        Retrieve the value for a given target context
        """
        if isinstance(target, commands.Context):
            target = target.message
        shown = await self.impl_show(target)
        return shown if shown is not None else str(self.default)

    @abc.abstractmethod
    async def impl_get(self, target: discord.Message) -> object:
        """
        The implementation should return the setting corresponding to this
        target context
        """

    async def get(
            self,
            target: TargetType
        ) -> object:
        """
        Retrieve the value for a given target context
        """
        if isinstance(target, commands.Context):
            target = target.message
        value = await self.impl_get(target)
        return value if value is not None else self.default

    @abc.abstractmethod
    async def impl_set(
            self,
            value: str,
            target: discord.Message,
            context: ContextType
        ) -> None:
        """
        The implementation should store the value specified for the
        corresponding target. The context contains any extra information
        specified by the user/admin.

        Context is a list of args or key-value pairs. If an item is a string,
        it is a single arg, otherwise it is pair of (key=value).
        """

    async def check(self, predicate: typing.Callable[[object], bool] = bool):
        """
        Decorator. Only allow the command if a predicate is satisfied.
        """
        async def checked(ctx):
            return predicate(await self.get(ctx))
        return commands.check(checked)

async def apply_user(target: TargetType, context: ContextType) -> discord.User:
    """
    Get user from either target or context
    """
    for entry in context:
        if isinstance(entry, tuple) and entry[0] == "user":
            return await resolver.fetch_user_nonnull(int(entry[1]))
    return target.author

def channel_or_server(
        target: TargetType,
        context: ContextType
    ) -> typing.Tuple[int, int]:
    """
    Returns a (channel, server) pair
    """
    for entry in context:
        if entry == "channel":
            return (target.channel.id, target.channel.guild.id)
        if isinstance(entry, tuple) and entry[0] == "channel":
            return (int(entry[1]), target.channel.guild.id)
        if entry == "server":
            return (-1, target.channel.guild.id)
        if isinstance(entry, tuple) and entry[0] == "server":
            raise ArgError("Cannot specify server")

    raise ArgError("Must use either option/channel or option/channel=<channel id> or option/server")

def true_false(string: str) -> bool:
    """
    Parse a string as a boolean.
    """
    string = string.lower().strip()
    if string in ("y", "yes", "t", "true", "1"):
        return True
    if string in ("n", "no", "f", "false", "0"):
        return False
    raise ValueError("Neither true nor false")

sql.require_table("settings", """
        server INTEGER NOT NULL,
        channel INTEGER NOT NULL,
        user INTEGER NOT NULL,
        option TEXT NOT NULL,
        value BLOB,
        PRIMARY KEY(server, channel, user, option)
        """)

def get_stored(
        option: str,
        default: object = None,
        *,
        server: int = -1,
        channel: int = -1,
        user: int = -1
    ) -> object:
    """
    Get a value from the SQL table
    """
    results = sql.query(f"""
        SELECT value FROM settings
        WHERE server=? AND channel=? AND user=? AND option=?
        """, server, channel, user, option)
    return results[0][0] if results else default

def delete_stored(
        option: str,
        *,
        server: int = -1,
        channel: int = -1,
        user: int = -1
    ) -> None:
    """
    Delete a value in the settings table
    """
    return sql.query(f"""
        DELETE FROM settings
        WHERE server=? AND channel=? AND user=? AND option=?
        """, server, channel, user, option)

def set_stored(
        option: str,
        value: object,
        *,
        server: int = -1,
        channel: int = -1,
        user: int = -1
    ) -> None:
    """
    Set a value in the settings table
    """
    if value is None:
        delete_stored(option, server=server, channel=channel, user=user)
        return

    sql.query(f"""
        INSERT OR REPLACE INTO settings(
            server, channel, user, option, value
        ) VALUES (?, ?, ?, ?, ?)
        """, server, channel, user, option, value)

class ServerSetting(SettingBase):
    """
    A server-wide settings.
    """

    def __init__(
            self,
            *,
            parse: typing.Callable[[str], object] = lambda x: x,
            deser: typing.Callable[[object], object] = lambda x: x,
            **kwargs
        ):
        super().__init__(**kwargs)

        self.parse = parse
        self.deser = deser

    async def impl_show(self, target: discord.Message) -> str:
        value = get_stored(self.name, server=target.channel.guild.id)
        return str(self.deser(value)) if value is not None else None

    async def impl_get(self, target: discord.Message) -> object:
        value = get_stored(self.name, server=target.channel.guild.id)
        return self.deser(value) if value is not None else None

    async def impl_set(
            self,
            value: str,
            target: discord.Message,
            context: ContextType
        ) -> None:
        parsed = self.parse(value)
        set_stored(self.name, parsed, server=target.channel.guild.id)

class ServerChannelSetting(SettingBase):
    """
    A channel-specific settings that allows a server-wide fallback.
    """

    def __init__(
            self,
            *,
            parse: typing.Callable[[str], object] = lambda x: x,
            deser: typing.Callable[[object], object] = lambda x: x,
            **kwargs
        ):
        super().__init__(**kwargs)

        self.parse = parse
        self.deser = deser

    async def impl_show(self, target: discord.Message) -> str:
        shown = ""
        serverwide = False
        results = sql.query("""
            SELECT channel, value FROM settings
            WHERE server=? AND option=?
            ORDER BY channel ASC
            """, target.channel.guild.id, self.name)

        for row in results:
            channame = "default"
            if row[0] > 0:
                chan = resolver.fetch_channel_maybe(row[0])
                if chan is None or chan.guild.id != target.guild.id:
                    channame = f"<invalid #{row[0]}>"
                else:
                    channame = chan.name
            else:
                serverwide = True

            shown += channame + ": " + str(self.deser(row[1])) + "\n"

        if not serverwide:
            shown += "default: " + str(self.default) + "\n"

        return shown

    async def impl_get(self, target: discord.Message) -> object:
        chan = target.channel
        value = get_stored(self.name, server=chan.guild.id, channel=chan.id)
        if value is None:
            value = get_stored(self.name, server=chan.guild.id)
        return self.deser(value) if value is not None else None

    async def impl_set(
            self,
            value: str,
            target: discord.Message,
            context: ContextType
        ) -> None:
        channel, server = channel_or_server(target, context)
        parsed = self.parse(value)
        set_stored(self.name, parsed, server=server, channel=channel)
