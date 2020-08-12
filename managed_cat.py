#!/usr/bin/env python3

"""
Allow server admins to create a "managed category", where users can join
(possibly creating) and leave channels. This allows temporary channels to be
made for specific topics/events.
"""

import asyncio
import datetime
import enum
import logging
import re
import typing
import unicodedata

import discord
from discord.ext import commands

from base import fragment, settings, resolver

# pylint: disable=invalid-name
managed_cat = settings.ServerSetting(
        name="managed_cat",
        description="ID of category for managed channels",
        parse=int)
dead_cat = settings.ServerSetting(
        name="dead_cat",
        description="ID of category to move channels when emptied",
        parse=int)
setup = fragment.Fragment()
_L = logging.getLogger(__name__)
# pylint: enable=invalid-name

class State(enum.Enum):
    """
    The different states a member can be
    """
    NONE = enum.auto()
    ACTIVE = enum.auto()
    PASSIVE = enum.auto()

    @staticmethod
    def from_overwrite(perms: discord.PermissionOverwrite):
        """
        Determine state from overwrite
        """
        if perms.send_messages:
            return State.ACTIVE
        if perms.read_messages:
            return State.PASSIVE
        return State.NONE

def slugify(name: str) -> str:
    """
    Convert string into a slug
    """
    slug = unicodedata.normalize('NFKD', name) # decompose unicode into ascii and diacritics
    slug = slug.encode('ascii', 'ignore').decode().lower() # remove non-ascii
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-') # convert non-words to ascii
    slug = re.sub(r'[-]+', '-', slug)
    return slug

def is_managed(ctx):
    catid = await managed_cat.get(ctx)
    return bool(catid)

async def to_managed(ctx: commands.Context, channame: typing.Optional[str]):
    """
    Convert a string into a managed channel, outputting appropriate errors.
    """
    catid = await managed_cat.get(ctx)

    if channame is None:
        chan = ctx.channel
        if chan.category_id != catid:
            await ctx.send("Channel not managed!", delete_after=10)
            return None
    else:
        chan = discord.utils.get(ctx.guild.text_channels, name=channame, category_id=catid)
        if chan is None:
            await ctx.send("Channel not found!", delete_after=10)
            return None

    return chan


def get_member_states(channel: discord.TextChannel):
    """
    Get the members and their states for a managed channel.
    """
    out = {i: [] for i in State if i != State.NONE}
    for member, overwrite in channel.overwrites.items():
        if (not isinstance(member, discord.Member) or
                member.bot):
            continue
        state = State.from_overwrite(overwrite)
        if state == State.NONE:
            continue
        out[state].append(member)
    return out


async def join_channel(user, channel):
    """
    Join a user to a channel
    """
    await channel.set_permissions(
        user, read_messages=True, send_messages=True,
        reason=f"{user.name} requested to join {channel.name}")

    now = datetime.datetime.now()
    nowstr = now.strftime("%A %-d %B, %X")

    embed = discord.Embed(
        title=f"#{channel.name}",
        description=f"__{user.mention}__ joined on __{nowstr}__")

    return embed


async def archive_channel(channel, category):
    """
    Archive a channel into a category
    """
    # TODO ensure that we can actually move the channel into the graveyard
    for member in channel.overwrites.keys():
        await channel.set_permissions(member, overwrite=None,
                                      reason="Kicking everyone out")

    grave_dt = datetime.datetime.utcnow().strftime("%-d%b%y-%H%M%S")
    await channel.edit(name=f"{channel.name}-{grave_dt}", category=category)


@setup.command("clear")
@commands.check(fragment.is_admin_or_owner)
@commands.check(is_managed)
async def clear_channel(ctx, *, channame: slugify = None):
    """
    Delete a managed channel, even if it still has members.

    This can only be done by admins.
    """
    chan = await to_managed(ctx, channame)
    if chan is None:
        return

    graveyard = ctx.guild.get_channel(await dead_cat.get(ctx))
    if graveyard is not None:
        await archive_channel(chan, graveyard)
    else:
        await chan.delete(reason="Forcibly depopulated by " + ctx.author.name)


