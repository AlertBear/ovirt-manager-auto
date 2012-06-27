#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading
import traceback

import re
from datetime import datetime
from dateutil.tz import tzutc
import code

from configobj import ConfigObj
from core_api.apis_exceptions import EntityNotFound, EngineTypeError
from socket import error as SocketError
from test_handler.settings import opts, plmanager
from test_handler.plmanagement.interfaces.tests_listener import SkipTest

EXC_BANNER_WIDTH = 68
EXC_BANNER_CHAR = '-'
TESTS_LOG_SEPARATOR =  '\n%s\n' % ('=' * 80)
FORKFOR_MAX_THREADS = 20
NO_TB_EXCEPTIONS = (EntityNotFound,)
_LOOP_INDEX = '#loop_index'
fetch_path = lambda x: os.path.abspath(\
        os.path.join(os.path.dirname(__file__), '..', x))
ACTIONS_PATH = fetch_path("conf/actions.conf")
ELEMENTS_PATH = fetch_path("conf/elements.conf")
CONFIG_PARAMS = 'PARAMETERS'


class _TestElm(dict):

    def __init__(self):
        super(_TestElm, self).__init__()
        self.name = None
        self.vital = False
        self.tcms_test_case = None
        self.description = None
        self.run = 'yes'

    def __getattribute__(self, key):
        try:
            return super(_TestElm, self).__getattribute__(key)
        except AttributeError as ex:
            try:
                return self[key]
            except KeyError:
                raise ex

    def __setattr__(self, key, val):
        self[key] = val


class TestGroup(_TestElm):
    '''
    Defines test group properties and methods
    '''

    def __init__(self):
        super(TestGroup, self).__init__()
        self.test_cases = []


class TestCase(_TestElm):
    '''
    Defines test case properties and methods
    '''

    def __init__(self):
        super(TestCase, self).__init__()
        self.positive = None
        self.id = None
        self.bz = None
        self.test_type = opts['engine']
        self.report = 'yes'
        self.group = None
#        self.fetch_output = None
        self.fetch_output = ''


class TestSuite(_TestElm):
    """
    Defines test suite properties and methods
    """
    def __init__(self):
        super(TestSuite, self).__init__()
        self.tcms_plan_id = None


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
            if not re.match(r'%s' %(placeHolder), runTest):
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

            try:
                plmanager.test_skippers.should_be_test_case_skipped(testCase)
                for i in range(startIter, iterNum):
                    self._run_test_case(i, funcName, testCase, testParametersStr, valsToIterate, loopParamVals, modPath, funcName, testGroup)
            except SkipTest:
                plmanager.test_cases.test_case_skipped(testCase)
        return testGroup, runGroup, saveGroupRows

    def _run_test_case(self, i, testCallable, testCase, testParametersStrOrg, valsToIterate, loopParamVals, modPath, funcName, testGroup):
        self.logger.debug("test_type: %s modPath: %s, funcName: %s", testCase['test_type'], modPath, funcName)

        try:
            exec("from " + modPath + " import " + funcName)
        except Exception:
            self.logger.error(traceback.format_exc())
            self.logger.error("Can't import action {0}\n{1}".format(funcName, \
                                                    TESTS_LOG_SEPARATOR))
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
            iteration = "%03d" % opts['iteration']

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
        if testCase['fetch_output_to']:
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
        plmanager.test_cases.pre_test_case(testCase)
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
        except SocketError:
            raise
        except EngineTypeError as e:
            self.logger.error("{0}\n{1}".format(e, TESTS_LOG_SEPARATOR))
            return
        except Exception as e:
            testStatus = False
            self.log_traceback(e, testCase['test_name'])
        plmanager.test_cases.post_test_case(testCase)


        if opts['compile']:
            return

        for outputKey in outputDict.keys():
            # insert fetched output values to self.output dictionary for further use
            outParamKey = fetchOutputTransl.get(outputKey, outputKey)
            self.output[outParamKey] = outputDict[outputKey]

        # add fetched output to report if necessary
        if opts['add_report_nodes'] != 'no':
            for outputKey in opts['add_report_nodes']:
                outParamKey = fetchOutputTransl.get(outputKey, outputKey)
                reportStats[outParamKey] = outputDict.get(outputKey, None)

        endTime = datetime.now(tzutc())

        # don't add positive to test parameters string
        if testCase['test_positive'] and testCase['test_positive'].lower()!='none':
            testParametersReport  = ', '.join(s.strip() for s in testParametersStr.split(',')[1:])
        else:
            testParametersReport  = ', '.join(s.strip() for s in testParametersStr.split(','))

        # replace fetched outputs with their values for reporting
        testParametersReport = re.sub("self.output\['\w+'\]", self._fetch_output_replacement, testParametersReport)

        reportStats['iter_num'] = iteration
        if testCase['id']:
            reportStats['id'] = testCase['id']
        if testCase['bz']:
            reportStats['bz'] = testCase['bz']
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
                reportStats['module_name'] = opts['actions'][testCase['test_action']].split('.')[-2].capitalize()
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

