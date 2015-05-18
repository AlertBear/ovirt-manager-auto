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

import logging
from time import strftime
from configobj import ConfigObj
from art.test_handler.settings import opts
from art.core_api.apis_exceptions import APICommandError
from utilities.logger_utils import initialize_logger
from art.test_handler import find_config_file

ELEMENTS = 'conf/elements.conf'
LOGGER_ART_CONF = 'conf/logger_art.conf'


class TestRunnerWrapper():
    '''
    Runs APIs functions not from run.py and without settings.conf.
    Required settings options are defined in constructor.

    Usage Example:
        from art.core_api.external_api import TestRunnerWrapper
        from art.core_api.apis_exceptions import APICommandError
        wrapper = TestRunnerWrapper('10.10.10.10')
        try:
            status = wrapper.runCommand(\
                'art.rhevm_api.tests_lib.low_level.datacenters.addDataCenter',
                'true',name='test',storage_type='NFS',version='3.1')
        except APICommandError:
            pass #handle error
    '''

    def __init__(self, ip, **kwargs):
        '''
        Defines settings configuration required to run REST APIs functions
        Parameters:
        * ip - vdc ip
        * kwargs - dictionary with settings configurations, keys names are
        the same as in settings.conf, if omitted - defaults are set
        '''

        opts['host'] = ip
        opts['scheme'] = kwargs.get('scheme', 'https')
        opts['port'] = kwargs.get('port', '443')
        opts['entry_point'] = kwargs.get('entry_point', 'api')
        opts['user'] = kwargs.get('user', 'admin')
        opts['user_domain'] = kwargs.get('user_domain', 'internal')
        opts['password'] = kwargs.get('password', '123456')
        opts['engine'] = kwargs.get('engine', 'rest')
        opts['debug'] = kwargs.get('debug', True)
        opts['media_type'] = kwargs.get('media_type', 'application/xml')
        opts['headers'] = kwargs.get('headers', {})
        opts['elements_conf'] = ConfigObj(find_config_file(ELEMENTS),
                                          raise_errors=True)
        opts['validate'] = kwargs.get('validate', True)
        opts['secure'] = kwargs.get('secure', False)
        opts['data_struct_mod'] = kwargs.get(
            'data_struct_mod', 'art.rhevm_api.data_struct.data_structures')
        opts['log'] = kwargs.get('log', "/var/tmp/%s_tests_%s.log" %
                                 (opts['engine'], strftime('%Y%m%d_%H%M%S')))
        opts['urisuffix'] = ''
        opts['uri'] = '%(scheme)s://%(host)s:%(port)s/%(entry_point)s%(urisuffix)s/' \
            % opts

        opts['in_parallel'] = kwargs.get('in_parallel', [])
        opts['parallel_run'] = True if opts['in_parallel'] else False
        opts['standalone'] = kwargs.get('standalone', False)

        for arg in kwargs:
            if arg not in opts:
                opts[arg] = kwargs[arg]

        initialize_logger(conf_file=find_config_file(LOGGER_ART_CONF),
                          log_file=opts['log'])
        self.logger = logging.getLogger(__name__)
        if opts['debug']:
            self.logger.setLevel(logging.DEBUG)
        self.logger.info("Log file is initialized at %s", opts['log'])

    @classmethod
    def runCommand(cls, action, *args, **kwargs):
        '''
        Runs REST APIs functions

        Parameters:
        * action - full path of the action which should be run
        * args - list of function's non-keyword arguments
        * kwargs - dictionary with function's keyword arguments

        Exceptions: raises APICommandError in case of error

        '''

        actionModulesNames = action.split(".")
        funcPackage = ".".join(actionModulesNames[:-1])
        funcName = actionModulesNames[-1]

        exec("from " + funcPackage + " import " + funcName)

        params = ''
        for arg in args:
            params = "{0},{1!r}".format(params, arg)

        for paramName, paramVal in kwargs.items():
            params = "{0},{1}={2!r}".format(params, paramName, paramVal)
        cmd = funcName + "(" + params.strip(' ,') + ")"

        try:
            return eval(cmd)
        except Exception as e:
            raise APICommandError(cmd, e)
