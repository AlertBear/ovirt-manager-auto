"""
3.6 Allow Gluster Mount With Additional Nodes
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_3_6/3_6_Storage_allow%20gluster%20mount%20with%20additional%20nodes
"""
import logging
from unittest2 import SkipTest
from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api.tests_lib.high_level import (
    hosts as hl_hosts,
)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
)
from art.rhevm_api.utils import storage_api
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as BaseTestCase
from art.rhevm_api.utils.log_listener import watch_logs
from multiprocessing import Process, Queue
from rhevmtests.storage import config

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS


NODES = config.GLUSTER_REPLICA_SERVERS
SPM_HOST = None
SPM_HOST_IP = None
SD_INACTIVE_TIMEOUT = 7 * 60
GLUSTER_CMD_TIMEOUT = 60


def setup_module():
    """
    Deactivate all hosts except for one
    """
    if not NODES or not config.GLUSTER_REPLICA_PATH:
        raise exceptions.CannotRunTests(
            "Cannot run tests, missing gluster resources"
        )
    global SPM_HOST, SPM_HOST_IP
    SPM_HOST = ll_hosts.getSPMHost(config.HOSTS)
    SPM_HOST_IP = ll_hosts.getHostIP(SPM_HOST)
    for host in config.HOSTS:
        if host != SPM_HOST:
            if not hl_hosts.deactivate_host_if_up(host):
                raise Exception("Unable to deactivate host %s", host)


def teardown_module():
    """
    Activate the hosts deactivated in the setup_module
    """
    exception_flag = False
    for host in config.HOSTS:
        if not hl_hosts.activate_host_if_not_up(host):
            logger.error("Unable to activate host %s", host)
            exception_flag = True
    if exception_flag:
        raise exceptions.TearDownException(
            "Test failed while executing teardown_module"
        )


