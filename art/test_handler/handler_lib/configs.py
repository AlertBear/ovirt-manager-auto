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
from utilities.validation_lib import ValidationFuncs
from configobj import ConfigObj, flatten_errors, get_extra_values,\
                      ConfigObjError
from validate import Validator, ValidateError, VdtTypeError

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    '''
    Raised when validation action failed
    '''
    pass


class ParamsValidator(ValidationFuncs):

    _parameters = 'PARAMETERS'
    _testConfSpec = 'test_conf_specs'
    _finePrintHeader = "#" * 80

    def __init__(self, confFile, confSpecFile, frameworkBasePath,
                 findConfigFileFunc, pluginManagerHandle=None):
        self._findConfigFile = findConfigFileFunc
        self._config = None
        self._confFile = confFile
        self._basePath = frameworkBasePath
        # init of validation functions stuff
        super(ParamsValidator, self).__init__()
        self.valFuncsDict = self.funcsDict
        self.valFuncsDict = {
                             'path_to_config': self.checkConfigFilePath,
                             'section_exists': self.checkSectionExistence,
                             'path_exists': self.checkIfPathExists,
                            }
        # preparing global spec file
        self._prepareSpecFile()
        self.prepareValidationOfConfigFile(confSpecFile)
        if pluginManagerHandle:
            self.prepareValidationOfPluginConfig(pluginManagerHandle)

        #writing global spec file
        self._globalConfSpec.write()
        logger.info("Global spec file: %s", self._globalConfSpecFileName)
        # cleaning global spec file (otherwise it will be
        # difficult to write specs)
        self._cleanGlobalSpecFile()
        self.validateConfiguration()

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

    def _prepareSpecFile(self):
        self._globalConfSpec = ConfigObj()
        self._globalConfSpecFileName = "%s.spec" %\
                                        self._confFile.rsplit('.', 1)[0]
        self._globalConfSpec.filename = self._globalConfSpecFileName

    def _cleanGlobalSpecFile(self):
        editedData = []
        with open(self._globalConfSpec.filename) as f:
            data = f.readlines()
            for line in data:
                if not line.startswith('['):
                    key, value = line.split('=', 1)
                    #looking for first "
                    funcStart = value.find("(")
                    candidate = value.find('"')
                    if candidate != -1 and candidate < funcStart:
                        editedValue = ''.join([value[:candidate],
                                               value[(candidate + 1): -2],
                                               value[-1]])
                        line = "%s=%s" % (key, editedValue)
                editedData.append(line)
        with open(self._globalConfSpec.filename, 'w') as f:
            f.writelines(editedData)

    def validateConfiguration(self):
        self._config = ConfigObj(self._confFile,
                                 configspec=self._globalConfSpec.filename,
                                 raise_errors=True)
        validator = Validator(self.valFuncsDict)
        result = self._config.validate(validator, preserve_errors=True,
                                       copy=True)

        if result == True:
            self._config.write()
            #printing parameters that were not validated
            logger.info(self._finePrintHeader)
            logger.info("These parameters were skipped in validation of %s:",
                        self._confFile)
            logger.info(self._finePrintHeader)
            for sections, name in get_extra_values(self._config):
                # this code gets the extra values themselves
                theSection = self._config
                for section in sections:
                    theSection = theSection[section]

                # the_value may be a section or a value
                theValue = theSection[name]

                sectionOrValue = 'value'
                if isinstance(theValue, dict):
                    # Sections are subclasses of dict
                    sectionOrValue = 'section'

                sectionString = '.'.join(sections) or "Top Level"
                if sectionOrValue == 'section':
                    if sectionString == "Top Level":
                        logger.info("%s section %s wasn't validated",
                                sectionString, name)
                    else:
                        logger.info("Section %s.%s wasn't validated",
                                sectionString, name)
                else:
                    logger.info("Value %s.%s wasn't validated",
                                sectionString, name)
            logger.info(self._finePrintHeader)
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
                            (self._confFile, self._globalConfSpec.filename))

    def _validateHelper(self, confSpecFile, funcsDict=None):
        try:
            self._config = ConfigObj(self._confFile, configspec=confSpecFile,
                                     raise_errors=True)
        except ConfigObjError, msg:
            raise ValidationError("Parsing of %s failed"\
                                  " with error:\n'%s'" % (self._confFile, msg))

        #updating spec files
        if isinstance(confSpecFile, ConfigObj):
            self._globalConfSpec = update(self._globalConfSpec,
                                               confSpecFile)
        else:
            specObj = ConfigObj(confSpecFile, _inspec=True, list_values=False)
            self._globalConfSpec = update(self._globalConfSpec, specObj)

        # updating funcDict with custom functions
        if funcsDict != None:
            self.valFuncsDict = funcsDict

    def prepareValidationOfConfigFile(self, confSpecFile):
        confSpecFile = self.checkConfigFilePath(confSpecFile)
        self._validateHelper(confSpecFile)
        # the only parameter that should be conf file is
        # PARAMETERS.tests_conf_spec
        if self._parameters in self._config and (self._testConfSpec in\
                                           self._config[self._parameters]):
            testConfSpecs = self._config[self._parameters].as_list(\
                                                           self._testConfSpec)
            for spec in testConfSpecs:
                if len(spec):
                    tmpVal = self.checkConfigFilePath(spec)
                    self._validateHelper(tmpVal)

    def prepareValidationOfPluginConfig(self, pluginManagerHandle):
        """
        This method uses pluginManager that has conf_validators interface
        """
        for entry in pluginManagerHandle.conf_validators:
            custom_funcs = copy(self.valFuncsDict)
            spec = ConfigObj(_inspec=True, list_values=False)
            entry.config_spec(spec, custom_funcs)
            self._validateHelper(spec, custom_funcs)

    """
    ART specific validation functions
    """
    def checkConfigFilePath(self, value):
        if not value:
            raise ValidateError("Empty value for config file")
        try:
            path = self._findConfigFile(value)
        except IOError as ex:
            raise ValidateError(str(ex))
        else:
            return path

    def checkSectionExistence(self, value, section):
        if section in self._config:
            return True
        else:
            raise ValidateError("Section %s doesn't exist in config file"\
                                % section)

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


def update(dictToUpdate, newDict):
        """
        recursive update method for dictionary that really
        updates and not erases old fields
        """
        for key, value in newDict.iteritems():
            if isinstance(value, collections.Mapping):
                updatedSubDict = update(dictToUpdate.get(key, {}), value)
                dictToUpdate[key] = updatedSubDict
            else:
                #don't update existing key (don't change already set key
                if key not in dictToUpdate:
                    dictToUpdate[key] = newDict[key]
        return dictToUpdate
