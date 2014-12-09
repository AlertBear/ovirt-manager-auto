"""
    rhevm cleanup module
"""

from rhevmtests.system.rhevm_utils import base
from utilities.rhevm_tools.cleanup import CleanUpUtility
import os
import logging
from unittest_conf import config, REST_API_HOST
from art.test_handler.tools import tcms
from art.unittest_lib import attr

logger = logging.getLogger(__name__)

NAME = 'cleanup'
TCMS_PLAN = 4657
host = REST_API_HOST

_multiprocess_can_split_ = True


@attr(tier=0)
class CleanUpTestCase(base.RHEVMUtilsTestCase):
    """
        rhevm cleanup test cases
    """

    __test__ = True
    utility = NAME
    utility_class = CleanUpUtility
    _multiprocess_can_split_ = True

    def create_answer_file(self):
        ans = os.path.join('/tmp', 'cleanup_answer_file')
        params = self.ut.setup.getInstallParams('__default__',
                                                config['CLEANUP_ANSWERS'])
        self.ut.setup.fillAnswerFile(ans, **params)
        logger.info("%s: clean engine with %s", host, params)

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
