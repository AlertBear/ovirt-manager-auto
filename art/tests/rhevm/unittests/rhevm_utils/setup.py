"""
    rhevm setup module
"""

from rhevm_utils.base import RHEVMUtilsTestCase, config, istest
from utilities.rhevm_tools.setup import SetupUtility, getInstallParams

NAME = 'setup'
_multiprocess_can_split_ = True


class SetupTestCase(RHEVMUtilsTestCase):
    """
        rhevm setup test cases
    """
    __test__ = True
    utility = NAME
    utility_class = SetupUtility
    clear_snap = 'clear_machine'
    _multiprocess_can_split_ = True

    @istest
    def generatingAnswerFile(self):
        """ generating_Answer_File """
        self.ut(gen_answer_file=self.c['answer_file'])
        self.ut.testGenerateAnswerFile()

    @istest
    def installSetup(self):
        """ install_Setup """
        self.generatingAnswerFile()
        params = getInstallParams(self.ut.setup.rpmVer, self.c,
                                  config.get('ANSWERS', {}))
        self.ut.fillAnswerFile(**params)
        self.ut(answer_file='host:'+self.c['answer_file'])
        self.ut.testInstallation()
