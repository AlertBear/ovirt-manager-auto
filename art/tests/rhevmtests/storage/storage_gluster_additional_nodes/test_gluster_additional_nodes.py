"""
3.6 Allow Gluster Mount With Additional Nodes
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_3_6/3_6_Storage_allow%20gluster%20mount%20with%20additional%20nodes
"""
from multiprocessing.pool import ThreadPool
import logging
import config
import pytest
import re
import time
from art.rhevm_api.tests_lib.high_level import (
    hosts as hl_hosts,

)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
)
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    tier3,
)
from art.unittest_lib import StorageTest as BaseTestCase, testflow
from art.rhevm_api.utils.log_listener import watch_logs
from rhevmtests.storage.storage_gluster_additional_nodes.fixtures import (
    block_connectivity_gluster_nodes, initialize_params,
    create_gluster_storage_domain_with_or_without_additional_nodes,
    unblock_connectivity_gluster_nodes,
)
from rhevmtests.storage.fixtures import (
    remove_storage_domain,
)
import rhevmtests.storage.helpers as storage_helpers

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS


@pytest.fixture(scope='module', autouse=True)
def deactivate_all_non_spm_hosts_non_test_gluster_sds(request):
    """
    Deactivate/Activate all non spm hosts
    """
    def finalizer():
        for host in config.HOSTS:
            assert hl_hosts.activate_host_if_not_up(host), (
                "Unable to activate host %s", host
            )
    request.addfinalizer(finalizer)

    assert config.GLUSTER_REPLICA_PATH, (
        "Cannot run tests, missing gluster resources"
    )
    spm_host = ll_hosts.get_spm_host(config.HOSTS)
    for host in config.HOSTS:
        if host != spm_host:
            assert hl_hosts.deactivate_host_if_up(host), (
                "Unable to deactivate host %s", host
            )


@pytest.mark.usefixtures(
    unblock_connectivity_gluster_nodes.__name__,
    remove_storage_domain.__name__,
    initialize_params.__name__,
    block_connectivity_gluster_nodes.__name__,
)
class BaseGlusterMount(BaseTestCase):
    """
    Base class for the implementation of all tests
    """
    __test__ = False
    storages = set([config.STORAGE_TYPE_GLUSTER])

    @classmethod
    def block_nodes(cls, nodes):
        """
        Block connection with iptables to the specific nodes

        :param nodes: List of gluster servers to block
        :type nodes: list
        :raises: Exception
        """
        for node_ip in nodes:
            logger.info(
                "Blocking source %s from target %s", cls.host_ip, node_ip
            )
            assert storage_helpers.setup_iptables(
                cls.host_ip, node_ip, block=True
            ), (
                "Unable to block connection to gluster node %s from host %s" %
                (node_ip, cls.host_ip)
            )

    @classmethod
    def unblock_nodes(cls, nodes):
        """
        Unblock connection with iptables to the specific nodes

        :param nodes: List of gluster servers to block
        :type nodes: list
        """
        for node_ip in nodes:
            logger.info(
                "Unblocking source %s from target %s", cls.host_ip, node_ip
            )
            assert storage_helpers.setup_iptables(
                cls.host_ip, node_ip, block=False
            ), "Unblock connection to gluster node %s from host %s failed" % (
                node_ip, cls.host_ip
            )

    @classmethod
    def add_storage_domain(cls, address, backupvolfile_list=None):
        """
        Add a gluster storage domain with optional backup volume files,
        return add domain status

        :param address: Address of the gluster server
        :type address: str
        :param backupvolfile_list: list of the gluster server addresses to add
        :type backupvolfile_list: list
        :returns: add storage domain status
        :rtype: bool
        """
        mount_options = None
        if backupvolfile_list:
            mount_options = (
                "backup-volfile-servers=%s" % ":".join(backupvolfile_list)
            )

        logger.info(
            "Adding gluster storage domain %s with mount point %s:%s and "
            "mount options %s", cls.storage_domain, address, cls.domain_path,
            mount_options
        )
        return ll_sd.addStorageDomain(
            True,  host=cls.host, path=cls.domain_path,
            name=cls.storage_domain,
            storage_type=config.STORAGE_TYPE_GLUSTER,
            type=config.TYPE_DATA, vfs_type=ENUMS['vfs_type_glusterfs'],
            address=address, mount_options=mount_options
        )

    def verify_add_storage_domain(
            self, positive, address=None, backupvolfile_list=None
    ):
        """
        Add a gluster storage domain with optional backup volume files
        and ensure the operation succeeds or fails according to positive
        parameter

        :param positive: Specifices if the operation should succeed or not
        :type positive: bool
        :param address: Address of the gluster server
        :type address: str
        :param backupvolfile_list: list of the gluster nodes to add
        :type backupvolfile_list: list
        :raises: AssertionError
        """
        status = self.add_storage_domain(address, backupvolfile_list)
        assert status == positive, (
            "Adding a gluster domain with %s address should have %s." %
            (address, "succeeded" if positive else "failed")
        )


