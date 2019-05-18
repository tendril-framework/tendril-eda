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


import os
import inspect
import iec60063
from six import iteritems
from decimal import Decimal

from tendril.conventions import electronics
from tendril.conventions.series import CustomValueSeries

from tendril.schema.base import SchemaControlledYamlFile
from tendril.schema.base import NakedSchemaObject
from tendril.schema.helpers import SchemaObjectList
from tendril.schema.helpers import SchemaObjectSet

from tendril.utils.types.electromagnetic import Resistance
from tendril.utils.types.electromagnetic import Capacitance
from tendril.utils.types.electromagnetic import Voltage
from tendril.utils.types.thermodynamic import ThermalDissipation

from tendril.utils import log
logger = log.get_logger(__name__, log.INFO)

template_path = os.path.normpath(os.path.join(
    inspect.getfile(inspect.currentframe()),
    os.pardir, os.pardir, os.pardir,
    'schema', 'templates', 'EDASymbolGenerator.yaml')
)


class CompositeSeriesDefinition(NakedSchemaObject):
    def elements(self):
        e = super(CompositeSeriesDefinition, self).elements()
        e.update({
            'name': self._p(('name',), required=True),
            'desc': self._p(('desc',), required=True),
        })
        return e

    def __repr__(self):
        return "<CompositeSeriesDefinition {0} ({1})>" \
               "".format(self.name, self.desc)


class ResistorValueList(SchemaObjectList):
    _validator = staticmethod(electronics.parse_resistor)


class CapacitorValueList(SchemaObjectList):
    _validator = staticmethod(electronics.parse_capacitor)


class ValueGeneratorDefinition(NakedSchemaObject):
    _bounds_type = None
    _components = []
    _generator_dimensions = []
    _ostrs = None

    def elements(self):
        e = super(ValueGeneratorDefinition, self).elements()
        e.update({
            'std':    self._p('std',    options=['iec60063']),
            'series': self._p('series', options=iec60063.all_series),
            'start':  self._p('start'),
            'end':    self._p('end'),
        })
        for component in self._components:
            if component.code in self._generator_dimensions:
                continue
            e[component.code] = self._p(
                component.code, parser=component.typeclass,
                required=component.required
            )
        return e

    @property
    def components(self):
        rval = {}
        for component in self._components:
            if hasattr(self, component.code):
                rval[component.code] = getattr(self, component.code)
        return rval

    @property
    def values(self):
        if self.std == 'iec60063':
            return iec60063.gen_vals(self.series, self._ostrs,
                                     start=self.start, end=self.end)

    def __repr__(self):
        param_string = ','.join([
            '{0}:{1}'.format(k.code, getattr(self, k.code))
            for k in self._components
            if hasattr(self, k.code) and getattr(self, k.code)
        ])
        return "<{0} {1} {2} @{5} ({3}-{4})>" \
               "".format(self.__class__.__name__, self.std,
                         self.series, self.start, self.end,
                         param_string)


class ResistorValueGenerator(ValueGeneratorDefinition):
    _bounds_type = Resistance
    _components = electronics.jb_resistor_defs()
    _generator_dimensions = ['resistance']
    _ostrs = iec60063.res_ostrs


class CapacitorValueGenerator(ValueGeneratorDefinition):
    _bounds_type = Capacitance
    _components = electronics.jb_capacitor_defs()
    _generator_dimensions = ['capacitance']
    _ostrs = iec60063.cap_ostrs


class ResistorGeneratorList(SchemaObjectList):
    _objtype = ResistorValueGenerator


class CapacitorGeneratorList(SchemaObjectList):
    _objtype = CapacitorValueGenerator


class CustomSeriesDefinition(NakedSchemaObject):
    _components = []
    _generator_dimensions = []

    def elements(self):
        e = super(CustomSeriesDefinition, self).elements()
        e.update({
            'type': self._p(('detail', 'type'), options=['resistor', 'capacitor']),
            'desc': self._p(('detail', 'desc'),),
            'values': self._p(('values',)),
        })
        for component in self._components:
            if component.code in self._generator_dimensions:
                continue
            e[component.code] = self._p(
                ('detail', component.code),
                parser=component.typeclass, required=False
            )
        return e

    @property
    def partnames(self):
        return set(self.values.values())

    @property
    def typevalues(self):
        return self.values.keys()

    @property
    def components(self):
        rval = {}
        for component in self._components:
            if hasattr(self, component.code):
                rval[component.code] = getattr(self, component.code)
        return rval

    def __repr__(self):
        return "<{0} {1}>".format(self.__class__.__name__, self.desc)


class CustomResistorSeries(CustomSeriesDefinition):
    _components = electronics.jb_resistor_defs()
    _generator_dimensions = ['resistance']


class CustomCapacitorSeries(CompositeSeriesDefinition):
    _components = electronics.jb_capacitor_defs()
    _generator_dimensions = ['capacitance']


