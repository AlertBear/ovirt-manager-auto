"""
3.3 Manually Reassign SPM
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Manually_Resign_SPM
"""
import logging
import config
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    disks as ll_disks,
    hosts as ll_hosts,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    vms as ll_vms,
)
import art.rhevm_api.utils.storage_api as st_api
from art.test_handler import exceptions
from art.test_handler.tools import bz, polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as BaseTestCase
from rhevm_api.utils.test_utils import wait_for_tasks
from rhevmtests.storage import helpers as storage_helpers

logger = logging.getLogger(__name__)
POLARION_PROJECT = "RHEVM3-"
RETRY_INTERVAL = 10
WAIT_FOR_SPM_TIMEOUT = 120
WAIT_FOR_DC_TIMEOUT = 360


class BasicEnvironment(BaseTestCase):
    """
    Base class that ensures DC, all domains and hosts are up, SPM is elected
    and SPM priorities are set to default for all hosts
    """
    spm_priorities = []
    spm_host = None
    hsm_hosts = []
    storages = config.NOT_APPLICABLE

    def setUp(self):
        """
        * Set hosts' SPM priorities according to spm_priorities list
        * SPM should be elected
        * Check that all entities for DC are up (hosts, SDs)
        """
        if not self.spm_priorities:
            self.spm_priorities = (
                [config.DEFAULT_SPM_PRIORITY] * len(config.HOSTS)
            )

        logger.info(
            'Setting SPM priorities for hosts: %s', self.spm_priorities
        )
        for host, priority in zip(config.HOSTS, self.spm_priorities):
            if not ll_hosts.setSPMPriority(True, host, priority):
                raise exceptions.HostException(
                    'Unable to set host %s priority' % host
                )

        logger.info('Getting SPM host')
        self.spm_host = ll_hosts.getSPMHost(config.HOSTS)
        self.hsm_hosts = [
            host for host in config.HOSTS if host != self.spm_host
            ]
        logger.info(
            'Found SPM host: %s, hsm hosts: %s', self.spm_host, self.hsm_hosts
        )

        logger.info('Ensuring SPM priority is for all hosts')
        for host, priority in zip(config.HOSTS, self.spm_priorities):
            if not ll_hosts.checkSPMPriority(True, host, str(priority)):
                raise exceptions.HostException(
                    'Unable to check host %s priority' % host
                )

    def tearDown(self):
        """
        Reset SPM priorities for all hosts to default (Normal)
        """
        logger.info(
            'Resetting SPM priority to %s for all hosts', self.spm_priorities
        )
        for host, priority in zip(config.HOSTS, self.spm_priorities):
            if not ll_hosts.setSPMPriority(True, host, priority):
                logger.error("Unable to set host %s priority", host)
                BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