@setup.command("list")
@commands.check(is_managed)
async def list_channels(ctx):
    """
    List available channels
    """
    catid = await managed_cat.get(ctx)
    if not catid:
        return

    embed = discord.Embed(title="Available channels")

    channels = ctx.guild.get_channel(catid).channels
    if channels:
        embed.description = f"{len(channels)} channels"
    else:
        embed.description = "No channels yet"

    for channel in channels:
        # HACK hardcoding the max number of fields in an embed
        if len(embed.fields) > 25:
            await ctx.send(embed=embed)
            embed = discord.Embed(title="Available channels")
        mstates = get_member_states(channel)
        active = len(mstates[State.ACTIVE])
        embed.add_field(name=channel.name, value=f"{active} users")

    await ctx.send(embed=embed)


@setup.command()
@commands.check(is_managed)
async def join(ctx, *, channame: slugify = None):
    """
    Join a channel
    """
    catid = await managed_cat.get(ctx)
    if not catid:
        return

    cat = ctx.guild.get_channel(catid)
    if channame is None:
        chan = ctx.channel
        if chan.category_id != catid:
            await ctx.send("No channel specified, and current is not managed", delete_after=10)
            return
        if ctx.author in get_member_states(chan)[State.ACTIVE]:
            await ctx.send("Already in this channel", delete_after=10)
            return
    elif not channame:
        await ctx.send("Invalid channel name", delete_after=10)
        return
    else:
        chan = discord.utils.get(cat.channels, name=channame)

    if chan is None:
        # create it
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
        }
        chan = await ctx.guild.create_text_channel(
            channame, overwrites=overwrites, category=cat,
            reason=f"{ctx.author.name} requested to join {channame}")

    embed = await join_channel(ctx.author, chan)
    await chan.send(embed=embed)

@setup.command()
@commands.check(is_managed)
async def view(ctx, *, channame: slugify = None):
    """
    Set yourself to only view the channel, without being able to send messages.

    If all other active members (i.e. those who can send messages) leave, the
    channel will be deleted even if you're still in it.
    """
    chan = await to_managed(ctx, channame)
    if chan is None:
        return

    active = get_member_states(chan)[State.ACTIVE]

    if len(active) == 1 and active[0].id == ctx.author.id:
        await ctx.send("\u200b:exclamation: You're the only one left. "
                       "Leave if you want to delete this channel.",
                       delete_after=60)
        return

    await chan.set_permissions(
        ctx.author, read_messages=True, send_messages=False,
        reason=f"{ctx.author.name} requested to only view {chan.name}")

@setup.command()
@commands.check(is_managed)
async def add(ctx, member: commands.MemberConverter, *, channame: slugify = None):
    """
    Add a user to a channel.

    This is useful for adding bots who can't join channels themselves.
    """
    chan = await to_managed(ctx, channame)
    if chan is None:
        return

    embed = await join_channel(member, chan)
    await chan.send(embed=embed)

@setup.command()
@commands.check(is_managed)
async def leave(ctx, *, channame: slugify = None):
    """
    Leave a channel
    """
    chan = await to_managed(ctx, channame)
    if chan is None:
        return

    await chan.set_permissions(ctx.author, overwrite=None,
                               reason=f"{ctx.author.name} requested to leave {chan.name}")

    # HACK to avoid 0-member channels
    await asyncio.sleep(0.5)

    if not get_member_states(chan)[State.ACTIVE]: # everyone left
        graveyard = ctx.guild.get_channel(await dead_cat.get(ctx))
        if graveyard is not None:
            # TODO handle this failing
            await archive_channel(chan, graveyard)

@setup.command()
@commands.check(is_managed)
async def whosin(ctx, *, channame: slugify = None):
    """
    List the people in a channel
    """
    chan = await to_managed(ctx, channame)
    if chan is None:
        return

    embed = discord.Embed(title="People in {}".format(chan.name))

    members = get_member_states(chan)
    embed.description = "\n".join(m.display_name for m in members[State.ACTIVE])
    embed.description += "\n"
    embed.description += "\n".join(f"[_viewing_] {m.display_name}" for m in members[State.PASSIVE])

    await ctx.send(embed=embed)
