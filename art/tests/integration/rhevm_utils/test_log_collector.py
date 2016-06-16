import art.rhevm_api.tests_lib.low_level.clusters as llclusters
import art.rhevm_api.tests_lib.low_level.datacenters as lldatacenters
import art.rhevm_api.tests_lib.low_level.hosts as llhosts
import art.rhevm_api.tests_lib.low_level.storagedomains as llstoragedomains
import art.rhevm_api.tests_lib.low_level.vms as llvms

from art.test_handler.exceptions import VMException
from art.test_handler.settings import opts
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.unittest_lib import attr
from rhevm_utils import base, unittest_conf
from utilities.rhevm_tools.log_collector import LogCollectorUtility
import logging

LOG_COLLECTOR_TEST_PLAN = 3748
NAME = 'log_collector'
LOGGER = logging.getLogger(__name__)
DISK_SIZE = 6 * 1024 * 1024 * 1024
ISCSI = unittest_conf.STORAGE_TYPE_ISCSI


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


class LogCollectorTestCaseBase(base.RHEVMUtilsTestCase):
    """
    rhevm-log-collector testcase
    """

    __test__ = True
    utility = NAME
    utility_class = LogCollectorUtility
    _multiprocess_can_split_ = True

    def setUp(self):
        super(LogCollectorTestCaseBase, self).setUp()
        self.kwargs = {}
        if unittest_conf.OUTPUT_DIR:
            self.kwargs = {'output': unittest_conf.OUTPUT_DIR}
            LOGGER.info("Output directory specified: %s.",
                        unittest_conf.OUTPUT_DIR)
        self.host = unittest_conf.HOSTS[0]
        self.vm_name = unittest_conf.VM_NAME
        self.cluster = unittest_conf.CLUSTER_NAME


@attr(tier=1)
class LogCollectorSingleDC(LogCollectorTestCaseBase):
    """ Tests with single DC and single cluster setup """

    @polarion("RHEVM3-7998")
    def test_log_collector_list(self):
        """ log_collector list"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(action='list', kwargs=self.kwargs)
        self.ut.autoTest()

    @bz({'1218526': {}})
    @polarion("RHEVM3-7989")
    def test_log_collector_collect(self):
        """ log_collector collect"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(action='collect', kwargs=self.kwargs)
        self.ut.autoTest()

    @polarion("RHEVM3-8003")
    def test_log_collector_collect_verbosity(self):
        """test different verbosity levels"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)

        self.ut(action='collect', kwargs=self.kwargs)
        normalLines = len(self.ut.out.split('\n'))
        kwargs = {'quiet': None}
        kwargs.update(self.kwargs)
        self.ut(action='collect', kwargs=kwargs)
        quietLines = len(self.ut.out.split('\n'))
        kwargs = {'verbose': None}
        kwargs.update(self.kwargs)
        self.ut(action='collect', kwargs=kwargs)
        verboseLines = len(self.ut.out.split('\n'))

        assert verboseLines > normalLines > quietLines

    @polarion("RHEVM3-8019")
    def test_log_collector_version(self):
        """log_collector --version"""
        kwargs = {'version': None}
        self.ut(kwargs=kwargs)
        reportedVersion = self.ut.out.rstrip().split('-', 1)[1].split('_')[0]

        cmd = ['rpm', '-qa', '\*log-collector\*']
        self.ut.execute(None, cmd)
        assert reportedVersion in self.ut.out

    @polarion("RHEVM3-8017")
    def test_log_collector_help(self):
        """log_collector --help"""
        kwargs = {'help': None}
        self.ut(kwargs=kwargs)
        self.ut.autoTest()

    @bz({'1218526': {}})
    @polarion("RHEVM3-8013")
    def test_log_collector_collect_no_postgres(self):
        """collect data skipping postregs"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        kwargs = {'no-postgresql': None}
        kwargs.update(self.kwargs)
        self.ut(action='collect', kwargs=kwargs)
        self.ut.autoTest()

    @bz({'1218526': {}})
    @polarion("RHEVM3-8004")
    def test_log_collector_collect_no_hypervisors(self):
        """skip host data"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        kwargs = {'no-hypervisors': None}
        kwargs.update(self.kwargs)
        self.ut(action='collect', kwargs=kwargs)
        self.ut.autoTest()

    @bz({'1218526': {}})
    @polarion("RHEVM3-8014")
    def test_log_collector_collect_single_host(self):
        """collect logs from a specified host"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)

        hosts = llhosts.get_host_list()
        kwargs = {'hosts': hosts[0].address}
        kwargs.update(self.kwargs)
        self.ut(action='collect', kwargs=kwargs)
        self.ut.autoTest()


