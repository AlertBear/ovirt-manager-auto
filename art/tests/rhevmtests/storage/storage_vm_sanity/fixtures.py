"""
Fixture module for storage vm sanity
"""
import config
import pytest
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
)
from rhevmtests.storage import helpers as storage_helpers


@pytest.fixture(scope='class')
def deactivate_hsms(request, storage):
    """
    Deactivate all HSMs
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Activating all HSMs")
        for host in self.hosts_to_activate:
            assert ll_hosts.activate_host(True, host), (
                "Failed to activate host %s" % host
            )

    request.addfinalizer(finalizer)

    spm_host = ll_hosts.get_spm_host(config.HOSTS)
    self.hosts_to_activate = list()
    testflow.setup("Deactivating all HSMs")
    for host in config.HOSTS:
        if host == spm_host:
            continue
        assert ll_hosts.deactivate_host(True, host), (
            "Failed to deactivate host %s" % host
        )
        self.hosts_to_activate.append(host)


@pytest.fixture(scope='class')
def initialize_object_names(request, storage):
    """
    Initialize storage_domain and VM names
    """
    self = request.node.cls

    self.vm_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    self.storage_domain = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, self.storage
    )[0]


@pytest.fixture(scope='class')
def wait_for_hosts_to_be_up(request, storage):
    """
    Wait for all host to be in 'up' state
    """
    def finalizer():
        assert ll_hosts.wait_for_hosts_states(True, config.HOSTS)

    request.addfinalizer(finalizer)
