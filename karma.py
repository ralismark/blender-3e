#!/usr/bin/env python3

import logging
import enum

import discord
from discord.ext import commands

from base import sql, fragment, settings, resolver, config

setup = fragment.Fragment()
_L = logging.getLogger(__name__)

class Kind(enum.IntEnum):
    UPVOTE = 1
    ANYREACT = 2

sql.require_table("karma", """
        giver INTEGER NOT NULL,
        message INTEGER NOT NULL,
        kind INTEGER NOT NULL,
        delta INTEGER NOT NULL,
        receiver INTEGER NOT NULL,
        PRIMARY KEY(giver, message, kind)
        """)

enable = settings.ServerChannelSetting(
        name="enable_karma",
        description="Enable voting on messages",
        parse=settings.true_false)

upvote = "🔺"

async def parse_payload(payload):
    channel = await resolver.fetch_channel_maybe(payload.channel_id)
    if channel is None or isinstance(channel, discord.abc.PrivateChannel):
        return None # Doesn't exist, or is DM channel
    message = await resolver.fetch_message_maybe(channel, payload.message_id)
    giver = await resolver.fetch_user_maybe(payload.user_id)
    if message is None or giver is None:
        return None # Doesn't exist

    if not await enable.get(message):
        return None

    if payload.user_id == message.author.id:
        return None # no self-upvote

    if message.author.bot or giver.bot:
        return None # no bots

    kind = Kind.UPVOTE
    if str(payload.emoji) != upvote:
        kind = Kind.ANYREACT
        # return # not an upvote

    return {
        "giver": payload.user_id,
        "message": payload.message_id,
        "kind": kind,
        "delta": 1,
        "receiver": message.author.id
        }

@setup.listen("on_raw_reaction_add")
async def on_reaction_add(payload):
    delta = await parse_payload(payload)
    if delta is None:
        return

    sql.query("""
        INSERT OR IGNORE INTO karma(
            giver, message, kind, delta, receiver
        ) VALUES (:giver, :message, :kind, :delta, :receiver)
        """, **delta)

@setup.listen("on_raw_reaction_remove")
async def on_reacton_remove(payload):
    delta = await parse_payload(payload)
    if delta is None:
        return

    sql.query("""
        DELETE FROM karma
        WHERE giver=:giver AND message=:message AND kind=:kind
        """, **delta)

@setup.command("karma")
async def get_karma(ctx, who: commands.UserConverter = None):
    """
    Get the amount of karma a person has.

    Karma is given by upvoting messages. This is done through reacting with
    :small_red_triangle:.
    """
    if who is None:
        who = ctx.author

    query = """
        SELECT ifnull(SUM(delta), 0) FROM karma
        WHERE receiver=?
        """

    if "no-anyreact" in config.get("karma"):
        query = """
            SELECT ifnull(SUM(delta), 0) FROM karma
            WHERE receiver=? AND kind != 2
            """

    karma = sql.query(query, who.id)
    karma = (karma[0][0] or 0) if karma else 0

    await ctx.send(f"🔶 {who} is at {karma}$", delete_after=60)

@setup.command("ktop")
async def leaderboards(ctx):
    """
    Show the people who have the most karma
    """

    query = """
        SELECT receiver, SUM(delta) AS net FROM karma
        GROUP BY receiver
        ORDER BY net DESC
        LIMIT 10
        """

    if "no-anyreact" in config.get("karma"):
        query = """
            SELECT receiver, SUM(delta) AS net FROM karma
            WHERE kind != 2
            GROUP BY receiver
            ORDER BY net DESC
            LIMIT 10
            """

    top = sql.query(query)
    embed = discord.Embed(title="Top karma")
    for idx, row in enumerate(top):
        user = await resolver.fetch_user_maybe(row[0])
        if not user:
            user = f"<user id {row[0]}>"
        embed.add_field(name=f"{idx+1}. {user}", value=f"{row[1]}$")

    await ctx.send(embed=embed, delete_after=60)
