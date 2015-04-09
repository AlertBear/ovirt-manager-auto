"""
    rhevm cleanup module
"""

from rhevmtests.system.rhevm_utils.base import RHEVMUtilsTestCase
from utilities.rhevm_tools.cleanup import CleanUpUtility
import os
import logging
from art.test_handler.tools import tcms
import unittest_conf
from art.unittest_lib import attr

logger = logging.getLogger(__name__)

NAME = 'cleanup'
TCMS_PLAN = 4657
host = unittest_conf.VDC_HOST

_multiprocess_can_split_ = True


@attr(extra_reqs={'utility': NAME})
class CleanUpTestCaseBase(RHEVMUtilsTestCase):
    """
        rhevm cleanup test cases
    """

    __test__ = True
    utility = NAME
    utility_class = CleanUpUtility
    _multiprocess_can_split_ = True

    def create_answer_file(self):
        ans = os.path.join('/tmp', 'cleanup_answer_file')
        params = self.ut.setup.getInstallParams(
            '__default__', unittest_conf.config['CLEANUP_ANSWERS'])
        self.ut.setup.fillAnswerFile(ans, **params)
        logger.info("%s: clean engine with %s", host, params)


@attr(tier=0, extra_reqs={'utility': NAME})
class CleanUpTestCase(CleanUpTestCaseBase):

    __test__ = True

    @tcms(TCMS_PLAN, 296506)
    def test_clean_up(self):
        """ clean_Up """
        self.create_answer_file()
        self.ut(config_append=self.c['cleanup_answer_file'])
        self.ut.autoTest()

    @tcms(TCMS_PLAN, 296481)
    def test_generating_answer_file(self):
        """ generating_Answer_File """
        self.create_answer_file()
        self.ut(config_append=self.c['cleanup_answer_file'],
                generate_answer=self.c['new_cleanup_ans_file'])
        self.ut.testGenerateAnswerFile()

    @tcms(TCMS_PLAN, 296462)
    def test_generating_log(self):
        """ generating_log """
        self.create_answer_file()
        self.ut(config_append=self.c['cleanup_answer_file'],
                log=self.c['cleanup_log_file'])
        self.ut.testGenerateLogFile()
