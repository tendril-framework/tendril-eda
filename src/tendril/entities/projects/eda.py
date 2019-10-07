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

"""
EDA Project Configuration Schema
--------------------------------
"""

from decimal import Decimal

from tendril.validation.base import ValidationError
from tendril.validation.configs import ConfigOptionPolicy
from tendril.conventions.status import Status

from tendril.schema.base import NakedSchemaObject
from tendril.entities.projects.config import ProjectConfig


class IndicativePCBOrderSpec(NakedSchemaObject):
    def elements(self):
        e = super(IndicativePCBOrderSpec, self).elements()
        e.update({
            'qty':   self._p('qty',   required=True, parser=int),
            'dterm': self._p('dterm', required=True, parser=int),
        })
        return e


class PCBSpec(NakedSchemaObject):
    _finishes = {
        'Au': "Immersion Gold/ENIG finish",
        'Sn': "Immersion Tin finish",
        'PBFREE': "Any Lead Free finish",
        'H': "Lead Free HAL finish",
        'NP': "No Copper finish",
        'I': "OSP finish",
        'OC': "Only Copper finish",
    }

    _stackup = {
        2: "Double Layer",
        4: 'ML4',
    }

    def elements(self):
        e = super(PCBSpec, self).elements()
        e.update({
            'pcbname': self._p('pcbname', required=True),
            '_layers': self._p('layers',  required=True, parser=int),
            'dX':      self._p('dX',      required=True, parser=Decimal),
            'dY':      self._p('dY',      required=True, parser=Decimal),
            '_finish': self._p('finish',  required=True,
                               options=self._finishes.keys()),
        })
        return e

    @property
    def layers(self):
        return self._stackup[self._layers]

    @property
    def finish(self):
        return self._finishes[self._finish]

    @property
    def descriptors(self):
        return [
            "{0:.1f} mm x {1:.1f} mm".format(self.dX, self.dY),
            self.layers, self.finish
        ]


class PCBDetails(NakedSchemaObject):
    def elements(self):
        e = super(PCBDetails, self).elements()
        e.update({
            '_status': self._p('status', required=True),
            'params': self._p('params', required=True, parser=PCBSpec),
            'indicativepricing': self._p('indicativepricing', required=False,
                                         parser=IndicativePCBOrderSpec,
                                         default={'qty': 3, 'dterm': 10})
        })
        return e

    @property
    def status(self):
        return Status(self._status.rstrip('!'))

    @property
    def status_forced(self):
        return self._status.startswith('!')


class EDAProjectConfig(ProjectConfig):
    supports_schema_name = 'EDAProjectConfig'
    supports_schema_version_max = Decimal('1.0')
    supports_schema_version_min = Decimal('1.0')

    def elements(self):
        e = super(EDAProjectConfig, self).elements()
        e.update({
            'pcbdetails': self._p('pcbdetails', required=False,
                                  default={}, parser=PCBDetails),
            'mactype': self._p('mactype', required=False, default=''),
            'pcbname': self._p('pcbname', required=False, default=''),
            'cblname': self._p('cblname', required=False, default=''),
        })
        return e

    @property
    def schfolder(self):
        return self.basefolder

    @property
    def _pcb_allowed(self):
        return True

    @property
    def projectname(self):
        if self.pcbname:
            return self.pcbname
        else:
            return self.cblname

    @property
    def is_pcb(self):
        if self._pcb_allowed and self.pcbname:
            return True
        else:
            return False

    @property
    def is_cable(self):
        if self.cblname:
            return True
        else:
            return False

    @property
    def pcbdescriptors(self):
        return self.pcbdetails.params.descriptors

    def validate(self):
        super(EDAProjectConfig, self).validate()
        if not self._pcb_allowed and self.pcbname is not None:
            e = ValidationError(
                ConfigOptionPolicy(self._validation_context, 'pcbname',
                                   is_error=True)
            )
            e.detail = "pcbname defined, but PCB is not supported " \
                       "for this project."
            self._validation_errors.add(e)

    @property
    def status(self):
        return self.pcbdetails.status

    @property
    def status_forced(self):
        return self.pcbdetails.status_forced
