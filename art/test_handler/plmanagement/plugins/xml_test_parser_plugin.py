
import os
import inspect

from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
import matrix_test_runner_plugin as mr
from lxml import etree
from art.test_handler import find_test_file

logger = get_logger('xml-test-parser')

RUN_SEC = 'RUN'
TESTS_FILE = 'tests_file'
ROOT_SUITE = 'root_suite'
TEST_CASE_TAG = 'test_case'

priority = 10000

class XMLTestFile(mr.TestFile):
    """
    Parses XML test file and provides an iteration of test elements.
    """
    def __init__(self, path, lines):
        path_to_test = find_test_file(path)
        super(XMLTestFile, self).__init__(path_to_test)
        self.tree = etree.parse(os.path.abspath(self.path))
        self.tree.xinclude()
        self.lines = lines

    def get_suites(self):
        root = self.tree.getroot()
        tcms_id = root.attrib.get('tcms_plan_id', None)
        description = self.__get_description(root)
        return [
                (ROOT_SUITE,
                    {'test_name': ROOT_SUITE,
                     'tcms_plan_id': tcms_id,
                     'workers': 1,
                     'description': description,
                    }
                )
               ]

    def __get_description(self, root):
        try:
            for elm in root:
                if not elm.tag is etree.Comment:
                    continue
                if elm.text is None:
                    continue
                if "TEST_DESCRIPTION" not in elm.text:
                    continue
                return elm.text
        except Exception:
            logger.debug("Reading description failed: %s", self.path, \
                    exc_info=True)
        return None

    def iter_suite(self, name):
        """
        Returns iterator of test suite elements.
        """
        return self.__iter__()

    def __iter__(self):
        from art.test_handler.test_runner import TestGroup
        smembers = [x[1] for x in inspect.getmembers(TestGroup,
                    lambda x: not(inspect.isroutine(x)))]
        for line, elm in enumerate(self.tree.getiterator(tag=TEST_CASE_TAG), 1):
            if self.lines and line not in self.lines:
                continue
            elm = dict((x.tag, x.text) for x in elm.getchildren()
                       if x.text is not None and isinstance(x.tag, str)
                       and x.tag in smembers)
            yield elm
        raise StopIteration()


class XMLTestParser(Component):
    """
    Plugin allows to matrix_based runner to parse XML tests
    """
    implements(mr.IMatrixBasedParser, IConfigurable, IPackaging)
    name = 'XML test parser'
    enabled = True

    def __init__(self):
        self.path_test = None
        self.lines = []

    def is_able_to_run(self, ti):
        if not ti.lower().endswith('.xml'):
            self.path_test = None
            return False
        self.path_test = ti
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

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Test parser for matrix-based test runnner'
        params['long_description'] = 'Plugin for ART. '\
                                'Allows to matrix-based test runner run '\
                                'tests written in XML format.'
        params['requires'] = ['art-plugin-matrix-based-test-composer']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.xml_test_parser_plugin']

