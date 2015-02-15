"""
Test Allocation/Total size properties
"""
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.high_level.storagedomains import (
    extend_storage_domain, addISCSIDataDomain, remove_storage_domain,
)
from art.rhevm_api.tests_lib.low_level.datacenters import (
    waitForDataCenterState,
)
from art.rhevm_api.tests_lib.low_level.disks import (
    addDisk, deleteDisk,  waitForDisksState, move_disk, get_disk_obj,
)
from art.rhevm_api.tests_lib.low_level.hosts import (
    waitForHostsStates, waitForSPM, getSPMHost, getHostIP,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    get_allocated_size, get_total_size, wait_for_change_total_size,
    get_used_size, getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.templates import (
    createTemplate, removeTemplate,
)
from art.rhevm_api.tests_lib.low_level.vms import createVm, removeVm
from art.rhevm_api.utils.test_utils import restartVdsmd
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
import config
import logging

logger = logging.getLogger(__name__)

TCMS_PLAN_ID = '2517'
VM_DISK_SIZE = 2 * config.GB

THIN_PROVISION = 'thin_provision'
PREALLOCATED = 'preallocated'


class BaseCase(TestCase):
    """
    Base class. Ensures environment is running and checks, creates disks
    and checks for the disk's value
    """
    __test__ = False

    domains = []

    disk_types = (THIN_PROVISION, PREALLOCATED)
    disk_sizes = [160 * config.GB, 7 * config.GB]

    current_allocated_size = {}
    current_total_size = {}
    current_used_size = {}

    expected_allocated_size = {}
    expected_total_size = {}

    def create_disks(self):
        """
        Creates disks of given types and sizes and updates expected details
        """
        self.disk_names = []
        for disk_type, disk_size, domain in zip(self.disk_types,
                                                self.disk_sizes,
                                                self.disk_domains):
            disk_name = '%s_disk' % disk_type
            logger.info('Creating a %s GB %s disk on domain %s',
                        disk_size, disk_type, domain)
            disk_args = {
                'positive': True,
                'provisioned_size': disk_size,
                'storagedomain': domain,
                'bootable': False,
                'interface': config.VIRTIO_BLK,
                'alias': disk_name,
                'sparse': disk_type == THIN_PROVISION,
                'format': config.RAW_DISK if disk_type == PREALLOCATED else
                config.COW_DISK
            }
            addDisk(**disk_args)
            self.expected_allocated_size[domain] += disk_size
            logger.info('Updating expected allocated size to: %s',
                        self.expected_allocated_size)
            self.disk_names.append(disk_name)
        logger.info('Waiting for disks to be OK')
        self.assertTrue(waitForDisksState(self.disk_names))

    @classmethod
    def setup_class(cls):
        """
        Ensure host + DC up
        """
        logger.info('Checking that host %s is up', config.HOSTS[0])
        assert waitForHostsStates(True, config.HOSTS[0])

        logger.info('Waiting for DC %s to be up', config.DATA_CENTER_NAME)
        assert waitForDataCenterState(config.DATA_CENTER_NAME)

        cls.domains = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)

        logger.info('Found data domains of type %s: %s', cls.storage,
                    cls.domains)

        # by default create both disks on the same domain
        cls.disk_domains = [cls.domains[0], cls.domains[0]]

        # set up parameters used by test
        for domain in cls.domains:
            cls.current_allocated_size[domain] = get_allocated_size(domain)
            cls.current_total_size[domain] = get_total_size(domain)
            cls.current_used_size[domain] = get_used_size(domain)

            logger.debug("Allocated size for %s is %d Total size is %d",
                         domain, cls.current_allocated_size[domain],
                         cls.current_total_size[domain])
            cls.expected_total_size[domain] = cls.current_total_size[domain]
            cls.expected_allocated_size[domain] = cls.current_allocated_size[
                domain]

    def run_scenario(self):
        """
        Run the test
        """
        self.perform_action()
        self.check_storage_details()

    def perform_action(self):
        """
        Should be overridden by actual cases
        """
        pass

    def check_storage_details(self):
        """
        Check that details match expected details
        """
        for domain in self.domains:
            logger.info('Checking info for domain %s', domain)
            allocated_size = get_allocated_size(domain)
            logger.info('Allocated size for domain %s is %s', domain,
                        allocated_size)
            self.assertEqual(allocated_size,
                             self.expected_allocated_size[domain],
                             'Allocated size is: %s, expected is %s'
                             % (allocated_size,
                                self.expected_allocated_size[domain]))
            total_size = get_total_size(domain)
            logger.info('total size for domain %s is %s', domain, total_size)
            self.assertEqual(total_size, self.expected_total_size[domain],
                             'Total size is: %s, expected is %s'
                             % (total_size, self.expected_total_size[domain]))


