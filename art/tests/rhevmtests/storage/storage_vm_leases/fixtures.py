import config
import pytest
import time
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
)
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from rhevmtests.storage import helpers as storage_helpers


@pytest.fixture(scope='class')
def unblock_engine_to_host(request, storage):
    """
    Unblock connection from engine to host
    """
    def finalizer():
        testflow.teardown(
            "Unblock connection from engine %s to host %s",
            config.ENGINE.host.ip, config.PLACEMENT_HOST_IP
        )
        storage_helpers.unblockOutgoingConnection(
            config.ENGINE.host.ip, config.HOSTS_USER, config.HOSTS_PW,
            config.PLACEMENT_HOST_IP
        )

    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def unblock_host_to_storage_domain(request, storage):
    """
    Unblock connection host to storage domain
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown(
            "Unblock connection from host %s to storage domain %s",
            config.PLACEMENT_HOST, self.storage_domain
        )
        for ip in self.storage_domain_ips:
            storage_helpers.unblockOutgoingConnection(
                config.PLACEMENT_HOST_IP, config.HOSTS_USER, config.HOSTS_PW,
                ip
            )

    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def initialize_params(request, storage):
    """
    Initialize all variables
    """
    self = request.node.cls

    self.vm_names = []
    num_of_vms = getattr(self, 'num_of_vms', 1)
    for index in range(num_of_vms):
        self.vm_names.append(
            storage_helpers.create_unique_object_name(
                "{0}_{1}".format(index, self.__name__),
                config.OBJECT_TYPE_VM
            )
        )
    if num_of_vms == 1:
        self.vm_name = self.vm_names[0]

    self.storage_domains = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, self.storage
    )
    # In case the test creates a new data center get the storage domain
    # attached to it
    self.storage_domain = getattr(
        self, 'new_storage_domain', self.storage_domains[0]
    )

    self.storage_domain_ips = hl_sd.get_storage_domain_addresses(
        self.storage_domain
    )
    self.storage_domain_kwargs = {
        'storage_type': config.STORAGE_TYPE_NFS,
        'address': config.UNUSED_DATA_DOMAIN_ADDRESSES[1],
        'path': config.UNUSED_DATA_DOMAIN_PATHS[1]
    }

    self.template_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_TEMPLATE
    )


@pytest.fixture(scope='class')
def finalizer_wait_for_host_up(request, storage):
    """
    Wait until host is back up
    """
    def finalizer():
        testflow.teardown(
            "Waiting for host %s to be UP", config.PLACEMENT_HOST
        )
        assert ll_hosts.wait_for_hosts_states(
            True, [config.PLACEMENT_HOST], config.HOST_UP
        )
        # Adding for testing WA for BZ1459865 - avoid creating external VM
        time.sleep(60)

    request.addfinalizer(finalizer)
