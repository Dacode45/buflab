#!/usr/bin/env python3
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
import os
from argparse import ArgumentParser, FileType

from lib.disassembler import Disassembler
from lib.utils import die, error
from lib.generate_ast import generate_ast
from lib.vim import generate_vim_syntax
from lib.context import Context
from lib.exceptions import (ExcSymNotFound, ExcNotExec, ExcArch,
     ExcFileFormat, ExcNotAddr, ExcIfelse, ExcPEFail, ExcSectionNotFound)


def parse_args():
    # Parse arguments
    parser = ArgumentParser(description=
        'Reverse engineering for x86/ARM/MIPS binaries. Generation of pseudo-C. '
        'Supported formats : ELF, PE. https://github.com/joelpx/reverse')
    parser.add_argument('filename', nargs='?', metavar='FILENAME')
    parser.add_argument('-nc', '--nocolor', action='store_true')
    parser.add_argument('-g', '--graph', action='store_true',
            help='Generate an html flow graph. See d3/index.html.')
    parser.add_argument('--nocomment', action='store_true',
            help="Don't print comments")
    parser.add_argument('--noandif', action='store_true',
            help="Print normal 'if' instead of 'andif'")
    parser.add_argument('--datasize', type=int, default=30, metavar='N',
            help='default 30, maximum of chars to display for strings or bytes array.')
    parser.add_argument('-x', '--entry', metavar='SYMBOLNAME|0xXXXXX|EP',
            help='default main. EP stands for entry point.')
    parser.add_argument('--vim', action='store_true',
            help='Generate syntax colors for vim')
    parser.add_argument('-s', '--symbols', action='store_true',
            help='Print all symbols')
    parser.add_argument('-c', '--calls', metavar='SECTION_NAME', type=str,
            help='Print all calls which are in the given section')
    parser.add_argument('--sections', action='store_true',
            help='Print all sections')
    parser.add_argument('--dump', action='store_true',
            help='Dump asm without decompilation')
    parser.add_argument('--data', action='store_true',
            help='Don\'t disassemble, print only bytes and detect ascii strings')
    parser.add_argument('-l', '--lines', type=int, default=30, metavar='N',
            help='Max lines used with --dump or --data')
    parser.add_argument('--bytes', action='store_true',
            help='Print instruction bytes')
    parser.add_argument('-i', '--interactive', action='store_true',
            help='Interactive mode')
    parser.add_argument('--symfile', metavar='FILENAME', type=FileType('r'),
            help=('Add user symbols for better readability of the analysis. '
            'Line format: ADDRESS_HEXA    SYMBOL_NAME'))
    parser.add_argument('-d', '--opt_debug', action='store_true')
    parser.add_argument('-ns', '--nosectionsname', action='store_true')
    parser.add_argument('--raw', metavar='x86|x64|arm|mips|mips64',
            help='Consider the input file as a raw binary')
    parser.add_argument('--rawbase', metavar='0xXXXXX',
            help='Set base address of a raw file (default=0)')
    parser.add_argument('--rawbe', action='store_true',
            help='If not set it\'s in little endian')

    args = parser.parse_args()

    ctx = Context()
    ctx.debug           = args.opt_debug
    ctx.print_andif     = not args.noandif
    ctx.color           = not args.nocolor
    ctx.comments        = not args.nocomment
    ctx.sectionsname    = not args.nosectionsname
    ctx.max_data_size   = args.datasize
    ctx.filename        = args.filename
    ctx.raw_type        = args.raw
    ctx.raw_base        = args.rawbase
    ctx.symfile         = args.symfile
    ctx.syms            = args.symbols
    ctx.calls_in_section = args.calls
    ctx.entry           = args.entry
    ctx.dump            = args.dump
    ctx.vim             = args.vim
    ctx.interactive     = args.interactive
    ctx.lines           = args.lines
    ctx.graph           = args.graph
    ctx.raw_big_endian  = args.rawbe
    ctx.list_sections   = args.sections
    ctx.print_bytes     = args.bytes
    ctx.print_data      = args.data

    if ctx.raw_base is not None:
        if ctx.raw_base.startswith("0x"):
            ctx.raw_base = int(ctx.raw_base, 16)
        else:
            error("--rawbase must in hex format")
            die()
    else:
        ctx.raw_base = 0

    return ctx


