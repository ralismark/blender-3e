#!/usr/bin/env python3

import logging

import discord
from discord.ext import commands

from base import fragment, settings, resolver

setup = fragment.Fragment()
_L = logging.getLogger(__name__)

STAR = '\u2b50'

pin_channel = settings.ServerChannelSetting(
        name="pin_channel",
        description="Channel to put pinned messages. 0 to disable this feature",
        parse=int)
pin_threshhold = settings.ServerChannelSetting(
        name="pin_threshhold",
        description="Minimum number of \u2b50 to pin message",
        parse=int)

@setup.listen("on_raw_reaction_add")
async def on_maybe_star(payload: discord.RawReactionActionEvent):
    """
    Possibly star a message
    """

    channel = await resolver.get_channel(payload.channel_id)
    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.errors.NotFound:
        return

    star = discord.utils.get(message.reactions, emoji=STAR)

    if (not star # no stars
            or payload.emoji.name != STAR # not star
            or star.me # we've starred this
            or (not message.clean_content and not message.attachments) # empty
       ):
        _L.debug("pin: message=%s does not satisfy requirements", message.id)
        return

    sb_id = await pin_channel.get(message)
    sb_threshhold = await pin_threshhold.get(message)
    if not sb_id:
        _L.debug("pin: message=%s not configured", message.id)
        return
    if star.count < sb_threshhold:
        _L.debug("pin: message=%s not enough stars", message.id)
        return

    _L.debug("pin: pinning message=%s into channel=%s", message.id, sb_id)

    # we've definitely starring at this point
    await message.add_reaction(STAR)

    sb_channel = await resolver.get_channel(sb_id)
    embed = discord.Embed(title=":star:", color=0xf8aa39, url=message.jump_url)
    embed.description = message.clean_content
    embed.set_footer(text=f"#{channel}")
    embed.set_author(name=message.author.display_name,
                     icon_url=message.author.avatar_url_as(format="png", size=64))
    embed.timestamp = message.created_at

    if message.attachments:
        field = "\n".join(f"[{att.filename}]({att.proxy_url})" for att in message.attachments)
        embed.add_field(name="Attachments", value=field, inline=False)

        if message.attachments[0].filename.endswith((".png", ".jpg", ".jpeg")):
            embed.set_image(url=message.attachments[0].proxy_url)

    await sb_channel.send(embed=embed)