class BaseGlusterMount(BaseTestCase):
    """
    Base class for the implementation of all tests
    """
    __test__ = False
    storages = set([config.STORAGE_TYPE_GLUSTER])

    domain_name = "storage_additional_gluster_nodes"
    domain_path = config.GLUSTER_REPLICA_PATH
    disabled_nodes_ips = []

    @classmethod
    def setup_class(cls):
        """
        Disable nodes for the test
        """
        cls.host = SPM_HOST
        cls.host_ip = SPM_HOST_IP
        cls.username = config.HOSTS_USER
        cls.password = config.HOSTS_PW
        cls.block_nodes(cls.disabled_nodes_ips)

    @classmethod
    def teardown_class(cls):
        """
        Enable the connection to each node after the test
        """
        cls.unblock_nodes(cls.disabled_nodes_ips)

    @classmethod
    def block_nodes(cls, nodes):
        """
        Block connection with iptables to the specific nodes

        :param nodes: List of gluster servers to block
        :type nodes: list
        :raises: Exception
        """
        for node_ip in nodes:
            if not storage_api.blockOutgoingConnection(
                cls.host_ip, cls.username, cls.password, node_ip
            ):
                raise Exception(
                    "Unable to block connection to gluster node %s "
                    "from host %s" % (node_ip, cls.host_ip)
                )

    @classmethod
    def unblock_nodes(cls, nodes):
        """
        Unblock connection with iptables to the specific nodes

        :param nodes: List of gluster servers to block
        :type nodes: list
        """
        for node_ip in nodes:
            if not storage_api.unblockOutgoingConnection(
                cls.host_ip, cls.username, cls.password, node_ip
            ):
                # Don't raise exception since this usually works as a clean up
                # call to remove all the iptables rules
                logger.warn(
                    "Unable to unblock connection to gluster node %s "
                    "from host %s", node_ip, cls.host_ip
                )

    def add_storage_domain(self, address, backupvolfile_list=None):
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
            "mount options %s", self.domain_name, address, self.domain_path,
            mount_options
        )
        return ll_sd.addStorageDomain(
            True,  host=self.host, path=self.domain_path,
            name=self.domain_name, storage_type=config.STORAGE_TYPE_GLUSTER,
            type=config.TYPE_DATA, vfs_type=ENUMS['vfs_type_glusterfs'],
            address=address, mount_options=mount_options
        )

    def verify_add_storage_domain(
            self, positive, address=NODES[0], backupvolfile_list=NODES[1:3]
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
        self.assertEqual(
            status, positive, "Adding a gluster domain with %s address "
            "should have %s." % (
                address, "succeeded" if positive else "failed"
            )
        )

    def tearDown(self):
        """
        In case the domain exists, remove it
        """
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        if not ll_sd.removeStorageDomains(
            True, self.domain_name, self.host,
        ):
            logger.error(
                "Error removing storage domain %s", self.domain_name
            )
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


@attr(tier=2)
class BaseTestBlockingNodes(BaseGlusterMount):
    """
    Test gluster domain is available after blocking different nodes
    """
    # TODO: Add the BaseTestCase method to generate an unique name for the disk
    disk_alias = "gluster_disk"

    def setUp(self):
        """
        Create storage domain for test
        """
        if self.backup_vol_file_server:
            self.add_storage_domain(
                address=NODES[0], backupvolfile_list=NODES[1:3])
        else:
            self.add_storage_domain(
                address=NODES[0], backupvolfile_list=[]
            )
        if not ll_sd.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.domain_name
        ):
            raise exceptions.StorageDomainException(
                "Unable to add storage domain %s" % self.domain_name
            )

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
        if not writable or not active:
            disk_operation_positive = False
        else:
            disk_operation_positive = True

        status = ll_disks.addDisk(
            disk_operation_positive, alias=self.disk_alias,
            provisioned_size=config.DISK_SIZE, interface=config.VIRTIO,
            sparse=True, format=config.COW_DISK, storagedomain=self.domain_name
        )
        raise_exception = False
        if disk_operation_positive == status:
            if not ll_disks.deleteDisk(True, self.disk_alias):
                logger.error("Failed to delete disk %s", self.disk_alias)
                raise_exception = True
        if not writable:
            self.assertTrue(
                status, "Storage domain %s is %s" % (
                    self.domain_name,
                    "in read-only mode" if disk_operation_positive else
                    "writable"
                )
            )

        if active:
            self.assertTrue(
                ll_sd.wait_storage_domain_status_is_unchanged(
                    config.DATA_CENTER_NAME, self.domain_name,
                    config.SD_ACTIVE
                ), "Storage domain %s is not active" % self.domain_name
            )
        else:
            try:
                ll_sd.waitForStorageDomainStatus(
                    True, config.DATA_CENTER_NAME, self.domain_name,
                    config.SD_INACTIVE, timeOut=SD_INACTIVE_TIMEOUT
                )
            except APITimeout:
                domain_obj = ll_sd.getDCStorage(
                    config.DATA_CENTER_NAME, self.domain_name
                )
                self.assertTrue(
                    False, "Storage domain %s is in status %s, expected "
                    "status is %s" % (
                        self.domain_name, domain_obj.get_status(),
                        config.SD_INACTIVE
                    )
                )

        if raise_exception:
            raise exceptions.DiskException(
                "Unable to remove disk %s", self.disk_alias
            )

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
        self.block_nodes([NODES[0]])
        self.verify_storage_domain_status()

        # Block a and b
        self.block_nodes([NODES[1]])
        self.verify_storage_domain_status(writable=False)

        # Block a and c
        self.unblock_nodes([NODES[1]])
        self.block_nodes([NODES[2]])
        self.verify_storage_domain_status(writable=False)

        # Block b
        self.unblock_nodes([NODES[0], NODES[2]])
        self.block_nodes([NODES[1]])
        self.verify_storage_domain_status()

        # Block c
        self.unblock_nodes([NODES[1]])
        self.block_nodes([NODES[2]])
        self.verify_storage_domain_status()

        # block b and c
        self.block_nodes([NODES[1]])
        self.verify_storage_domain_status(writable=False)

        # block a, b and c
        self.block_nodes([NODES[0]])
        self.verify_storage_domain_status(active=False)

    def tearDown(self):
        """
        Enable the connection to each node after the test
        """
        self.unblock_nodes(NODES)
        try:
            ll_sd.waitForStorageDomainStatus(
                True, config.DATA_CENTER_NAME, self.domain_name,
                config.SD_ACTIVE,
            )
        except exceptions.APITimeout:
            logger.error(
                "Storage domain %s is not in status active", self.domain_name
            )
            BaseTestCase.test_failed = True
        super(BaseTestBlockingNodes, self).tearDown()


@attr(tier=2)
class TestBlockingNodesBackupVolFile(BaseTestBlockingNodes):
    """
    Test gluster domain is available after blocking different nodes
    with backupvolfile-server option
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    backup_vol_file_server = True


@attr(tier=2)
class TestBlockingNodesWithNoBackupVolFile(BaseTestBlockingNodes):
    """
    Test gluster domain is available after blocking different nodes
    with no backupvolfile-server option
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    backup_vol_file_server = False


