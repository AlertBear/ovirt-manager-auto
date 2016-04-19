import logging
import pytest
import config
import helpers
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    hosts as ll_hosts,
    storageconnections as ll_sd_conn,
    storagedomains as ll_sd,
)
from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as TestCase
from rhevmtests import helpers as rhevm_helpers

logger = logging.getLogger(__name__)
NFS = config.STORAGE_TYPE_NFS
GLUSTER = config.STORAGE_TYPE_GLUSTER
POSIXFS = config.STORAGE_TYPE_POSIX
HOST_CLUSTER = None

# TODO: TestCasePosixFS will only be executed with nfs directories
# Make it compatible in the future with other storage types (glusterfs, ...)
# TODO: Add a new glusterfs class for testing if the same flows applies for
# glusterfs domains


@pytest.fixture(scope='module')
def initializer_module(request):
    """
    Removes one host
    """
    def finalizer_module():
        """
        Add back host to the environment
        """
        if not ll_hosts.addHost(
            True, name=config.HOST_FOR_MOUNT, cluster=HOST_CLUSTER,
            root_password=config.HOSTS_PW, address=config.HOST_FOR_MOUNT_IP
        ):
            raise exceptions.HostException(
                "Failed to add host %s back to GE environment"
                % config.HOST_FOR_MOUNT
            )
    request.addfinalizer(finalizer_module)
    # Remove the host, this is needed to copy the data between
    # storage domains
    global HOST_CLUSTER
    HOST_CLUSTER = ll_hosts.getHostCluster(config.HOST_FOR_MOUNT)
    if not ll_hosts.deactivateHost(True, config.HOST_FOR_MOUNT):
        raise exceptions.HostException(
            "Failed to deactivate host %s" % config.HOST_FOR_MOUNT
        )
    if not ll_hosts.removeHost(True, config.HOST_FOR_MOUNT):
        raise exceptions.HostException(
            "Failed to remove host %s" % config.HOST_FOR_MOUNT
        )


class TestCasePosix(TestCase):
    conn = None
    host = None
    storage_type = None
    storage_domain_type = config.TYPE_DATA
    additional_params = None
    vfs_type = None
    unused_domains = []

    def initializer_TestCasePosix(self):
        """
        Add new storage domain
        """
        self.address = config.UNUSED_RESOURCE_ADDRESS[self.storage][0]
        self.path = config.UNUSED_RESOURCE_PATH[self.storage][0]
        ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)
        self.host = ll_hosts.getSPMHost(config.HOSTS_FOR_TEST)
        if not ll_sd.addStorageDomain(
            True, address=self.address, path=self.path,
            storage_type=self.storage_type, host=self.host,
            type=self.storage_domain_type,
            name=self.sd_name, **self.additional_params
        ):
            exceptions.StorageDomainException(
                "Failed to add new storage domain %s" % self.sd_name
            )

        if not ll_sd.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ):
            exceptions.StorageDomainException(
                "Failed to attach new storage domain %s to datacenter %s"
                % (self.sd_name, config.DATA_CENTER_NAME)
            )

        ll_sd.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.sd_name,
            config.SD_ACTIVE
        )

        conns = ll_sd.getConnectionsForStorageDomain(self.sd_name)
        if not len(conns) == 1:
            raise exceptions.StorageDomainException(
                "Storage domain %s should have only one storage connection "
                "actual amount of connections: %s" %
                (self.sd_name, len(conns))
            )
        self.conn = conns[0].id

    def finalizer_TestCasePosix(self):
        """
        Removing the storage domain created for test
        """
        logger.info("Detaching and deactivating domain")
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        if not hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, self.sd_name
        ):
            logger.error(
                "Failed to deactivate storage domain %s", self.sd_name
            )
            TestCase.test_failed = True
        logger.info("Removing domain %s", self.sd_name)
        if not ll_sd.removeStorageDomain(
            True, self.sd_name, self.host, 'true'
        ):
            logger.error(
                "Failed to remove storage domain %s", self.sd_name
            )
            TestCase.test_failed = True
        rhevm_helpers.cleanup_file_resources([self.storage])
        TestCase.teardown_exception()

    def positive_flow(self, vfs_type):
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        if not ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ):
            raise exceptions.StorageDomainException(
                "Failed to deactivate storage domain %s" % self.sd_name
            )

        new_address = config.UNUSED_RESOURCE_ADDRESS[self.storage][1]
        new_path = config.UNUSED_RESOURCE_PATH[self.storage][1]
        helpers.copy_posix_sd(
            self.address, self.path, new_address, new_path,
            config.HOST_FOR_MOUNT_IP, config.HOSTS_USER, config.HOSTS_PW,
            vfs_type
        )
        sd = ll_sd.get_storage_domain_obj(self.sd_name)
        self.unused_domains.append([self.address, self.path, sd.get_id()])
        logger.info("Changing connection")
        result = self.default_update()
        logger.info("Change connection result is %s", result)
        if not result:
            exceptions.StorageDomainException(
                "Failed to update storage domain's (%s) connection"
                % self.sd_name
            )

        logger.info("Activating storage domain %s", self.sd_name)
        if not ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ):
            raise exceptions.StorageDomainException(
                "Failed to activate storage domain %s" % self.sd_name
            )

    def change_connection_in_active_sd(self):
        """
        Changing the storage connection used by an active storage domain
        should fail
        """
        logger.info("Changing storage connection on active storage domain")
        self.assertFalse(
            self.default_update(),
            "Changing the storage connection used by an active storage domain "
            "should fail"
        )


