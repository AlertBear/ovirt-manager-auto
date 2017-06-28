import logging
import pytest
import config
import helpers
import rhevmtests.helpers as rhevm_helpers

from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    hosts as ll_hosts,
    storageconnections as ll_sd_conn,
    storagedomains as ll_sd,
)
from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import polarion
from art.unittest_lib import (
    StorageTest as TestCase,
    tier3,
)

from fixtures import add_storage_domain
from rhevmtests.storage.fixtures import deactivate_and_detach_export_domain
from fixtures import a0_initialize_variables_clean_storages  # noqa
from fixtures import a1_initializer_module_nfs  # noqa

logger = logging.getLogger(__name__)
NFS = config.STORAGE_TYPE_NFS
GLUSTER = config.STORAGE_TYPE_GLUSTER
POSIXFS = config.STORAGE_TYPE_POSIX
HOST_CLUSTER = None

# TODO: TestCasePosixFS will only be executed with nfs directories
# Make it compatible in the future with other storage types (glusterfs, ...)
# TODO: Add a new glusterfs class for testing if the same flows applies for
# glusterfs domains


class TestCasePosix(TestCase):
    conn = None
    host = None
    storage_type = None
    storage_domain_type = config.TYPE_DATA
    additional_params = {}
    vfs_type = None
    unused_domains = []

    def initializer_TestCasePosix(self):
        """
        Add new storage domain
        """
        self.address = config.UNUSED_RESOURCE[self.storage][0]['address']
        self.path = config.UNUSED_RESOURCE[self.storage][0]['path']
        ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)
        self.host = ll_hosts.get_spm_host(config.HOSTS_FOR_TEST)
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

        ll_sd.wait_for_storage_domain_status(
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
            config.ENGINE, config.DATA_CENTER_NAME
        )
        if not hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, self.sd_name, engine=config.ENGINE
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
            engine=config.ENGINE, datacenter=config.DATA_CENTER_NAME
        )
        if not ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ):
            raise exceptions.StorageDomainException(
                "Failed to deactivate storage domain %s" % self.sd_name
            )

        new_address = config.UNUSED_RESOURCE[self.storage][1]['address']
        new_path = config.UNUSED_RESOURCE[self.storage][1]['path']
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
        assert not self.default_update(), (
            "Changing the storage connection used by an active storage domain "
            "should fail"
        )


@pytest.mark.usefixtures(
    add_storage_domain.__name__,
)
class TestCaseNFSAndGlusterFS(TestCasePosix):
    """
    Base class for NFS storage connections
    """
    additional_params = {'vfs_type': ''}

    def default_update(self):
        logger.debug(
            "The parameters to be used in the connection update are: %s",
            config.PARAMETERS
        )
        new_address = config.UNUSED_RESOURCE[self.storage][1]['address']
        new_path = config.UNUSED_RESOURCE[self.storage][1]['path']
        return ll_sd_conn.update_connection(
            True, self.conn, address=new_address, path=new_path,
            type=self.storage, nfs_version='V3', host=self.host,
            vfs_type=self.additional_params['vfs_type']
        )[1]


@pytest.mark.usefixtures(
    add_storage_domain.__name__,
)
class TestCasePosixFS(TestCasePosix):

    storage_type = POSIXFS
    additional_params = {'vfs_type': ''}

    def default_update(self):
        logger.debug(
            "The parameters to be used in the connection update are: %s",
            config.PARAMETERS
        )
        new_address = config.UNUSED_RESOURCE[self.storage][1]['address']
        new_path = config.UNUSED_RESOURCE[self.storage][1]['path']

        return ll_sd_conn.update_connection(
            True, self.conn, address=new_address, path=new_path,
            host=self.host, type=POSIXFS
        )[1]


@pytest.mark.usefixtures(
    deactivate_and_detach_export_domain.__name__,
    add_storage_domain.__name__,
)
class TestCaseExport(TestCasePosix):
    """
    Base class for NFS storage connections
    """
    storage_type = NFS
    storage_domain_type = config.TYPE_EXPORT

    def default_update(self):
        logger.debug(
            "The parameters to be used in the connection update are: %s",
            config.PARAMETERS
        )
        new_address = config.UNUSED_RESOURCE[self.storage][1]['address']
        new_path = config.UNUSED_RESOURCE[self.storage][1]['path']
        return ll_sd_conn.update_connection(
            True, self.conn, address=new_address, path=new_path, type=NFS,
            nfs_version='V3', host=self.host
        )[1]


@pytest.mark.usefixtures(
    add_storage_domain.__name__,
)
class TestCaseISO(TestCasePosix):
    """
    Base class for ISO storage connections
    """
    storage_type = NFS
    storage_domain_type = config.TYPE_ISO

    def default_update(self):
        logger.debug(
            "The parameters to be used in the connection update are: %s",
            config.PARAMETERS
        )
        new_address = config.UNUSED_RESOURCE[self.storage][1]['address']
        new_path = config.UNUSED_RESOURCE[self.storage][1]['path']
        return ll_sd_conn.update_connection(
            True, self.conn, address=new_address, path=new_path, type=NFS,
            nfs_version='V3', host=self.host
        )[1]


