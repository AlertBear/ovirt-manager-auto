from art.rhevm_api.tests_lib.low_level.clusters import addCluster, \
    removeCluster
from art.rhevm_api.tests_lib.low_level.datacenters import addDataCenter, \
    removeDataCenter
from art.rhevm_api.tests_lib.low_level.hosts import get_host_list

from art.test_handler.exceptions import DataCenterException
from art.test_handler.tools import tcms
from rhevm_utils.base import RHEVMUtilsTestCase, REST_API_PASS, LOG_COL_CONF
from utilities.rhevm_tools.log_collector import LogCollectorUtility
from . import ART_CONFIG

LOG_COLLECTOR_TEST_PLAN = 3748
NAME = 'log_collector'


class LogCollectorSingleDC(RHEVMUtilsTestCase):
    """ Tests with single DC and single cluster setup """

    __test__ = True
    utility = NAME
    utility_class = LogCollectorUtility
    _multiprocess_can_split_ = True

    @tcms(LOG_COLLECTOR_TEST_PLAN, 275493)
    def test_log_collector_list(self):
        """ log_collector list"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)
        self.ut(action='list')
        self.ut.autoTest()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95162)
    def test_log_collector_collect(self):
        """ log_collector collect"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)
        self.ut(action='collect')
        self.ut.autoTest()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 337745)
    def test_log_collector_collect_verbosity(self):
        """test different verbosity levels"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)

        self.ut(action='collect')
        normalLines = len(self.ut.out.split('\n'))
        args = {'quiet': None}
        self.ut(action='collect', kwargs=args)
        quietLines = len(self.ut.out.split('\n'))
        args = {'verbose': None}
        self.ut(action='collect', kwargs=args)
        verboseLines = len(self.ut.out.split('\n'))

        assert verboseLines > normalLines > quietLines

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95174)
    def test_log_collector_version(self):
        """log_collector --version"""
        args = {'version': None}
        self.ut(kwargs=args)
        reportedVersion = self.ut.out.rstrip().split('-', 1)[1]

        cmd = ['rpm', '-qa', '*log-collector*']
        self.ut.execute(None, cmd)
        assert reportedVersion in self.ut.out

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95172)
    def test_log_collector_help(self):
        """log_collector --help"""
        args = {'help': None}
        self.ut(kwargs=args)
        self.ut.autoTest()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95168)
    def test_log_collector_collect_no_postgres(self):
        """collect data skipping postregs"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)
        args = {'no-postgresql': None}
        self.ut(action='collect', kwargs=args)
        self.ut.autoTest()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 337746)
    def test_log_collector_collect_no_hypervisors(self):
        """skip host data"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)
        args = {'no-hypervisors': None}
        self.ut(action='collect', kwargs=args)
        self.ut.autoTest()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95169)
    def test_log_collector_collect_single_host(self):
        """collect logs from a specified host"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)

        hosts = get_host_list()
        args = {'hosts': hosts[0].address}

        self.ut(action='collect', kwargs=args)
        self.ut.autoTest()


class LogCollectorMoreDCs(RHEVMUtilsTestCase):
    """ Tests with additional DC and cluster """

    __test__ = True
    utility = NAME
    utility_class = LogCollectorUtility
    _multiprocess_can_split_ = True

    def setUp(self):
        super(LogCollectorMoreDCs, self).setUp()
        self.config = ART_CONFIG['PARAMETERS']

        if not (addDataCenter(positive=True,
                              name=self.config.get('new_datacenter_name'),
                              storage_type=self.config.get('data_center_type'),
                              version=self.config.get('compatibility_version'))
                and
                addCluster(positive=True,
                           name=self.config.get('new_cluster_name'),
                           cpu=self.config.get('cpu_family'),
                           data_center=self.config.get('new_datacenter_name'),
                           version=self.config.get('compatibility_version'))):
            raise DataCenterException("Failed to create second DC and Cluster")

    def tearDown(self):
        if not (removeCluster(True, self.config.get('new_cluster_name')) and
                removeDataCenter(True,
                                 self.config.get('new_datacenter_name'))):
            raise DataCenterException("Failed to remove second DC and Cluster")
        super(LogCollectorMoreDCs, self).tearDown()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95167)
    def test_log_collector_empty_cluster(self):
        """collect logs from specific cluster"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)
        args = {'cluster': self.config.get('new_cluster_name')}
        self.ut(action='collect', kwargs=args)
        self.ut.autoTest()
        assert 'No hypervisors were selected' in self.ut.out

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95166)
    def test_log_collector_collect_empty_DC(self):
        """collect logs from single data center"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)
        args = {'data-center': self.config.get('new_datacenter_name')}
        self.ut(action='collect', kwargs=args)
        self.ut.autoTest()
        assert 'No hypervisors were selected' in self.ut.out

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95165)
    def test_log_collector_list_empty_DC(self):
        """ log_collector list empty data center"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)
        args = {'data-center': self.config.get('new_datacenter_name')}
        self.ut(action='list', kwargs=args)
        assert 'No hypervisors were found' in self.ut.out
