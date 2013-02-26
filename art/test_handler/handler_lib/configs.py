#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

"""
A module containing functionality for validation of configuration
"""
import os
import logging
import collections
from copy import copy
from utilities.validation_lib import ValidationFuncs, ConfigValidator,\
        ConfigLoader
from configobj import ConfigObj, flatten_errors, get_extra_values,\
                      ConfigObjError
from validate import Validator, ValidateError, VdtTypeError
from art.test_handler import find_config_file
import art

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    '''
    Raised when validation action failed
    '''
    pass


class ARTValidationFuncs(ValidationFuncs):

    def __init__(self):
        super(ARTValidationFuncs, self).__init__()
        self._basePath = os.path.dirname(art.__file__)

        # init of validation functions stuff
        self['path_to_config'] = self.checkConfigFilePath
        self['path_exists'] = self.checkIfPathExists

    def findConfigFile(self, path):
        return find_config_file(path)

    def checkConfigFilePath(self, value):
        if not value:
            raise ValidateError("Empty value for config file")
        try:
            path = self.findConfigFile(value)
        except IOError as ex:
            raise ValidateError(str(ex))
        else:
            return path

    def checkIfPathExists(self, value):
        path = value
        try:
            if not value:
                raise ValidateError("Empty value")
            if not value.startswith(os.sep):
                # case with relative path
                path = os.path.join(os.getcwd(), value)
                if not os.path.exists(path):  # check working dir
                    path = os.sep.join([self._basePath, value])

            if not os.path.exists(path):
                raise ValidateError("File  %s doesn't exist" % value)
        except TypeError:
            raise VdtTypeError("%s is not string" % value)

        return path


class ARTConfigValidator(ConfigValidator):
    _parameters = 'PARAMETERS'
    _test_conf_spec = 'test_conf_specs'

    def __init__(self, conf, spec, plmngmnt):
        funcs = ARTValidationFuncs()
        super(ARTConfigValidator, self).__init__(conf, spec, funcs,
                True)
        self.funcs['section_exists'] = self.checkSectionExistence
        self.plmngmnt = plmngmnt

    def prepareSpec(self):
        spec = super(ARTConfigValidator, self).prepareSpec()
        self.__loadSpecFromPlugins(spec)
        self.__loadSpecFromFiles(spec)
        return spec

    def __loadSpecFromPlugins(self, spec):
        for entry in self.plmngmnt.conf_validators:
            plspec = ConfigObj(_inspec=True, list_values=False)
            entry.config_spec(plspec, self.funcs)
            spec.merge(plspec)

    def __loadSpecFromFiles(self, spec):
        conf = self.prepareConf()
        if self._parameters not in conf:
            return
        parameters = conf[self._parameters]
        if self._test_conf_spec not in parameters:
            return

        for filename in parameters.as_list(self._test_conf_spec):
            filename = self.funcs.findConfigFile(filename)
            custom_spec = ConfigLoader(filename, _inspec=True,
                    raise_errors=True).load()
            spec.merge(custom_spec)

    def checkSectionExistence(self, value, section):
        if section in self.conf:
            return True
        raise ValidateError("Section %s doesn't exist in config file"\
                            % section)