class CustomResistorSeriesSet(SchemaObjectSet):
    _objtype = CustomResistorSeries


class CustomCapacitorSeriesSet(SchemaObjectSet):
    _objtype = CustomCapacitorSeries


class EDASymbolGeneratorBase(SchemaControlledYamlFile):
    supports_schema_name = 'EDASymbolGenerator'
    supports_schema_version_max = Decimal('1.0')
    supports_schema_version_min = Decimal('1.0')
    template = template_path

    def __init__(self, genpath, *args, **kwargs):
        super(EDASymbolGeneratorBase, self).__init__(genpath, *args, **kwargs)
        self._process_specialized()

        self.composite_series = None
        self.values = []
        self.igen = []
        self.iseries = []

        self._get_data()

    def symbol_template(self):
        raise NotImplementedError

    def _stub_content(self):
        c = super(EDASymbolGeneratorBase, self)._stub_content()
        tsym = self.symbol_template()
        c.update({
            'value': tsym.value or '',
            'symbolfile': tsym.gname,
            'description': tsym.description or ''
        })
        return c

    def elements(self):
        e = super(EDASymbolGeneratorBase, self).elements()
        e.update({
            'type':              self._p('type', options=['simple', 'resistor', 'capacitor', 'wire']),
            'symbolfile':        self._p('symbolfile'),
            'desc':              self._p('desc',             required=False),
            '_composite_series': self._p('composite_series', required=False, parser=CompositeSeriesDefinition),
            '_values':           self._p('values',           required=False, parser=SchemaObjectList),
        })
        return e

    def _elements_simple(self):
        return {}

    def _elements_capacitor(self):
        return {
            'generators':    self._p('generators',    required=False, parser=CapacitorGeneratorList),
            'capacitances':  self._p('capacitances',  required=False, parser=CapacitorValueList),
            'stdvoltage':    self._p('stdvoltage',    required=False, parser=Voltage),
            'custom_series': self._p('custom_series', required=False, parser=CustomCapacitorSeriesSet),
        }

    def _elements_resistor(self):
        return {
            'generators':    self._p('generators',    required=False, parser=ResistorGeneratorList),
            'resistances':   self._p('resistances',   required=False, parser=ResistorValueList),
            'stdwattage':    self._p('stdwattage',    required=False, parser=ThermalDissipation),
            'custom_series': self._p('custom_series', required=False, parser=CustomResistorSeriesSet),
        }

    def _elements_wire(self):
        return {
            'gauges': self._p('gauges', required=True, parser=SchemaObjectList),
            'colors': self._p('colors', required=True, parser=SchemaObjectList)
        }

    def _process_specialized(self):
        elements = getattr(self, '_elements_{0}'.format(self.type))()
        for key, policy in iteritems(elements):
            self._process_element(key, policy)

    def _get_data_rc(self):
        if self.type == 'resistor':
            svattr = 'resistances'
            constructor = electronics.construct_resistor
        elif self.type == 'capacitor':
            svattr = 'capacitances'
            constructor = electronics.construct_capacitor
        else:
            raise Exception

        tsymbol = self.symbol_template()

        # Spwcifically defined and qualified part names
        if getattr(self, svattr):
            self.values.extend(getattr(self, svattr).content)

        # Composite of all standard (generator) series
        if self._composite_series is not None:
            self.composite_series = CustomValueSeries(
                self._composite_series.name, self.type,
                device=tsymbol.device, footprint=tsymbol.footprint
            )

        # Generator series
        if self.generators:
            for generator in self.generators:
                self.igen.append(generator)
                for val in generator.values:
                    pval = constructor(val, **generator.components)
                    self.values.append(pval)
                    if self.composite_series:
                        self.composite_series.add_value(val, pval)

        if self.composite_series:
            self.iseries.append(self.composite_series)

        # Custom series
        if self.custom_series:
            for name, series in iteritems(self.custom_series.content):
                assert series.type == self.type
                iseries = CustomValueSeries(
                    name, series.type,
                    device=tsymbol.device, footprint=tsymbol.footprint
                )
                iseries._desc = series.desc
                iseries._aparams = series.components
                for type_val, val in iteritems(series.values):
                    iseries.add_value(type_val, val)
                self.iseries.append(iseries)
                self.values.extend(series.partnames)

    def _get_data_wire(self):
        for gauge in self.gauges:
            for color in self.colors:
                self.values.append('{0} {1}'.format(gauge, color))

    def _get_data(self):
        self.values = []
        # Spwcifically defined and unqualified part names
        if hasattr(self, '_values') and self._values:
            self.values.extend(self._values.content)

        if self.type == 'simple':
            return
        elif self.type in ['resistor', 'capacitor']:
            self._get_data_rc()
        elif self.type == 'wire':
            self._get_data_wire()
        else:
            raise AttributeError('Unrecognized generator type : {0}'.format(self.type))