# TBD: Remove this when is implemented in the main story, storage sanity
# http://rhevm-qe-storage.pad.engineering.redhat.com/11?
@attr(tier=0)
class TestCase286305(BaseCase):
    """
    TCMS Test Case 286305 - Create new disk and check storage details
    """

    __test__ = True
    tcms_test_case = '286305'

    def perform_action(self):
        """
        Create a preallocated and a thin provision disk
        """
        self.create_disks()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_create_disks_and_check_size(self):
        """
        Create preallocated and thin provision disk then check if storage
        domain details are updated accordingly
        """
        self.domains = [self.domains[0]]
        self.run_scenario()

    def tearDown(self):
        """
        Remove the disks that were created
        """
        for name in self.disk_names:
            logger.info('Removing disk %s', name)
            self.assertTrue(deleteDisk(True, name))


@attr(tier=1)
class TestCase286768(BaseCase):
    """
    TCMS Test Case 286768 - Delete disk and check storage details
    https://tcms.engineering.redhat.com/case/286768/
    """

    __test__ = True
    tcms_test_case = '286768'

    def setUp(self):
        """
        Create preallocated and thin provision disks
        """
        self.create_disks()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_delete_disks(self):
        """
        Delete disk and check storage details are updated
        """
        self.domains = [self.domains[0]]
        self.run_scenario()

    def perform_action(self):
        """
        Delete both disks
        """
        for disk_name in self.disk_names:
            disk = get_disk_obj(disk_name)
            logger.info('Removing disk %s', disk.get_alias())
            self.assertTrue(deleteDisk(True, disk.get_alias()))
            self.expected_allocated_size[self.domains[0]] -= \
                disk.get_size()


# TBD: Remove this when is implemented in the main story, storage sanity
# http://rhevm-qe-storage.pad.engineering.redhat.com/11?
@attr(tier=1)
class TestCase286772(BaseCase):
    """
    TCMS Test Case 286772 - Move disks and check storage details of both
    domains
    """

    # TODO: Move floating disk through REST not working development -
    # enable test once this feature works
    __test__ = False
    tcms_test_case = '286772'

    disk_types = ('thin_provision', 'preallocated')
    disk_sizes = [160 * config.GB, 7 * config.GB]

    def setUp(self):
        """
        Create preallocated and thin provision disks
        """
        self.create_disks()

    def perform_action(self):
        """
        Move disks from first domain to second domain
        """
        for disk_name in self.disk_names:
            disk = get_disk_obj(disk_name)
            logger.info('Moving disk %s from domain %s to domain %s',
                        disk.get_alias(), self.domains[0],
                        self.domains[1])
            self.assertTrue(
                move_disk(
                    disk_name=disk.get_alias(),
                    target_domain=self.domains[1]
                )
            )
            self.expected_allocated_size[self.domains[0]] -= disk.get_size()
            self.expected_allocated_size[self.domains[1]] += \
                disk.get_size()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_move_disks(self):
        """
        Move disks and check domain details
        """
        self.run_scenario()

    def tearDown(self):
        """
        Delete disks that were created in setup
        """
        for name in self.disk_names:
            logger.info('Removing disk %s', name)
            self.assertTrue(deleteDisk(True, name))


