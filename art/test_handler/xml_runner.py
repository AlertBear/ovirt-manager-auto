#!/usr/bin/env python
# -*- coding: utf-8 -*-

from art.test_handler.test_runner import TestRunner, TestSuite, TestCase, \
                                                    opts
from art.test_handler.settings import initPlmanager

from lxml import etree
import re

plmanager = initPlmanager()


class XmlRunner(TestRunner):
    '''
    Implements methods for test runs from xml files
    '''
    def __init__(self, lines, groups, *args):
        '''
        Parameters:
           * groups - groups that should be run or None for all
           * lines - lines that should be run or None for all
        '''
        super(XmlRunner, self).__init__(*args)

        self.groups = groups
        self.lines = lines
        self.test_suite = None

    def load(self, testFile):
        '''
        Description: load xml file
        Author: edolinin, atal
        Parameters:
           * testFile - path to xml file
        Return: loaded file instance after include all XMLs
        '''

        tree = etree.parse(testFile)
        tree.xinclude()
        root_node = tree.getroot()
        tcms_plan_id = root_node.attrib.get('tcms_plan_id', None)
        self.test_suite = TestSuite(tcms_plan_id)
        plmanager.test_suites.pre_test_suite(self.test_suite)
        return tree.getiterator(tag='test_case')

    def _get_node_val(self, testCase, nodeName, nodeReportAs=None, defaultVal=''):
        '''
        Description: fetch values of test case xml nodes
        Author: edolinin
        Parameters:
           * testCase - reference to a test case node
           * nodeName - node name
           * nodeReportAs - name of node to appear in log reporting
           * defaultVal - node default value if node doesn't exist
        Return: cell value in str format
        '''

        nodeVal = testCase.findtext(nodeName, defaultVal)
        if nodeReportAs:
            self.logger.info("{0}:\t{1}".format(nodeReportAs, nodeVal))
        return nodeVal

    def run_part(self, iter, saveGroupRows):
        for rerunCase in self.rerunCases:
            testGroup, runGroup, saveGroupRows = \
                self._run_test_loop(rerunCase, self.testGroupRerun, self.testGroupLoopVal, saveGroupRows, iter)

    def run_test(self, tree):
        '''
        Description: run rows from specific sheet of ods file
        Author: edolinin
        Parameters:
           * tree - reference to an xml tree that should be run
        Return: none
        '''
        # convert ElementDepthFirstIterator object to a list
        testCases = map(lambda a: a, tree)

        testGroup = ''
        runGroup = 'yes'
        saveGroupRows = None # if to save test case (for looped group)

        if self.lines:
            removeTestCases = []
            for i, r in enumerate(testCases, 1):
                if i not in self.lines:
                    removeTestCases.append(r)

            for testCase in removeTestCases:
                testCases.remove(testCase)

        for testCase in testCases:
            if saveGroupRows:
                self._save_cases(testCase, testGroup, runGroup)
            elif self.rerunCases: # rerun saved test cases for a number of defined iterations (for looped group)
                testGroup, runGroup, saveGroupRows = self._rerun_loop_cases(testGroup, runGroup, saveGroupRows)
            testGroup, runGroup, saveGroupRows = self._run_test_loop(testCase, testGroup, runGroup, saveGroupRows, self.startIter)
        if self.rerunCases:
            testGroup, runGroup, saveGroupRows = self._rerun_loop_cases(testGroup, runGroup, saveGroupRows)

        plmanager.test_suites.post_test_suite(self.test_suite)


    def _rerun_loop_cases(self, testGroup, runGroup, saveGroupRows):
        '''
        Description: run loop test cases
        Author: edolinin
        Parameters:
           * testGroup - name of test group if exists
           * runGroup - has value if test group is running, None otherwise
           * saveGroupRows - if to keep rows for further rerun, used when test group runs in a loop
        Return: testGroup, runGroup, saveGroupRows
        '''

        for iter in range(self.startIter + 1, self.runGrouptIters):
            for rerunCase in self.rerunCases:
                testGroup, runGroup, saveGroupRows = \
                    self._run_test_loop(rerunCase, self.testGroupRerun, self.testGroupLoopVal, saveGroupRows, iter)
        self.rerunCases = []
        self.startIter = 0
        self.runGrouptIters = 0

        return testGroup, runGroup, saveGroupRows


    def _run_test_loop(self, xmlTestCase, testGroup, runGroup, saveGroupRows, startIter=0):
        '''
        Description: run and report tests for a specific test case (row)
        Author: edolinin
        Parameters:
           * xmlTestCase - reference to xml node that should be run
           * testGroup - name of test group if exists
           * runGroup - has value if test group is running, None otherwise
           * saveGroupRows - if to keep rows for further rerun, used when test group runs in a loop
           * startIter - used when running test group in a loop
        Return: testGroup, runGroup, saveGroupRows
        '''

        testCase = TestCase()

        testName = self._get_node_val(xmlTestCase, 'test_name', "Test name")
        testCase['test_name'] = self._parse_parameters(testName)

        if not testCase['test_name'] or testCase['test_name'].startswith('END_GROUP'):
            if not saveGroupRows:
                self.groupDescription = ''
            return None, 'yes', None

        if testCase['test_name'].startswith('START_GROUP'):
            runGroup = self._get_node_val(xmlTestCase, 'run', "Run test")

        testGroup, runGroup, saveGroupRows = self._check_for_group_start(testCase['test_name'], testGroup, runGroup, saveGroupRows, self.groups)

        if runGroup == 'no' or testCase['test_name'].startswith('START_GROUP'):
            self.groupTcmsTestCase = self._get_node_val(xmlTestCase, 'tcms_test_case', "Tcms test case")
            if not self.groupDescription:
                self.groupDescription = self._get_node_val(xmlTestCase, 'test_description', "Test Description", None)
            return testGroup, runGroup, saveGroupRows

        testCase['test_run'] = self._get_node_val(xmlTestCase, 'run', "Run test")
        testCase['test_run'] = self._check_run_test_val(testCase['test_run'])

        if runGroup and not re.match('\d+', runGroup) and re.match('yes', testCase['test_run'].lower()):
            testCase['test_run'] = runGroup

        if testCase['test_run'].lower() == 'no':
            return testGroup, runGroup, saveGroupRows

        testCase['test_type'] = self._get_node_val(xmlTestCase, 'test_type', "Test type", opts['engine'])
        if not testCase['test_type'].strip():
            testCase['test_type'] = opts['engine']

        testCase['test_action'] = self._get_node_val(xmlTestCase, 'test_action', "Test action")

        testCase['test_parameters'] = self._get_node_val(xmlTestCase, 'parameters', "Test parameters")

        testCase['test_positive'] = self._get_node_val(xmlTestCase, 'positive', "Test positive")

        testCase['test_report'] = self._get_node_val(xmlTestCase, 'report', "Report test", "yes")

        testCase['fetch_output_to'] = self._get_node_val(xmlTestCase, 'fetch_output', "Fetch output")

        testCase['test_vital'] = self._get_node_val(xmlTestCase, 'vital', "Vital test", "false")

        if self.groupTcmsTestCase:
            testCase['tcms_test_case'] = self.groupTcmsTestCase
        else:
            testCase['tcms_test_case'] = self._get_node_val(xmlTestCase, 'tcms_test_case', "Tcms test case")

        testCase['test_description'] = self._get_node_val(xmlTestCase, 'test_description', "Test Description")

        testCase['id'] = self._get_node_val(xmlTestCase, 'id', "Test id", None)

        testCase['bz'] = self._get_node_val(xmlTestCase, 'bz', "Test BZ", None)

        testCase['conf'] = self._get_node_val(xmlTestCase, 'conf',
                                "Change Global Conf Values", None)

        return super(XmlRunner, self)._run_test_loop(testCase, testGroup, runGroup, startIter, saveGroupRows)