@attr(tier=2)
class LogCollectorMoreDCs(LogCollectorTestCaseBase):
    """ Tests with additional DC and cluster """

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
        assert lldatacenters.remove_datacenter(
            True, unittest_conf.NEW_DC_NAME)
        super(LogCollectorMoreDCs, self).tearDown()

    @bz({'1218526': {}})
    @polarion("RHEVM3-8012")
    def test_log_collector_empty_cluster(self):
        """collect logs from specific cluster"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        kwargs = {'cluster': unittest_conf.NEW_CLUSTER_NAME}
        kwargs.update(self.kwargs)
        self.ut(action='collect', kwargs=kwargs)
        self.ut.autoTest()
        assert 'No hypervisors were selected' in self.ut.out

    @bz({'1218526': {}})
    @polarion("RHEVM3-8011")
    def test_log_collector_collect_empty_DC(self):
        """collect logs from single data center"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        kwargs = {'data-center': unittest_conf.NEW_DC_NAME}
        kwargs.update(self.kwargs)
        self.ut(action='collect', kwargs=kwargs)
        self.ut.autoTest()
        assert 'No hypervisors were selected' in self.ut.out

    @polarion("RHEVM3-8010")
    def test_log_collector_list_empty_DC(self):
        """ log_collector list empty data center"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        kwargs = {'data-center': unittest_conf.NEW_DC_NAME}
        kwargs.update(self.kwargs)
        self.ut(action='list', kwargs=kwargs)
        assert 'No hypervisors were found' in self.ut.out


@attr(tier=2)
class LogCollectorRegressionBz1058894(LogCollectorTestCaseBase):
    """ Regression tests for the log-collector """

    __test__ = (ISCSI in opts['storages'])
    storages = set([ISCSI])

    def setUp(self):
        if unittest_conf.GOLDEN_ENV:
            return
        super(LogCollectorRegressionBz1058894, self).setUp()
        storage_domain = llstoragedomains.get_master_storage_domain_name(
            unittest_conf.DC_NAME
        )
        assert storage_domain
        LOGGER.info('Adding VM to SD: %s' % storage_domain)
        assert llvms.createVm(
            True, self.vm_name, 'description does not matter',
            cluster=self.cluster, provisioned_size=DISK_SIZE, nic='nic0',
            storageDomainName=storage_domain)
        assert llvms.startVm(True, self.vm_name)

    def tearDown(self):
        if unittest_conf.GOLDEN_ENV:
            return
        if not llvms.removeVm(positive=True, vm=self.vm_name, stopVM='true'):
            raise VMException("Cannot remove vm %s" % self.vm_name)
        LOGGER.info("Successfully removed %s.", self.vm_name)

        super(LogCollectorRegressionBz1058894, self).tearDown()

    @polarion("RHEVM3-8023")
    def test_log_collector_bug_1058894(self):
        """ collect from host running a VM on iSCSI storage"""
        assert self.ut.setRestConnPassword(NAME, unittest_conf.LOG_COL_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(action='collect', kwargs=self.kwargs)
        self.ut.autoTest()