class ReassignSPMWithStorageBlocked(BasicEnvironment):
    """
    Block connection between specified hosts and specified domain and try to
    reassign SPM
    """
    target_host_address = None
    origin_host_address = None
    blocked_domain = None
    blocked_domain_name = None
    master_domain = None
    master_domain_address = None
    non_master_domain = None
    non_master_address = None

    def setUp(self):
        """
        Extract domains' names and addresses
        """
        super(ReassignSPMWithStorageBlocked, self).setUp()
        found, master_domain_obj = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        if not found:
            raise exceptions.StorageDomainException(
                "Could not find master storage domain on Data center '%s'" %
                config.DATA_CENTER_NAME
            )

        found, non_master_domain_obj = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )
        if not found:
            raise exceptions.StorageDomainException(
                "Could not find non-master storage domains on Data center '%s'"
                % config.DATA_CENTER_NAME
            )

        self.master_domain = master_domain_obj['masterDomain']
        self.non_master_domain = non_master_domain_obj['nonMasterDomains'][0]
        logger.info(
            'Found master domain: %s, non-master domain: %s',
            self.master_domain, self.non_master_domain
        )

        rc, master_domain_address = ll_sd.getDomainAddress(
            True, self.master_domain
        )
        if not rc:
            raise exceptions.StorageDomainException(
                "Could not get the address of '%s'" % self.master_domain
            )

        rc, non_master_address = ll_sd.getDomainAddress(
            True, self.non_master_domain
        )
        if not rc:
            raise exceptions.StorageDomainException(
                "Could not get the address of '%s'" % self.non_master_address
            )

        self.master_domain_address = master_domain_address['address']
        self.non_master_address = non_master_address['address']
        logger.info(
            'Found master domain address: %s, non-master domain '
            'address: %s', self.master_domain_address, self.non_master_address
        )

    def block_connection_and_reassign_spm(self, positive=True):
        """
        Block connection between host to domain/engine and select a new SPM

        :param positive: True if HSM should become SPM, False otherwise
        :type positive: bool
        """
        logger.info(
            'Blocking connection between %s and %s', self.origin_host_address,
            self.target_host_address
        )
        if not st_api.blockOutgoingConnection(
            self.origin_host_address, config.HOSTS_USER, config.HOSTS_PW,
            self.target_host_address
        ):
            raise exceptions.NetworkException(
                'Unable to block connection between %s and %s' %
                (self.origin_host_address, self.target_host_address)
            )

        self.blocked_domain = self.origin_host_address

        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        logger.info('Setting host %s to be new SPM', self.hsm_hosts[0])
        status = ll_hosts.select_host_as_spm(
            True, self.hsm_hosts[0], config.DATA_CENTER_NAME,
            timeout=WAIT_FOR_SPM_TIMEOUT
        )
        if positive and not status:
            raise exceptions.HostException(
                'Unable to set host %s as SPM' % self.hsm_hosts[0]
            )
        else:
            logger.info('Unable to set host %s as SPM' % self.hsm_hosts[0])

        if positive:
            logger.info('Ensuring host %s is SPM', self.hsm_hosts[0])
            if not ll_hosts.checkHostSpmStatus(
                True, self.hsm_hosts[0]
            ):
                raise exceptions.HostException(
                    "Host %s doesn't elected as SPM" % self.hsm_hosts[0]
                )

    def tearDown(self):
        """
        Remove iptables rule
        """
        logger.info(
            "Host '%s' blocked from reaching '%s'", self.target_host_address,
            self.blocked_domain
        )

        logger.info(
            'Unblocking connection between %s and %s', self.blocked_domain,
            self.target_host_address
        )
        if not st_api.unblockOutgoingConnection(
            self.blocked_domain, config.HOSTS_USER, config.HOSTS_PW,
            self.target_host_address
        ):
            logger.error(
                'Failed to unblock connection between %s and %s',
                self.target_host_address, self.blocked_domain
            )
            BaseTestCase.test_failed = True

        if not ll_dc.waitForDataCenterState(
            config.DATA_CENTER_NAME, config.DATA_CENTER_UP,
            timeout=WAIT_FOR_DC_TIMEOUT
        ):
            logger.error(
                "Datacenter %s failed to reach status 'up'",
                config.DATA_CENTER_NAME
            )
            BaseTestCase.test_failed = True

        if not ll_hosts.waitForHostsStates(True, self.blocked_domain_name):
            logger.error(
                "Host %s failed to reach status 'up'", self.spm_host
            )
            BaseTestCase.test_failed = True
        super(ReassignSPMWithStorageBlocked, self).tearDown()


@attr(tier=1)
class TestCase5815(BasicEnvironment):
    """
    RHEVM3-5815 - Assign HSM host to be SPM while another host is SPM of DC
    """
    __test__ = True
    polarion_test_case = '5815'

    @polarion(POLARION_PROJECT, polarion_test_case)
    def test_reassign_spm(self):
        """
        * Select HSM to be SPM
        Expected result: HSM host should become the SPM
        """
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        self.assertTrue(
            ll_hosts.select_host_as_spm(
                True, self.hsm_hosts[0], config.DATA_CENTER_NAME
            ), 'Unable to set host %s as SPM' % self.hsm_hosts[0]
        )


@attr(tier=1)
class TestCase5823(BasicEnvironment):
    """
    RHEVM3-5823 - Reassign of SPM server when entering maintenance mode
    """
    __test__ = True
    polarion_test_case = '5823'

    @polarion(POLARION_PROJECT, polarion_test_case)
    def test_reassign_spm_when_deactivate_spm_host(self):
        """
        * Put SPM host in maintenance
        * Verify HSM host become the SPM
        Expected result: HSM host becomes SPM
        """
        self.assertTrue(
            ll_hosts.deactivateHosts(True, self.spm_host),
            "Unable to deactivate host %s " % self.spm_host
        )

        logger.info('Waiting for SPM to be elected')
        self.assertTrue(
            ll_hosts.waitForSPM(
                config.DATA_CENTER_NAME, WAIT_FOR_SPM_TIMEOUT, RETRY_INTERVAL
            ), 'A new SPM host was not elected'
        )

    def tearDown(self):
        """
        Activate host
        """
        if not ll_hosts.activateHost(True, self.spm_host):
            logger.error(
                "Unable to activate host %s ", self.spm_host
            )
            BaseTestCase.test_failed = True
        ll_hosts.waitForHostsStates(True, self.spm_host)
        super(TestCase5823, self).tearDown()


