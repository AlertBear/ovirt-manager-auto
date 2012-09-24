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
A module containing the functions for validation of configuration
"""
import os
import subprocess
import logging
import sys
from copy import copy
from socket import getaddrinfo, gaierror
from urlparse import urlsplit
from configobj import ConfigObj, flatten_errors, get_extra_values,\
                      ConfigObjError
from validate import Validator, ValidateError, VdtTypeError


# conf file parameters names
RUN = 'RUN'
VALIDATE = 'validate'
PARAMETERS = 'PARAMETERS'
TEST_CONF_SPEC = 'test_conf_specs'
FINE_PRINT_HEADER = "#" * 80
ART_DIR = 'art'

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    '''
    Raised when validation action failed
    '''
    pass


class ParamsValidator(object):

    def __init__(self, confFile, confSpecFile, funcsDict=None):
        self.valFuncsDict = {'domain_format': self.checkDomainFormat,
                            'path_exists': self.checkIfPathExists,
                            'is_alive': self.checkHostIsAlive,
                            'is_url_alive': self.checkURLIfAlive,
                            'python_module': self.checkPythonModule,
                            'section_exists': self.checkSectionExistence}
        self._config = None
        self._confFile = confFile
        self._confSpecFile = confSpecFile
        self._extraParameters = None
        self._extra_values_keys = None
        self._basePath = os.sep.join([sys.path[0], ART_DIR])
        #updating validation functions dictionary
        if funcsDict is not None:
                self.valFuncsDict = funcsDict

        self.validateConfigFile(confSpecFile)
        self.validatedPluginConfig()
        self.printSkippedParameters()

    @property
    def valFuncsDict(self):
        return self._valFuncsDict

    @valFuncsDict.setter
    def valFuncsDict(self, funcsDict):
        if  not isinstance(funcsDict, dict):
            raise ValidationError("validation functions dictionary '%s' "
                                   "is not a dictionary" % funcsDict)

        for key, val in funcsDict.iteritems():
            if not hasattr(val, '__call__'):
                raise ValidationError("validation function '%s' for key '%s' "
                                      "is not function" % (val, key))
        if not hasattr(self, '_valFuncsDict'):
            self._valFuncsDict = {}

        self._valFuncsDict.update(funcsDict)

    def printSkippedParameters(self):
        # printing parameters that were not validated
        logger.info(FINE_PRINT_HEADER)
        logger.info("These parameters were skipped in validation of %s:",
                    self._confFile)
        logger.info(FINE_PRINT_HEADER)
        for sections, name in self._extraParameters:
            # this code gets the extra values themselves
            the_section = self._config
            for section in sections:
                the_section = the_section[section]

            # the_value may be a section or a value
            the_value = the_section[name]

            section_or_value = 'value'
            if isinstance(the_value, dict):
                # Sections are subclasses of dict
                section_or_value = 'section'

            section_string = ', '.join(sections) or "top level"
            logger.info('Skipped parameter in section: %s. parameter %r is'
                        ' a %s', section_string, name, section_or_value)

    def editExtraVal(self, newExtraParameters, newExtraValuesKeys):
        candidate = []
        tmpExtraVal = copy(self._extraParameters)
        #looking for all root keys that doesn't appear in newExtraValuesKeys
        # - it means that they are validated there (fully or partially)
        for val in self._extra_values_keys:
            if val not in newExtraValuesKeys:
                candidate.append((val,))
                # updating
                if ((), val) in tmpExtraVal:
                    tmpExtraVal.remove(((), val))

        #looking for all partially validated sections in newExtraParameters
        for sect, val in newExtraParameters:
            if sect in candidate:
                if (sect, val) not in self._extraParameters:
                    tmpExtraVal.append((sect, val))

        self._extraParameters = copy(tmpExtraVal)

    def _validateHelper(self, confSpecFile, funcsDict=None):
        try:
            self._config = ConfigObj(self._confFile, configspec=confSpecFile,
                                     raise_errors=True)
        except ConfigObjError, msg:
            raise ValidationError("Parsing of %s failed"\
                                  " with error:\n'%s'" % (self._confFile, msg))

        # in case that customized funcsDict for this
        # function run should be used
        if funcsDict == None:
            validator = Validator(self.valFuncsDict)
        else:
            validator = Validator(funcsDict)

        result = self._config.validate(validator, preserve_errors=True,
                                       copy=True)

        if result == True:
            # first time
            if not self._extraParameters and not self._extra_values_keys:
                self._extraParameters = get_extra_values(self._config)
                self._extra_values_keys = self._config.extra_values
            else:
                newExtraParameters = get_extra_values(self._config)
                newExtraValuesKeys = self._config.extra_values
                self.editExtraVal(newExtraParameters, newExtraValuesKeys)
            self._config.write()

        else:
            logger.error('Config file validation failed!')
            for (section_list, key, err) in flatten_errors(self._config,
                                                           result):
                if key is not None:
                    logger.error('The "%s" key in the section "%s" failed '\
                          'validation with this error message %s' % (key,
                                     ', '.join(section_list), err))
                else:
                    logger.error('The following section was missing:%s' %\
                                 ', '.join(section_list))

            raise ValidationError('Validation  of %s with %s failed' %\
                                   (self._confFile, confSpecFile))

    def validateConfigFile(self, confSpecFile):
        self._validateHelper(confSpecFile)
        testConfSpecs = self._config[PARAMETERS][TEST_CONF_SPEC]
        for spec in testConfSpecs:
            # case with absolute path
            if spec.startswith(os.sep):
                tmpVal = spec
            # case with relative path
            else:
                tmpVal = os.sep.join([self._basePath, spec])

            self._validateHelper(tmpVal)

    def validatedPluginConfig(self):
        from art.test_handler.settings import initPlmanager

        plmng = initPlmanager()
        for entry in plmng.conf_validators:
            custom_funcs = copy(self.valFuncsDict)
            spec = ConfigObj(_inspec=True, list_values=False)
            entry.config_spec(spec, custom_funcs)
            self._validateHelper(spec, custom_funcs)

    """
    Extension of validation functions for validator module
    """
    def checkDomainFormat(self, value):
        if value == 'internal':
            return value
        try:
            getaddrinfo(value, None)
        except gaierror:
            raise ValidateError("Domain %s doesn't exist" % value)

        return value

    def checkHostIsAlive(self, value):
        if subprocess.call("ping -c 5 %s > /dev/null" % value, shell=True):
            raise ValidateError("Host %s is not accessible" % value)

        return value

    def checkURLIfAlive(self, value):
        res = urlsplit(value)
        self.checkHostIsAlive(res.netloc)

        return value

    def checkIfPathExists(self, value):
        try:
            if not value:
                raise ValidateError("Empty value")
            # case with absolute path
            if value.startswith(os.sep):
                tmpVal = value
            # case with relative path
            else:
                tmpVal = os.sep.join([self._basePath, value])

            if not os.path.exists(tmpVal):
                raise ValidateError("File  %s doesn't exist" % value)
        except TypeError:
            raise VdtTypeError("%s is not string" % value)

        return value

    def checkPythonModule(self, value):
        try:
            __import__(value)
        except ValueError:
            raise ValidateError("Empty value")
        except TypeError:
            raise ValidateError("Incorrect type of value: '%s'" % value)
        except ImportError:
            raise ValidateError("%s is not Python module" % value)

        return value

    def checkSectionExistence(self, value, section):
        if section in self._config:
            return True
        else:
            raise ValidateError("Section %s doesn't exist in config file"\
                                % section)