def load_file(ctx):
    if not os.path.exists(ctx.filename):
        error("file {ctx.filename} doesn't exists".format(ctx=ctx))
        if ctx.interactive:
           return False
        die()

    if not os.path.isfile(ctx.filename):
        error("this is not a file".format(ctx=ctx))
        if ctx.interactive:
           return False
        die()

    try:
        dis = Disassembler(ctx.filename, ctx.raw_type,
                           ctx.raw_base, ctx.raw_big_endian)
    except ExcArch as e:
        error("arch %s is not supported" % e.arch)
        if ctx.interactive:
            return False
        die()
    except ExcFileFormat:
        error("the file is not PE or ELF binary")
        if ctx.interactive:
            return False
        die()
    except ExcPEFail as e:
        error(str(e.e))
        error("It seems that pefile.parse_data_directories is bugged.")
        error("Maybe you should Retry")
        if ctx.interactive:
            return False
        die()

    ctx.dis = dis
    ctx.libarch = dis.load_arch_module()

    if ctx.symfile:
        dis.load_user_sym_file(ctx.symfile)

    return True


def init_addr(ctx):
    if ctx.calls_in_section is not None:
        try:
            addr = ctx.dis.binary.section_start(ctx.calls_in_section)
        except ExcSectionNotFound as e:
            error("section %s not found" % e.section)
            if ctx.interactive:
                return False
            die()

    elif ctx.entry == "EP":
        addr = ctx.dis.binary.get_entry_point()

    else:
        try:
            addr = ctx.dis.get_addr_from_string(ctx.entry, ctx.raw_type != None)
        except ExcSymNotFound as e:
            error("symbol %s not found" % e.symname)
            if ctx.interactive:
                return False
            error("You can see all symbols with -s (if resolution is done).")
            error("Note: --dump need the option -x.")
            die()

    try:
        ctx.dis.check_addr(ctx, addr)
    except ExcNotExec as e:
        error("the address 0x%x is not in an executable section" % e.addr)
        if ctx.interactive:
            return False
        die()
    except ExcNotAddr as e:
        error("the address 0x%x cannot be found" % e.addr)
        if ctx.interactive:
            return False
        die()

    ctx.entry_addr = addr

    return True


def disasm(ctx):
    ctx.gph = ctx.dis.get_graph(ctx.entry_addr)
    if ctx.gph == None:
        error("capstone can't disassemble here")
        return
    paths = ctx.gph.get_paths()
    paths.gph = ctx.gph
    paths.cache_obj()
    
    if ctx.graph:
        ctx.gph.html_graph()

    try:
        ast = generate_ast(ctx, paths)
    except ExcIfelse as e:
        error("can't have a ifelse here     %x" % e.addr)
        if ctx.interactive:
            return
        die()

    if ctx.vim:
        base = os.path.basename(ctx.filename)
        # re-assign if no colors
        ctx.libarch.process_ast.assign_colors(ctx, ast)
        ctx.color = False
        generate_vim_syntax(ctx, base + ".vim")
        sys.stdout = open(base + ".rev", "w+")

    o = ctx.libarch.output.Output(ctx)
    o.print_ast(ctx.entry_addr, ast)

    if ctx.vim:
        print("Run :  vim {0}.rev -S {0}.vim".format(base), file=sys.stderr)


def reverse(ctx):
    if not load_file(ctx):
        die()

    if ctx.list_sections:
        for name, start, end in ctx.dis.binary.iter_sections():
           ctx.dis.print_section_meta(name, start, end) 
        return

    if ctx.syms:
        ctx.dis.print_symbols(ctx.sectionsname)
        return

    init_addr(ctx)

    if ctx.calls_in_section is not None:
        ctx.dis.print_calls(ctx)
        return

    if ctx.dump or ctx.print_data:
        if ctx.vim:
            base = os.path.basename(ctx.filename)
            ctx.color = False
            sys.stdout = open(base + ".rev", "w+")

        if ctx.dump:
            ctx.dis.dump_asm(ctx, ctx.lines)
        else:
            ctx.dis.dump_data(ctx, ctx.lines)

        if ctx.vim:
            generate_vim_syntax(ctx, base + ".vim")
            print("Run :  vim {0}.rev -S {0}.vim".format(base), file=sys.stderr)
        return

    disasm(ctx)