@attr(tier=2)
class TestCase5818(BasicEnvironment):
    """
    RHEVM3-5818 - Manually reassign SPM during async task
    """
    __test__ = True
    polarion_test_case = '5818'
    disk_alias = None

    @polarion(POLARION_PROJECT, polarion_test_case)
    def test_select_new_host_as_spm_during_async_task(self):
        """
        *  Run an async task (such as adding a disk)
        *  Attempt to reassign the SPM during the async task execution
        Expected result: HSM host shouldn't become SPM
        """
        self.disk_alias = self.create_unique_object_name(
            config.OBJECT_TYPE_DISK
        )
        domain_name = (
            ll_sd.get_master_storage_domain_name(config.DATA_CENTER_NAME)
        )

        self.assertTrue(
            ll_disks.addDisk(
                True, alias=self.disk_alias, size=config.GB,
                interface=config.VIRTIO, sparse=False, format=config.RAW_DISK,
                storagedomain=domain_name
            ), "Failed to add disk '%s'" % self.disk_alias
        )
        self.assertFalse(
            ll_hosts.select_host_as_spm(
                False, self.hsm_hosts[0], config.DATA_CENTER_NAME
            ), 'Host %s set as SPM' % self.hsm_hosts[0]
        )

    def tearDown(self):
        """
        Remove disk
        """
        ll_jobs.wait_for_jobs([config.JOB_ADD_DISK])

        if not ll_disks.deleteDisk(True, self.disk_alias):
            logger.error("Unable to delete disk %s ", self.disk_alias)
            BaseTestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        super(TestCase5818, self).tearDown()


@attr(tier=2)
class TestCase5819(BasicEnvironment):
    """
    RHEVM3-5819 - Reassign SPM during storage domain deactivation
    """
    __test__ = True
    polarion_test_case = '5819'

    def setUp(self):
        """
        Extract non-master domain name
        """
        super(TestCase5819, self).setUp()
        status, non_master_dom = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )
        if not status:
            raise exceptions.StorageDomainException(
                "Could not find non-master storage domains on Data center '%s'"
                % config.DATA_CENTER_NAME
            )
        self.non_master_domain = non_master_dom['nonMasterDomains'][0]
        logger.info(
            'Non-master storage domain %s selected', self.non_master_domain
        )

    @polarion(POLARION_PROJECT, polarion_test_case)
    def test_reassign_spm_during_deactivate_domain(self):
        """
        * Deactivate storage domain
        * Attempt to reassign SPM while storage domain is being deactivated
        Expected result: HSM host shouldn't become SPM
        """
        logger.info('Deactivating storage domain %s', self.non_master_domain)
        self.assertTrue(
            ll_sd.deactivateStorageDomain(
                True, config.DATA_CENTER_NAME, self.non_master_domain,
                wait=False
            ), 'Unable to deactivate domain %s' % self.non_master_domain
        )

        logger.info('Trying to select host %s as new SPM', self.hsm_hosts[0])
        self.assertFalse(
            ll_hosts.select_host_as_spm(
                False, self.hsm_hosts[0], config.DATA_CENTER_NAME
            ), 'Host %s set as SPM' % self.hsm_hosts[0]
        )

    def tearDown(self):
        """
        Activate the storage domain
        """
        if not ll_hosts.waitForSPM(
            config.DATA_CENTER_NAME, WAIT_FOR_SPM_TIMEOUT, RETRY_INTERVAL
        ):
            logger.error('SPM host was not elected')
            BaseTestCase.test_failed = True

        if not ll_sd.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.non_master_domain,
            config.ENUMS['storage_domain_state_maintenance']
        ):
            logger.error(
                "Storage domain '%s' failed to reach maintenance mode" %
                self.non_master_domain
            )
            BaseTestCase.test_failed = True

        logger.info('Activating domain %s', self.non_master_domain)
        if not ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.non_master_domain
        ):
            logger.error(
                "Unable to activate domain %s ", self.non_master_domain
            )
            BaseTestCase.test_failed = True
        super(TestCase5819, self).tearDown()


