"""
3.3 Manually Reassign SPM
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Manually_Resign_SPM
"""
import logging
import pytest
import config
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler import exceptions
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    tier3,
    tier4,
    storages,
)
from art.unittest_lib import StorageTest as BaseTestCase, testflow
from rhevmtests.storage import helpers as storage_helpers
from rhevmtests.storage.fixtures import (
    delete_disks, set_spm_priorities, init_master_domain_params, create_vm
)
from rhevmtests.storage.fixtures import remove_vm  # noqa
from rhevmtests.storage.storage_manually_reassign_spm.fixtures import (
    init_non_master_domains_params, flush_iptable_block, activate_domain,
    start_vm_on_hsm_host, retrieve_master_domain_for_vm_creation,
    fin_activate_host
)
logger = logging.getLogger(__name__)


@storages((config.NOT_APPLICABLE,))
@pytest.mark.usefixtures(
    set_spm_priorities.__name__
)
class BasicEnvironment(BaseTestCase):
    """
    Base class that ensures DC, all domains and hosts are up, SPM is elected
    and SPM priorities are set to default for all hosts
    """


@pytest.mark.usefixtures(
    init_master_domain_params.__name__,
    init_non_master_domains_params.__name__,
    flush_iptable_block.__name__
)
class ReassignSPMWithStorageBlocked(BasicEnvironment):
    """
    Block connection between specified hosts and specified domain and try to
    reassign SPM
    """
    target_host_address = None
    origin_host_address = None
    blocked_domain = None
    blocked_domain_name = None

    def block_connection_and_reassign_spm(self, positive=True):
        """
        Block connection between host to domain/engine and select a new SPM

        :param positive: True if HSM should become SPM, False otherwise
        :type positive: bool
        """
        testflow.step(
            "Blocking connection between %s and %s", self.origin_host_address,
            self.non_master_domain
        )
        assert storage_helpers.setup_iptables(
            self.origin_host_address, self.target_host_address, block=True
        ), (
            "Unable to block connection between %s and %s" %
            (self.origin_host_address, self.non_master_domain)
        )

        self.blocked_domain = self.origin_host_address
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
        testflow.step("Setting host %s to be new SPM", self.hsm_hosts[0])
        status = ll_hosts.select_host_as_spm(
            True, self.hsm_hosts[0], config.DATA_CENTER_NAME,
            timeout=config.WAIT_FOR_SPM_TIMEOUT
        )
        if positive and not status:
            raise exceptions.HostException(
                "Unable to set host %s as SPM" % self.hsm_hosts[0]
            )
        else:
            logger.info("Unable to set host %s as SPM" % self.hsm_hosts[0])

        if positive:
            logger.info("Ensuring host %s is SPM", self.hsm_hosts[0])
            assert ll_hosts.check_host_spm_status(True, self.hsm_hosts[0]), (
                "Host %s doesn't elected as SPM" % self.hsm_hosts[0]
            )


class TestCase5815(BasicEnvironment):
    """
    Assign HSM host to be SPM while another host is SPM of DC
    """
    __test__ = True
    polarion_test_case = '5815'

    @polarion("RHEVM3-5815")
    @tier2
    def test_reassign_spm(self):
        """
        * Select HSM to be SPM
        Expected result: HSM host should become the SPM
        """
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
        testflow.step("Selecting host %s as new SPM", self.hsm_hosts[0])
        assert ll_hosts.select_host_as_spm(
            True, self.hsm_hosts[0], config.DATA_CENTER_NAME
        ), "Unable to set host %s as SPM" % self.hsm_hosts[0]


@pytest.mark.usefixtures(
    fin_activate_host.__name__
)
class TestCase5823(BasicEnvironment):
    """
    Reassign of SPM server when entering maintenance mode
    """
    __test__ = True
    polarion_test_case = '5823'

    @polarion("RHEVM3-5823")
    @tier2
    def test_reassign_spm_when_deactivate_spm_host(self):
        """
        * Put SPM host in maintenance
        * Verify HSM host become the SPM
        Expected result: HSM host becomes SPM
        """
        testflow.step("Deactivate SPM host %s", self.spm_host)
        wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
        assert ll_hosts.deactivate_host(
            True, self.spm_host
        ), "Unable to deactivate host %s " % self.spm_host
        testflow.step("Waiting for new SPM to be elected")
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.RETRY_INTERVAL
        ), "A new SPM host was not elected"


@pytest.mark.usefixtures(
    delete_disks.__name__
)
class TestCase5818(BasicEnvironment):
    """
    Manually reassign SPM during async task
    """
    __test__ = True
    polarion_test_case = '5818'
    disk_alias = None
    disks_to_remove = list()

    @polarion("RHEVM3-5818")
    @tier2
    def test_select_new_host_as_spm_during_async_task(self):
        """
        *  Run an async task (such as adding a disk)
        *  Attempt to reassign the SPM during the async task execution
        Expected result: HSM host shouldn't become SPM
        """
        self.disk_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        domain_name = (
            ll_sd.get_master_storage_domain_name(config.DATA_CENTER_NAME)
        )
        testflow.step(
            "Perform async operation - Add disk %s", self.disk_alias
        )
        assert ll_disks.addDisk(
            True, alias=self.disk_alias, provisioned_size=config.GB,
            interface=config.VIRTIO, sparse=False, format=config.RAW_DISK,
            storagedomain=domain_name
        ), "Failed to add disk '%s'" % self.disk_alias
        self.disks_to_remove.append(self.disk_alias)
        testflow.step("Trying to select host %s as new SPM", self.hsm_hosts[0])
        assert not ll_hosts.select_host_as_spm(
            False, self.hsm_hosts[0], config.DATA_CENTER_NAME
        ), 'Host %s set as SPM' % self.hsm_hosts[0]