class TestCase5250(TestCaseNFSAndGlusterFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = (NFS in ART_CONFIG['RUN']['storages'] or
                GLUSTER in ART_CONFIG['RUN']['storages'])
    storages = set([NFS, GLUSTER])

    @tier3
    @polarion("RHEVM3-5250")
    def test_change_nfs_and_gluster_connection(self):
        """
        Tries to change an nfs and glusterfs connection
        """
        self.positive_flow(self.storage)


class TestCase5251(TestCasePosixFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = (NFS in ART_CONFIG['RUN']['storages'] or
                GLUSTER in ART_CONFIG['RUN']['storages'])
    storages = set([NFS, GLUSTER])

    @tier3
    @polarion("RHEVM3-5251")
    def test_change_posixfs_connection(self):
        """
        Tries to change a posixfs connection
        """
        self.positive_flow(self.storage)


class TestCase10650(TestCaseISO):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = NFS in ART_CONFIG['RUN']['storages']
    storages = set([NFS])

    @tier3
    @polarion("RHEVM3-10650")
    def test_change_iso_connection(self):
        """
        Tries to change an iso domain connection
        """
        self.positive_flow(NFS)


class TestCase10651(TestCaseExport):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = NFS in ART_CONFIG['RUN']['storages']
    storages = set([NFS])

    @tier3
    @polarion("RHEVM3-10651")
    def test_change_export_connection(self):
        """
        Tries to change an export domain connection
        """
        self.positive_flow(NFS)


class TestCase5255(TestCasePosixFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = (NFS in ART_CONFIG['RUN']['storages'] or
                GLUSTER in ART_CONFIG['RUN']['storages'])
    storages = set([NFS, GLUSTER])
    conn = None

    @tier3
    @polarion("RHEVM3-5255")
    def test_change_posixfs_connection_in_active_sd(self):
        """
        Tries to change a posixfs connection used by an active domain,
        action should fail.
        """
        self.change_connection_in_active_sd()


class TestCase5254(TestCaseNFSAndGlusterFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = (NFS in ART_CONFIG['RUN']['storages'] or
                GLUSTER in ART_CONFIG['RUN']['storages'])
    storages = set([NFS, GLUSTER])
    conn = None

    @tier3
    @polarion("RHEVM3-5254")
    def test_change_nfs_and_gluster_connection_in_active_sd(self):
        """
        Tries to change an nfs connection used by an active domain,
        action should fail
        """
        self.change_connection_in_active_sd()


class TestCase5253(TestCaseNFSAndGlusterFS):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = (NFS in ART_CONFIG['RUN']['storages'] or
                GLUSTER in ART_CONFIG['RUN']['storages'])
    storages = set([NFS, GLUSTER])

    @tier3
    @polarion("RHEVM3-5253")
    def test_change_conn_more_than_once(self):
        """
        Tries to change the same connection twice
        """
        logger.info(
            "Waiting for tasks before deactivating the storage domain"
        )
        test_utils.wait_for_tasks(
            engine=config.ENGINE, datacenter=config.DATA_CENTER_NAME
        )
        assert ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ), "Failed to deactivate storage domain %s" % self.sd_name

        new_address = config.UNUSED_RESOURCE[self.storage][1]['address']
        new_path = config.UNUSED_RESOURCE[self.storage][1]['path']

        helpers.copy_posix_sd(
            self.address, self.path, new_address, new_path,
            config.HOST_FOR_MOUNT_IP, config.HOSTS_USER, config.HOSTS_PW,
            self.storage
        )

        result = ll_sd_conn.update_connection(
            True, conn_id=self.conn, address=new_address, path=new_path,
            type=self.storage, host=self.host,
            vfs_type=self.additional_params['vfs_type']
        )[1]
        assert result, "Failed to update storage domain's (%s) connection" % (
            self.sd_name
        )
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ), "Failed to activate storage domain %s" % self.sd_name
        logger.info(
            "Waiting for tasks before deactivating the storage domain"
        )
        test_utils.wait_for_tasks(
            engine=config.ENGINE, datacenter=config.DATA_CENTER_NAME
        )
        assert ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ), "Failed to deactivate storage domain %s" % self.sd_name

        new_address = config.UNUSED_RESOURCE[self.storage][2]['address']
        new_path = config.UNUSED_RESOURCE[self.storage][2]['path']

        helpers.copy_posix_sd(
            self.address, self.path, new_address, new_path,
            config.HOST_FOR_MOUNT_IP, config.HOSTS_USER, config.HOSTS_PW,
            self.storage
        )

        ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)
        ll_hosts.wait_for_hosts_states(True, self.host)

        result = ll_sd_conn.update_connection(
            True, conn_id=self.conn, address=new_address, path=new_path,
            type=self.storage, host=self.host,
            vfs_type=self.additional_params['vfs_type']
        )[1]
        assert result, "Failed to update storage domain's '%s' connection" % (
            self.sd_name
        )
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name
        ), "Failed to activate storage domain %s" % self.sd_name
