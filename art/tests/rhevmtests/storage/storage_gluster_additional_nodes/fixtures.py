"""
Fixtures for test_gluster_additional_nodes module
"""
import pytest
import logging
import config
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
)
from rhevmtests.storage import helpers as storage_helpers
from art.unittest_lib.common import testflow

logger = logging.getLogger(__name__)


@pytest.fixture()
def block_connectivity_gluster_nodes(request, storage):
    """
    Block selected gluster nodes connections to SPM
    """
    self = request.node.cls

    testflow.setup(
        "Blocking the following gluster nodes %s",
        self.disabled_nodes_ips
    )
    self.block_nodes(self.disabled_nodes_ips)


@pytest.fixture()
def unblock_connectivity_gluster_nodes(request, storage):
    """
    Unblock specific gluster nodes connections
    """

    self = request.node.cls

    def finalizer():
        testflow.teardown(
            "Unblocking specific gluster nodes %s",
            self.disabled_nodes_ips
        )
        self.unblock_nodes(self.disabled_nodes_ips)
    request.addfinalizer(finalizer)


@pytest.fixture()
def initialize_params(request, storage):
    """
    Initialize parameters
    """
    self = request.node.cls

    self.storage_domain = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_SD
    )
    self.disk_alias = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_DISK
    )
    self.domain_path = config.GLUSTER_REPLICA_PATH
    self.disabled_nodes_ips = getattr(self, 'disabled_nodes_ips', [])

    self.host = ll_hosts.get_spm_host(config.HOSTS)
    self.host_ip = ll_hosts.get_host_ip(self.host)

    self.address = config.NODES[0]
    self.mount_point = "%s:%s" % (self.address, self.domain_path)


@pytest.fixture()
def create_gluster_storage_domain_with_or_without_additional_nodes(
    request, storage
):
    """
    Create/Remove gluster storage domain w/wo additional nodes
    """

    self = request.node.cls

    if self.backup_vol_file_server:
        logger.info(
            "Adding storage domain %s with additional nodes %s",
            self.storage_domain, config.NODES[1:3]
        )
        self.add_storage_domain(
            address=config.NODES[0], backupvolfile_list=config.NODES[1:3])
    else:
        logger.info(
            "Adding storage domain %s without additional nodes",
            self.storage_domain
        )
        self.add_storage_domain(
            address=config.NODES[0], backupvolfile_list=[]
        )
    logger.info(
        "Attaching storage domain %s to data center %s",
        self.storage_domain, config.DATA_CENTER_NAME
    )
    assert ll_sd.attachStorageDomain(
        True, config.DATA_CENTER_NAME, self.storage_domain
    ), "Unable to add storage domain %s" % self.storage_domain
