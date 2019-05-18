#!/usr/bin/env python
# encoding: utf-8

# Copyright (C) 2019 Chintalagiri Shashank
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


import importlib
from six import iteritems

from tendril.config import EDA_LIBRARY_FUSION
from tendril.config import EDA_LIBRARY_PRIORITY

from tendril.validation.base import ValidationContext
from tendril.utils.fsutils import get_namespace_package_names
from tendril.utils import log
logger = log.get_logger(__name__, log.DEFAULT)


class EDALibraryManager(object):
    def __init__(self, prefix):
        self._prefix = prefix
        self._validation_context = ValidationContext(self.__module__)
        self._index = {}
        self._libraries = {}
        self._exc_classes = {}
        self._load_libraries()
        self._generate_index()

    def _load_libraries(self):
        logger.debug("Loading EDA library modules from {0}".format(self._prefix))
        modules = list(get_namespace_package_names(self._prefix))
        for m_name in modules:
            if m_name == __name__:
                continue
            m = importlib.import_module(m_name)
            m.load(self)

    def install_library(self, name, library):
        self._libraries[name] = library

    def install_exc_class(self, name, exc_class):
        self._exc_classes[name] = exc_class

    def __getattr__(self, item):
        if item in self._libraries.keys():
            return self._libraries[item]
        if item in self._exc_classes.keys():
            return self._exc_classes[item]
        raise AttributeError('No attribute {0} in {1}!'
                             ''.format(item, self.__class__.__name__))

    def export_audits(self):
        for name, library in iteritems(self._libraries):
            library.export_audit(name)

    def regenerate(self):
        for name, library in iteritems(self._libraries):
            log.info("Regenerating EDA library '{0}'".format(name))
            library.regenerate()
        self._generate_index()

    def _generate_index(self):
        self.index = {}
        if not EDA_LIBRARY_FUSION:
            self.index = self._libraries[EDA_LIBRARY_PRIORITY[0]].index

        for lname in EDA_LIBRARY_PRIORITY:
            library = self._libraries[lname]
            for ident, symbols in iteritems(library.index):
                if ident in self.index:
                    self.index[ident].extend(symbols)
                else:
                    self.index[ident] = symbols

    @property
    def idents(self):
        return self.index.keys()

    def is_recognized(self, ident):
        if ident in self.idents:
            return True
        return False

    def get_symbol(self, ident, get_all=False):
        if not ident.strip():
            raise self.nosymbolexception(
                "Ident cannot be left blank")

        if self.is_recognized(ident):
            if not get_all:
                return self.index[ident][0]
            else:
                return self.index[ident]

        raise self.nosymbolexception(
            'Symbol {0} not found in fused library'.format(ident))

    def find_jellybean(self, finder, *args, **kwargs):
        if not EDA_LIBRARY_FUSION:
            return getattr(self._libraries[
                EDA_LIBRARY_PRIORITY[0]
            ], finder)(*args, **kwargs)

        for lname in EDA_LIBRARY_PRIORITY:
            library = self._libraries[lname]
            try:
                return getattr(library, finder)(*args, **kwargs)
            except self.nosymbolexception:
                continue
        raise self.nosymbolexception(*args)

    def find_resistor(self, *args, **kwargs):
        return self.find_jellybean('find_resistor', *args, **kwargs)

    def find_capacitor(self, *args, **kwargs):
        return self.find_jellybean('find_capacitor', *args, **kwargs)

    def jb_harmonize(self, item):
        return self._libraries[EDA_LIBRARY_PRIORITY[0]].jb_harmonize(item)

    @property
    def nosymbolexception(self):
        return self._exc_classes['EDASymbolNotFound']
