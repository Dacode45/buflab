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

import time

from lib.ast import (Ast_Branch, Ast_Comment, Ast_Goto, Ast_Loop,
        Ast_IfGoto, Ast_Ifelse, Ast_AndIf)
from lib.utils import BRANCH_NEXT, BRANCH_NEXT_JUMP, debug__
from lib.exceptions import ExcIfelse


def get_ast_ifgoto(ctx, paths, curr_loop_idx, inst):
    nxt = ctx.gph.link_out[inst.address]

    # A jump is normally alone in a block, but for some architectures
    # we save the prefetched instruction after.
    blk = ctx.gph.nodes[inst.address]
    if len(blk) == 2:
        prefetch = blk[1]
    else:
        prefetch = None

    c1 = paths.loop_contains(curr_loop_idx, nxt[BRANCH_NEXT])
    c2 = paths.loop_contains(curr_loop_idx, nxt[BRANCH_NEXT_JUMP])

    if c1 and c2:
        raise ExcIfelse(inst.addr)

    # If the address of the jump is inside the loop, we
    # invert the conditions. example :
    #
    # jmp conditions
    # loop:
    #    code ...
    # conditions:
    #    cmp ...
    #    jg loopend
    #    cmp ...
    #    jne loop
    # loopend:
    #
    # Here the last jump point inside the loop. We want to
    # replace by this : 
    #
    # loop {
    #    cmp ...
    #    jg loopend
    #    cmp ...
    #    je loopend
    #    code ...
    # } # here there is an implicit jmp to loop
    # loopend:
    #

    cond_id = ctx.libarch.utils.get_cond(inst)
    br = nxt[BRANCH_NEXT_JUMP]
    if c2:
        cond_id = ctx.libarch.utils.invert_cond(inst)
        br = nxt[BRANCH_NEXT]

    return Ast_IfGoto(inst, cond_id, br, prefetch)


def get_ast_branch(ctx, paths, curr_loop_idx=[], last_else=-1):
    ast = Ast_Branch()
    is_if_printed = False

    if paths.rm_empty_paths():
        return ast

    while 1:
        ad = paths.first()
        if ad in ctx.seen:
            ast.add(Ast_Goto(ad))
            return ast

        # Stop at the first split or loop
        nb_commons, is_loop, is_ifelse, force_stop_addr = \
            paths.head_last_common(curr_loop_idx)

        if nb_commons > 0:
            common_path = paths.pop(nb_commons)

            for ad in common_path:
                ctx.seen.add(ad)
                blk = ctx.gph.nodes[ad]

                # Here if we have conditional jump, it's not a ifelse,
                # it's a condition for a loop. It will be replaced by a
                # goto. ifgoto are skipped by head_last_common.
                if ad in ctx.gph.cond_jumps_set:
                    inst = blk[0] # first inst
                    ast.add(get_ast_ifgoto(ctx, paths, curr_loop_idx, inst))
                else:
                    ast.add(blk)

            if paths.rm_empty_paths():
                return ast

            ad = paths.first()
            if ad in ctx.seen:
                ast.add(Ast_Goto(ad))
                return ast

        # See comments in paths.__enter_new_loop
        if force_stop_addr != 0:
            ad = paths.first()
            blk = ctx.gph.nodes[ad]
            ast.add(blk)

            if ad not in ctx.gph.uncond_jumps_set:
                ast.add(Ast_Goto(ctx.gph.link_out[blk[0].address][BRANCH_NEXT]))
            break

        if is_loop:
            # last_else == -1
            # -> we can't go to a same else inside a loop
            a, endpoint = get_ast_loop(ctx, paths, curr_loop_idx, -1)
            ast.add(a)
        elif is_ifelse:
            a, endpoint = get_ast_ifelse(
                               ctx, paths, curr_loop_idx,
                               last_else, is_if_printed)
            is_if_printed = isinstance(a, Ast_Ifelse)
            ast.add(a)
        else:
            endpoint = paths.first()

        if endpoint == -1 or paths.goto_addr(endpoint):
            break

    return ast


# TODO move in class Paths
# Assume that the beginning of paths is the beginning of a loop
def paths_is_infinite(paths):
    for k, p in paths.paths.items():
        for addr in p:
            if addr in paths.gph.cond_jumps_set:
                nxt = paths.gph.link_out[addr]
                if nxt[BRANCH_NEXT] not in paths or \
                   nxt[BRANCH_NEXT_JUMP] not in paths: \
                    return False
    return True


