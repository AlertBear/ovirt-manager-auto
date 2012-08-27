
import os

from art.test_handler.plmanagement import Component, implements, get_logger, PluginError
from art.test_handler.plmanagement.interfaces.application import ITestParser, IConfigurable
#import art.test_handler.plmanagement.plugins.matrix_test_runner_plugin as mrunner
import matrix_test_runner_plugin as mrunner
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

ROOT_SUITE = 'root_suite'


ELMS_NAME_MAP = {
            TEST_CASE_TAG: mrunner.TEST_CASE,
            TEST_ID_TAG: mrunner.TEST_ID,
            TEST_CONF_TAG: mrunner.TEST_CONF,
            TEST_NAME_TAG: mrunner.TEST_NAME,
            TEST_RUN_TAG: mrunner.TEST_RUN,
            TEST_DESCR_TAG: mrunner.TEST_DESCR,
            TEST_ACTION_TAG: mrunner.TEST_ACTION,
            TEST_PARAMS_TAG: mrunner.TEST_PARAMS,
            TEST_POSITIVE_TAG: mrunner.TEST_POSITIVE,
            TEST_REPORT_TAG: mrunner.TEST_REPORT,
            TEST_FETCH_OUTPUT_TAG: mrunner.TEST_FETCH_OUTPUT,
            TEST_BZ_ID_TAG: mrunner.TEST_BZ_ID,
            TEST_VITAL_TAG: mrunner.TEST_VITAL,
        }


class XMLTestFile(mrunner.TestFile):

    def __init__(self, path):
        super(XMLTestFile, self).__init__(path)
        self.tree = etree.parse(os.path.abspath(self.path))
        self.tree.xinclude()

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
        for elm in self.tree.getiterator(tag=TEST_CASE_TAG):
            elm = dict((ELMS_NAME_MAP[x.tag], x.text) \
                    for x in elm.getchildren() if x.text is not None \
                    and x.tag in ELMS_NAME_MAP)
            positive = elm.get(mrunner.TEST_POSITIVE, 'none').lower()
            elm[mrunner.TEST_POSITIVE] = {'none': None, 'true': True, 'false': False}[positive]
            if mrunner.TEST_PARAMS not in elm:
                elm[mrunner.TEST_PARAMS] = str()
            if mrunner.TEST_FETCH_OUTPUT not in elm:
                elm[mrunner.TEST_FETCH_OUTPUT] = None
            elm[mrunner.TEST_REPORT] = mrunner.get_attr_as_bool(elm, mrunner.TEST_REPORT)
            elm[mrunner.TEST_VITAL] = mrunner.get_attr_as_bool(elm, mrunner.TEST_VITAL, default='no')
            if mrunner.TEST_RUN not in elm:
                elm[mrunner.TEST_RUN] = 'yes'
            yield elm


class XMLTestParser(Component):
    """
    Plugin allows to matrix_based runner to parse XML tests
    """
    implements(mrunner.IMatrixBasedParser, IConfigurable)
    name = 'XML test parser'
    enabled = True

    def __init__(self):
        self.path_test = None

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
        return XMLTestFile(self.path_test)

    @classmethod
    def add_options(cls, parser):
        pass

    def configure(self, params, conf):
        if self.path_test is None:
            XMLTestParser.enabled = False


    @classmethod
    def is_enabled(cls, a, b):
        return cls.enabled
