import art.rhevm_api.tests_lib.low_level.clusters as llclusters
import art.rhevm_api.tests_lib.low_level.datacenters as lldatacenters
import art.rhevm_api.tests_lib.low_level.hosts as llhosts
import art.rhevm_api.tests_lib.low_level.storagedomains as llstoragedomains
import art.rhevm_api.tests_lib.low_level.vms as llvms

from art.test_handler.exceptions import VMException
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.unittest_lib import attr
from unittest_conf import REST_API_PASS, LOG_COL_CONF
from utilities.rhevm_tools.log_collector import LogCollectorUtility
from art.test_handler.settings import ART_CONFIG
import logging

from rhevmtests.system.rhevm_utils import base

LOG_COLLECTOR_TEST_PLAN = 3748
NAME = 'log_collector'
LOGGER = logging.getLogger(__name__)
DISK_SIZE = 6 * 1024 * 1024 * 1024


def setup_module():
    base.setup_module()


def teardown_module():
    base.teardown_module()


@attr(tier=0)
class LogCollectorSingleDC(base.RHEVMUtilsTestCase):
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

        hosts = llhosts.get_host_list()
        args = {'hosts': hosts[0].address}

        self.ut(action='collect', kwargs=args)
        self.ut.autoTest()


@attr(tier=1)
class LogCollectorMoreDCs(base.RHEVMUtilsTestCase):
    """ Tests with additional DC and cluster """

    __test__ = True
    utility = NAME
    utility_class = LogCollectorUtility
    _multiprocess_can_split_ = True

    def setUp(self):
        super(LogCollectorMoreDCs, self).setUp()
        self.config = ART_CONFIG['PARAMETERS']
        datacenter_name = self.config.get('new_datacenter_name')

        assert lldatacenters.addDataCenter(
            positive=True,
            name=datacenter_name,
            storage_type=self.config.get('data_center_type'),
            version=self.config.get('compatibility_version'))
        assert llclusters.addCluster(
            positive=True,
            name=self.config.get('new_cluster_name'),
            cpu=self.config.get('cpu_family'),
            data_center=datacenter_name,
            version=self.config.get('compatibility_version'))

    def tearDown(self):
        assert llclusters.removeCluster(
            True,
            self.config.get('new_cluster_name'))
        assert lldatacenters.removeDataCenter(
            True,
            self.config.get('new_datacenter_name'))
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


@attr(tier=1)
class LogCollectorRegressionBz1058894(base.RHEVMUtilsTestCase):
    """ Regression tests for the log-collector """

    __test__ = ART_CONFIG['PARAMETERS'].get('storage_type') == 'iscsi'
    utility = NAME
    utility_class = LogCollectorUtility

    def setUp(self):
        super(LogCollectorRegressionBz1058894, self).setUp()
        self.config = ART_CONFIG['PARAMETERS']
        self.host = self.config.as_list('vds')[0]
        cluster = 'cluster_' + self.config.get('basename')
        self.vm_name = self.config.get('vm_name')

        storagedomains = llstoragedomains.get_storagedomain_names()
        assert storagedomains
        assert llvms.createVm(
            True, self.vm_name, 'description does not matter',
            cluster=cluster, size=DISK_SIZE, nic='nic0',
            storageDomainName=storagedomains[0])
        assert llvms.startVm(True, self.vm_name)

    def tearDown(self):
        if not llvms.removeVm(positive=True, vm=self.vm_name, stopVM='true'):
            raise VMException("Cannot remove vm %s" % self.vm_name)
        LOGGER.info("Successfully removed %s.", self.vm_name)

        super(LogCollectorRegressionBz1058894, self).tearDown()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 339921)
    def test_log_collector_bug_1058894(self):
        """ collect from host running a VM on iSCSI storage"""
        assert self.ut.setRestConnPassword(NAME, LOG_COL_CONF, REST_API_PASS)
        self.ut(action='collect')
        self.ut.autoTest()