@pytest.mark.usefixtures(
    create_gluster_storage_domain_with_or_without_additional_nodes.__name__,
)
class BaseTestBlockingNodes(BaseGlusterMount):
    """
    Test gluster domain is available after blocking different nodes
    """

    def verify_storage_domain_status(self, writable=True, active=True):
        """
        Verify gluster storage domain's status including whether it is
        writable and active

        :param writable: Specify whether the storage domain is writable
        :type writable: bool
        :param active: Specify wheter the storage domain status should be
        active
        :type active: bool
        :raises: DiskException, AssertionError
        """
        logger.info(
            "storage domain is writable:%s active:%s", writable, active
        )
        if not writable or not active:
            disk_operation_positive = False
        else:
            disk_operation_positive = True

        status = ll_disks.addDisk(
            disk_operation_positive, alias=self.disk_alias,
            provisioned_size=config.DISK_SIZE, interface=config.VIRTIO,
            sparse=True, format=config.COW_DISK,
            storagedomain=self.storage_domain
        )
        if disk_operation_positive == status:
            assert ll_disks.deleteDisk(True, self.disk_alias), (
                "Failed to delete disk %s" % self.disk_alias
            )

        if not writable:
            assert status, "Storage domain %s is %s" % (
                self.storage_domain,
                "in read-only mode" if disk_operation_positive else
                "writable"
            )

        if active:
            assert ll_sd.wait_storage_domain_status_is_unchanged(
                config.DATA_CENTER_NAME, self.storage_domain,
                config.SD_ACTIVE
            ), "Storage domain %s is not active" % self.storage_domain

    @polarion("RHEVM3-14683")
    def test_blocking_gluster(self):
        """
        Test whether the gluster storage domain is up or in read-only mode
        after blocking different nodes.

        If only one node is active, the storage domain should be in read-only
        mode. If all the nodes are blocked, the storage domain should be
        in inactive status

        block a
        block a and b      => read-only
        block a and c      => read-only
        block b
        block c
        block b and c      => read-only
        block a, b and c   => inactive
        """
        # Block a
        logger.info("Blocking node %s expecting active SD", config.NODES[0])
        self.block_nodes([config.NODES[0]])
        self.verify_storage_domain_status()

        # Block a and b
        logger.info(
            "Blocking nodes %s and %s expecting read only SD", config.NODES[0],
            config.NODES[1]
        )
        self.block_nodes([config.NODES[1]])
        self.verify_storage_domain_status(writable=False)

        # Block a and c
        logger.info(
            "Blocking nodes %s and %s expecting read only SD", config.NODES[0],
            config.NODES[2]
        )
        self.unblock_nodes([config.NODES[1]])
        self.block_nodes([config.NODES[2]])
        self.verify_storage_domain_status(writable=False)

        # Block b
        logger.info("Blocking node %s expecting active SD", config.NODES[1])
        self.unblock_nodes([config.NODES[0], config.NODES[2]])
        self.block_nodes([config.NODES[1]])
        self.verify_storage_domain_status()

        # Block c
        logger.info("Blocking node %s expecting active SD", config.NODES[2])
        self.unblock_nodes([config.NODES[1]])
        self.block_nodes([config.NODES[2]])
        self.verify_storage_domain_status()

        # block b and c
        logger.info(
            "Blocking nodes %s and %s expecting read only SD", config.NODES[1],
            config.NODES[2]
        )
        self.block_nodes([config.NODES[1]])
        self.verify_storage_domain_status(writable=False)

        # block a, b and c
        logger.info("Blocking all nodes expecting non-active SD")
        self.block_nodes([config.NODES[0]])
        self.verify_storage_domain_status(active=False)
        self.unblock_nodes(config.NODES)


