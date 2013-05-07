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
A module containing the functions for loading the configuration
and preparing the environment for the tests.
"""

import argparse
import sys
import os
import re
from time import strftime
from shutil import copyfile
from configobj import ConfigObj

from art.test_handler.handler_lib.configs import ARTConfigValidator, \
        ConfigLoader
from art.test_handler.plmanagement.manager import PluginManager
from art.test_handler import find_config_file

opts = {}
""" A options global for all REST tests. """
plmanager = None
RC_RANGE = [2, 9]


class ReturnCode:
    General, IO, Connection, CommandLine, Validation, Plugin, API =\
                                   range(RC_RANGE[0], RC_RANGE[1])


class CmdLineError(ValueError):
    '''
    Raised when there was something wrong with the command line arg.
    '''
    pass


def initPlmanager():
    global plmanager
    if plmanager is None:
        plmanager = PluginManager()
    return plmanager


def populateOptsFromArgv(argv):
    '''
    Populates the opts variable from the argv.

    Author: edolinin, jhenner
    Parameters:
       argv - the list of arguments (as sys.argv) to populate from
    Return: None
    '''

    opts['art_base_path'] = os.path.dirname(argv[0])
    parser = argparse.ArgumentParser(
        prog=argv[0],
        description='Execute the test specified by config file.'
    )

    parser.add_argument('--logdir', '-logdir',
                                default='/var/tmp',
                                help='path to the log directory (%(default)s)')
    parser.add_argument('--log', '-log',
    # log file will be generated when test_handler.reports.initializeLogger()
    # will be called in test suite runner
                                default=None,
                                help='path to the log files')
    parser.add_argument('--configFile', '-conf', required=True,
                                help='path to the config file',
                                dest='conf')
    parser.add_argument('--SpecFile', '-spec',
                                default='conf/specs/main.spec',
                                help='path to the main conf spec file',
                                dest='confSpec')
    parser.add_argument('--standalone', '-standalone', action='store_true',
                                help='run without opts dependencies')
    parser.add_argument('-D',   metavar='OPTION', action='append',
                                default=[],
                                help='modify the option in config',
                                dest='redefs')

    plmanager.configurables.add_options(parser)

    args = parser.parse_args(argv[1:])

    plmanager.configure.im_func.func_defaults = (args, \
            plmanager.configure.im_func.func_defaults[1])


    opts.update((k, v) for k, v in vars(args).iteritems() if k!='redefs')
    return args.redefs


def rewriteConfig(config, redefs):
    '''
    Rewrite values specified by redefs string.
    Parameters:
     * config - ConfigObject
     * redefs - iterable of strings specifying the config-space path to rewrite
                the value in. For example ["REST.type=rest"].
    '''
    for r in redefs:
        try:
            sectionPath, value = r.split('=', 1)
        except ValueError:
            raise CmdLineError, "Expected '=' sign somewhere in '%s'." % r
        sectionPath = sectionPath.split('.')
        redef(config, sectionPath[:-1], sectionPath[-1], value)


def redef(section, confspacePath, key, value):
    '''
    Set `value` to field specified by `key` on the `confspacePath`
    in the dict-like structure rooted in `section`.
    '''
    for sectionName in confspacePath:
        section.setdefault(sectionName, {})
        section = section.get(sectionName)
    section[key] = value.split(",") if value.find(",") != -1 else value


def readTestRunOpts(path, redefs):
    '''
    Description: Reads the config file on, updating opts
    with some options from the RUN section.

    Author: edolinin, jhenner
    Parameters:
       path - the path to the configuration file
    Return: configObj - an instance of ConfigObj.
    '''

    global opts

    if not os.path.exists(path):
        raise IOError("Configuration file doesn't exist: %s" % path)

    #preparing working copy of conf file
    confFileCopyName = "%s.copy" % path
    copyfile(path, confFileCopyName)

    config = ConfigObj(confFileCopyName)
    rewriteConfig(config, redefs)
    config.write()

    conf = ConfigLoader(find_config_file(confFileCopyName), raise_errors=True)
    spec = ConfigLoader(find_config_file(opts['confSpec']), raise_errors=True,
                        _inspec=True)
    validator = ARTConfigValidator(conf.load(), spec.load(), initPlmanager())

    config = validator()

    plmanager.configure.im_func.func_defaults = \
        (plmanager.configure.im_func.func_defaults[0], config)

    opts['headers'] = config.get('HTTP_HEADERS', {})

    # Populate opts from the RUN section.
    runSection = config['RUN']

    opts['elements_conf'] = ConfigObj(runSection['elements_conf'],
                                      raise_errors=True)

    opts['test_file_name'] = []
    opts['tests'] = runSection.as_list('tests_file')
    for ind, test in enumerate(opts['tests']):
        opts['test_file_name'].append(os.path.basename(test))

    buildTestsFilesMatrix(config, opts['test_file_name'])

    opts['in_parallel'] = runSection.get('in_parallel')
    opts['parallel_run'] = True if opts['in_parallel'] else False
    opts['parallel_configs'] = runSection.get('parallel_configs')
    opts['parallel_sections'] = runSection.get('parallel_sections')

    opts['engine'] = runSection['engine']
    opts['data_struct_mod'] = runSection['data_struct_mod']
    opts['media_type'] = runSection['media_type']
    opts['secure'] = runSection.as_bool('secure')
    opts['validate'] = runSection.as_bool('validate')

    reportSection = config['REPORT']
    opts['has_sub_tests'] = reportSection['has_sub_tests']

    opts['add_report_nodes'] = reportSection.get('add_report_nodes')

    opts['iteration'] = 0

    opts['debug'] = runSection['debug'] == "yes"

    # Populate opts from the REST section.
    restSection = config['REST_CONNECTION']
    opts['scheme'] = restSection['scheme']
    opts['host'] = restSection['host']
    opts['port'] = restSection['port']
    opts['entry_point'] = restSection['entry_point']
    opts['user'] = restSection['user']
    opts['user_domain'] = restSection['user_domain']
    opts['password'] = restSection['password']
    opts['urisuffix'] = ''
    opts['uri'] = '%(scheme)s://%(host)s:%(port)s/%(entry_point)'\
                      's%(urisuffix)s/' % opts

    # Populate opts from the CLI section.
    cliSection = config['CLI_CONNECTION']
    opts['cli_tool'] = cliSection['tool']
    opts['cli_log_file'] = cliSection['cli_log_file']
    opts['cli_optional_params'] = cliSection['optional_params']
    opts['validate_cli_command'] = cliSection['validate_cli_command']
    return config


def buildTestsFilesMatrix(config, testsList):
    '''
    Creates dictionary for each test that should be run
    and puts it at opts[test_name]

    Author: edolinin
    Parameters:
       * config - instance of ConfigObj
       * testsList - list of test files names
    Return: None
    '''

    for test in testsList:
        opts[test] = {}

        testSection = config['RUN']
        if config.has_key(test):
            testSection = config[test]

        opts[test]['in_parallel'] = testSection.get('in_parallel', [])

        if testSection.has_key('lines'):
            linesVal = testSection.as_list('lines')
            opts[test]['lines'] = parseLines(','.join(linesVal))

        if testSection.has_key('groups'):
            opts[test]['groups'] = testSection.as_list('groups')