@attr(tier=1)
class TestCase286775(BaseCase):
    """
    TCMS Test Case 286775 - Extend domain and check storage details
    https://tcms.engineering.redhat.com/case/286775
    """
    # test case only relevant to iscsi domains
    __test__ = BaseCase.storage == config.STORAGE_TYPE_ISCSI
    apis = BaseCase.apis - set(['sdk'])
    tcms_test_case = '286775'
    new_sd_name = "storage_domain_%s" % tcms_test_case

    @classmethod
    def setup_class(cls):
        """
        Add a new storage domain and extend it. Needed so that the original
        environment is not changed in case is run in a common environment,
        such as in the case of the golden environment or in a tiered approach
        """
        cls.spm_host = getSPMHost(config.HOSTS)
        assert addISCSIDataDomain(
            config.HOSTS[0], cls.new_sd_name, config.DATA_CENTER_NAME,
            config.EXTEND_LUN[0], config.EXTEND_LUN_ADDRESS[0],
            config.EXTEND_LUN_TARGET[0],
        )
        super(TestCase286775, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """Remove the added storage domain"""
        remove_storage_domain(
            cls.new_sd_name, config.DATA_CENTER_NAME, cls.spm_host)

    def perform_action(self):
        """
        Extend first domain
        """
        logger.info('Extending first domain %s', self.new_sd_name)
        extend_luns = config.EXTEND_LUNS.pop()
        extend_storage_domain(self.new_sd_name,
                              config.STORAGE_TYPE,
                              config.HOSTS[0],
                              **extend_luns)
        self.expected_total_size[self.new_sd_name] += \
            config.EXTEND_SIZE * config.GB

        # Waits until total size changes (extend is done)
        # wait_for_tasks doesn't work (value is not updated properly)
        wait_for_change_total_size(
            self.new_sd_name, self.current_total_size[self.new_sd_name])

        # Assert size hasn't changed during the extend
        self.assertEqual(self.current_used_size[self.new_sd_name],
                         get_used_size(self.new_sd_name))

    @bz({'1159637': {'engine': None, 'version': ['3.5']}})
    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_extend_domain_and_check_details(self):
        """
        Extend storage domain and check if total size is updated
        """
        self.run_scenario()


@attr(tier=1)
class TestCase321336(BaseCase):
    """
    TCMS Test Case 321336 - Create template and check storage details
    https://tcms.engineering.redhat.com/case/321336
    """

    __test__ = True
    tcms_test_case = '321336'
    vms = (THIN_PROVISION, PREALLOCATED)

    def setUp(self):
        """
        Create 2 vms, one with preallocated and one with thin provision disks
        """
        for vm_name in self.vms:
            logger.info('Creating vm with %s disks', vm_name)
            is_thin_provision = vm_name == THIN_PROVISION
            disk_format = config.COW_DISK if is_thin_provision else \
                config.RAW_DISK
            vm_args = {
                'positive': True,
                'vmName': vm_name,
                'vmDescription': vm_name,
                'cluster': config.CLUSTER_NAME,
                'storageDomainName': self.domains[0],
                'size': VM_DISK_SIZE,
                'volumeType': is_thin_provision,
                'volumeFormat': disk_format
            }
            self.assertTrue(createVm(**vm_args),
                            'unable to create vm %s' % vm_name)
            self.expected_allocated_size[self.domains[0]] += VM_DISK_SIZE

        self.template_names = ['%s_template' % name for name in self.vms]

    def tearDown(self):
        """
        Remove vms and templates
        """
        for vm_name in self.vms:
            logger.info('Removing vm %s', vm_name)
            self.assertTrue(removeVm(True, vm_name),
                            'Unable to remove vm %s' % vm_name)

        for template in self.template_names:
            logger.info('Removing template %s', template)
            self.assertTrue(removeTemplate(True, template))

    def perform_action(self):
        """
        Create templates from vms (one with preallocated disk, one with thin
        provision disk)
        """
        for vm_name, template_name in zip(self.vms, self.template_names):
            logger.info('Creating template %s from vm %s', vm_name,
                        template_name)
            template_args = {
                'positive': True,
                'name': template_name,
                'vm': vm_name,
            }
            self.assertTrue(createTemplate(**template_args),
                            "Unable to create template %s" % template_name)
            self.expected_allocated_size[self.domains[0]] += VM_DISK_SIZE

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_create_templates(self):
        """
        Create templates and check storage domain details
        """
        self.run_scenario()


@attr(tier=3)
class TestCase286779(BaseCase):
    """
    TCMS Test Case 286779 - Check  storage domain details after rollback
    https://tcms.engineering.redhat.com/case/286779
    """

    # TODO: Move floating disk through REST not working development -
    # enable test once this feature works
    __test__ = False

    tcms_test_case = '286779'

    def perform_action(self):
        """
        Start moving disk, then restart vdsm and wait for action to fail
        """
        logger.info('Starting to move disk %s', self.disk_name)
        self.assertTrue(move_disk(self.disk_name, self.domains[0],
                                  self.domains[1], wait=False))
        self.assertTrue(waitForDisksState([self.disk_name],
                                          status=config.DISK_LOCKED),
                        'Disk %s never moved to locked status'
                        % self.disk_name)

        self.spm = getSPMHost(config.HOSTS)
        self.spm_ip = getHostIP(self.spm)
        logger.info('Restarting vdsm on host %s [%s]', self.spm, self.spm_ip)
        self.assertTrue(restartVdsmd(self.spm_ip, config.HOSTS_PW),
                        'Unable to restart vdsm on host %s' % self.spm)

        logger.info('Waiting for host to come back up')
        self.assertTrue(waitForSPM(config.DATA_CENTER_NAME, 60, 5),
                        'SPM was not elected on datacenter %s'
                        % config.DATA_CENTER_NAME)

        logger.info('Waiting for disk %s to be OK after rollback',
                    self.disk_name)
        self.assertTrue(waitForDisksState([self.disk_name]))

    def setUp(self):
        """
        Create preallocated disk
        """
        self.disk_types = (PREALLOCATED)
        self.disk_sizes = (5 * config.GB,)
        self.disk_domains = (self.domains[0],)
        self.disk_name = 'preallocated_disk'
        self.disk_names = [self.disk_name]
        self.create_disks()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_rollback_disk_move(self):
        """
        Start disk move and fail it, then check details after rollback
        """
        self.run_scenario()


# This test for a weird behaviour in which the second time the storage domain
# is extended the used value changes without reason
# Disabling while is being investigated
class TestCaseUsedSpace(BaseCase):
    """
    Checking behaviour used space
    """
    __test__ = False
    apis = BaseCase.apis - set(['sdk'])

    @bz({'1159637': {'engine': None, 'version': ['3.5']}})
    def test_used_space(self):
        """
        Test extending an iscsi domain doesn't remove used space
        """
        self.storage_domain = self.domains[0]
        for extend_lun in config.EXTEND_LUNS:
            logger.info('Extending storage domain %s', self.storage_domain)
            extend_storage_domain(self.domains[0],
                                  config.STORAGE_TYPE,
                                  config.HOSTS[0],
                                  **extend_lun)

            # Waits until total size changes (extend is done)
            # wait_for_tasks doesn't work (value is not updated properly)
            wait_for_change_total_size(
                self.storage_domain,
                self.current_total_size[self.storage_domain])

            # Assert size hasn't changed during the extend
            # TODO: The logic is pretty strange here, why isn't this captured
            # TODO: before the extend operation?
            previous = self.current_used_size[self.storage_domain]
            current = get_used_size(self.storage_domain)
            total = get_total_size(self.storage_domain)
            allocated = get_allocated_size(self.storage_domain)

            logger.info("Storage domain %s. Allocated: %s Total: %d Used: %d",
                        self.storage_domain, allocated, total, current)

            if previous != current:
                logger.error("Used size for %s is %d, before extend was %d",
                             self.storage_domain, current, previous)

            self.current_total_size[self.storage_domain] = total
            self.current_used_size[self.storage_domain] = current
            self.current_allocated_size[self.storage_domain] = allocated
