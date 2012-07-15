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
from configobj import ConfigObj
import os
import re
from time import strftime
import socket
from test_handler.plmanagement.manager import PluginManager

opts = {}
""" A options global for all REST tests. """
plmanager = None


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

    junit_results_default = os.path.join(os.path.dirname(__file__),
                                         "../results/junit_results.xml")

    results_default = os.path.join(os.path.dirname(__file__),
                                   "../results/results.xml")

    results_default =  os.path.normpath(results_default)
    junit_results_default =  os.path.normpath(junit_results_default)


    parser = argparse.ArgumentParser(
        prog=argv[0],
        description='Execute the test specified by config file.'
    )

    parser.add_argument('--logdir', '-logdir',
                                default = '/var/tmp',
                                help='path to the log directory (%(default)s)')
    parser.add_argument('--log', '-log',
                                default = None,
                                help='path to the log files')
    parser.add_argument('--junitResultsFile', '-junit', metavar='JUNIT_XML_FILE',
                                default=junit_results_default,
                                help='path to the junit results file (%(default)s)',
                                dest='junit_results')
    parser.add_argument('--resultXmlFile', '-res', metavar='RESULTS_XML_FILE',
                                default=results_default,
                                help='path to the results file (%(default)s)',
                                dest='results')
    parser.add_argument('--lines', '-lines',
                                help='which lines from the test file should be executed')
    parser.add_argument('--groups', '-groups',
                                help='which groups from the test file should be executed')
    parser.add_argument('--compile', action='store_true',
                                help='which lines from the test file should be executed')
    parser.add_argument('--configFile', '-conf', required=True,
                                help='path to the config file',
                                dest='conf')
    parser.add_argument('--standalone', '-standalone', action='store_true',
                                help='run without rhevm dependencies')
    parser.add_argument('-D',   metavar='OPTION', action='append',
                                default=[],
                                help='modify the option in config',
                                dest='redefs')

    plmanager.configurables.add_options(parser)

    args = parser.parse_args(argv[1:])

    plmanager.configure.im_func.func_defaults = (args, \
            plmanager.configure.im_func.func_defaults[1])

    if args.groups:
        args.groups = args.groups.split(',')
    if args.lines:
        args.lines = parseLines(args.lines)

    opts.update((k, v) for k, v in vars(args).iteritems() if k!='redefs')
    return args.redefs


def parseLines(arg):
    '''
    Converts lines numbers from user format to list of rows
    Author: edolinin, jhenner
    Parameters:
    * arg - value for lines numbers supplied by the user
    Return: list of rows numbers that should be run
    '''

    lines = []
    for part in arg.split(','):
        m = re.match('^((\d+)-(\d+))|(\d+)$', part)
        if m:
            if m.group(1):
                # We got some interval.
                startRange = int(m.group(2))
                endRange = int(m.group(3))
            else:
                # We got singleton number.
                startRange  = endRange = int(m.group(4))
            lines.extend(range(startRange, endRange + 1)) # include the range end.
        else:
            raise CmdLineError(
                    "The '%s' bit of the lines to run is malformed." % part
            )
    return lines


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
    Set `value` to field specified by `key` on the `confspacePath` in the dict-like
    structure rooted in `section`.
    '''
    for sectionName in confspacePath:
        section = section.get(sectionName, None)
        if section is None:
            raise CmdLineError, 'Section %s not found in the config.' % section
    section[key] = value.split(",") if value.find(",")!=-1 else value


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

    config = ConfigObj(path)
    rewriteConfig(config, redefs)

    plmanager.configure.im_func.func_defaults = \
            (plmanager.configure.im_func.func_defaults[0], config)

    opts['headers'] = config.get('HTTP_HEADERS', {})

    # Populate opts from the RUN section.
    runSection = config['RUN']

    opts['test_file_name'] = []
    opts['tests'] = runSection.as_list('tests_file')
    for ind, test in enumerate(opts['tests']):
        opts['test_file_name'].append(os.path.basename(test))

    buildTestsFilesMatrix(config, opts['test_file_name'])

    opts['in_parallel'] = runSection.get('in_parallel', [])
    opts['parallel_run'] = True if opts['in_parallel'] else False
    opts['parallel_configs'] = runSection.get('parallel_configs', [])
    opts['parallel_sections'] = runSection.get('parallel_sections', [])

    opts['engine'] = runSection['engine']
    opts['data_struct_mod'] = runSection['data_struct_mod']
    opts['media_type'] = runSection['media_type']

    try:
        __import__(opts['data_struct_mod'])
    except ImportError as exc:
        raise ImportError("Can't import 'data_struct_mod': {0}".format(exc))

    opts['api_xsd'] = runSection['api_xsd']

    if not opts['log']:
        timestamp = strftime('%Y%m%d_%H%M%S')
        opts['log'] = "%s/%sTests%s.log" % (opts['logdir'], opts['engine'], timestamp)

    reportSection = config['REPORT']
    opts['has_sub_tests'] = reportSection['has_sub_tests']

    opts['add_report_nodes'] = reportSection.get('add_report_nodes', 'no')

    opts['iteration'] = 0

    opts['debug'] = runSection['debug'] == "yes"

    # Populate opts from the REST section.
    restSection = config['REST_CONNECTION']
    opts['scheme'] = restSection['scheme']
    opts['host'] = restSection['host']
    if opts['host'] == 'localhost':
        opts['host'] = socket.gethostname()

    opts['port'] = restSection['port']
    opts['entry_point'] = restSection['entry_point']
    opts['user'] = restSection['user']
    opts['user_domain'] = restSection['user_domain']
    opts['password'] = restSection['password']
    opts['urisuffix'] = ''
    opts['uri'] = '%(scheme)s://%(host)s:%(port)s/%(entry_point)s%(urisuffix)s/' \
            % opts

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

