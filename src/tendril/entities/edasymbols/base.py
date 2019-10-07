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
import arrow

from tendril.conventions.status import get_status
from tendril.conventions.status import Status
from tendril.conventions.electronics import DEVICE_CLASSES
from tendril.conventions.electronics import ident_transform
from tendril.conventions.electronics import fpiswire
from tendril.conventions.electronics import fpismodlen

from tendril.validation.base import ValidatableBase
from tendril.utils.types.lengths import Length

from .generator import EDASymbolGeneratorBase


class EDASymbolBase(ValidatableBase):
    _gen_class = EDASymbolGeneratorBase

    def __init__(self):
        """
        Base class for EDA symbols. This class should not be used directly,
        but sub-classed per EDA suite, the sub-classes designed to interface
        with the way each EDA suite handles symbol libraries.

        """
        super(EDASymbolBase, self).__init__()
        self.device = ''
        self.value = ''
        self.footprint = ''
        self._status = None
        self.description = None
        self.package = None
        self._last_updated = None
        self._datasheet = None
        self._manufacturer = None
        self._vendors = None
        self._indicative_sourcing_info = None
        self._img_repr_path = None

        self._get_sym()
        self._generate_img_repr()

    def _get_sym(self):
        raise NotImplementedError

    def _generate_img_repr(self):
        raise NotImplementedError

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if not isinstance(value, Status):
            self._status = get_status(value)
        else:
            self._status = value

    @property
    def last_updated(self):
        return self._last_updated

    @last_updated.setter
    def last_updated(self, value):
        self._last_updated = arrow.get(value)

    # Derived Properties
    @property
    def ident(self):
        return ident_transform(self.device, self.value, self.footprint)

    @property
    def ident_generic(self):
        return ident_transform(self.device, self.value, self.footprint,
                               generic=True)

    @property
    def is_wire(self):
        return fpiswire(self.device)

    @property
    def is_modlen(self):
        return fpismodlen(self.device)

    @property
    def img_repr_fname(self):
        return os.path.splitext(self.gname)[0] + '.png'

    @property
    def indicative_sourcing_info(self):
        if self._indicative_sourcing_info is None:
            self._indicative_sourcing_info = self.sourcing_info_qty(1)
        return self._indicative_sourcing_info

    def sourcing_info_qty(self, qty):
        # TODO Complete Migration
        try:
            from tendril.inventory.guidelines import electronics_qty
            from tendril.sourcing.electronics import get_sourcing_information
            from tendril.sourcing.electronics import SourcingException
        except ImportError:
            return []
        if fpiswire(self.device) and not isinstance(qty, Length):
            iqty = Length(qty)
        else:
            iqty = qty
        iqty = electronics_qty.get_compliant_qty(self.ident, iqty)
        try:
            vsi = get_sourcing_information(self.ident, iqty,
                                           allvendors=True)
        except SourcingException:
            vsi = []
        return vsi

    @property
    def datasheet_url(self):
        if self._datasheet is not None:
            return self._datasheet
        for source in self.indicative_sourcing_info:
            if source.vpart.datasheet is not None:
                return source.vpart.datasheet

    @property
    def manufacturer(self):
        if self._manufacturer is not None:
            return self._manufacturer
        for source in self.indicative_sourcing_info:
            if source.vpart.manufacturer is not None:
                return source.vpart.manufacturer

    @property
    def vendors(self):
        if self._vendors is not None:
            return self._vendors
        _vendors = []
        for source in self.indicative_sourcing_info:
            _vendors.append(source.vobj.name)
        self._vendors = list(set(_vendors))

    # Validation
    @property
    def sym_ok(self):
        # TODO Migrate to ValidatableBase
        return self._symbol_validate()

    def _symbol_validate(self):
        # TODO Migrate to ValidatableBase
        if self.device not in DEVICE_CLASSES:
            return False
        return True

    def _validate(self):
        pass

    # Status
    @property
    def is_virtual(self):
        if self.status == 'Virtual':
            return True
        return False

    @property
    def is_deprecated(self):
        if self.status == 'Deprecated':
            return True
        return False

    @property
    def is_experimental(self):
        if self.status == 'Experimental':
            return True
        return False

    @is_virtual.setter
    def is_virtual(self, value):
        if self.status == 'Generator':
            if value is True:
                self.status = 'Virtual'
        else:
            raise AttributeError

    # Generator
    @property
    def is_generator(self):
        if self.status == 'Generator':
            return True
        return False

    @property
    def gname(self):
        raise NotImplementedError

    @property
    def gpath(self):
        raise NotImplementedError

    @property
    def genident(self):
        return os.path.splitext(self.gname)[0] + '.gen'

    @property
    def genpath(self):
        if self.is_generator:
            return os.path.splitext(self.gpath)[0] + '.gen.yaml'
        else:
            raise AttributeError

    @property
    def generator(self):
        if not self.is_generator:
            raise AttributeError
        return self._gen_class(self.genpath)

    @property
    def idents(self):
        if not self.is_generator:
            raise AttributeError
        if not self.generator.values:
            return None
        return [ident_transform(self.device, v, self.footprint)
                for v in self.generator.values]

    def __repr__(self):
        return '{0:40}'.format(self.ident)
