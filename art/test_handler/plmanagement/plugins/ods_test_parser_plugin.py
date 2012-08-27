
#import os
#
#from art.test_handler.plmanagement import Component, implements, get_logger, PluginError
#from art.test_handler.plmanagement.interfaces.application import ITestParser, IConfigurable
##import art.test_handler.plmanagement.plugins.matrix_test_runner_plugin as mrunner
#import matrix_test_runner_plugin as mr
#from odf.opendocument import load
#from odf.table import Table,TableRow,TableCell
#from odf.text import P
#
#logger = get_logger('ods-test-parser')
#
#RUN_SEC = 'RUN'
#TESTS_FILE = 'tests_file'
#TESTS_SHEETS = 'tests_sheets'
#
#TEST_CASE_COL = '?'
#TEST_NAME_COL = '?'
#TEST_RUN_COL = '?'
#TEST_DESCR_COL= '?'
#
#
#ELMS_NAME_MAP = {
#            TEST_CASE_COL: mr.TEST_CASE,
#            TEST_NAME_COL: mr.TEST_NAME,
#            TEST_RUN_COL: mr.TEST_RUN,
#            TEST_DESCR_COL: mr.TEST_DESCR,
#        }
#
#
#class ODSTestFile(mrunner.TestFile):
#
#    def __init__(self, path, sheets):
#        super(ODSTestFile, path)
#        self.sheets = sheets
#        self.odf = load(path)
#
#    def get_suites(self):
#        res = []
#        for sheet in self.odf.spreadsheet.getElementsByType(Table):
#            sheetName = sheet.getAttribute('name')
#            if sheetName not in self.sheets:
#                continue
#            data = {}
#            res.append((sheetName, data))
#        return res
#
#    def iter_suite(self, name):
#        raise NotImplementedError()
#
#    def _get_cell_val(self, cells_obj, cell_ind):
#        '''
#        Description: fetch values of ods cells
#        Author: edolinin
#        Parameters:
#           * cellsObj - reference to a cells list in ods file
#           * cellInd - cell index
#        Return: cell value in str format
#        '''
#
#        if cells_obj and cells_obj[cell_ind] and cells_obj[cell_ind].getElementsByType(P):
#            cell_val = map(lambda x: x.firstChild, cells_obj[cell_ind].getElementsByType(P))[0]
#            try:
#                cell_val = cell_val.data.encode('utf-8', 'replace') # convert to utf-8 format
#            except AttributeError:
#                if cell_val.hasChildNodes:
#                    cell_val = cell_val.firstChild.data.encode('utf-8', 'replace') # convert to utf-8 format
#        else:
#            cell_val = ""
#        self.logger.info(paramName + ": " + str(cell_val))
#        return str(cell_val)
#
#    def _build_headers(self, first_row):
#        '''
#        Description: build a dictionary of ods headers indexes
#        Author: edolinin
#        Parameters:
#           * first_row - first row of ods file
#        Return: none
#        '''
#
#        headers_cells = first_row.getElementsByType(TableCell)
#
#        for cell_ind in range(0,len(headers_cells)):
#            cell = self._get_cell_val(headers_cells, cell_ind, "Header " + str(cell_ind))
#            self.headers[cell] = cell_ind
#
#    def _run_test_loop(self, row):
#        '''
#        Description: run and report tests for a specific test case (row)
#        Author: edolinin
#        Parameters:
#           * row - reference to a row that should be run
#        '''
#
#        test_case = {}
#
#        cells = row.getElementsByType(TableCell)
#
#        test_name = self._get_cell_val(cells, self.headers['test name'], "Test name")
#        testCase[mr.TEST_NAME] = self._parse_parameters(testName)
#
#
#        if testCase[rm.TEST_NAME].startswith('START_GROUP'):
#            runGroup = self._get_cell_val(cells, self.headers['run'], "Run test")
#
#        testGroup, runGroup, saveGroupRows = self._check_for_group_start(testCase['test_name'], testGroup, runGroup, saveGroupRows, self.groups)
#
#        if runGroup == 'no' or testCase['test_name'].startswith('START_GROUP'):
#            if self.headers.has_key('tcms_test_case'):
#                self.groupTcmsTestCase = self._get_cell_val(cells, self.headers['tcms_test_case'], "Tcms test case")
#            if not self.groupDescription:
#                self.groupDescription = self._get_cell_val(cells, self.headers['test_description'], "Test Description") if self.headers.has_key('test_description') else None
#            return testGroup, runGroup, saveGroupRows
#
#        testCase['test_run'] = self._get_cell_val(cells, self.headers['run'], "Run test")
#        testCase['test_run'] = self._check_run_test_val(testCase['test_run'])
#
#        if runGroup and not re.match('\d+', runGroup) and re.match('yes', testCase['test_run'].lower()):
#            testCase['test_run'] = runGroup
#
#        if testCase['test_run'].lower() == 'no':
#            self.logger.info("Skipping test '%s'.\n%s",
#                         testCase['test_name'], TESTS_LOG_SEPARATOR)
#            return testGroup, runGroup, saveGroupRows
#
#        testCase['test_type'] = self._get_cell_val(cells, self.headers['test_type'], "Test type") \
#                                if self.headers.has_key('test_type') else ""
#        if not testCase['test_type'].strip():
#            testCase['test_type'] = opts['type']
#
#        testCase['test_action'] = self._get_cell_val(cells, self.headers['test action'], "Test action")
#
#        testCase['test_parameters'] = self._get_cell_val(cells, self.headers['parameters'], "Test parameters")
#
#        testCase['test_positive'] = self._get_cell_val(cells, self.headers['positive'], "Test positive") if self.headers.has_key('positive') else ""
#
#        testCase['test_report'] = self._get_cell_val(cells, self.headers['report'], "Report test") if self.headers.has_key('report') else "yes"
#
#        testCase['fetch_output_to'] = self._get_cell_val(cells, self.headers['fetch_output'], "Fetch output") if self.headers.has_key('fetch_output') else ""
#
#        testCase['test_vital'] = self._get_cell_val(cells, self.headers['vital'], "Vital test") if self.headers.has_key('vital') else "false"
#
#        if self.groupTcmsTestCase:
#            testCase['tcms_test_case'] = self.groupTcmsTestCase
#        else:
#            testCase['tcms_test_case'] = self._get_cell_val(cells, self.headers['tcms_test_case'], "Tcms test case") if self.headers.has_key('tcms_test_case') else ""
#
#        testCase['test_description'] = self._get_cell_val(cells, self.headers['test_description'], "Test Description") if self.headers.has_key('test_description') else ""
#
#        testCase['id'] = self._get_cell_val(cells, self.headers['id'], "Test Id") \
#            if self.headers.has_key('id') else None
#
#        testCase['bz'] = self._get_cell_val(cells, self.headers['bz'], "Test BZ") \
#            if self.headers.has_key('bz') else None
#
#        testCase['conf'] = self._get_cell_val(cells, self.headers['conf'], \
#            "Change Global Conf Values") if self.headers.has_key('conf') else None
#
#
#class ODSTestParser(Component):
#    """
#    Plugin allows to matrix_based runner to parse ODS tests
#    """
#    implements(mrunner.IMatrixBasedParser, IConfigurable)
#    name = 'XML test parser'
#
#    def is_able_to_run(self, ti):
#        ext = os.path.splitext(ti)[1].lower()
#        if ext != '.ods':
#            return False
#        return True
#
#    def provide_test_file(self):
#        return ODSTestFile(self.path_test, self.sheet_list)
#
#    @classmethod
#    def add_options(cls, parser):
#        pass
#
#    def configure(self, params, conf):
#        # these sections there don't have to be there.
#        self.path_test = conf[RUN_SEC][TESTS_FILE]
#        self.sheet_list = []
#        if TESTS_SHEETS in conf[RUN_SEC]:
#            self.sheet_list = conf[RUN_SEC].as_list(TESTS_SHEETS)
#
#
#    @classmethod
#    def is_enabled(cls, a, b):
#        return True
