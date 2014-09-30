import art.rhevm_api.tests_lib.low_level.clusters as llclusters
import art.rhevm_api.tests_lib.low_level.datacenters as lldatacenters
import art.rhevm_api.tests_lib.low_level.hosts as llhosts
import art.rhevm_api.tests_lib.low_level.storagedomains as llstoragedomains
import art.rhevm_api.tests_lib.low_level.vms as llvms

from art.test_handler.exceptions import VMException
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.unittest_lib import attr
import unittest_conf
from utilities.rhevm_tools.log_collector import LogCollectorUtility
import logging

from rhevmtests.system.rhevm_utils import base

LOG_COLLECTOR_TEST_PLAN = 3748
NAME = 'log_collector'
LOGGER = logging.getLogger(__name__)
DISK_SIZE = 6 * 1024 * 1024 * 1024


def setup_module():
    if unittest_conf.GOLDEN_ENV:
        LOGGER.info("Golden environment - skipping setup_module")
        return
    base.setup_module()


def teardown_module():
    if unittest_conf.GOLDEN_ENV:
        LOGGER.info("Golden environment - skipping teardown_module")
        return
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
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(action='list')
        self.ut.autoTest()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95162)
    def test_log_collector_collect(self):
        """ log_collector collect"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(action='collect')
        self.ut.autoTest()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 337745)
    def test_log_collector_collect_verbosity(self):
        """test different verbosity levels"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)

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
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        args = {'no-postgresql': None}
        self.ut(action='collect', kwargs=args)
        self.ut.autoTest()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 337746)
    def test_log_collector_collect_no_hypervisors(self):
        """skip host data"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        args = {'no-hypervisors': None}
        self.ut(action='collect', kwargs=args)
        self.ut.autoTest()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95169)
    def test_log_collector_collect_single_host(self):
        """collect logs from a specified host"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)

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

        assert lldatacenters.addDataCenter(
            positive=True,
            name=unittest_conf.NEW_DC_NAME,
            storage_type=unittest_conf.STORAGE_TYPE,
            version=unittest_conf.COMP_VERSION)
        assert llclusters.addCluster(
            positive=True,
            name=unittest_conf.NEW_CLUSTER_NAME,
            cpu=unittest_conf.CPU_NAME,
            data_center=unittest_conf.NEW_DC_NAME,
            version=unittest_conf.COMP_VERSION)

    def tearDown(self):
        assert llclusters.removeCluster(
            True, unittest_conf.NEW_CLUSTER_NAME)
        assert lldatacenters.removeDataCenter(
            True, unittest_conf.NEW_DC_NAME)
        super(LogCollectorMoreDCs, self).tearDown()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95167)
    def test_log_collector_empty_cluster(self):
        """collect logs from specific cluster"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        args = {'cluster': unittest_conf.NEW_CLUSTER_NAME}
        self.ut(action='collect', kwargs=args)
        self.ut.autoTest()
        assert 'No hypervisors were selected' in self.ut.out

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95166)
    def test_log_collector_collect_empty_DC(self):
        """collect logs from single data center"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        args = {'data-center': unittest_conf.NEW_DC_NAME}
        self.ut(action='collect', kwargs=args)
        self.ut.autoTest()
        assert 'No hypervisors were selected' in self.ut.out

    @tcms(LOG_COLLECTOR_TEST_PLAN, 95165)
    def test_log_collector_list_empty_DC(self):
        """ log_collector list empty data center"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        args = {'data-center': unittest_conf.NEW_DC_NAME}
        self.ut(action='list', kwargs=args)
        assert 'No hypervisors were found' in self.ut.out


@attr(tier=1)
class LogCollectorRegressionBz1058894(base.RHEVMUtilsTestCase):
    """ Regression tests for the log-collector """

    __test__ = unittest_conf.STORAGE_TYPE == 'iscsi'
    utility = NAME
    utility_class = LogCollectorUtility

    def setUp(self):
        if unittest_conf.GOLDEN_ENV:
            return
        super(LogCollectorRegressionBz1058894, self).setUp()
        self.host = unittest_conf.HOSTS[0]
        cluster = 'cluster_' + unittest_conf.BASENAME
        self.vm_name = unittest_conf.VM_NAME[0]

        storagedomains = llstoragedomains.get_storagedomain_names()
        assert storagedomains
        assert llvms.createVm(
            True, self.vm_name, 'description does not matter',
            cluster=cluster, size=DISK_SIZE, nic='nic0',
            storageDomainName=storagedomains[0])
        assert llvms.startVm(True, self.vm_name)

    def tearDown(self):
        if unittest_conf.GOLDEN_ENV:
            return
        if not llvms.removeVm(positive=True, vm=self.vm_name, stopVM='true'):
            raise VMException("Cannot remove vm %s" % self.vm_name)
        LOGGER.info("Successfully removed %s.", self.vm_name)

        super(LogCollectorRegressionBz1058894, self).tearDown()

    @tcms(LOG_COLLECTOR_TEST_PLAN, 339921)
    def test_log_collector_bug_1058894(self):
        """ collect from host running a VM on iSCSI storage"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(action='collect')
        self.ut.autoTest()
