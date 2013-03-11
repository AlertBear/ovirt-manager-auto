#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Red Hat, Inc.
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
from art.test_handler.settings import opts
from lxml.etree import Element, ElementTree, PI
from lxml.builder import E
import threading
import os
from sys import stderr
from lockfile import FileLock
from abc import ABCMeta, abstractmethod
import datetime
from dateutil import tz
from time import strftime


COLORS = {
    'ERROR': 31,
    'WARNING': 33,
    'INFO': 32,
    'DEBUG': 34,
}


FMT = '%(asctime)s - %(threadName)s - %(name)s - ' \
      '$COL_LVL%(levelname)s$COL_RST - %(message)s'

JUNIT_NOFRAMES_STYLESHEET = "junit-noframes.xsl"


def colorize_fmt(fmt, colours):
    for placeholder, colour in colours.iteritems():
        fmt = fmt.replace(placeholder, colour)
    return fmt


class ColoredFormatter(logging.Formatter):
    '''
    Colorizes the logging records by their level and content.
    '''
    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg)
        self.useColor = use_color
        self.colors = {'$COL_LVL': '', '$COL_RST': ''}

    def format(self, record):
        if self.useColor:
            self.colors['$COL_LVL'] = '\033[%d;1m' \
                    % COLORS.get(record.levelname, 35)
            self.colors['$COL_RST'] = '\033[0m'
        else:
            self.colors['$COL_LVL'] = '\033[%dm' \
                    % COLORS.get(record.levelname, 35)
            self.colors['$COL_RST'] = '\033[0m'

        self._fmt = colorize_fmt(FMT, self.colors)
        return logging.Formatter.format(self, record)


def initializeLogger():
    '''
    Initialize logger so that it spits output to file and stderr. Colorize only
    the messages going to tty through stderr to not cause mess in the files.
    Author: jhenner
    '''

    logLevel = logging.INFO

    # Prepare empty colours for the colour placeholders for messages going to
    # file.
    bw_colours = {'$COL_LVL': '', '$COL_RST': ''}
    bw_fmt = colorize_fmt(FMT, bw_colours)

    if not opts['log']:
        timestamp = strftime('%Y%m%d_%H%M%S')
        opts['log'] = "%s/%sTests.log" % (opts['logdir'], timestamp)

    logging.basicConfig(level=logLevel, filemode='w', format=bw_fmt,
                        filename=opts['log'])

    # Prepare handler and formatter for stderr outputs.
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(ColoredFormatter(FMT, stderr.isatty()))
    logging.getLogger().addHandler(sh)


def create_results_dir_path(path):
    path = os.path.dirname(os.path.abspath(path))
    if not os.path.lexists(path):
        os.makedirs(path)


class ResultsReporter(object):
    __metaclass__ = ABCMeta

    def __init__(self, suite_name, suite_type, path):
        '''
        Parameters:
         * suite_name - Name of the test suite.
         * suite_type - The default type of test suite.
         * path      - Path to the xml file.
        '''

        self.suite_name = suite_name
        self.suite_type = suite_type
        self.path = path
        self.log_path = None
        self.test_path = None
        create_results_dir_path(self.path)
        self.reporting_lock = threading.Lock()
        self.file_lock = FileLock(path)
        self.tree = None

    @abstractmethod
    def set_log_path(self, log_path):
        ''' Set path to the log file to be reported in root node of the xml.'''

    @abstractmethod
    def set_test_path(self, test_path):
        ''' Set path to test file to be reported in root node of the xml.'''

    @abstractmethod
    def init_report(self, test_path, log_path):
        '''
        Set the test_path and log_path. This method is there mainly to overcome
        problems with sharing the test reporters between several TestRunners.
        '''

    def _commit(self):
        self.tree.write(self.path, encoding="utf-8",
                        pretty_print=True, xml_declaration=True)

    @abstractmethod
    def add_test_report(self, mod_path, func_name, **kwargs):
        '''
        Add the nodes of the test case report. This method should be threadsafe.
        '''
        pass


def total_seconds(td):
    ''' For Py2.7 compatibility. There is no function in Py2.6 computing this. '''
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10.**6