@attr(tier=2)
class TestCase14812(BasicEnvironment):
    """
    RHEVM3-14812 - Bug 1319987 - Storage activities are failing with error
    "Image is not a legal chain"
    """
    __test__ = True
    polarion_test_case = '14812'

    def setUp(self):
        """
        Create VM and run it on HSM host
        """
        super(TestCase14812, self).setUp()
        self.vm_host = self.hsm_hosts[0]
        self.storage_domain = (
            ll_sd.get_master_storage_domain_name(config.DATA_CENTER_NAME)
        )
        self.vm_name = self.create_unique_object_name(config.OBJECT_TYPE_VM)
        self.disk_alias = self.create_unique_object_name(
            config.OBJECT_TYPE_DISK
        )
        logger.info(
            "Creating vm %s on storage domain %s",
            self.vm_name, self.storage_domain
        )
        args = config.create_vm_args.copy()
        args['storageDomainName'] = self.storage_domain
        args['vmName'] = self.vm_name
        if not storage_helpers.create_vm_or_clone(**args):
            raise exceptions.VMException(
                "Failed to create or clone VM '%s'" % self.vm_name
            )
        if not ll_vms.startVm(
            True, self.vm_name, wait_for_status=config.VM_UP,
            placement_host=self.vm_host
        ):
            raise exceptions.VMException(
                "Failed to activate VM '%s' on '%s'" %
                (self.vm_name, self.vm_host)
            )

    @polarion(POLARION_PROJECT, polarion_test_case)
    def test_reassign_spm_to_host_with_vm_and_perform_storage_operation(self):
        """
        * Create VM and run it on HSM host
        * Reassign SPM to the HSM host running the VM created
        * Power off the VM and add a floating disk
        """
        logger.info("Set '%s' to be the SPM", self.vm_host)
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        self.assertTrue(
            ll_hosts.select_host_as_spm(
                True, self.vm_host, config.DATA_CENTER_NAME,
                timeout=WAIT_FOR_SPM_TIMEOUT, sleep=RETRY_INTERVAL, wait=True
            ), 'Unable to set host %s as SPM' % self.vm_host
        )

        logger.info("Power off VM '%s'", self.vm_name)
        self.assertTrue(
            ll_vms.stop_vms_safely([self.vm_name]),
            'Failed to power off VM %s' % self.vm_name
        )

        logger.info(
            "Perform Storage operation - Add disk '%s'", self.disk_alias
        )
        self.assertTrue(
            ll_disks.addDisk(
                True, alias=self.disk_alias, size=config.GB,
                interface=config.VIRTIO, sparse=False, format=config.RAW_DISK,
                storagedomain=self.storage_domain
            ), "Failed to add disk '%s'" % self.disk_alias
        )
        self.assertTrue(
            ll_disks.wait_for_disks_status([self.disk_alias]),
            "Disk %s is not in the expected state 'OK" % self.disk_alias
        )
        logger.info("Disk '%s' created successfully", self.disk_alias)

    def tearDown(self):
        """
        Remove VM and disk
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to remove VM %s", self.vm_name)
            BaseTestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])

        if not ll_disks.deleteDisk(True, self.disk_alias):
            logger.error("Unable to delete disk %s ", self.disk_alias)
            BaseTestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        super(TestCase14812, self).tearDown()


@attr(tier=4)
class TestCase5820(ReassignSPMWithStorageBlocked):
    """
    RHEVM3-5820 - Resign SPM where host can't see non-Master Storage Domain
    """
    __test__ = True
    polarion_test_case = '5820'

    # Bug description - SPM Host become Non-responsive when block connection
    # to Master/Non-master Storage Domain
    # https://bugzilla.redhat.com/show_bug.cgi?id=1326009
    @bz({'1326009': {}})
    @polarion(POLARION_PROJECT, polarion_test_case)
    def test_set_spm_with_blocked_non_master_domain(self):
        """
        * Block connection between SPM and non-master domain
        * Set HSM host as SPM
        Expected result: HSM host should become SPM,
        former SPM host becomes non-operational
        """
        self.target_host_address = self.non_master_address
        self.blocked_domain_name = self.spm_host
        self.origin_host_address = ll_hosts.getHostIP(self.blocked_domain_name)
        self.block_connection_and_reassign_spm()


@attr(tier=4)
class TestCase5821(ReassignSPMWithStorageBlocked):
    """
    RHEVM3-5821 - Resign SPM where host can't see Master Storage Domain
    """
    __test__ = True
    polarion_test_case = '5821'

    # Bug description - SPM Host become Non-responsive when block connection
    # to Master/Non-master Storage Domain
    # https://bugzilla.redhat.com/show_bug.cgi?id=1326009
    @bz({'1326009': {}})
    @polarion(POLARION_PROJECT, polarion_test_case)
    def test_set_spm_with_blocked_master_domain(self):
        """
        * Block connection between SPM and master domain
        * Set HSM host as SPM
        Expected result: HSM host should become SPM,
        former SPM become non-operational
        """
        self.target_host_address = self.master_domain_address
        self.blocked_domain_name = self.spm_host
        self.origin_host_address = ll_hosts.getHostIP(self.blocked_domain_name)
        self.block_connection_and_reassign_spm()
