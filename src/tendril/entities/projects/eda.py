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
Base Class for EDA Projects
===========================
"""


from tendril.schema.edaprojects import EDAProjectConfig
from .base import ProjectBase


class EDAProject(ProjectBase):
    _config_class = EDAProjectConfig

    @property
    def is_pcb(self):
        return self.config.is_pcb

    @property
    def is_cable(self):
        return self.config.is_cable
    
    @property
    def modules(self):
        return 