class DefaultResultsReporter(ResultsReporter):
    '''
    Saves the test result to xml file.
    Author: jhenner
    '''

    TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    ''' Time format used in the reports. '''

    def __init__(self, suite_name, suite_type, path):
        '''
        Parameters:
         * suite_type - Name of root of the xml documment. You would probably
                       want to use "rest" here.
         * path      - Path to the xml file.
        '''
        assert suite_name is not None
        assert suite_type is not None
        assert path
        ResultsReporter.__init__(self, suite_name, suite_type, path)
        self.root = Element(self.suite_type)
        self.tree = ElementTree(self.root)

    def init_report(self, test_path, log_path):
        self.set_log_path(log_path)
        self.set_test_path(test_path)
        self._commit()

    def set_test_path(self, test_path):
        self.root.attrib['testfile'] = test_path

    def set_log_path(self, log_path):
        self.root.attrib['logfile'] = log_path

    def add_test_report(self, mod_path, func_name, **kwargs):
        # For explanation why this threading.lock is used here, see
        # https://trac.qa.lab.tlv.redhat.com/trac/automation/ticket/739#comment:5
        #
        # Also note that mangling the DOM also probably should be protected with lock.
        with self.reporting_lock:
            with self.file_lock: # lock results file while reporting
                module = Element(kwargs['module_name']) \
                            if kwargs['module_name'] \
                            else Element('test')
                if kwargs.has_key('group_desc'):
                    module.set('description', kwargs['group_desc'])
                    del kwargs['group_desc']

                # Convet times to machine-local timezone and write it.
                local_tz = tz.tzlocal()
                s_time = kwargs['start_time'].astimezone(local_tz)
                e_time = kwargs['end_time'].astimezone(local_tz)
                module.append(E.start_time(s_time.strftime(self.TIME_FORMAT)))
                module.append(E.end_time(e_time.strftime(self.TIME_FORMAT)))

                # Delete what we wrote already.
                del kwargs['start_time']
                del kwargs['end_time']
                del kwargs['module_name']

                # Write the remaining fields.
                for key in kwargs:
                    element = Element(key)
                    element.text = kwargs[key]
                    module.append(element)

                self.root.append(module)
                self._commit()


class JUnitResultsReporter(ResultsReporter):
    '''
    Saves the test result to jUnit report xml file.
    Author: jhenner
    '''
    def __init__(self, suite_name, suite_type, path):
        ResultsReporter.__init__(self, suite_name, suite_type, path)
        self.suite_start = datetime.datetime.now(tz.tzutc())
        timestamp = self.suite_start.replace(microsecond=0).isoformat()

        self.testsuites = E.testsuites()
        XSLT = PI('xml-stylesheet',
                text='type="text/xsl" href="%s"'
                % JUNIT_NOFRAMES_STYLESHEET)
        self.testsuites.addprevious(XSLT)
        self.testsuite = E.testsuite(name=str(suite_name),
                                     timestamp=timestamp)
        self.testsuites.append(self.testsuite)

        self.testsuite_props = E.properties()
        self.testsuite.append(self.testsuite_props)

        self.failures = self.errors = self.tests = 0
        self.update_testsuite_attrs()
        self.tree = ElementTree(self.testsuites)
        self.testsuites.addprevious(XSLT)

    def set_test_path(self, test_path):
        ''' Appends the test_sheet_path property to the testsutie properties. '''
        assert not self.testsuite_props.xpath('property[name="test_sheet_path"]')
        self.testsuite_props.append(E.property(name='test_sheet_path',
                                               value=str(test_path)))

    def set_log_path(self, log_path):
        ''' Appends the log_path property to the testsutie properties. '''
        assert not self.testsuite_props.xpath('property[name="log_path"]')
        self.testsuite_props.append(E.property(name='log_path',
                                               value=str(log_path)))

    def init_report(self, test_path, log_path):
        self.set_log_path(log_path)
        self.set_test_path(test_path)

    def add_test_report(self, mod_path, func_name, **kwargs):
        '''
        Add the nodes of the test case report. This method should be threadsafe.
        '''

        # For explanation why this threading.lock is used here, see
        # https://trac.qa.lab.tlv.redhat.com/trac/automation/ticket/739#comment:5
        #
        # Also note that mangling the DOM also probably should be protected with lock.
        with self.reporting_lock:
            with self.file_lock: # lock results file while reporting
                time_delta = kwargs['end_time'] - kwargs['start_time']
                test_name = '{0}({1[test_parameters]})'.format(
                                func_name, kwargs)
                test_classname = '%s.%s.%s' % (kwargs['test_type'],
                                            kwargs['module_name'],
                                            kwargs['test_name'].replace(".", ";"))
                real_classname = '%s.%s' % (mod_path, func_name)
                start_time = kwargs['start_time'].astimezone(tz.tzlocal())
                start_time = start_time.isoformat()

                testcase = Element('testcase')
                testcase.attrib['name']         = test_name
                testcase.attrib['classname']    = test_classname
                testcase.attrib['time']         = str(total_seconds(time_delta))

                if kwargs['status'] == 'Fail':
                    self.failures += 1
                    failure = E.failure('Sorry, no support for backtrace yet.')
                    testcase.append(failure)
                elif kwargs['status'] is None:
                    self.errors += 1
                    error = E.error('Sorry, no support for backtrace yet.')
                    testcase.append(error)
                self.tests += 1

                self.testsuite.append(testcase)
                self.update_testsuite_attrs()


                for k in 'start_time end_time test_name status'.split():
                    del kwargs[k]

                traits = E.traits()
                testcase.append(traits)
                for k in kwargs:
                    traits.append(E.trait(name=str(k), value=str(kwargs[k])))
                traits.append(E.trait(name='real_classname',
                                      value=real_classname))
                traits.append(E.trait(name='start_time',
                                      value=start_time))
                self._commit()

    def update_testsuite_attrs(self):
        tsa = self.testsuite.attrib
        tsa['failures'] = str(self.failures)
        tsa['errors'] = str(self.errors)
        tsa['tests'] = str(self.tests)
        time_delta = datetime.datetime.now(tz.tzutc()) - self.suite_start
        tsa['time'] = str(total_seconds(time_delta))

