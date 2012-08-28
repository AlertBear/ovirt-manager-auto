
import os

from art.test_handler.plmanagement import Component, implements, get_logger, PluginError
from art.test_handler.plmanagement.interfaces.application import ITestParser, IConfigurable
#import art.test_handler.plmanagement.plugins.matrix_test_runner_plugin as rm
import matrix_test_runner_plugin as mr
from lxml import etree

logger = get_logger('xml-test-parser')

RUN_SEC = 'RUN'
TESTS_FILE = 'tests_file'

TEST_CASE_TAG = 'test_case'
TEST_ID_TAG = 'id'
TEST_NAME_TAG = 'test_name'
TEST_RUN_TAG = 'run'
TEST_DESCR_TAG = 'test_description'
TEST_ACTION_TAG = 'test_action'
TEST_PARAMS_TAG = 'parameters'
TEST_POSITIVE_TAG = 'positive'
TEST_REPORT_TAG = 'report'
TEST_FETCH_OUTPUT_TAG = 'fetch_output'
TEST_BZ_ID_TAG = 'bz'
TEST_VITAL_TAG = 'vital'
TEST_CONF_TAG = 'conf'
TEST_EXP_EVENTS_TAG = 'exp_events'
TEST_EXPECT_TAG = 'expect'

ROOT_SUITE = 'root_suite'


ELMS_NAME_MAP = {
            TEST_CASE_TAG: mr.TEST_CASE,
            TEST_ID_TAG: mr.TEST_ID,
            TEST_CONF_TAG: mr.TEST_CONF,
            TEST_NAME_TAG: mr.TEST_NAME,
            TEST_RUN_TAG: mr.TEST_RUN,
            TEST_DESCR_TAG: mr.TEST_DESCR,
            TEST_ACTION_TAG: mr.TEST_ACTION,
            TEST_PARAMS_TAG: mr.TEST_PARAMS,
            TEST_POSITIVE_TAG: mr.TEST_POSITIVE,
            TEST_REPORT_TAG: mr.TEST_REPORT,
            TEST_FETCH_OUTPUT_TAG: mr.TEST_FETCH_OUTPUT,
            TEST_BZ_ID_TAG: mr.TEST_BZ_ID,
            TEST_VITAL_TAG: mr.TEST_VITAL,
            TEST_EXP_EVENTS_TAG: mr.TEST_EXP_EVENTS,
            TEST_EXPECT_TAG: mr.TEST_EXPECTED_EXCEPTIONS,
        }


class XMLTestFile(mr.TestFile):

    def __init__(self, path, lines):
        super(XMLTestFile, self).__init__(path)
        self.tree = etree.parse(os.path.abspath(self.path))
        self.tree.xinclude()
        self.lines = lines

    def get_suites(self):
        return [
            ( ROOT_SUITE,
            {
            'test_name': ROOT_SUITE,
            'tcms_test_plan_id': self.tree.getroot().attrib.get('tcms_plan_id', None),
            'workers': 1,
            })
            ]

    def iter_suite(self, name):
        return self.__iter__()

    def __iter__(self):
        for line, elm in enumerate(self.tree.getiterator(tag=TEST_CASE_TAG), 1):
            if self.lines and line not in self.lines:
                continue
            elm = dict((ELMS_NAME_MAP[x.tag], x.text) \
                    for x in elm.getchildren() if x.text is not None \
                    and x.tag in ELMS_NAME_MAP)
            positive = elm.get(mr.TEST_POSITIVE, 'none').lower()
            elm[mr.TEST_POSITIVE] = {'none': None, 'true': True, 'false': False}[positive]
            if mr.TEST_PARAMS not in elm:
                elm[mr.TEST_PARAMS] = str()
            if mr.TEST_FETCH_OUTPUT not in elm:
                elm[mr.TEST_FETCH_OUTPUT] = None
            elm[mr.TEST_REPORT] = mr.get_attr_as_bool(elm, mr.TEST_REPORT)
            elm[mr.TEST_VITAL] = mr.get_attr_as_bool(elm, mr.TEST_VITAL, default='no')
            if mr.TEST_RUN not in elm:
                elm[mr.TEST_RUN] = 'yes'
            elm[mr.TEST_EXP_EVENTS] = int(elm.get(mr.TEST_EXP_EVENTS, 1))
            elm[mr.TEST_EXPECTED_EXCEPTIONS] = \
                    tuple(elm.get(mr.TEST_EXPECTED_EXCEPTIONS, '').replace(',', ' ').split())
            yield elm
        raise StopIteration()


class XMLTestParser(Component):
    """
    Plugin allows to matrix_based runner to parse XML tests
    """
    implements(mr.IMatrixBasedParser, IConfigurable)
    name = 'XML test parser'
    enabled = True

    def __init__(self):
        self.path_test = None
        self.lines = []

    def is_able_to_run(self, ti):
        self.path_test = os.path.abspath(ti)
        if not os.path.exists(self.path_test):
            import art
            self.path_test = os.path.join(os.path.dirname(art.__file__), ti)
            if not os.path.exists(self.path_test):
                return False
        ext = os.path.splitext(ti)[1].lower()
        if ext != '.xml':
            self.path_test = None
            return False
        return True

    def provide_test_file(self):
        return XMLTestFile(self.path_test, self.lines)

    @classmethod
    def add_options(cls, parser):
        pass

    def configure(self, params, conf):
        if self.path_test is None:
            return
        self.lines = params.lines


    @classmethod
    def is_enabled(cls, a, b):
        return True
