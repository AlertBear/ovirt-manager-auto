from rhevm_utils.base import RHEVMUtilsTestCase, istest, logger, \
    REST_API_PASS, LOG_COL_CONF
from utilities.rhevm_tools.log_collector import  LogCollectorUtility

NAME = 'log_collector'


class LogCollectorTestCase(RHEVMUtilsTestCase):

    __test__ = True
    utility = NAME
    utility_class = LogCollectorUtility
    _multiprocess_can_split_ = True

    @istest
    def logCollectorList(self):
        """ log_collector list"""
        print ("debug: Inside logCollectorList function")
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)
        self.ut('list')
        self.ut.autoTest()

    @istest
    def logCollectorCollect(self):
        """ log_collector collect"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)
        self.ut('collect')
        self.ut.autoTest()



