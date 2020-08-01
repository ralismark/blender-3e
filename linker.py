#!/usr/bin/env python3

from base import fragment

# pylint: disable=invalid-name
setup = fragment.Fragment()
# pylint: enable=invalid-name

COURSE_PREFIX = "https://www.handbook.unsw.edu.au/undergraduate/courses/2020/"

@setup.command("course")
async def handbook_course(ctx, *codes):
    """
    Link to UNSW courses from their code
    """
    codes = [f"{COURSE_PREFIX}{code.strip().upper()}" for code in codes]
    await ctx.send("\u200b:bookmark_tabs: " + "\n".join(codes))
