#!/bin/python3
#
# Reverse : Generate an indented asm code (pseudo-C) with colored syntax.
# Copyright (C) 2015    Joel
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.    If not, see <http://www.gnu.org/licenses/>.
#

import sys
from textwrap import dedent
from pathlib import Path


def default_custom_file():
    filename = str(Path(__file__).parent.parent / "custom_colors.py")
    with open(filename, "w+") as fd:
        fd.write(dedent("""\
            VERSION = 1

            class COLOR:
                def __init__(self, val, bold):
                    self.val  = str(val)
                    self.bold = bold

            COLOR_SECTION        = COLOR(81, False)
            COLOR_KEYWORD        = COLOR(161, True)
            COLOR_VAR            = COLOR(208, True)
            COLOR_TYPE           = COLOR(81, False)
            COLOR_COMMENT        = COLOR(242, False)
            COLOR_ADDR           = COLOR(242, False)
            COLOR_STRING         = COLOR(144, False)
            COLOR_SYMBOL         = COLOR(144, False)
            COLOR_RETCALL        = COLOR(161, False)
            COLOR_INTERN_COMMENT = COLOR(38, False)
            """))


try:
    from custom_colors import *
except:
    default_custom_file()
    from custom_colors import *


# Old versions of custom_colors.py
try:
    COLOR_INTERN_COMMENT
    VERSION
except:
    filename = str(Path(__file__).parent.parent / "custom_colors.py")
    with open(filename, "a") as fd:
        fd.write((dedent("""\n\
        COLOR_INTERN_COMMENT = COLOR(38, False)
        VERSION = 1""")))
    print("Your file custom_colors.py has been updated.")
    print("You can run again your command")
    sys.exit(0)


ctx = None


def pick_color(addr):
    if addr in ctx.addr_color:
        return

    if ctx.color_counter == 230:
        ctx.color_counter = 112
    else:
        ctx.color_counter += 2

    ctx.addr_color[addr] = ctx.color_counter


def color(text, c): # type c == int
    if not ctx.color:
        return text
    return "\x1b[38;5;" + str(c) + "m" + text + "\x1b[0m"


def color_class(text, c):
    if not ctx.color:
        return text
    if c.bold:
        return "\x1b[38;5;" + c.val + "m" + bold(text) + "\x1b[0m"
    return "\x1b[38;5;" + c.val + "m" + text + "\x1b[0m"


def bold(text):
    return "\x1b[1m" + text + "\x1b[0m"


def color_section(text):
    return color_class(text, COLOR_SECTION)


def color_keyword(text):
    return color_class(text, COLOR_KEYWORD)


def color_var(text):
    return color_class(text, COLOR_VAR)


def color_type(text):
    return color_class(text, COLOR_TYPE)


def color_comment(text):
    return color_class(text, COLOR_COMMENT)


def color_intern_comment(text):
    return color_class(text, COLOR_INTERN_COMMENT)


def color_addr(addr, print_colon=True):
    s = hex(addr)
    if print_colon:
        s += ": "
    if addr in ctx.addr_color:
        return color(s, ctx.addr_color[addr])
    return color_class(s, COLOR_ADDR)


def color_string(text):
    return color_class(text, COLOR_STRING)


def color_symbol(text):
    return color_class(text, COLOR_SYMBOL)


def color_retcall(text):
    return color_class(text, COLOR_RETCALL)
