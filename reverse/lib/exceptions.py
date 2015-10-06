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


class ExcSymNotFound(Exception):
    def __init__(self, symname):
        self.symname = symname


class ExcSectionNotFound(Exception):
    def __init__(self, section):
        self.section = section


class ExcNotExec(Exception):
    def __init__(self, addr):
        self.addr = addr


class ExcArch(Exception):
    def __init__(self, arch):
        self.arch = arch


class ExcFileFormat(Exception):
    pass


class ExcIfelse(Exception):
    def __init__(self, addr):
        self.addr = addr


class ExcNotAddr(Exception):
    def __init__(self, addr):
        self.addr = addr


class ExcPEFail(Exception):
    def __init__(self, e):
        self.e = e
