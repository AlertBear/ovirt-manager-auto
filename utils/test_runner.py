#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading
import traceback
from getopt import GetoptError
from sys import argv, exit, exc_info

import re
from datetime import datetime
from dateutil.tz import tzutc
import logging
import code

from configobj import ConfigObj
from utils.reports import initializeLogger, DefaultResultsReporter, JUnitResultsReporter
from utils.http import check_connection
from utils.settings import opts, populateOptsFromArgv, readTestRunOpts
from utils.apis_exceptions import EntityNotFound

from lxml import etree

ACTIONS_PATH = "conf/actions.conf"
ELEMENTS_PATH = "conf/elements.conf"
EXC_BANNER_WIDTH = 68
EXC_BANNER_CHAR = '-'
TESTS_LOG_SEPARATOR =  '\n%s\n' % ('=' * 80)
FORKFOR_MAX_THREADS = 20
NO_TB_EXCEPTIONS = (EntityNotFound,)

_LOOP_INDEX = '#loop_index'
CONFIG_PARAMS = 'PARAMETERS'


class CannotRunTests(Exception):
    ''' Raised when some problem occured during running the test scenario. '''


class TestRunner(object):
    '''
    Implements general methods for test runs
    '''
    def __init__(self, config, logger, input, results_reporters, config_section, auto_devices):
        self.results_reporters = results_reporters
        for rr in results_reporters:
            rr.init_report(','.join(opts['test_file_name']), opts['log'])

        self.config = config
        self.logger = logger
        self.inputFile = input
        self.elementsConf = ConfigObj(ELEMENTS_PATH)
        self.groupDescription = ''
        self.testConfSection = config[CONFIG_PARAMS]
        self.output = {} # dictionary for fetched output
        self.parallelConfigs = {} # dictionary for parallel_configs

        self.rerunCases = [] # cases to be rerun in case of groups running in a loop
        self.startIter = 0 # loop starting iteration
        self.runGrouptIters = 0 # number of iterations for looped group
        self.testGroupLoopVal = '' # group run value for looped group
        self.testGroupRerun = '' # name of looped group
        self.groupTcmsTestCase = None
        self.lastTestStatus = None
      
        confDataCenterType = config[config_section].get('data_center_type', 'none').lower()
        if confDataCenterType != 'none' and confDataCenterType in config.sections:
            self.testConfSection.merge(config[confDataCenterType])

        if config_section != CONFIG_PARAMS:
            self.testConfSection = config[config_section]
            self.testConfSection.merge(config[CONFIG_PARAMS])


    def log_traceback(self, exc, test=None):
        '''
        Prints the last traceback and exception title to the logger.
        Return: none
        Author: jhenner.
        '''
        if opts['compile']:
            self.logger.error("Compilation error '%s' %s in test: %s" % (exc.__class__.__name__,exc.args,test))
        else:
            HEADING = ' {0} '.format(exc.__class__.__name__)
            CENTERED_HEADING = HEADING.center(EXC_BANNER_WIDTH, EXC_BANNER_CHAR)
            self.logger.error('{0}\n{1}'.format(CENTERED_HEADING, traceback.format_exc()))


    def _parse_parameters(self, parameters, runTest=''):
        '''
        Description: replace place holders with values from settings
        Author: edolinin
        Parameters:
           * parameters - string which should be parsed for place holders existence
           * runTest - value of 'run' column
        Return: parsed parameters
        '''

        testConfSection = self._get_conf_section()

        enumsSection = self.elementsConf['RHEVM Enums']
        permitsSection = self.elementsConf['RHEVM Permits']
        enumsSection.merge(permitsSection)

        parameters = parameters.replace('\'\'','\'')

        # replace enums params
        testParametersEnums = re.findall(r'e{\w+}',parameters)
        for placeHolder in testParametersEnums:
            try:
                placeHolderVal = enumsSection[placeHolder.lstrip("e{").rstrip("}")]
            except KeyError:
                self.logger.error("Enum %s doesn't exist." % (placeHolder))
                return parameters

            parameters=parameters.replace(placeHolder,placeHolderVal)

        # replace settings params (single values)
        testParametersPlaceHolders = re.findall(r'{\w+}',parameters)
        for placeHolder in testParametersPlaceHolders:
            if not re.match(r'%s' %(placeHolder),runTest):
                try:
                    placeHolderVal = testConfSection[placeHolder.strip("{}")]
                except KeyError:
                    placeHolderVal = placeHolder
                    self.logger.warn("Parameter %s doesn't exist." % (placeHolder))

                if not isinstance(placeHolderVal,list):
                    parameters=parameters.replace(placeHolder,placeHolderVal)

        # replace settings params (list values)
        testParametersArrPlaceHolders = re.findall(r'{\w+\[\d+\]}',parameters)
        for placeHolder in testParametersArrPlaceHolders:
            placeHolder = placeHolder.strip("{}")
            placeHolderName, placeHolderInd = placeHolder.strip(']').split('[')
            try:
                placeHolderArr = testConfSection.as_list(placeHolderName)
                placeHolderVal = placeHolderArr[int(placeHolderInd)]
            except KeyError:
                placeHolderVal = "{%s}" % placeHolderName
                self.logger.warn("Parameter %s with index %s doesn't exist." % (placeHolderName, placeHolderInd))
            except IndexError:
                placeHolderVal = "{%s}" % placeHolderName
                self.logger.warn("Parameter %s with index %s doesn't exist." % (placeHolderName, placeHolderInd))

            parameters=parameters.replace('{' + placeHolder + '}',placeHolderVal)

        # replace settings params, take list value as a single string element
        testParametersPlaceHolders = re.findall(r'\[\w+\]',parameters)
        for placeHolder in testParametersPlaceHolders:
            try:
                placeHolderVal = testConfSection.as_list(placeHolder.strip("[]"))
            except KeyError:
                placeHolderVal = placeHolder
                self.logger.warn("Parameter %s doesn't exist." % (placeHolder))

            parameters = parameters.replace(placeHolder,",".join(placeHolderVal))

        # replace fetch output values with stored in ouput dictionary by key name
        testParametersDictPlaceHolders = re.findall(r'%\w+%',parameters)
        for placeHolder in testParametersDictPlaceHolders:
            keyName = placeHolder.strip("%")
            if self.output.has_key(keyName):
                parameters = parameters.replace(placeHolder,"self.output['" + keyName + "']")
            else:
                parameters = parameters.replace(placeHolder,'None')

        return parameters

    def _check_run_test_val(self, runVal, runGroup = None):
        '''
        Description: parse and translate values for 'run' column
        Author: edolinin
        Parameters:
           * runVal - 'run' cell value
        Return: none
        '''

        if re.match('^yes|no$', runVal, re.I):
            return runVal.lower()

        # replace place holders in params with settings values
        runVal = self._parse_parameters(runVal)

        # split by conditions separator
        runValStates = runVal.split(';')

        actionMatch = re.compile("ifaction\((.*)\)")
        for runValState in runValStates:

            # if action should be tested - run the defined action
            if actionMatch.search(runValState):
                match = actionMatch.search(runValState)

                # action parameters
                actionParams = match.group(1).split(',')

                # action module path
                ifActionDict = {    
                                'test_action':  actionParams[0],
                                }
                funcPackage, funcName = self.resolveFuncPath(ifActionDict, opts)

                # import action
                exec("from {0} import {1}".format(funcPackage,funcName))

                # build action command
                params = ''
                for arg in actionParams[1:]:
                    params = "{0},{1}".format(params, arg)
                actionCmd = "{0}({1})".format(funcName,params.strip(' ,'))

                # if 'not ifaction' - run negative test
                if runValState.startswith('not'):
                    actionCmd = "not {0}".format(actionCmd)

                # run action
                runVal = "yes"
                try:
                    if not eval(actionCmd):
                        return "no"
                except Exception as e:
                    self.logger.warn('ifaction function {0} existed with exception: {1}'.format(actionCmd, e))
                    return "no"

            # evaluate 'if' condition
            match = re.match("if\((.*)\)", runValState, re.I)
            if match:
                runVal = "yes"
                if not eval(match.group(1)):
                    return "no"

            # in case of loop - return loop value
            match = re.match("loop\((.*)\)", runValState, re.I)
            if  match:
                runVal = match.group(1)
        
        if runGroup and not re.match('\d+', runGroup) and re.match('yes', runVal.lower()):
            runVal = runGroup

        return runVal


    def _fetch_output_replacement(self, match):
        '''
        Description: replace parameter value with fetched output
        Author: edolinin
        Parameters:
           * match - re match object for fetched output key
        Return: none
        '''

        return str(eval(match.group(0)))

    def _get_conf_section(self):
        '''
        Description: gets conf section from a proper conf file,
        if parallel configs exist - the defined config, default otherwise
        Author: edolinin
        Parameters:
           * None
        Return: test conf section
        '''

        try:
            confSection = self.parallelConfigs[threading.currentThread().name]
        except KeyError:
            confSection = self.testConfSection

        return confSection

    def _save_cases(self, testCase, testGroup, runGroup):
        '''
        Description: save test cases when running in group loop
        Author: edolinin
        Parameters:
           * testCase - test case to save
           * testGroup - test group the test belongs to
           * runGroup - value for run group
        Return: none
        '''

        # add case to a list of cases to be rerun
        self.rerunCases.append(testCase)
        testConfSection = self._get_conf_section()

        if not self.runGrouptIters:
            self.testGroupRerun = testGroup
            self.testGroupLoopVal = runGroup

            # group should be run in a loop over a certain parameter
            if re.match(r'{\w+}', runGroup):
                groupLoopIterOver = testConfSection[runGroup.strip("{}")]
                self.runGrouptIters = len(groupLoopIterOver)

            # group should be run in a loop over a defined range
            elif re.match(r'(\d+)-(\d+)',runGroup):
                self.startIter, self.runGrouptIters = runGroup.split('-')
                self.startIter = int(self.startIter)
                self.runGrouptIters = int(self.runGrouptIters) + 1

            # group should be run in a loop for a defined number of times
            else:
                self.runGrouptIters = int(runGroup)


    def _check_for_group_start(self, testName, testGroup, runGroup, saveGroupRows, groups):
        '''
        Description: check for start group flag and set run values accordingly
        Author: edolinin
        Parameters:
           * testName - test name cell/tag value
           * testGroup - test group the test belongs to
           * runGroup - value for run group
           * saveGroupRows - if current case should be saved or not
           * groups - groups that should be run
        Return: none
        '''

        if testName.startswith('START_GROUP'):
            match = re.match("START_GROUP:(.*)", testName)

            # group name
            testGroup = "".join(match.group(1).split())

            try:
                # if running with --groups option
                if groups and not testGroup in groups:
                    return testGroup, 'no', False

                # parse run group value
                runGroup = self._check_run_test_val(runGroup)
                # if running group in a loop - save test cases
                if re.match('\d+|{\w+}', runGroup):
                    saveGroupRows = True
            except IndexError:
                pass

        return testGroup, runGroup, saveGroupRows

    def resolveFuncPath(self, testCase, opts):
        '''
        Prepare the funcName and modPath for executing
        from {modPath} import {funcName}
        '''
        try:
            test_action = opts['actions'][testCase['test_action']].rsplit(".")
        except KeyError:
            self.logger.error("Action is not implemented yet '{0}'".format(testCase['test_action']))
            return None, None
       
        modPath = '.'.join(test_action[:-1])
        funcName = test_action[-1]
        return modPath, funcName


    def _run_test_loop(self, testCase, testGroup, runGroup, startIter,  saveGroupRows):
        '''
        Description: run test loop
        Author: edolinin
        Parameters:
           * testCase -  dictionary containing test case properties
           * testGroup - name of the group the test belongs to
           * runGroup -  run group condition/value
           * startIter - test iteration to count from
           * saveGroupRows - if to save run test case (relevant when running loop in group scope)
        Return: none
        '''

        if  testCase['test_name']:
            modPath, funcName = self.resolveFuncPath(testCase, opts)
            if not funcName:
                return testGroup, runGroup, saveGroupRows
            iterNum = 1 + startIter # number of iterations for test case
            valsToIterate = [] # for test case running in a loop over settings parameters

            # test case runs in a loop for a defined number of iterations
            if re.match('[0-9]+', testCase['test_run']):
                if re.search('-', testCase['test_run']):
                    startIter, testCase['test_run'] = testCase['test_run'].split('-') # if range is defined
                    startIter = int(startIter)
                    iterNum = int(testCase['test_run']) + 1
                else:
                    try:
                        iterNum = int(testCase['test_run'])
                    except Exception:
                        pass

            loopParamVals = []
            # test case runs in a loop over a settings parameter/s
            if re.match(r'{\w+}', testCase['test_run']):
                runTestParams = re.sub(r'\s', '', testCase['test_run']).split(',')
                valsToIterate.extend(runTestParams)

                testConfSection = self._get_conf_section()

                # get settings values for parameters place-holders
                paramConfValues = [testConfSection[runTestParam.strip("{}")] for runTestParam in runTestParams]
                loopParamVals = dict(zip(runTestParams, paramConfValues)) # dict of parameters names and values

                # if runGroup doesn't contain loop over a parameter
                if not runGroup or not re.match(r'{\w+}',runGroup):
                    iterNum = len(loopParamVals.itervalues().next())

                if runGroup and re.match('\d+',runGroup):
                    startIter = 0

                if saveGroupRows:
                    # save current test case
                    saveGroupRows = iterNum

            testParametersStr = testCase['test_parameters']

            # positive should a first parameter in test parameters
            if testCase['test_positive'] and testCase['test_positive'].lower()!='none':
                testParametersStr = "{0}, {1}".format(testCase['test_positive'].capitalize(), testCase['test_parameters'])

            for i in range(startIter, iterNum):
                self._run_test_case(i, funcName, testCase, testParametersStr, valsToIterate, loopParamVals, modPath, funcName, testGroup)
        return testGroup, runGroup, saveGroupRows

    def _run_test_case(self, i, testCallable, testCase, testParametersStrOrg, valsToIterate, loopParamVals, modPath, funcName, testGroup):
        self.logger.debug("test_type: %s modPath: %s, funcName: %s", testCase['test_type'], modPath, funcName)
        try:
            exec("from " + modPath + " import " + funcName)
        except ImportError:
            self.logger.info("Can't import action {0}\n{1}".format(funcName, TESTS_LOG_SEPARATOR))
            return

        testStatus = True
        reportStats = {}
        startTime = datetime.now(tzutc())

        testParametersStr = testParametersStrOrg.replace(_LOOP_INDEX, str(i))

        # replace loop parameters with their values
        for valToIterate in valsToIterate:
            testParametersStr = testParametersStr.replace(valToIterate, loopParamVals[valToIterate][i])

        testParametersStr = self._parse_parameters(testParametersStr, testCase['test_run'])

        iteration = ''
        if testCase['test_report'].lower() != "no":
            opts['iteration'] = opts['iteration'] + 1
            iteration = str(opts['iteration'])

        self.logger.info( "Iteration number: " + iteration)
        self.logger.info( "Current loop index: " + str(i))

        outputDict = {} # dictionary for fetched output
        testOutputStr = 'testStatus'

        # add outputDict to get function returned values if necessary
        if testCase['fetch_output_to'] != "" or \
            (opts['add_report_nodes'] != "no" and testCase['test_report'].lower() == "yes"):
            testOutputStr = "testStatus,outputDict"

        # prepare dictionary of fetched output 'from' and 'to' keys
        fetchOutputTransl = {}
        if testCase['fetch_output_to'] != "":
            testCase['fetch_output_to'] = self._parse_parameters(testCase['fetch_output_to'])
            #split fetch_output_to by whitespaces
            fromToList = re.split('\W*,\W*', testCase['fetch_output_to'])
            fromToList = [fromTo.split('->') for fromTo in fromToList]
            if any([len(ft) != 2 for ft in fromToList]):
                self.logger.error("Expected comma separated list of 'foo->bar', but %s found.",
                                testCase['fetch_output_to'])
                return
            fromToList = [(f.strip(), t.replace(_LOOP_INDEX, str(i)).strip()) \
                          for f, t in fromToList]
            fetchOutputTransl = dict(fromToList)

        # results command that should be run for a test case
        if not modPath.startswith('frontend'):
            cmd = '%s = %s(%s)' % (testOutputStr, funcName, testParametersStr)
        else:
            exec("import %s" % testCase['test_type'])
            cmd = '%s = %s(%s, %s)' % (testOutputStr, funcName, testCase['test_type'], testParametersStr)

        self.logger.info("Running command: " + cmd)

        # Run the test, catching the exceptions makes the test fail, but the
        # scenario continues.
        try:
            if opts['compile']:
                funcVars = ()
                # get names of function arguments
                exec('funcVars = %s.func_code.co_varnames' % funcName)
                sentVars = re.findall(r'(\w+)=', testParametersStrOrg)
                for x in sentVars:
                    if x not in funcVars:
                        raise TypeError("Wrong arguments passed to function: '%s'" % x)
                code.compile_command(cmd) # compile the command
            else:
                exec(cmd)
        except NO_TB_EXCEPTIONS as e:
            testStatus = False
            self.logger.error(e)
        except Exception as e:
            testStatus = False
            self.log_traceback(e, testCase['test_name'])


        if opts['compile']:
            return

        for outputKey in outputDict.keys():
            # insert fetched output values to self.output dictionary for further use
            outParamKey = fetchOutputTransl.get(outputKey, outputKey)
            self.output[outParamKey] = outputDict[outputKey]

            # add fetched output to report if necessary
            if outputKey in opts['add_report_nodes']:
                reportStats[outParamKey] = outputDict[outputKey]

        endTime = datetime.now(tzutc())

        # don't add positive to test parameters string
        if testCase['test_positive'] and testCase['test_positive'].lower()!='none':
            testParametersReport  = ', '.join(s.strip() for s in testParametersStr.split(',')[1:])
        else:
            testParametersReport  = ', '.join(s.strip() for s in testParametersStr.split(','))

        # replace fetched outputs with their values for reporting
        testParametersReport = re.sub("self.output\['\w+'\]", self._fetch_output_replacement, testParametersReport)

        reportStats['iter_num'] = iteration
        reportStats['test_name'] = testCase['test_name']
        reportStats['test_description'] = testCase['test_description']
        reportStats['start_time'] = startTime
        reportStats['end_time'] = endTime
        reportStats['tcms_test_case'] = testCase['tcms_test_case']
        reportStats['test_parameters'] = testParametersReport
        reportStats['test_type'] = testCase['test_type']
        reportStats['status'] = "Pass" if testStatus else "Fail"
        self.lastTestStatus = testStatus

        # set node name for test case parent
        if testGroup:
            reportStats['module_name'] = testGroup.capitalize()
            if self.groupDescription:
                reportStats['group_desc'] = self.groupDescription
        else:
            if opts['has_sub_tests'] == "yes":
                reportStats['module_name'] = opts['actions'][testCase['test_action']].split('.')[0].capitalize()
            else:
                reportStats['module_name'] = None

        if testCase['test_positive']:
            reportStats['test_positive'] = testCase['test_positive']

        if str(testCase['test_report']).lower() != "no":
            for rr in self.results_reporters:
                rr.add_test_report(modPath, funcName, **reportStats)

        severity = "info"
        if not testStatus:
            severity = "error"
        getattr(self.logger, severity)("Test status for test '%s': %s" %(testCase['test_name'], reportStats['status']))

        self.logger.info("Test with iteration number %s is finished.\n%s",
                         iteration, TESTS_LOG_SEPARATOR)

        if testCase['test_vital'].lower() == "true" and not testStatus:
            self.logger.error("Vital test failed: '" + testCase['test_name'] + "', can't run any further test. Exiting...")
            os._exit(1)


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


    @staticmethod
    def load(testFile):
        '''
        Description: load xml file
        Author: edolinin
        Parameters:
           * testFile - path to xml file
        Return: loaded file instance
        '''

        return etree.parse(testFile)

    def _get_node_val(self, testCase, nodeName, nodeReportAs = None, defaultVal = ''):
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

    def run_test(self, input):
        '''
        Description: run rows from specific sheet of ods file
        Author: edolinin
        Parameters:
           * sheet - reference to a sheet that should be run
        Return: none
        '''

        testCases = input.findall('test_case')

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

        testCase = {}

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

        return super(XmlRunner, self)._run_test_loop(testCase, testGroup, runGroup, startIter, saveGroupRows)


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

        self.autoDevices = self.config['RUN'].get('auto_devices','no') == "yes"
        self.type = self.config['RUN']['engine']

        self.actionsConf = ConfigObj(ACTIONS_PATH)
        opts['actions'] = {}

    def _build_actions_map(self, section, key):
        '''
        Description: build hash of possible actions, key - action name, value - action function
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

        self.logger.info('Running with the following command lines arguments: {0}'.format(argv[1:]))

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
        MSG = "Test %s not found in and it's subdirs %s." % (filename, confRoot)
        raise CannotRunTests, MSG

    def run_suite(self):
        '''
        Description: run tests suite
        Author: edolinin
        Parameters: None
        Return: none
        '''

        self._initialize_run()
        default_reporter = DefaultResultsReporter(self.config['RUN']['tests_file'],
                opts['engine'], opts['results'])
        junit_reporter= JUnitResultsReporter(self.config['RUN']['tests_file'],
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
                testRunner = OdsRunner(lines, groups, self.config, self.logger, testName,
                            results_reporters, config_section, self.autoDevices)
                test_cases = testRunner.load(testFilePath)
                testRunner.run_test(test_cases)

            elif testName.endswith('xml'):
                if opts['in_parallel']:
                    testInd = 1
                    threadName = testName
                    while test in opts['in_parallel']:
                        config = self.config
                        if opts['parallel_configs']:
                            config = ConfigObj(opts['parallel_configs'].pop(0)) # get relevant config file
                            threadName = "{0}-{1}".format(testName, testInd)

                        if opts['parallel_sections']:
                            config_section = opts['parallel_sections'].pop(0)
                            threadName = "{0}-{1}".format(testName, testInd)

                        testRunner = XmlRunner(lines, groups, config, self.logger, testName,
                                    results_reporters, config_section, self.autoDevices)
                        opts['in_parallel'].remove(test)
                        opts['tests'].remove(test)

                        test_cases = testRunner.load(testFilePath)
                        thread = threading.Thread(target=testRunner.run_test, name=threadName, args=(test_cases,))
                        thread.start()
                        threads.append(thread)

                        testInd += 1

                    if threads and not opts['in_parallel']:
                        self.logger.info("waiting for parallel tests finish")
                        for thr in threads:
                            thr.join()
                else:
                    testRunner = XmlRunner(lines, groups, self.config, self.logger, testName,
                                results_reporters, config_section, self.autoDevices)
                    test_cases = testRunner.load(testFilePath)
                    testRunner.run_test(test_cases)
        except Exception as ex:
            MSG = "Can't run tests from input file '{0}' because of {1.__class__.__name__}: {1}".format(testName, ex)
            raise CannotRunTests, MSG, exc_info()[2]


if __name__ == "__main__":
    '''
    Main function - reads args and runs the tests
    This part should be a replacement for run.py when TestRunner module is ready
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

