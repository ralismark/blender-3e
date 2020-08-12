#!/usr/bin/env python3

import re

from base import fragment

# pylint: disable=invalid-name
setup = fragment.Fragment()
# pylint: enable=invalid-name

COURSE_PREFIX = "https://www.handbook.unsw.edu.au/undergraduate/courses/2020/"
COURSE_PATTERN = re.compile(r'[A-Za-z]{4}[0-9]{4}')

@setup.command("course")
async def handbook_course(ctx, *codes):
    """
    Link to UNSW courses from their code
    """
    for code in codes:
        if not COURSE_PATTERN.fullmatch(code):
            await ctx.send("\u200b:x: not a valid course code", delete_after=10)
            return

    codes = [f"{COURSE_PREFIX}{code.strip().upper()}" for code in codes]
    await ctx.send("\u200b:bookmark_tabs: " + "\n".join(codes))
