#!/usr/bin/env python
# -*- coding: utf-8 -*-

from test_handler.test_runner import TestRunner, TestCase as _TestCase, \
        TestGroup as _TestGroup
runner = None


class TestGroup(_TestGroup):
    '''
    Defines test group properties and methods
    '''

    def __init__(self):
        super(TestGroup, self).__init__()

    def add_test_case(self, test_case):
        self.test_cases.append(test_case)

    def run(self):
        for case in self.test_cases:
            case.run()


class TestCase(_TestCase):
    '''
    Defines test case properties and methods
    '''

    def __init__(self):
        super(TestCase, self).__init__()
        self.engine = runner.get()
        self.config = self.engine.config

    @property
    def status(self):
        return self.engine.lastTestStatus

    @property
    def logger(self):
        return self.engine.logger

    @property
    def output(self):
        return self.engine.output

    def run(self):
        self.engine.run_test_case(self)


class PythonRunner(TestRunner):
    '''
    Implements methods for test runs from python script
    usage example:
    from test_handler.python_runner import TestCase


    def addCluster():
        test = TestCase()
        test.name = 'Add Cluster'
        test.action = 'addCluster'
        test.positive = True
        name = test.config['PARAMETERS'].get('cluster_name')
        version = test.config['PARAMETERS'].get('compatibility_version')
        test.params = "name='{0}', version='{1}', cluster='Test',\
                       wait=False".format(name, version)
        test.run()

        test.logger.info(test.status)
        test.logger.info(test.output)
    '''

    def __init__(self, groups, *args):
        '''
        Parameters:
           * groups - groups that should be run or None for all
        '''
        super(PythonRunner, self).__init__(*args)
        self.groups = groups
        global runner
        runner = self

    def get(self):
        '''
        Returns PythonRunner instance
        '''
        return self

    def run_test(self):
        '''
        Runs python tests script
        '''
        execfile(self.inputFile, locals())

    def get_property_val(self, testCase, keyName, reportName):
        '''
        Gets object property value by property name
        '''
        proertyVal = getattr(testCase, keyName)
        self.logger.info("{0}:\t{1}".format(reportName, proertyVal))
        return str(proertyVal)

    def run_test_case(self, test_case):
        '''
        Description: run and report tests for a specific test case
        Parameters:
           * test_case - TestCase object
        '''

        testCase = TestCase()
        testCase['test_name'] = \
            self.get_property_val(test_case, 'name', 'Test name')

        testCase['test_action'] = \
            self.get_property_val(test_case, 'action', 'Test action')

        testCase['test_parameters'] = \
            self.get_property_val(test_case, 'params', 'Test parameters')

        testCase['test_type'] = \
            self.get_property_val(test_case, 'test_type', 'Test type')
        if not testCase['test_type']:
            testCase['test_type'] = 'rest'

        testCase['test_positive'] = \
            self.get_property_val(test_case, 'positive', 'Test positive')

        testCase['test_report'] = \
            self.get_property_val(test_case, 'report', 'Report test')

        testCase['test_vital'] = \
            self.get_property_val(test_case, 'vital', 'Vital test')

        group = test_case.group

        if group and group.tcms_test_case:
            testCase['tcms_test_case'] = group.tcms_test_case
        else:
            testCase['tcms_test_case'] = \
                self.get_property_val(test_case, 'tcms_test_case',
                                  '   Tcms test case')

        testCase['test_description'] = \
            self.get_property_val(test_case, 'description', 'Test description')

        testCase['fetch_output_to'] = \
            self.get_property_val(test_case, 'fetch_output', 'Fetch output')

        testCase['id'] = \
            self.get_property_val(test_case, 'id', 'Test Id')

        testCase['bz'] = \
            self.get_property_val(test_case, 'bz', 'Test BZ')

        testCase['test_run'] = 'yes'

        return super(PythonRunner, self)._run_test_loop(testCase, group,
                                                         'yes', 0, False)