@tier2
class TestBlockingNodesBackupVolFile(BaseTestBlockingNodes):
    """
    Test gluster domain is available after blocking different nodes
    with backupvolfile-server option
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in ART_CONFIG['RUN']['storages']
    backup_vol_file_server = True


@tier2
class TestBlockingNodesWithNoBackupVolFile(BaseTestBlockingNodes):
    """
    Test gluster domain is available after blocking different nodes
    with no backupvolfile-server option
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in ART_CONFIG['RUN']['storages']
    backup_vol_file_server = False


@tier3
class Test12320(BaseGlusterMount):
    """
    Test gluster setup with Unavailable Master and 2 Available secondary
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in ART_CONFIG['RUN']['storages']
    disabled_nodes_ips = [config.NODES[0]] if config.NODES else None

    @polarion("RHEVM3-12320")
    def test_creation_backupvolfile(self):
        """
        * Block connection to the primary server
        * Try adding the gluster storage domain
        => PASS
        """
        testflow.step(
            "Adding gluster SD %s with backup gluster nodes %s",
            config.NODES[0],
            config.NODES[1:3]
        )
        self.verify_add_storage_domain(
            positive=True, address=config.NODES[0],
            backupvolfile_list=config.NODES[1:3]
        )


@tier3
class Test12322(BaseGlusterMount):
    """
    Test Gluster setup with Available Master and 1 Available Secondary
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in ART_CONFIG['RUN']['storages']
    disabled_nodes_ips = [config.NODES[1]] if config.NODES else None

    @polarion("RHEVM3-12322")
    def test_creation_backupvolfile(self):
        """
        * Block connection to one of the secondary servers
        * Try adding the gluster storage domain
        => PASS
        """
        self.verify_add_storage_domain(
            positive=True, address=config.NODES[0],
            backupvolfile_list=config.NODES[1:3]
        )


@tier3
class Test12323(BaseGlusterMount):
    """
    Test Gluster setup with Unavailable Master and 1 Available Secondary
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in ART_CONFIG['RUN']['storages']
    disabled_nodes_ips = config.NODES[0:2] if config.NODES else None

    @polarion("RHEVM3-12323")
    def test_creation_backupvolfile(self):
        """
        * Block connection to the primary server and one of the secondary
        servers
        * Try adding the gluster storage domain
        => FAIL (When two of the gluster servers are blocked, the gluster
        volume mode is changed to read-only)
        """
        self.verify_add_storage_domain(
            positive=False, address=config.NODES[0],
            backupvolfile_list=config.NODES[1:3]
        )


@tier2
class Test12324(BaseGlusterMount):
    """
    Test Gluster setup with with All RHS servers available
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in ART_CONFIG['RUN']['storages']

    @polarion("RHEVM3-12324")
    def test_creation_backupvolfile(self):
        """
        * Try adding the gluster storage domain when all the servers are
        available
        => PASS
        """
        self.verify_add_storage_domain(
            positive=True, address=config.NODES[0],
            backupvolfile_list=config.NODES[1:3]
        )