class TestCaseNFSAndGlusterFS(TestCasePosix):
    """
    Base class for NFS storage connections
    """
    @pytest.fixture(scope='function')
    def initializer_TestCaseNFSAndGlusterFS(
        self, request, initializer_module
    ):
        """
        Initialize parameters and executes setup
        """
        def finalizer_TestCaseNFSAndGlusterFS():
            self.finalizer_TestCasePosix()

        request.addfinalizer(finalizer_TestCaseNFSAndGlusterFS)
        self.storage_type = self.storage
        self.additional_params = {'vfs_type': self.storage}
        self.initializer_TestCasePosix()

    def default_update(self):
        logger.debug(
            "The parameters to be used in the connection update are: %s",
            config.PARAMETERS
        )
        new_address = config.UNUSED_RESOURCE_ADDRESS[self.storage][1]
        new_path = config.UNUSED_RESOURCE_PATH[self.storage][1]
        return ll_sd_conn.update_connection(
            self.conn, address=new_address, path=new_path, type=self.storage,
            nfs_version='V3', host=self.host
        )[1]


class TestCasePosixFS(TestCasePosix):
    @pytest.fixture(scope='function')
    def initializer_TestCasePosixFS(self, request, initializer_module):
        """
        Initialize parameters and executes setup
        """
        def finalizer_TestCasePosixFS():
            self.finalizer_TestCasePosix()

        request.addfinalizer(finalizer_TestCasePosixFS)
        self.storage_type = POSIXFS
        self.additional_params = {'vfs_type': self.storage}
        self.initializer_TestCasePosix()

    def default_update(self):
        logger.debug(
            "The parameters to be used in the connection update are: %s",
            config.PARAMETERS
        )
        new_address = config.UNUSED_RESOURCE_ADDRESS[self.storage][1]
        new_path = config.UNUSED_RESOURCE_PATH[self.storage][1]

        return ll_sd_conn.update_connection(
            self.conn, address=new_address, path=new_path, host=self.host,
            type=POSIXFS
        )[1]


class TestCaseExport(TestCasePosix):
    """
    Base class for NFS storage connections
    """
    @pytest.fixture(scope='function')
    def initializer_TestCaseExport(self, request, initializer_module):
        """
        Initialize parameters and detach export domain
        """
        def finalizer_TestCaseExport():
            """
            Attach the export domain back to the environment
            """
            self.finalizer_TestCasePosix()
            if not hl_sd.attach_and_activate_domain(
                config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME
            ):
                logger.error("Failed to attach export domain back")
                TestCase.test_failed = True
            TestCase.teardown_exception()

        request.addfinalizer(finalizer_TestCaseExport)
        self.storage_type = NFS
        self.additional_params = {}
        self.storage_domain_type = config.TYPE_EXPORT
        if not hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME
        ):
            raise exceptions.StorageDomainException(
                "Failed to deactivate and detach export domain"
            )
        self.initializer_TestCasePosix()

    def default_update(self):
        logger.debug(
            "The parameters to be used in the connection update are: %s",
            config.PARAMETERS
        )
        new_address = config.UNUSED_RESOURCE_ADDRESS[self.storage][1]
        new_path = config.UNUSED_RESOURCE_PATH[self.storage][1]
        return ll_sd_conn.update_connection(
            self.conn, address=new_address, path=new_path, type=NFS,
            nfs_version='V3', host=self.host
        )[1]


class TestCaseISO(TestCasePosix):
    """
    Base class for ISO storage connections
    """
    @pytest.fixture(scope='function')
    def initializer_TestCaseISO(self, request, initializer_module):
        """
        Initialize parameters and executes setup
        """
        def finalizer_TestCaseISO():
            self.finalizer_TestCasePosix()

        request.addfinalizer(finalizer_TestCaseISO)
        self.storage_type = NFS
        self.additional_params = {}
        self.storage_domain_type = config.TYPE_ISO
        self.initializer_TestCasePosix()

    def default_update(self):
        logger.debug(
            "The parameters to be used in the connection update are: %s",
            config.PARAMETERS
        )
        new_address = config.UNUSED_RESOURCE_ADDRESS[self.storage][1]
        new_path = config.UNUSED_RESOURCE_PATH[self.storage][1]
        return ll_sd_conn.update_connection(
            self.conn, address=new_address, path=new_path, type=NFS,
            nfs_version='V3', host=self.host
        )[1]


