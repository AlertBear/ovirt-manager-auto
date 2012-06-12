#!/usr/bin/env python
# -*- coding: utf-8 -*-

from framework_utils.test_runner import TestRunner
runner = None

class TestGroup(object):

    def __init__(self, name=None, vital=None, tcms_test_case=None):
        self.name = name
        self.vital = vital
        self.tcms_test_case = tcms_test_case
        self.test_cases = []

    @property
    def name(self):
        return self.name

    @property
    def vital(self):
        return self.vital

    @property
    def tcms_test_case(self):
        return self.tcms_test_case

    def add_test_case(self, test_case):
        self.test_cases.append(test_case)

    def run(self):
        for case in self.test_cases:
            case.run()
            

class TestCase(object):

    def __init__(self, positive=None, vital=None, test_type=None, report='yes', \
        group=None, tcms_test_case=None, description=None, fetch_output=''):
        self._positive = positive
        self._vital = vital
        self._test_type = test_type
        self._report = report
        self._group = group
        self._tcms_test_case = tcms_test_case
        self._description = description
        self._fetch_output = fetch_output
        self.engine = runner.get()
        self.config = self.engine.config

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value


    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, value):
        self._action = value

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, value):
        self._params = value

    @property
    def positive(self):
        return self._positive

    @positive.setter
    def positive(self, value):
        self._positive = value

    @property
    def vital(self):
        return self._vital

    @vital.setter
    def vital(self, value):
        self._vital = value

    @property
    def test_type(self):
        return self._test_type

    @test_type.setter
    def test_type(self, value):
        self._test_type = value

    @property
    def tcms_test_case(self):
        return self._tcms_test_case

    @tcms_test_case.setter
    def tcms_test_case(self, value):
        self._tcms_test_case = value

    @property
    def report(self):
        return self._report

    @report.setter
    def report(self, value):
        self._report = value

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, value):
        self._group = value

    @property
    def fetch_output(self):
        return self._fetch_output

    @fetch_output.setter
    def fetch_output(self, value):
        self._fetch_output = value

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
    Implements methods for test runs from xml files
    '''
   
    def __init__(self, groups, *args):
        
        super(PythonRunner, self).__init__(*args)
        self.groups = groups
        global runner
        runner = self

    def get(self):
        return self

    def run_test(self):
        execfile(self.inputFile)

    def run_test_case(self, test_case):

        testCase = {}
        testCase['test_name'] = test_case.name

        testCase['test_action'] = test_case.action
        
        testCase['test_parameters'] = test_case.params

        testCase['test_type'] = test_case.test_type
        if not testCase['test_type']:
            testCase['test_type'] = 'rest'

        testCase['test_positive'] = str(test_case.positive)

        testCase['test_report'] = test_case.report

        testCase['test_vital'] = str(test_case.vital)

        group = test_case.group
        
        if group and group.tcms_test_case:
            testCase['tcms_test_case'] = group.tcms_test_case
        else:
            testCase['tcms_test_case'] = test_case.tcms_test_case

        testCase['test_description'] = test_case.description

        testCase['fetch_output_to'] = test_case.fetch_output

        testCase['test_run'] = 'yes'

        


        return super(PythonRunner, self)._run_test_loop(testCase, group, 'yes', 0, False)
