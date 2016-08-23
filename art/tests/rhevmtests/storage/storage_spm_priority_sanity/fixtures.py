import pytest
import logging
import config
import helpers
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
)
from art.unittest_lib import testflow
from rhevmtests.storage.fixtures import (
    unblock_connectivity_storage_domain_teardown
)  # flake8: noqa

logger = logging.getLogger(__name__)


@pytest.fixture()
def wait_for_spm(request, storage):
    """
    Wait for SPM to be elected
    """

    def finalizer():
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME,
            config.WAIT_FOR_SPM_TIMEOUT, config.RETRY_INTERVAL
        ), 'SPM host was not elected in %s' % config.DATA_CENTER_NAME
    request.addfinalizer(finalizer)


@pytest.fixture()
def remove_host(request, storage):
    """
    Remove host from the environment
    """
    self = request.node.cls

    self.removed_host = getattr(
        self, 'removed_host', self.hsm_hosts[0]
    )
    self.host_object = config.VDS_HOSTS[config.HOSTS.index(self.removed_host)]
    testflow.setup(
        "Remove host '%s' from %s", self.removed_host, config.DATA_CENTER_NAME
    )
    assert ll_hosts.remove_host(True, self.removed_host, True), (
        "Failed to remove host %s" % self.removed_host
    )


@pytest.fixture()
def activate_hosts(request, storage):
    """
    Activate given hosts
    """
    self = request.node.cls

    def finalizer():
        """
        Activate given hosts
        """
        testflow.teardown("Activate hosts: %s ", self.hosts_to_activate)
        for host in self.hosts_to_activate:
            assert ll_hosts.activate_host(True, host), (
                "Failed to activate host %s" % host
            )
    request.addfinalizer(finalizer)
    self.hosts_to_activate = getattr(self, 'hosts_to_activate', list())


@pytest.fixture()
def deactivate_hsm_hosts(request, storage, activate_hosts):
    """
    Deactivate HSM hosts
    """
    self = request.node.cls

    def finalizer():
        """
        Activate all HSM hosts
        """
        testflow.teardown("Activate hosts: %s ", self.hsm_hosts)
        self.hosts_to_activate = self.hsm_hosts
    request.addfinalizer(finalizer)

    helpers.deactivate_and_verify_hosts(hosts=self.hsm_hosts)


@pytest.fixture()
def initialize_hosts_params(request, storage, activate_hosts):
    """
    Initialize hosts params
    """
    self = request.node.cls

    def finalizer():
        """
        Set host that should be activate by 'activate_hosts'
        """
        self.hosts_to_activate = [
            host for host in config.HOSTS if host not in self.hosts
        ]
    request.addfinalizer(finalizer)

    self.high_spm_priority_host = getattr(
        self, 'high_spm_priority_host', self.hsm_hosts[0]
    )
    self.low_spm_priority_host = getattr(
        self, 'low_spm_priority_host', self.hsm_hosts[1]
    )
    self.hosts = getattr(
        self, 'hosts',
        [self.high_spm_priority_host, self.low_spm_priority_host]
    )
    self.priorities = getattr(
        self, 'priorities',
        [config.DEFAULT_SPM_PRIORITY, config.DEFAULT_SPM_PRIORITY - 1]
    )


@pytest.fixture()
def activate_old_master_domain(request, storage):
    """
    Activate old master storage domain
    """
    self = request.node.cls

    def finalizer():
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.old_master_domain, wait=True
        ), ("Failed to activate storage domain '%s'", self.old_master_domain)
    request.addfinalizer(finalizer)

    if not hasattr(self, 'old_master_domain'):
        self.old_master_domain = ll_sd.get_master_storage_domain_name(
            config.DATA_CENTER_NAME
        )
    self.old_master_domain = getattr(
        self, 'old_master_domain', ll_sd.get_master_storage_domain_name(
            config.DATA_CENTER_NAME
        )
    )


@pytest.fixture()
def set_different_host_priorities(request, storage):
    """
    Set different priorities to HSM hosts and SPM host
    """
    self = request.node.cls

    self.hsm_priorities = getattr(
        self, 'hsm_priorities', [config.MIN_SPM_PRIORITY] * len(self.hsm_hosts)
    )
    testflow.setup("Setting HSM priorities for hosts: %s", self.hsm_hosts)
    for host, priority in zip(self.hsm_hosts, self.hsm_priorities):
        assert ll_hosts.set_spm_priority(True, host, priority), (
            'Unable to set host %s priority' % host
        )
    self.spm_priority = getattr(self, 'spm_priority', 2)
    testflow.setup("Setting SPM priority for hosts: %s", self.spm_host)
    assert ll_hosts.set_spm_priority(True, self.spm_host, self.spm_priority), (
        'Unable to set host %s priority' % self.spm_host
    )


@pytest.fixture()
def check_hosts_status(request, activate_hosts):
    """
    Create list of hosts to activate after test
    """
    self = request.node.cls

    def finalizer():
        for host in config.HOSTS:
            if ll_hosts.is_host_up(False, host):
                self.hosts_to_activate.append(host)

    request.addfinalizer(finalizer)


@pytest.fixture()
def init_host_and_sd_params(request, storage):
    """
    Initialize host and storage domain for test
    """
    self = request.node.cls

    self.host_ip = ll_hosts.get_host_ip(self.spm_host)
    found, non_master_obj = ll_sd.findNonMasterStorageDomains(
        True, config.DATA_CENTER_NAME,
    )
    assert found, "Failed to find non-master storage domain"
    self.non_master = non_master_obj['nonMasterDomains'][0]
    self.storage_domain_ip = ll_sd.getDomainAddress(
        True, self.non_master
    )[1]['address']


@pytest.fixture()
def init_params_for_unblock(
    request, unblock_connectivity_storage_domain_teardown
):
    """
    Initialize parameters for unblock connectivity teardown
    """
    self = request.node.cls

    def finalizer():
        self.host_ip = ll_hosts.get_host_ip(self.high_spm_priority_host)
        self.storage_domain_ip = self.engine_ip

    request.addfinalizer(finalizer)