@tier3
class Test12325(BaseGlusterMount):
    """
    Test a Gluster setup with an Available master and 2 Unavailable
    secondary RHS servers
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in ART_CONFIG['RUN']['storages']
    disabled_nodes_ips = config.NODES[1:3] if config.NODES else None

    @polarion("RHEVM3-12325")
    def test_creation_backupvolfile(self):
        """
        * Block connection to both secondary servers
        * Try adding the gluster storage domain
        => FAIL (When two of the gluster servers are blocked, the gluster
        volume mode is changed to read-only)
        """
        self.verify_add_storage_domain(
            positive=False, address=config.NODES[0],
            backupvolfile_list=config.NODES[1:3]
        )


@tier2
class Test12326(BaseGlusterMount):
    """
    Test Gluster setup with with All RHS servers unavailable
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in ART_CONFIG['RUN']['storages']

    @polarion("RHEVM3-12326")
    def test_creation_backupvolfile(self):
        """
        * Block connection to all the servers
        * Try adding the gluster storage domain
        => FAIL
        """
        self.verify_add_storage_domain(positive=False)


@tier3
class VerifyGlusterMountParameteres(BaseGlusterMount):
    """
    Test the backup-volfile-servers parameter works as expected.
    Verify the mount command on the spm host
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in ART_CONFIG['RUN']['storages']

    def verify_gluster_mount_cmd(
        self, backupvolfile_list, backupvolfile_regex
    ):
        """
        Add the gluster storage domain with the backup-volfile-servers
        parameter, and verify the mount options are present in the vdsm log
        """

        if backupvolfile_list:
            self.regex = "backup-volfile-servers=%s" % (
                ":".join(backupvolfile_regex)
            )
        else:
            self.regex = re.escape("bricks: %s" % config.NODES)

        pool = ThreadPool(processes=1)
        async_result = pool.apply_async(
            watch_logs, (
                config.VDSM_LOG, self.regex, None, config.LOG_LISTENER_TIMEOUT,
                self.host_ip, config.HOSTS_USER, config.HOSTS_PW
            )
        )
        time.sleep(5)

        assert self.add_storage_domain(self.address, backupvolfile_list), (
            "Error adding gluster storage domain %s" % self.address
        )

        return_val = async_result.get()
        assert return_val[0], "regex %s was not found" % (
            self.regex
        )

    @polarion("RHEVM3-14682")
    def test_add_gluster_domain_without_backvolfile(self):
        """
        * Add a gluster storage domain without the backup-volfile-servers
        parameter
        => Verify the backup-volfile-servers parameter contains the
        replica 3 servers' ips from the autodiscover operation
        """
        # Not passing backup-volfile-servers parameter will autodisvover
        # the nodes in the replica
        self.verify_gluster_mount_cmd(
            backupvolfile_list=None, backupvolfile_regex=config.NODES[1:3]
        )

    @polarion("RHEVM3-14682")
    def test_add_gluster_domain_with_one_node(self):
        """
        * Add a gluster storage domain, passing one gluster node to the
        backup-volfile-servers parameter
        => Verify that backup-volfile-servers contains the gluster node
        that was passed in
        """
        self.verify_gluster_mount_cmd(
            backupvolfile_list=[config.NODES[1]],
            backupvolfile_regex=[config.NODES[1]]
        )

    @polarion("RHEVM3-14682")
    def test_add_gluster_domain_with_two_nodes(self):
        """
        * Add a gluster storage domain, passing two gluster nodes to the
        backup-volfile-server parameter
        => Verify that backup-volfile-servers contains both gluster nodes
        that were passed in
        """
        self.verify_gluster_mount_cmd(
            backupvolfile_list=config.NODES[1:3],
            backupvolfile_regex=config.NODES[1:3]
        )


# TODO
"""
RHEVM3-11327
Test a Gluster setup with 5 Available servers in 2 different Clusters
"""
