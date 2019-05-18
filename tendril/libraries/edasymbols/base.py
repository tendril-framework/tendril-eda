#!/usr/bin/env python
# encoding: utf-8

# Copyright (C) 2018 Chintalagiri Shashank
#
# This file is part of tendril.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import csv
from tendril.config import AUDIT_PATH

from tendril.conventions.series import register_custom_series
from tendril.conventions.electronics import ident_transform
from tendril.conventions.electronics import resistor_tools
from tendril.conventions.electronics import capacitor_tools
from tendril.conventions.electronics import jb_tools_for_ident

from tendril.validation.base import ValidatableBase
from tendril.entities.edasymbols.base import EDASymbolBase
from tendril.entities.edasymbols.base import EDASymbolGeneratorBase
from tendril.utils.fsutils import VersionedOutputFile
from tendril.utils.types import ParseException


class EDASymbolNotFound(Exception):
    pass


class EDASymbolLibraryBase(ValidatableBase):
    _symbol_class = EDASymbolBase
    _generator_class = EDASymbolGeneratorBase
    _exc_class = EDASymbolNotFound

    def __init__(self, path, recursive=True,
                 resolve_generators=True, include_generators=False,
                 **kwargs):
        super(EDASymbolLibraryBase, self).__init__(**kwargs)
        self.path = path
        self._recursive = recursive
        self._resolve_generators = resolve_generators
        self._include_generators = include_generators

        self.symbols = []
        self.generators = []
        self.index = {}
        self.regenerate()

    def get_folder_symbols(self, path=None, **kwargs):
        return self.__class__(path, **kwargs)

    def _load_library(self):
        raise NotImplementedError

    def _generate_index(self):
        self.index = {}
        for symbol in self.symbols:
            ident = symbol.ident_generic
            if ident in self.index.keys():
                self.index[ident].append(symbol)
            else:
                self.index[ident] = [symbol]

    def _register_series(self):
        for generator in self.generators:
            for iseries in generator.generator.iseries:
                register_custom_series(iseries)

    def regenerate(self):
        self.symbols = []
        self.generators = []
        self.index = {}

        self._load_library()
        self._generate_index()
        self._register_series()

    @property
    def idents(self):
        return self.index.keys()

    def is_recognized(self, ident):
        if ident in self.idents:
            return True
        return False

    def get_symbol(self, ident, get_all=False):
        if not ident.strip():
            raise self._exc_class("Ident cannot be left blank")

        if self.is_recognized(ident):
            if not get_all:
                return self.index[ident][0]
            else:
                return self.index[ident]

        raise self._exc_class('Symbol {0} not found in {1}'
                              ''.format(ident, self.name))

    def get_symbol_folder(self, ident):
        symfolder = os.path.split(self.get_symbol(ident).gpath)[0]
        return os.path.relpath(symfolder, self.path)

    def preconform_device(self, device):
        return device

    def preconform_footprint(self, footprint):
        return footprint

    def find_jellybean(self, jb_tools, device, footprint, typevalue, **kwargs):
        footprint = self.preconform_footprint(footprint)
        device = self.preconform_device(device)

        if isinstance(typevalue, str):
            try:
                typevalue = jb_tools.defs()[0].typeclass(typevalue)
            except ParseException:
                tident = ident_transform(device, typevalue, footprint)
                return self.get_symbol(tident)

        tjb = jb_tools.pack(typevalue,
                            context={'device': device, 'footprint': footprint},
                            **kwargs)

        candidates = []
        for symbol in self.symbols:
            # TODO Don't search _everything_ here
            # TODO Handle special resistors?
            if symbol.device == device and symbol.footprint == footprint:
                try:
                    sjb = jb_tools.parse(symbol.value)
                except ParseException:
                    continue
                symscore = jb_tools.match(tjb, sjb)
                if symscore:
                    candidates.append((symbol, symscore))

        if not len(candidates):
            raise self._exc_class(typevalue)

        candidates = sorted(candidates, key=lambda c: c[1], reverse=True)
        maxscore = candidates[0][1]
        candidates = [x for x in candidates if x[1] == maxscore]
        return jb_tools.bestmatch(tjb, candidates)

    def find_resistor(self, *args, **kwargs):
        return self.find_jellybean(resistor_tools, *args, **kwargs)

    def find_capacitor(self, *args, **kwargs):
        return self.find_jellybean(capacitor_tools, *args, **kwargs)

    def jb_harmonize(self, item):
        ident = ident_transform(item.data['device'],
                                item.data['value'],
                                item.data['footprint'])
        jb_tools = jb_tools_for_ident(ident)
        if not jb_tools:
            return item

        item.data['footprint'] = self.preconform_footprint(item.data['footprint'])  # noqa
        item.data['device'] = self.preconform_footprint(item.data['device'])
        context = {'device': item.data['device'],
                   'footprint': item.data['footprint']}

        params = jb_tools.parse(item.data['value'], context)._asdict()
        typevalue = params.pop(jb_tools.defs()[0].code)
        try:
            jb = self.find_jellybean(jb_tools,
                                     item.data['device'],
                                     item.data['footprint'],
                                     typevalue,
                                     **params)
            item.data['value'] = jb.value
        except self._exc_class:
            pass
        return item

    @property
    def generator_names(self):
        return [os.path.splitext(x.gname)[0] + '.gen'
                for x in self.generators]

    def get_generator(self, gen):
        for generator in self.generators:
            if os.path.splitext(generator.gname)[0] + '.gen' == gen:
                return generator

    def get_latest_symbols(self, n=10, include_virtual=False):
        if include_virtual is False:
            tlib = (x for x in self.symbols if x.is_virtual is False)
        else:
            tlib = self.symbols
        return sorted(tlib, key=lambda y: y.last_updated, reverse=True)[:n]

    def export_audit(self, name):
        auditfname = os.path.join(
            AUDIT_PATH, 'esymlib-{0}.audit.csv'.format(name)
        )
        outf = VersionedOutputFile(auditfname)
        outw = csv.writer(outf)
        outw.writerow(['filename', 'status', 'ident', 'device', 'value',
                       'footprint', 'description', 'path', 'package'])
        for symbol in self.symbols:
            outw.writerow(
                [symbol.gname, symbol.status, symbol.ident, symbol.device,
                 symbol.value, symbol.footprint, symbol.description,
                 symbol.gpath, symbol.package]
            )
        outf.close()

    def _validate(self):
        pass


def load(manager):
    manager.install_exc_class('EDASymbolNotFound', EDASymbolNotFound)
