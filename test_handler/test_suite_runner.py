#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading
from getopt import GetoptError
from sys import argv, exit, exc_info

import logging

from configobj import ConfigObj
from test_handler.reports import initializeLogger, DefaultResultsReporter,\
                                 JUnitResultsReporter
from core_api.http import check_connection
from test_handler.settings import opts, populateOptsFromArgv, readTestRunOpts
from socket import error as SocketError
from test_handler.python_runner import PythonRunner
from test_handler.xml_runner import XmlRunner
from test_handler.ods_runner import OdsRunner
from test_handler.test_runner import CONFIG_PARAMS, ACTIONS_PATH
from core_api.apis_exceptions import CannotRunTests


class TestSuiteRunner:
    '''
    Implements methods for running a tests suite (collection of tests)
    '''
    def __init__(self, redefs):
        self.lines = opts.get('lines', None)
        self.groups = opts.get('groups', None)

        self.config = readTestRunOpts(opts['conf'], redefs)
        if not opts['standalone']:
            check_connection(opts)  # check connection to vdc rhevm-api

        initializeLogger()
        self.logger = logging.getLogger(__name__)

        self.autoDevices = self.config['RUN'].get('auto_devices',
                                                  'no') == "yes"
        self.type = self.config['RUN']['engine']

        self.actionsConf = ConfigObj(ACTIONS_PATH)
        opts['actions'] = {}

    def _build_actions_map(self, section, key):
        '''
        Description: build hash of possible actions,
                     key - action name, value - action function
        Author: edolinin
        Parameters:
           * section - section name, passed automatically from 'walk' command
           * key - action key name, passed automatically from 'walk' command
        Return: none
        '''

        opts['actions'][key] = section[key]

    def _initialize_run(self):
        '''
        Description: initialize tests suite run
        Author: edolinin
        Parameters: None
        Return: none
        '''

        self.actionsConf.walk(self._build_actions_map, call_on_sections=True)

        if opts['compile']:
            logging.disable(logging.INFO)
            logging.disable(logging.WARN)

        self.logger.info('Running with the following command\
                          lines arguments: {0}'.format(argv[1:]))

    def _getTestFullPath(self, filename):
        '''
        Description: search the ../conf for test file
        Author: lustalov
        Parameters: test filename
        Return: full pathname
        '''
        confRoot = os.path.join(os.path.dirname(__file__), '../conf')
        for root, dirs, names in os.walk(confRoot):
            if filename in names:
                return os.path.join(root, filename)
        MSG = "Test %s not found in and it's subdirs %s." % (filename,
                                                             confRoot)
        self.logger.exception(MSG)
        raise CannotRunTests, MSG

    def run_suite(self):
        '''
        Description: run tests suite
        Author: edolinin
        Parameters: None
        Return: none
        '''

        self._initialize_run()
        default_reporter = DefaultResultsReporter(\
                                self.config['RUN']['tests_file'],
                                opts['engine'], opts['results'])
        junit_reporter = JUnitResultsReporter(\
                                self.config['RUN']['tests_file'],
                                opts['engine'], opts['junit_results'])

        results_reporters = default_reporter, junit_reporter

        for test in opts['tests']:
            self.run_suite_test(test, results_reporters)

    def run_suite_test(self, test, results_reporters):
        '''
        Description: run tests suite
        Author: edolinin
        Parameters:
          test - The name of test.
          results_reporters
        '''
        try:
            threads = []
            testName = os.path.basename(test)
            testFilePath = test
            if not os.path.exists(testFilePath):
                testFilePath = self._getTestFullPath(testName)
            opts['in_parallel'] = opts[testName]['in_parallel']

            lines = self.lines
            if 'lines' in opts[testName]:
                lines = opts[testName]['lines']

            groups = self.groups
            if 'groups' in opts[testName]:
                groups = opts[testName]['groups']

            config_section = CONFIG_PARAMS
            testRunner = None
            if testName.endswith('ods'):
                testRunner = OdsRunner(lines, groups, self.config, self.logger,
                                       testName, results_reporters,
                                       config_section, self.autoDevices)
                test_cases = testRunner.load(testFilePath)
                testRunner.run_test(test_cases)

            elif testName.endswith('py'):
                testRunner = PythonRunner(groups, self.config, self.logger,
                                          testFilePath, results_reporters,
                                          config_section, self.autoDevices)
                testRunner.run_test()

            elif testName.endswith('xml'):
                if opts['in_parallel']:
                    testInd = 1
                    threadName = testName
                    while test in opts['in_parallel']:
                        config = self.config
                        if opts['parallel_configs']:
                            # get relevant config file
                            config = ConfigObj(opts['parallel_configs'].pop(0))
                            threadName = "{0}-{1}".format(testName, testInd)

                        if opts['parallel_sections']:
                            config_section = opts['parallel_sections'].pop(0)
                            threadName = "{0}-{1}".format(testName, testInd)

                        testRunner = XmlRunner(lines, groups, config,
                                               self.logger, testName,
                                               results_reporters,
                                               config_section,
                                               self.autoDevices)
                        opts['in_parallel'].remove(test)
                        opts['tests'].remove(test)

                        test_cases = testRunner.load(testFilePath)
                        thread = threading.Thread(target=testRunner.run_test,
                                                  name=threadName,
                                                  args=(test_cases,))
                        thread.start()
                        threads.append(thread)

                        testInd += 1

                    if threads and not opts['in_parallel']:
                        self.logger.info("waiting for parallel tests finish")
                        for thr in threads:
                            thr.join()
                else:
                    testRunner = XmlRunner(lines, groups, self.config,
                                           self.logger, testName,
                                           results_reporters, config_section,
                                           self.autoDevices)
                    test_cases = testRunner.load(testFilePath)
                    testRunner.run_test(test_cases)
        except SocketError:
            raise
        except Exception as ex:
            MSG = "Can't run tests from input file '{0}'\
                   because of {1.__class__.__name__}: {1}".format(testName, ex)
            self.logger.exception(MSG)
            raise CannotRunTests, MSG, exc_info()[2]


if __name__ == "__main__":
    '''
    Main function - reads args and runs the tests
    This part should be a replacement for run.py
    when TestRunner module is ready
    '''

    try:
        redefs = populateOptsFromArgv(argv)
    except GetoptError, err:
        print str(err)
        exit(2)

    try:
        suiteRunner = TestSuiteRunner(redefs)
        suiteRunner.run_suite()
    except KeyboardInterrupt:
        pass
