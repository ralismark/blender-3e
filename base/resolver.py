#!/usr/bin/env python3

import typing
import logging

import discord

_L = logging.getLogger(__name__)

_BOT = None

def setup(bot):
    _L.info("resolver has been initialised")
    global _BOT
    _BOT = bot

async def fetch_user_nonnull(uid: int) -> discord.User:
    """
    Tries to fetch a user, throwing an exception if the user is not found.

    Parameters:
    - uid - The user's ID to fetch from

    Raises:
    - discord.NotFound - A user with this ID does not exist.
    - discord.HTTPException - Fetching the user failed. User may or may not
      exist.

    Returns:
    - discord.User - The requested user
    """
    cached = _BOT.get_user(uid)
    if cached is not None:
        return cached
    try:
        return await _BOT.fetch_user(uid)
    except discord.HTTPException as err:
        _L.warning("fetch_user: HTTPException %s: %s", err.status, err.text)
        raise

async def fetch_user_maybe(uid: int) -> typing.Optional[discord.User]:
    """
    Fetch a user from a given user ID, or None if the user doesn't exist.

    Parameters:
    - uid - The user's ID to fetch from

    Raises:
    - discord.HTTPException - Fetching the user failed. User may or may not
      exist.

    Returns:
    - The requested user, or None if not found.
    """
    try:
        return await fetch_user_nonnull(uid)
    except discord.NotFound:
        return None

async def fetch_channel_nonnull(
        cid: int
        ) -> typing.Union[discord.abc.GuildChannel, discord.abc.PrivateChannel]:
    """
    Fetch a channel (guild or private) or category from a given ID, throwing if
    not found.

    Parameters:
    - cid - The channel/category ID to fetch

    Raises:
    - discord.HTTPException - Fetching the channel failed.
    - discord.InvalidData - An unknown channel type was returned from Discord
    - discord.NotFound - The channel does not exist
    - discord.Forbidden - Insufficient permissions to get the channel

    Return:
    - The requested channel/category
    """
    cached = _BOT.get_channel(cid)
    if cached is not None:
        return cached
    try:
        return await _BOT.fetch_channel(cid)
    except discord.HTTPException as err:
        _L.warning("fetch_channel: HTTPException %s: %s", err.status, err.text)
        raise
    except discord.InvalidData as err:
        _L.error("fetch_channel: InvalidData %s", err)
        raise

async def fetch_channel_maybe(
        cid: int
        ) -> typing.Union[discord.abc.GuildChannel, discord.abc.PrivateChannel]:
    """
    Similar to fetch_channel_nonnull, but returns None instead of throwing if
    the channel does not exist. Still throws for other errors.

    Having insufficient permissions to fetch the channel will result in None
    being returned.

    Parameters:
    - cid - The channel/category ID to fetch

    Raises:
    - discord.HTTPException - Fetching the channel failed.
    - discord.InvalidData - An unknown channel type was returned from Discord

    Returns:
    - The requested channel/category, or None if it can't be found.
    """
    try:
        return await fetch_channel_nonnull(cid)
    except discord.NotFound:
        return None
    except discord.Forbidden:
        # Same deal as fetch_message_maybe - this is equivalent to "no channel"
        return None

async def fetch_message_nonnull(
        where: typing.Union[discord.abc.Messageable, discord.User, discord.Member],
        mid: int
        ) -> discord.Message:
    """
    Finds a message using a given ID from a given place. Throws if message not
    found.

    Parameters:
    - where - The place to search for the message
    - mid - The ID of the message to fetch

    Raises:
    - discord.NotFound - The message was not found
    - discord.Forbidden - Insufficient permissions to get the requested message
    - discord.HTTPException - Retrieving the message failed

    Returns:
    - The requested message
    """
    return await where.fetch_message(mid)

async def fetch_message_maybe(
        where: typing.Union[discord.abc.Messageable, discord.User, discord.Member],
        mid: int
        ) -> typing.Optional[discord.Message]:
    """
    A wrapper around fetch_message_nonnull to instead return None if the
    message is not accessible (due to permissions) or doesn't exist.

    Parameters:
    - where - The place to search for the message
    - mid - The ID of the message to fetch

    Raises:
    - discord.HTTPException - Retrieving the message failed

    Returns:
    - The requested message, or None of not accessible/missing.
    """
    try:
        return await fetch_message_nonnull(where, mid)
    except discord.NotFound:
        return None
    except discord.Forbidden:
        # We're treating this as "message not found" since to the bot, the
        # message doesn't exist
        return None