@attr(tier=2)
class Test12320(BaseGlusterMount):
    """
    Test Gulester setup with Unavailable Master and 2 Available secondary
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    disabled_nodes_ips = [NODES[0]]
    # BZ1303977: KeyError when primary server used to mount gluster volume is
    # down
    bz = {'1303977': {'engine': None, 'version': ["3.6"]}}

    @polarion("RHEVM3-12320")
    def test_creation_backupvolfile(self):
        """
        * Block connection to the primary server
        * Try adding the gluster storage domain
        => PASS
        """
        # Bugzilla plugin doesn't support skip for bugs from non ovirt/rhevm
        # products, 1303977
        # TODO: When pytest is enabled, use the bz attribute instead of raise
        # the SkipTest exception
        raise SkipTest(
            "Skip test due to bug 1303977"
        )
        self.verify_add_storage_domain(positive=True)


@attr(tier=2)
class Test12322(BaseGlusterMount):
    """
    Test Gluster setup with Available Master and 1 Available Secondary
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    disabled_nodes_ips = [NODES[1]]

    @polarion("RHEVM3-12322")
    def test_creation_backupvolfile(self):
        """
        * Block connection to one of the secondary servers
        * Try adding the gluster storage domain
        => PASS
        """
        self.verify_add_storage_domain(positive=True)


@attr(tier=2)
class Test12323(BaseGlusterMount):
    """
    Test Gluster setup with Unavailable Master and 1 Available Secondary
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    disabled_nodes_ips = [NODES[0], NODES[1]]

    @polarion("RHEVM3-12323")
    def test_creation_backupvolfile(self):
        """
        * Block connection to the primary server and one of the secondary
        servers
        * Try adding the gluster storage domain
        => FAIL (When two of the gluster servers are blocked, the gluster
        volume mode is changed to read-only)
        """
        self.verify_add_storage_domain(positive=False)


@attr(tier=2)
class Test12324(BaseGlusterMount):
    """
    Test Gluster setup with with All RHS servers available
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    disabled_nodes_ips = []

    @polarion("RHEVM3-12324")
    def test_creation_backupvolfile(self):
        """
        * Try adding the gluster storage domain when all the servers are
        available
        => PASS
        """
        self.verify_add_storage_domain(positive=True)


@attr(tier=2)
class Test12325(BaseGlusterMount):
    """
    Test a Gluster setup with an Available master and 2 Unavailable
    secondary RHS servers
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    disabled_nodes_ips = [NODES[1], NODES[2]]

    @polarion("RHEVM3-12325")
    def test_creation_backupvolfile(self):
        """
        * Block connection to both secondary servers
        * Try adding the gluster storage domain
        => FAIL (When two of the gluster servers are blocked, the gluster
        volume mode is changed to read-only)
        """
        self.verify_add_storage_domain(positive=False)


@attr(tier=2)
class Test12326(BaseGlusterMount):
    """
    Test Gluster setup with with All RHS servers unavailable
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    disabled_nodes_ips = NODES

    @polarion("RHEVM3-12326")
    def test_creation_backupvolfile(self):
        """
        * Block connection to all the servers
        * Try adding the gluster storage domain
        => FAIL
        """
        self.verify_add_storage_domain(positive=False)


@attr(tier=2)
class VerifyGlusterMountParameteres(BaseGlusterMount):
    """
    Test the backup-volfile-servers parameter works as expected.
    Verify the mount command on the spm host
    """
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']

    def setUp(self):
        """
        Initialize attributes
        """
        super(VerifyGlusterMountParameteres, self).setUp()
        self.address = NODES[0]
        self.mount_point = "%s:%s" % (self.address, self.domain_path)

    def verify_gluster_mount_cmd(
        self, backupvolfile_list, backupvolfile_regex
    ):
        """
        Add the gluster storage domain with the backup-volfile-servers
        parameter, and verify the mount options are present in the vdsm log
        """
        self.regex = "mount -t glusterfs -o backup-volfile-servers=%s %s" % (
            ":".join(backupvolfile_regex), self.mount_point
        )

        def f(q):
            q.put(
                watch_logs(
                    files_to_watch=config.VDSM_LOG,
                    regex=self.regex,
                    time_out=GLUSTER_CMD_TIMEOUT,
                    ip_for_files=self.host_ip,
                    username=self.username, password=self.password,
                )
            )

        q = Queue()
        p = Process(target=f, args=(q,))
        p.start()
        status = self.add_storage_domain(self.address, backupvolfile_list)
        p.join()
        exception_code, output = q.get()
        if not status:
            raise exceptions.StorageDomainException(
                "Error adding gluster storage domain %s" % self.mount_point
            )
        self.assertTrue(
            exception_code,
            "Couldn't find regex %s, output %s" % (self.regex, output)
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
            backupvolfile_list=None, backupvolfile_regex=NODES[1:3]
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
            backupvolfile_list=[NODES[1]], backupvolfile_regex=[NODES[1]]
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
            backupvolfile_list=NODES[1:3], backupvolfile_regex=NODES[1:3]
        )


# TODO
"""
RHEVM3-11327
Test a Gluster setup with 5 Available servers in 2 different Clusters
"""
