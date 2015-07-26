import config
import helpers
import logging
from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storageconnections
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd

from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as TestCase

from utilities.machine import Machine

sd_api = test_utils.get_api('storage_domain', 'storagedomains')

logger = logging.getLogger(__name__)
NFS = config.STORAGE_TYPE_NFS

# TODO: TestCasePosixFS will only be executed with nfs directories
# Make it compatible in the future with other storage types (glusterfs, ...)
# TODO: Add a new glusterfs class for testing if the same flows applies for
# glusterfs domains


def setup_module():
    """
    Creates data center, adds hosts, clusters, storages according to
    the config file for non-GE and removes one host for NFS/Posix cases
    Remove one host for GE
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config.PARAMETERS, config.PARAMETERS, config.STORAGE_TYPE,
            basename=config.TESTNAME,
            local=config.STORAGE_TYPE == config.ENUMS['storage_type_local']
        )

    if config.GOLDEN_ENV or config.STORAGE_TYPE == config.STORAGE_TYPE_NFS:
        # Remove the host, this is needed to copy the data between
        # storage domains
        assert hosts.deactivateHost(True, config.HOST_FOR_MOUNT)
        assert hosts.removeHost(True, config.HOST_FOR_MOUNT)


def teardown_module():
    """
    Clean the data center for non GE
    Add back host to the environment for GE
    """
    if not config.GOLDEN_ENV:
        datacenters.clean_datacenter(True, config.DATA_CENTER_NAME)
    else:
        assert hosts.addHost(
            True, name=config.HOST_FOR_MOUNT, cluster=config.CLUSTER_NAME,
            root_password=config.HOSTS_PW, address=config.HOST_FOR_MOUNT_IP
        )


# We're are not currently testing for local data centers
@attr(**{'extra_reqs': {'convert_to_ge': True}} if config.GOLDEN_ENV else {})
class TestCaseLocalFS(TestCase):
    __test__ = False
    sd_name = None
    conn = None
    machine = None

    def setUp(self):
        spm_host = hosts.getSPMHost(config.HOSTS_FOR_TEST)
        spm_user, spm_password = helpers.get_user_and_passwd_for_host(spm_host)
        self.machine = Machine(
            host=spm_host, user=spm_user, password=spm_password).util('linux')
        logger.info("Creating local storage path")
        try:
            rc, out = self.machine.createLocalStorage(self.path)
        except Exception, ex:
            logger.info(ex)
        logger.info("output: %s", out)
        assert rc

        self.host = spm_host
        self.password = spm_password
        logger.info("Looking for non-master sd domains")
        status, domains = storagedomains.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME)
        logger.info("Non master answer: %s %s" % (status, domains))
        assert status
        self.sd_name = domains['nonMasterDomains'][0]

        conns = storagedomains.getConnectionsForStorageDomain(self.sd_name)
        logger.info("Connections %s", conns)
        assert len(conns) == 1
        self.old_path = conns[0].path
        self.conn = conns[0].id

    def tearDown(self):
        if self.machine is not None:
            self.machine.removeFile(self.path)


# TODO: Enable this when
# https://projects.engineering.redhat.com/browse/RHEVM-2272 and
# https://projects.engineering.redhat.com/browse/RHEVM-2261
# will solved
@attr(**{'extra_reqs': {'convert_to_ge': True}} if config.GOLDEN_ENV else {})
class TestCasePosix(TestCase):
    __test__ = False
    conn = None
    host = None
    left_domains = []

    def setUp(self, storage_type, additional_params):
        self.address = config.DOMAIN_ADDRESSES[0]
        self.path = config.DOMAIN_PATHS[0]
        datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        self.host = hosts.getSPMHost(config.HOSTS_FOR_TEST)
        _, self.password = helpers.get_user_and_passwd_for_host(self.host)

        assert storagedomains.addStorageDomain(
            True, address=self.address, path=self.path,
            storage_type=storage_type, host=self.host,
            type=config.ENUMS['storage_dom_type_data'],
            name=self.sd_name, **additional_params
        )

        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        assert storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.sd_name,
            config.ENUMS['storage_domain_state_active'])

        conns = storagedomains.getConnectionsForStorageDomain(self.sd_name)
        assert len(conns) == 1
        self.conn = conns[0].id

    def tearDown(self, vfs_type):
        logger.info("Detaching and deactivating domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATA_CENTER_NAME)
        hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, self.sd_name)
        logger.info("Removing domain %s", self.sd_name)
        storagedomains.removeStorageDomain(
            True, self.sd_name, self.host, 'true'
        )
        for (addr, path, sd_id) in self.left_domains:
            logger.info("Cleaning domain %s:%s", addr, path)
            helpers.clean_posix_domain(
                addr, path, sd_id, config.HOST_FOR_MOUNT_IP, config.HOSTS_USER,
                config.HOSTS_PW, vfs_type
            )

    def default_update(self):
        pass

    def positive_flow(self, vfs_type):
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATA_CENTER_NAME)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        new_address = config.EXTRA_DOMAIN_ADDRESSES[0]
        new_path = config.EXTRA_DOMAIN_PATHS[0]

        helpers.copy_posix_sd(
            self.address, self.path, new_address, new_path,
            config.HOST_FOR_MOUNT_IP, config.HOSTS_USER, config.HOSTS_PW,
            vfs_type
        )

        sd = sd_api.find(self.sd_name)
        self.left_domains.append([self.address, self.path, sd.get_id()])

        logger.info("Changing connection")
        result = self.default_update()
        logger.info("result: %s", result)
        assert result

        logger.info("Activating storage domain %s", self.sd_name)
        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

    def change_connection_in_active_sd(self):
        """
        Change the storage connection used by an active storage domain should
        fail
        """
        logger.info("Changing storage connaction on active storage domain")
        self.assertFalse(
            self.default_update(),
            "Changing the storage connection used by an active storage domain "
            "should fail"
        )


# TODO: Enable this when
# https://projects.engineering.redhat.com/browse/RHEVM-2272 and
# https://projects.engineering.redhat.com/browse/RHEVM-2261
# will solved
@attr(**{'extra_reqs': {'convert_to_ge': True}} if config.GOLDEN_ENV else {})
class TestCaseNFS(TestCasePosix):
    def setUp(self):
        super(TestCaseNFS, self).setUp(NFS, {})

    def tearDown(self):
        super(TestCaseNFS, self).tearDown(NFS)

    def default_update(self):
        logger.info("params: %s" % config.PARAMETERS)
        new_address = config.EXTRA_DOMAIN_ADDRESSES[0]
        new_path = config.EXTRA_DOMAIN_PATHS[0]

        return storageconnections.update_connection(
            self.conn, address=new_address, path=new_path, type=NFS,
            nfs_version='V3', nfs_retrans=9, nfs_timeo=900, host=self.host)[1]


# TODO: Enable this when
# https://projects.engineering.redhat.com/browse/RHEVM-2272 and
# https://projects.engineering.redhat.com/browse/RHEVM-2261
# will solved
@attr(**{'extra_reqs': {'convert_to_ge': True}} if config.GOLDEN_ENV else {})
class TestCasePosixFS(TestCasePosix):
    def setUp(self):
        super(TestCasePosixFS, self).setUp(
            'posixfs', {'vfs_type': NFS})

    def tearDown(self):
        super(TestCasePosixFS, self).tearDown(NFS)

    def default_update(self):
        new_address = config.EXTRA_DOMAIN_ADDRESSES[0]
        new_path = config.EXTRA_DOMAIN_PATHS[0]

        return storageconnections.update_connection(
            self.conn, address=new_address, path=new_path, host=self.host,
            type='posixfs')[1]


@attr(tier=0)
class TestCase5251(TestCasePosixFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    storages = set([NFS])
    polarion_test_case = '5251'
    sd_name = "sd_%s" % polarion_test_case

    @polarion("RHEVM3-5251")
    def test_change_posixfs_connection(self):
        """ Tries to change a posixfs connection
        """
        self.positive_flow(NFS)


@attr(tier=0)
class TestCase5250(TestCaseNFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    storages = set([NFS])
    polarion_test_case = '5250'
    sd_name = "sd_%s" % polarion_test_case

    @polarion("RHEVM3-5250")
    def test_change_nfs_connection(self):
        """ Tries to change an nfs connection
        """
        self.positive_flow(NFS)


@attr(tier=1)
class TestCase5255(TestCasePosixFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    storages = set([NFS])
    polarion_test_case = '5255'
    sd_name = "sd_%s" % polarion_test_case
    conn = None

    @polarion("RHEVM3-5255")
    def test_change_posixfs_connection_in_active_sd(self):
        """ Tries to change a posixfs connection used by an active domain,
            action should fail.
        """
        self.change_connection_in_active_sd()


@attr(tier=1)
class TestCase5254(TestCaseNFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    storages = set([NFS])
    polarion_test_case = '5254'
    sd_name = "sd_%s" % polarion_test_case
    conn = None

    @polarion("RHEVM3-5254")
    def test_change_nfs_connection_in_active_sd(self):
        """ Tries to change an nfs connection used by an active domain,
            action should fail
        """
        self.change_connection_in_active_sd()


@attr(tier=1)
class TestCase5253(TestCaseNFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    storages = set([NFS])
    polarion_test_case = '5253'
    sd_name = "sd_%s" % polarion_test_case

    @polarion("RHEVM3-5253")
    def test_change_conn_more_than_once(self):
        """ Tries to change the same connection twice.
        """
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATA_CENTER_NAME)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        )

        new_address = config.EXTRA_DOMAIN_ADDRESSES[0]
        new_path = config.EXTRA_DOMAIN_PATHS[0]
        sd = sd_api.find(self.sd_name)

        helpers.copy_nfs_sd(
            self.address, self.path, new_address, new_path,
            config.HOST_FOR_MOUNT_IP, config.HOSTS_USER, config.HOSTS_PW
        )

        result = storageconnections.update_connection(
            self.conn, address=new_address, path=new_path, type=NFS,
            host=self.host
        )[1]
        assert result

        helpers.clean_nfs_domain(
            self.address, self.path, sd.get_id(), config.HOST_FOR_MOUNT_IP,
            config.HOSTS_USER, config.HOSTS_PW
        )

        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATA_CENTER_NAME)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        )

        old_address = new_address
        old_path = new_path

        new_address = config.EXTRA_DOMAIN_ADDRESSES[1]
        new_path = config.EXTRA_DOMAIN_PATHS[1]

        helpers.copy_nfs_sd(
            old_address, old_path, new_address, new_path,
            config.HOST_FOR_MOUNT_IP, config.HOSTS_USER, config.HOSTS_PW
        )

        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        assert hosts.waitForHostsStates(True, self.host)

        result = storageconnections.update_connection(
            self.conn, address=new_address, path=new_path, type=NFS,
            host=self.host
        )[1]
        assert result

        helpers.clean_nfs_domain(
            old_address, old_path, sd.get_id(), config.HOST_FOR_MOUNT_IP,
            config.HOSTS_USER, config.HOSTS_PW
        )

        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        )


@attr(tier=1)
class TestCase5257(TestCaseNFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    storages = set([NFS])
    polarion_test_case = '5257'
    sd_name = "sd_%s" % polarion_test_case
    cluster = 'cl_%s' % polarion_test_case
    data_center = 'dc_%s' % polarion_test_case
    old_cluster = None

    @polarion("RHEVM3-5257")
    def test_editing_with_no_active_host(self):
        """
        Tries to edit storage connection when there is no host in
        the data center. Action should fail.
        """
        self.host_cluster_map = {}
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATA_CENTER_NAME)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        for host in config.HOSTS_FOR_TEST:
            self.host_cluster_map[host] = hosts.getHostCluster(host)
        assert datacenters.addDataCenter(
            True, name=self.data_center, version=config.COMP_VERSION,
            local=False, storage_type=config.STORAGE_TYPE_NFS
        )
        assert clusters.addCluster(
            True, name=self.cluster, cpu=config.CPU_NAME,
            version=config.COMP_VERSION,
            data_center=self.data_center
        )
        for host in self.host_cluster_map.keys():
            assert clusters.attachHostToCluster(
                True, host, self.cluster
            )
        assert hosts.waitForHostsStates(True, self.host_cluster_map.keys())

        new_address = config.EXTRA_DOMAIN_ADDRESSES[0]
        new_path = config.EXTRA_DOMAIN_PATHS[0]
        result = storageconnections.update_connection(
            self.conn, address=new_address, path=new_path, type=NFS,
            host=self.host)[1]
        assert not result

    def tearDown(self):
        """
        Put the hosts back into original cluster
        """
        for host, cluster in self.host_cluster_map.items():
            clusters.attachHostToCluster(True, host, cluster)
        assert hosts.waitForHostsStates(True, self.host_cluster_map.keys())
        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        clusters.removeCluster(True, self.cluster)
        datacenters.removeDataCenter(True, self.data_center)
        super(TestCase5257, self).tearDown()


@attr(tier=0)
class TestCase5252(TestCaseLocalFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE == 'localfs')
    polarion_test_case = '5252'
    path = "/home/manage_conn_test_%s" % polarion_test_case

    @polarion("RHEVM3-5252")
    def test_change_local_connection(self):
        """ Tries to change a local connection
        """
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATA_CENTER_NAME)
        logger.info("Deactivating storage domain")
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        logger.info("Copying sd")
        helpers.copy_local_sd(self.old_path, self.path, self.machine)

        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)

        logger.info("Updating storage connection")

        _, result = storageconnections.update_connection(
            self.conn, path=self.path, type='localfs', host=self.host)
        assert result

        logger.info("Activating storage domain")
        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

    def tearDown(self):
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATA_CENTER_NAME)
        storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        logger.info("Reverting changes in storage connections")
        storageconnections.update_connection(
            self.conn, path=self.old_path, type='localfs', host=self.host)

        logger.info('Re-activating storage domain')
        storagedomains.activateStorageDomain(True, config.DATA_CENTER_NAME,
                                             self.sd_name)

        super(TestCase5252, self).tearDown()


@attr(tier=1)
class TestCase5256(TestCaseLocalFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE == 'localfs')
    polarion_test_case = '5256'
    path = "/home/manage_conn_test_%s" % polarion_test_case

    @polarion("RHEVM3-5256")
    def test_try_to_change_local_connection_in_active_sd(self):
        """ Tries to change a local connection used by an active domain,
            action should fail.
        """
        result = storageconnections.update_connection(
            self.conn, path=self.path, type='localfs', host=self.host)[1]
        assert not result