@pytest.mark.usefixtures(
    init_non_master_domains_params.__name__,
    activate_domain.__name__
)
class TestCase5819(BasicEnvironment):
    """
    Reassign SPM during storage domain deactivation
    """
    __test__ = True
    polarion_test_case = '5819'

    @polarion("RHEVM3-5819")
    @tier2
    def test_reassign_spm_during_deactivate_domain(self):
        """
        * Deactivate storage domain
        * Attempt to reassign SPM while storage domain is being deactivated
        Expected result: HSM host shouldn't become SPM
        """
        testflow.step("Deactivating storage domain %s", self.non_master_domain)
        assert ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.non_master_domain,
            wait=False
        ), "Unable to deactivate domain %s" % self.non_master_domain

        testflow.step("Trying to select host %s as new SPM", self.hsm_hosts[0])
        assert not ll_hosts.select_host_as_spm(
            False, self.hsm_hosts[0], config.DATA_CENTER_NAME
        ), "Host %s set as SPM" % self.hsm_hosts[0]


@pytest.mark.usefixtures(
    retrieve_master_domain_for_vm_creation.__name__,
    create_vm.__name__,
    start_vm_on_hsm_host.__name__,
    delete_disks.__name__
)
class TestCase14812(BasicEnvironment):
    """
    Bug 1319987 - Storage activities are failing with error
    "Image is not a legal chain"
    """
    __test__ = True
    polarion_test_case = '14812'

    disk_alias = None
    disks_to_remove = list()

    @polarion("RHEVM3-14812")
    @tier3
    def test_reassign_spm_to_host_with_vm_and_perform_storage_operation(self):
        """
        * Create VM and run it on HSM host
        * Reassign SPM to the HSM host running the VM created
        * Power off the VM and add a floating disk
        """
        testflow.step("Set '%s' to be the SPM", self.vm_host)
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
        assert ll_hosts.select_host_as_spm(
            True, self.vm_host, config.DATA_CENTER_NAME,
            timeout=config.WAIT_FOR_SPM_TIMEOUT, sleep=config.RETRY_INTERVAL,
            wait=True
        ), "Unable to set host %s as SPM" % self.vm_host

        testflow.step("Power off VM '%s'", self.vm_name)
        assert ll_vms.stop_vms_safely(
            [self.vm_name]
        ), "Failed to power off VM %s" % self.vm_name

        self.disk_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )

        testflow.step(
            "Perform async operation - Add disk '%s'", self.disk_alias
        )
        assert ll_disks.addDisk(
            True, alias=self.disk_alias, provisioned_size=config.GB,
            interface=config.VIRTIO, sparse=False, format=config.RAW_DISK,
            storagedomain=self.storage_domain
        ), "Failed to add disk '%s'" % self.disk_alias
        assert ll_disks.wait_for_disks_status(
            [self.disk_alias]
        ), "Disk %s is not in the expected state 'OK" % self.disk_alias
        self.disks_to_remove.append(self.disk_alias)
        testflow.step("Disk '%s' created successfully", self.disk_alias)


class TestCase5820(ReassignSPMWithStorageBlocked):
    """
    Resign SPM where host can't see non-Master Storage Domain
    """
    __test__ = True
    polarion_test_case = '5820'

    @polarion("RHEVM3-5820")
    @tier4
    def test_set_spm_with_blocked_non_master_domain(self):
        """
        * Block connection between SPM and non-master domain
        * Set HSM host as SPM
        Expected result: HSM host should become SPM,
        former SPM host becomes non-operational
        """
        self.target_host_address = self.non_master_address
        self.blocked_domain_name = self.spm_host
        self.origin_host_address = ll_hosts.get_host_ip(
            self.blocked_domain_name
        )
        self.block_connection_and_reassign_spm()


class TestCase5821(ReassignSPMWithStorageBlocked):
    """
    Resign SPM where host can't see Master Storage Domain
    """
    __test__ = True
    polarion_test_case = '5821'

    @polarion("RHEVM3-5821")
    @tier4
    def test_set_spm_with_blocked_master_domain(self):
        """
        * Block connection between SPM and master domain
        * Set HSM host as SPM
        Expected result: HSM host should become SPM,
        former SPM become non-operational
        """
        self.target_host_address = self.master_domain_address
        self.blocked_domain_name = self.spm_host
        self.origin_host_address = ll_hosts.get_host_ip(
            self.blocked_domain_name
        )
        self.block_connection_and_reassign_spm()