@attr(tier=1)
class TestCase5250(TestCaseNFSAndGlusterFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '5250'
    sd_name = "sd_%s" % polarion_test_case

    @polarion("RHEVM3-5250")
    @pytest.mark.usefixtures("initializer_TestCaseNFSAndGlusterFS")
    def test_change_nfs_and_gluster_connection(self):
        """
        Tries to change an nfs and glusterfs connection
        """
        self.positive_flow(self.storage)


@attr(tier=2)
@pytest.mark.usefixtures("initializer_TestCasePosixFS")
class TestCase5251(TestCasePosixFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '5251'
    sd_name = "sd_%s" % polarion_test_case

    @polarion("RHEVM3-5251")
    def test_change_posixfs_connection(self):
        """
        Tries to change a posixfs connection
        """
        self.positive_flow(self.storage)


@attr(tier=2)
@pytest.mark.usefixtures("initializer_TestCaseISO")
class TestCase10650(TestCaseISO):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '10650'
    sd_name = "sd_%s" % polarion_test_case

    @polarion("RHEVM3-10650")
    def test_change_iso_connection(self):
        """
        Tries to change an iso domain connection
        """
        self.positive_flow(NFS)


@attr(tier=2)
@pytest.mark.usefixtures("initializer_TestCaseExport")
class TestCase10651(TestCaseExport):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '10651'
    sd_name = "sd_%s" % polarion_test_case

    @polarion("RHEVM3-10651")
    def test_change_export_connection(self):
        """
        Tries to change an export domain connection
        """
        self.positive_flow(NFS)


@attr(tier=2)
@pytest.mark.usefixtures("initializer_TestCasePosixFS")
class TestCase5255(TestCasePosixFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '5255'
    sd_name = "sd_%s" % polarion_test_case
    conn = None

    @polarion("RHEVM3-5255")
    def test_change_posixfs_connection_in_active_sd(self):
        """
        Tries to change a posixfs connection used by an active domain,
        action should fail.
        """
        self.change_connection_in_active_sd()


@attr(tier=2)
@pytest.mark.usefixtures("initializer_TestCaseNFSAndGlusterFS")
class TestCase5254(TestCaseNFSAndGlusterFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '5254'
    sd_name = "sd_%s" % polarion_test_case
    conn = None

    @polarion("RHEVM3-5254")
    def test_change_nfs_and_gluster_connection_in_active_sd(self):
        """
        Tries to change an nfs connection used by an active domain,
        action should fail
        """
        self.change_connection_in_active_sd()


@attr(tier=2)
@pytest.mark.usefixtures("initializer_TestCaseNFSAndGlusterFS")
class TestCase5253(TestCaseNFSAndGlusterFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '5253'
    sd_name = "sd_%s" % polarion_test_case

    @polarion("RHEVM3-5253")
    def test_change_conn_more_than_once(self):
        """
        Tries to change the same connection twice
        """
        logger.info(
            "Waiting for tasks before deactivating the storage domain"
        )
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        self.assertTrue(ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ), "Failed to deactivate storage domain %s" % self.sd_name)

        new_address = config.UNUSED_RESOURCE_ADDRESS[self.storage][1]
        new_path = config.UNUSED_RESOURCE_PATH[self.storage][1]

        helpers.copy_posix_sd(
            self.address, self.path, new_address, new_path,
            config.HOST_FOR_MOUNT_IP, config.HOSTS_USER, config.HOSTS_PW,
            self.storage
        )

        result = ll_sd_conn.update_connection(
            conn_id=self.conn, address=new_address, path=new_path,
            type=self.storage, host=self.host
        )[1]
        self.assertTrue(
            result, "Failed to update storage domain's (%s) connection" %
                    self.sd_name
        )
        self.assertTrue(ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ), "Failed to activate storage domain %s" % self.sd_name)
        logger.info(
            "Waiting for tasks before deactivating the storage domain"
        )
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        self.assertTrue(ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ), "Failed to deactivate storage domain %s" % self.sd_name)

        new_address = config.UNUSED_RESOURCE_ADDRESS[self.storage][2]
        new_path = config.UNUSED_RESOURCE_PATH[self.storage][2]

        helpers.copy_posix_sd(
            self.address, self.path, new_address, new_path,
            config.HOST_FOR_MOUNT_IP, config.HOSTS_USER, config.HOSTS_PW,
            self.storage
        )

        ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)
        ll_hosts.waitForHostsStates(True, self.host)

        result = ll_sd_conn.update_connection(
            self.conn, address=new_address, path=new_path, type=self.storage,
            host=self.host
        )[1]
        self.assertTrue(
            result, "Failed to update storage domain's '%s' connection" %
                    self.sd_name
        )
        self.assertTrue(ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name),
            "Failed to activate storage domain %s" % self.sd_name
        )
