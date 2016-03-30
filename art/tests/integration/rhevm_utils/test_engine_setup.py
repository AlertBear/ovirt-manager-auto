"""
    rhevm setup module
"""
import os
import logging
from pprint import pformat

from rhevm_utils import base, unittest_conf
from utilities.rhevm_tools.setup import SetupUtility

from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr

logger = logging.getLogger(__name__)

NAME = 'setup'
_multiprocess_can_split_ = True

host = unittest_conf.VDC_HOST


@attr(extra_reqs={'utility': NAME})
class SetupTestCase(base.RHEVMUtilsTestCase):
    """
        rhevm setup test cases
    """
    __test__ = True
    utility = NAME
    utility_class = SetupUtility
    clear_snap = 'clear_machine'
    _multiprocess_can_split_ = True

    def create_answer_file(self):
        ans = os.path.join('/tmp', 'answer_file')
        params = self.ut.setup.getInstallParams(
            '__default__', unittest_conf.config['ANSWERS'])
        self.ut.setup.fillAnswerFile(ans, **params)
        logger.info("%s: install setup with %s", host, pformat(params))

    @polarion("RHEVM3-8037")
    def test_generating_answer_file(self):
        """ generating_Answer_File """
        self.create_answer_file()
        self.ut(config_append=self.c['answer_file'],
                generate_answer=self.c['new_ans_file'])
        self.ut.testGenerateAnswerFile()
        self.ut.setup.clean(unittest_conf.config)

    @polarion("RHEVM3-8039")
    def test_install_setup(self):
        """ install_Setup """
        self.create_answer_file()
        self.ut(config_append=self.c['answer_file'])
        self.ut.testInstallation()
