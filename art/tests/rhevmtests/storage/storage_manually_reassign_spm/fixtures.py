import pytest
import logging
import config

from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    hosts as ll_hosts,
    vms as ll_vms,
    storagedomains as ll_sd,
)
import rhevmtests.storage.helpers as storage_helpers
from art.unittest_lib import testflow

logger = logging.getLogger(__name__)


@pytest.fixture()
def init_non_master_domains_params(request, storage):
    """
    Extract non-master domain name and address
    """
    self = request.node.cls

    found, non_master_domain_obj = ll_sd.findNonMasterStorageDomains(
        True, config.DATA_CENTER_NAME
    )
    assert found, (
        "Could not find non-master storage domains on Data center '%s'"
        % config.DATA_CENTER_NAME
    )
    self.non_master_domain = non_master_domain_obj['nonMasterDomains'][0]

    rc, non_master_address = ll_sd.getDomainAddress(
        True, self.non_master_domain
    )
    assert rc, (
        "Could not get the address of '%s'" % self.non_master_domain
    )
    self.non_master_address = non_master_address

    logger.info(
        'Found non-master %s domain in address: %s',
        self.non_master_domain, self.non_master_address['address']
    )


@pytest.fixture()
def flush_iptable_block(request, storage):
    """
    Flush iptables rule
    """
    self = request.node.cls

    def finalizer():
        self.blocked_domain = ll_hosts.get_host_ip(self.spm_host)
        testflow.teardown(
            "Unblocking connection between %s and %s" % (
                self.blocked_domain, self.non_master_address['address']
            )
        )
        assert storage_helpers.setup_iptables(
            self.blocked_domain, self.non_master_address, block=False
        ), "Failed to unblock connection between %s and %s" % (
            self.blocked_domain, self.non_master_address['address']
        )

        assert ll_dc.waitForDataCenterState(
            config.DATA_CENTER_NAME, config.DATA_CENTER_UP,
            timeout=config.WAIT_FOR_DC_TIMEOUT
        ), "Datacenter %s failed to reach status 'up'" % (
            config.DATA_CENTER_NAME
        )
        assert ll_hosts.wait_for_hosts_states(
            True, self.spm_host
        ), ("Host %s failed to reach status 'up'" % self.spm_host)
    request.addfinalizer(finalizer)


@pytest.fixture()
def fin_activate_host(request, storage):
    """
    Activate host
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Activate host %s", self.spm_host)
        assert ll_hosts.activate_host(True, self.spm_host), (
            "Unable to activate host %s ", self.spm_host
        )
        ll_hosts.wait_for_hosts_states(True, self.spm_host)
    request.addfinalizer(finalizer)


@pytest.fixture()
def activate_domain(request, storage):
    """
    activates storage domain
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown(
            "Activating storage domain %s", self.non_master_domain
        )
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.RETRY_INTERVAL
        ), "SPM host was not elected"

        assert ll_sd.wait_for_storage_domain_status(
            True, config.DATA_CENTER_NAME, self.non_master_domain,
            config.ENUMS['storage_domain_state_maintenance']
        ), "Storage domain '%s' failed to reach maintenance mode" % (
            self.non_master_domain
        )
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.non_master_domain
        ), "Failed to activate storage domain %s" % self.non_master_domain

    request.addfinalizer(finalizer)


@pytest.fixture()
def start_vm_on_hsm_host(request, storage):
    """
    Start VM on HSM host
    """
    self = request.node.cls

    self.vm_host = self.hsm_hosts[0]
    assert ll_vms.startVm(
        True, self.vm_name, wait_for_status=config.VM_UP,
        placement_host=self.vm_host
    ), "Failed to Start VM '%s' on '%s'" % (self.vm_name, self.vm_host)


@pytest.fixture()
def retrieve_master_domain_for_vm_creation(request, storage):
    """
    Create VM on master storage domain
    """
    self = request.node.cls

    if not hasattr(self, 'storage_domain'):
        found, master_domain_obj = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        assert found, (
            "Could not find master storage domain on Data center '%s'" %
            config.DATA_CENTER_NAME
        )
        self.storage_domain = master_domain_obj['masterDomain']
