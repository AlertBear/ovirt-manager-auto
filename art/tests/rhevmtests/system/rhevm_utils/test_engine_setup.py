"""
    rhevm setup module
"""
import os
import logging
from pprint import pformat

from rhevmtests.system.rhevm_utils import base
from utilities.rhevm_tools.setup import SetupUtility
import unittest_conf

from art.test_handler.tools import tcms
from art.unittest_lib import attr

logger = logging.getLogger(__name__)

NAME = 'setup'
TCMS_PLAN = 3749
_multiprocess_can_split_ = True

host = unittest_conf.VDC_HOST


@attr(tier=0)
class SetupTestCase(base.RHEVMUtilsTestCase):
    """
        rhevm setup test cases
    """
    __test__ = not unittest_conf.GOLDEN_ENV
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

    @tcms(TCMS_PLAN, 296387)
    def test_generating_answer_file(self):
        """ generating_Answer_File """
        self.create_answer_file()
        self.ut(config_append=self.c['answer_file'],
                generate_answer=self.c['new_ans_file'])
        self.ut.testGenerateAnswerFile()
        self.ut.setup.clean(unittest_conf.config)

    @tcms(TCMS_PLAN, 296383)
    def test_install_setup(self):
        """ install_Setup """
        self.create_answer_file()
        self.ut(config_append=self.c['answer_file'])
        self.ut.testInstallation()
