#!/usr/bin/env python
# -*- coding: utf-8 -*-

from configobj import ConfigObj
import threading
import traceback

from art.test_handler.test_runner import TestRunner, opts, TestCase
from odf.opendocument import load
from odf.table import Table,TableRow,TableCell
from odf.text import P
import re


class OdsRunner(TestRunner):
    '''
    Implements methods for test runs from ods files
    '''
    def __init__(self, lines, groups, *args):
        '''
        Parameters:
           * groups - groups that should be run or None for all
           * lines - lines that should be run or None for all
        '''

        super(OdsRunner, self).__init__(*args)

        self.groups = groups # if running with --groups option
        self.lines = lines # if running with --lines option
        self.headers = {} # ods headers

    @classmethod
    def load(self, testFile):
        '''
        Description: load ods file
        Author: edolinin
        Parameters:
           * testFile - path to ods file
        Return: loaded file instance
        '''

        return load(testFile)


    def run_test(self, input):
        '''
        Description: run test sheets from ods file in parallel or sequentially
        Author: edolinin
        Parameters:
           * input - path to ods file
        Return: none
        '''

        sheetNum = 1 # number of sheet for parallel_configs runs

        threads = []
        for sheet in input.spreadsheet.getElementsByType(Table) :
            sheetName = sheet.getAttribute('name')
            if sheetName in opts['in_parallel']: # parallel run
                while sheetName in opts['in_parallel']: # same sheet running parallely
                    opts['in_parallel'].remove(sheetName)

                    if sheetName in opts['sheets']:
                        opts['sheets'].remove(sheetName)

                    try:
                        sheetTreadName = sheetName
                        if opts['parallel_configs']:
                            config = ConfigObj(opts['parallel_configs'][0]) # get relevant config file
                            sheetTreadName = sheetName + str(sheetNum)

                            # insert testing section of relevant config file to parallelConfigs dictionary
                            self.parallelConfigs[sheetTreadName] = config[opts['type'].upper()]
                            opts['parallel_configs'].remove(opts['parallel_configs'][0])

                        thread = threading.Thread(target=self._run_sheet, name=sheetTreadName, args=(sheet,))
                        thread.start()
                        threads.append(thread)

                        sheetNum += 1

                    except Exception:
                        self.logger.error(traceback.format_exc())

            elif sheetName in opts['sheets']: # sequential run
                opts['sheets'].remove(sheetName)
                try:
                    self.logger.info('Running sheet %s' %(sheetName))
                    self._run_sheet(sheet)
                except Exception:
                    self.logger.error(traceback.format_exc())

            if threads and not opts['in_parallel']:
                self.logger.info("waiting for parallel tests finish")
                for thr in threads:
                    thr.join()

        # if some sheet wasn't run - it doesn't exist in ods
        if opts['sheets'] or opts['in_parallel']:
            nonRunSheets = ','.join(opts['sheets'] + opts['in_parallel'])
            self.logger.error("The following sheets doesn't exist in your .ods file: %s" % nonRunSheets)


    def _build_headers(self, firstRow):
        '''
        Description: build a dictionary of ods headers indexes
        Author: edolinin
        Parameters:
           * firstRow - first row of ods file
        Return: none
        '''

        headersCells = firstRow.getElementsByType(TableCell)

        for cellInd in range(0,len(headersCells)):
            cell = self._get_cell_val(headersCells, cellInd, "Header " + str(cellInd))
            self.headers[cell] = cellInd


    def _run_sheet(self, sheet):
        '''
        Description: run rows from specific sheet of ods file
        Author: edolinin
        Parameters:
           * sheet - reference to a sheet that should be run
        Return: none
        '''

        rows = sheet.getElementsByType(TableRow)
        self._build_headers(rows[0])

        testGroup = '' # group name
        runGroup = 'yes'
        saveGroupRows = None # if to save test case (for looped groups)

        if self.lines:
            for i,r in enumerate(rows[1:], 2):  # Don't allow to remove the
                                                # header row.
                if i not in self.lines:
                    rows.remove(r)

        for row in rows[1:]:
            try:
                if saveGroupRows:
                    self._save_cases(row, testGroup, runGroup)
                elif self.rerunCases: # rerun saved test cases for a number of defined iterations (for looped group)
                    for iter in range(self.startIter + 1, self.runGrouptIters):
                        for rerunCase in self.rerunCases:
                            testGroup, runGroup, saveGroupRows = \
                                self._run_test_loop(rerunCase, self.testGroupRerun, self.testGroupLoopVal, saveGroupRows, iter)
                    self.rerunCases = []
                    self.startIter = 0
                    self.runGrouptIters = 0

                testGroup, runGroup, saveGroupRows = self._run_test_loop(row, testGroup, runGroup, saveGroupRows, self.startIter)
            except Exception as e:
                self.log_traceback(e, row.firstChild)

    def _run_test_loop(self, row, testGroup, runGroup, saveGroupRows, startIter=0):
        '''
        Description: run and report tests for a specific test case (row)
        Author: edolinin
        Parameters:
           * row - reference to a row that should be run
           * testGroup - name of test group if exists
           * runGroup - has value if test group is running, None otherwise
           * saveGroupRows - if to keep rows for further rerun, used when test group runs in a loop
           * startIter - used when running test group in a loop
        Return: testGroup, runGroup, saveGroupRows
        '''

        testCase = TestCase()

        cells = row.getElementsByType(TableCell)

        testName = self._get_cell_val(cells, self.headers['test name'], "Test name")
        testCase['test_name'] = self._parse_parameters(testName)

        if not testCase['test_name'] or testCase['test_name'].startswith('END_GROUP'):
            if not saveGroupRows:
                self.groupDescription = ''
            return None, 'yes', None

        if testCase['test_name'].startswith('START_GROUP'):
            runGroup = self._get_cell_val(cells, self.headers['run'], "Run test")

        testGroup, runGroup, saveGroupRows = self._check_for_group_start(testCase['test_name'], testGroup, runGroup, saveGroupRows, self.groups)

        if runGroup == 'no' or testCase['test_name'].startswith('START_GROUP'):
            if self.headers.has_key('tcms_test_case'):
                self.groupTcmsTestCase = self._get_cell_val(cells, self.headers['tcms_test_case'], "Tcms test case")
            if not self.groupDescription:
                self.groupDescription = self._get_cell_val(cells, self.headers['test_description'], "Test Description") if self.headers.has_key('test_description') else None
            return testGroup, runGroup, saveGroupRows

        testCase['test_run'] = self._get_cell_val(cells, self.headers['run'], "Run test")
        testCase['test_run'] = self._check_run_test_val(testCase['test_run'])

        if runGroup and not re.match('\d+', runGroup) and re.match('yes', testCase['test_run'].lower()):
            testCase['test_run'] = runGroup

        if testCase['test_run'].lower() == 'no':
            self.logger.info("Skipping test '%s'.\n%s",
                         testCase['test_name'], TESTS_LOG_SEPARATOR)
            return testGroup, runGroup, saveGroupRows

        testCase['test_type'] = self._get_cell_val(cells, self.headers['test_type'], "Test type") \
                                if self.headers.has_key('test_type') else ""
        if not testCase['test_type'].strip():
            testCase['test_type'] = opts['type']

        testCase['test_action'] = self._get_cell_val(cells, self.headers['test action'], "Test action")

        testCase['test_parameters'] = self._get_cell_val(cells, self.headers['parameters'], "Test parameters")

        testCase['test_positive'] = self._get_cell_val(cells, self.headers['positive'], "Test positive") if self.headers.has_key('positive') else ""

        testCase['test_report'] = self._get_cell_val(cells, self.headers['report'], "Report test") if self.headers.has_key('report') else "yes"

        testCase['fetch_output_to'] = self._get_cell_val(cells, self.headers['fetch_output'], "Fetch output") if self.headers.has_key('fetch_output') else ""

        testCase['test_vital'] = self._get_cell_val(cells, self.headers['vital'], "Vital test") if self.headers.has_key('vital') else "false"

        if self.groupTcmsTestCase:
            testCase['tcms_test_case'] = self.groupTcmsTestCase
        else:
            testCase['tcms_test_case'] = self._get_cell_val(cells, self.headers['tcms_test_case'], "Tcms test case") if self.headers.has_key('tcms_test_case') else ""

        testCase['test_description'] = self._get_cell_val(cells, self.headers['test_description'], "Test Description") if self.headers.has_key('test_description') else ""

        testCase['id'] = self._get_cell_val(cells, self.headers['id'], "Test Id") \
            if self.headers.has_key('id') else None

        testCase['bz'] = self._get_cell_val(cells, self.headers['bz'], "Test BZ") \
            if self.headers.has_key('bz') else None

        testCase['conf'] = self._get_cell_val(cells, self.headers['conf'], \
            "Change Global Conf Values") if self.headers.has_key('conf') else None

        return super(OdsRunner, self)._run_test_loop(testCase, testGroup, runGroup, startIter, saveGroupRows)


    def _get_cell_val(self, cellsObj, cellInd, paramName):
        '''
        Description: fetch values of ods cells
        Author: edolinin
        Parameters:
           * cellsObj - reference to a cells list in ods file
           * cellInd - cell index
           * paramName - cell's header
        Return: cell value in str format
        '''

        if cellsObj and cellsObj[cellInd] and cellsObj[cellInd].getElementsByType(P):
            cellVal = map(lambda x: x.firstChild, cellsObj[cellInd].getElementsByType(P))[0]
            try:
                cellVal = cellVal.data.encode('utf-8', 'replace') # convert to utf-8 format
            except AttributeError:
                if cellVal.hasChildNodes:
                    cellVal = cellVal.firstChild.data.encode('utf-8', 'replace') # convert to utf-8 format
        else:
            cellVal = ""
        self.logger.info(paramName + ": " + str(cellVal))
        return str(cellVal)