def get_ast_loop(ctx, paths, last_loop_idx, last_else):
    ast = Ast_Loop()
    curr_loop_idx = paths.get_loops_idx()
    first_blk = ctx.gph.nodes[paths.get_loop_start(curr_loop_idx)]

    # if the first instruction of the loop is a jump, it means
    # it's a loop condition.
    if first_blk[0].address in ctx.gph.cond_jumps_set:
        ast.add(get_ast_ifgoto(ctx, paths, curr_loop_idx, first_blk[0]))
    else:
        ast.add(first_blk)

    loop_paths, loopends, loopends_start = \
        paths.extract_loop_paths(curr_loop_idx, last_loop_idx)

    # Checking if loopend == [] to determine if it's an 
    # infinite loop is not sufficient
    # tests/nestedloop2
    ast.set_infinite(paths_is_infinite(loop_paths))

    addr = loop_paths.pop(1)[0]
    ctx.seen.add(addr)
    ast.add(get_ast_branch(ctx, loop_paths, curr_loop_idx))

    if not loopends:
        return ast, -1

    epilog = Ast_Branch()
    if len(loopends) > 1:
        epilog_num = 1

        for i, el in enumerate(loopends[:-1]):
            if isinstance(el, Ast_Goto):
                epilog.add(el)
                continue

            if el.first() in loopends_start:
                epilog.add(Ast_Comment("loopend " + str(epilog_num)))
                epilog_num += 1

            epilog.add(get_ast_branch(ctx, el, last_loop_idx))

        if loopends[-1].first() in loopends_start:
            epilog.add(Ast_Comment("loopend " + str(epilog_num)))

        ast.set_epilog(epilog)

    return ast, loopends[-1].first()


def get_ast_ifelse(ctx, paths, curr_loop_idx, last_else, is_if_printed):
    addr = paths.pop(1)[0]
    ctx.seen.add(addr)
    paths.rm_empty_paths()
    nxt = ctx.gph.link_out[addr]
    jump_inst = ctx.gph.nodes[addr][0]

    # A jump is normally alone in a block, but for some architectures
    # we save the prefetched instruction after.
    blk = ctx.gph.nodes[addr]
    if len(blk) == 2:
        prefetch = blk[1]
    else:
        prefetch = None

    if_addr = nxt[BRANCH_NEXT]
    else_addr = nxt[BRANCH_NEXT_JUMP]

    # If endpoint == -1, it means we are in a sub-if and the endpoint 
    # is after. When we create_split, only address inside current
    # if and else are kept.
    endpoint = paths.first_common_ifelse(curr_loop_idx, else_addr)
    split = paths.split(addr, endpoint)

    # is_if_printed : better output (tests/if5)
    #
    # example C file :
    #
    # if 1 {
    #   if 2 {
    #     ...
    #   }
    #   if 3 {
    #     ...
    #   }
    # }
    #
    #
    # output without the is_if_printed. This is correct, the andif is 
    # attached to the "if 1", but it's not very clear.
    #
    # if 1 {
    #   if 2 { 
    #     ...
    #   }
    #   and if 3
    #   ...
    # }
    #
    # output with the is_if_printed :
    # Instead of the andif, we have the same code as the original.
    #

    # last_else allows to not repeat the else part when there are some 
    # and in the If. example :
    #
    # if (i > 0 && i == 1) {
    #     part 1
    # } else {
    #     part 2
    # }
    #
    #
    # output without this "optimization" :
    #
    # ...
    # if > {
    #     ...
    #     if == {
    #         part 1
    #     } else != {
    #         part 2
    #     }
    # } else <= {
    #     part 2
    # }
    # 
    #
    # output with "optimization" :
    #
    # ...
    # if > {
    #     ...
    #     and if ==    means that if the condition is false, goto else
    #     part 1
    # } else <= {
    #     part 2
    # }
    #

    if ctx.print_andif and last_else != -1 and not is_if_printed:
        if else_addr == last_else:
            return (Ast_AndIf(jump_inst,
                              ctx.libarch.utils.invert_cond(jump_inst),
                              prefetch),
                    if_addr)

        if if_addr == last_else:
            return (Ast_AndIf(jump_inst,
                              ctx.libarch.utils.get_cond(jump_inst),
                              prefetch),
                    else_addr)

    if split[BRANCH_NEXT_JUMP].next_addr == else_addr:
        a1 = Ast_Branch()
        a2 = get_ast_branch(ctx, split[BRANCH_NEXT], curr_loop_idx, else_addr)
        return (Ast_Ifelse(jump_inst, a1, a2, prefetch), else_addr)

    a1 = get_ast_branch(ctx, split[BRANCH_NEXT_JUMP], curr_loop_idx, -1)
    a2 = get_ast_branch(ctx, split[BRANCH_NEXT], curr_loop_idx, else_addr)
    return (Ast_Ifelse(jump_inst, a1, a2, prefetch), endpoint)


def generate_ast(ctx__, paths):
    global ctx
    ctx = ctx__

    start = time.clock()

    ast = get_ast_branch(ctx, paths)

    elapsed = time.clock()
    elapsed = elapsed - start
    debug__("Ast generated in %fs" % elapsed)

    # Process ast

    start = time.clock()

    for func in ctx.libarch.registered:
        func(ctx, ast)

    elapsed = time.clock()
    elapsed = elapsed - start
    debug__("Functions for processing ast in %fs" % elapsed)

    if ctx.color:
        ctx.libarch.process_ast.assign_colors(ctx, ast)

    return ast
