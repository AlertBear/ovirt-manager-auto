"""
Test Allocation/Total size properties
"""
from art.unittest_lib import StorageTest as TestCase
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.high_level.storagedomains import \
    extend_storage_domain
from art.rhevm_api.tests_lib.low_level.datacenters import \
    waitForDataCenterState
from art.rhevm_api.tests_lib.low_level.disks import addDisk, deleteDisk, \
    getStorageDomainDisks, waitForDisksState, move_disk
from art.rhevm_api.tests_lib.low_level.hosts import waitForHostsStates, \
    waitForSPM
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter, \
    get_allocated_size, get_total_size, findMasterStorageDomain, \
    findNonMasterStorageDomains
from art.rhevm_api.tests_lib.low_level.templates import createTemplate, \
    removeTemplate
from art.rhevm_api.tests_lib.low_level.vms import createVm, removeVm
from art.rhevm_api.utils.test_utils import restartVdsmd
from art.test_handler.tools import tcms, bz
import time
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
    disk_names = []

    current_allocated_size = {}
    current_total_size = {}

    expected_allocated_size = {}
    expected_total_size = {}

    def create_disks(self):
        """
        Creates disks of given types and sizes and updates expected details
        """
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

        rc, master_dom = findMasterStorageDomain(True, config.DATA_CENTER_NAME)
        assert rc

        rc, nonmaster_dom = findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME)
        assert rc

        cls.master_domain = master_dom['masterDomain']
        cls.nonmaster_domain = nonmaster_dom['nonMasterDomains'][0]

        logger.info('Found master domain: %s, nonmaster domain: %s',
                    cls.master_domain, cls.nonmaster_domain)

        cls.domains = [cls.master_domain, cls.nonmaster_domain]

        # by default create both disks on master domain
        cls.disk_domains = [cls.master_domain, cls.master_domain]

        # set up parameters used by test
        for domain in cls.domains:
            cls.current_allocated_size[domain] = get_allocated_size(domain)
            cls.current_total_size[domain] = get_total_size(domain)

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
    @bz('1025294')
    def test_create_disks_and_check_size(self):
        """
        Create preallocated and thin provision disk then check if storage
        domain details are updated accordingly
        """
        self.domains = [self.master_domain]
        self.run_scenario()

    def tearDown(self):
        """
        Remove the disks that were created
        """
        disk_names = ['%s_disk' % disk_type for disk_type in self.disk_types]
        for name in disk_names:
            logger.info('Removing disk %s', name)
            self.assertTrue(deleteDisk(True, name))


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
        self.domains = [self.master_domain]
        self.run_scenario()

    def perform_action(self):
        """
        Delete both disks
        """
        for disk in getStorageDomainDisks(self.master_domain, False):
            if disk.get_alias() in self.disk_names:
                logger.info('Removing disk %s', disk.get_alias())
                self.assertTrue(deleteDisk(True, disk.get_alias()))
                self.expected_allocated_size[self.master_domain] -= \
                    disk.get_size()


# TBD: Remove this when is implemented in the main story, storage sanity
# http://rhevm-qe-storage.pad.engineering.redhat.com/11?
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
        Move disks from master domain to second domain
        """
        for disk in getStorageDomainDisks(self.master_domain, False):
            logger.info('Moving disk %s from domain %s to domain %s',
                        disk.get_alias(), self.master_domain,
                        self.nonmaster_domain)
            self.assertTrue(move_disk(disk.get_alias(), self.master_domain,
                                      self.nonmaster_domain))
            self.expected_allocated_size[self.master_domain] -= disk.get_size()
            self.expected_allocated_size[self.nonmaster_domain] += \
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
        disk_names = ['%s_disk' % disk_type for disk_type in self.disk_types]
        for name in disk_names:
            logger.info('Removing disk %s', name)
            self.assertTrue(deleteDisk(True, name))


class TestCase286775(BaseCase):
    """
    TCMS Test Case 286775 - Extend domain and check storage details
    https://tcms.engineering.redhat.com/case/286775
    """

    # test case only relevant to iscsi domains
    __test__ = config.STORAGE_TYPE == 'iscsi'
    tcms_test_case = '286775'

    def perform_action(self):
        """
        Extend master domain
        """
        logger.info('Extending master domain')
        extend_storage_domain(self.master_domain,
                              config.ISCSI_DOMAIN,
                              config.HOSTS[0],
                              config.PARAMETERS)
        self.expected_total_size[self.master_domain] += \
            config.EXTEND_SIZE * config.GB

        # wait for storage details to update
        time.sleep(10)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_extend_domain_and_check_details(self):
        """
        Extend storage domain and check if total size is updated
        """
        self.run_scenario()


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
                'storageDomainName': self.master_domain,
                'size': VM_DISK_SIZE,
                'volumeType': is_thin_provision,
                'volumeFormat': disk_format
            }
            self.assertTrue(createVm(**vm_args),
                            'unable to create vm %s' % vm_name)
            self.expected_allocated_size[self.master_domain] += VM_DISK_SIZE

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
            self.expected_allocated_size[self.master_domain] += VM_DISK_SIZE

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    @bz('1025294')
    def test_create_templates(self):
        """
        Create templates and check storage domain details
        """
        self.run_scenario()


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
        self.assertTrue(move_disk(self.disk_name, self.master_domain,
                                  self.nonmaster_domain, wait=False))
        self.assertTrue(waitForDisksState([self.disk_name],
                                          status=config.DISK_LOCKED),
                        'Disk %s never moved to locked status'
                        % self.disk_name)

        logger.info('Restarting vdsm on host %s', config.HOSTS[0])
        self.assertTrue(restartVdsmd(config.HOSTS[0], config.VDS_PASSWORDS[0]),
                        'Unable to restart vdsm on host %s' % config.HOSTS[0])

        logger.info('Waiting for host to come back up')
        self.assertTrue(waitForSPM(config.DATA_CENTER_NAME, 60, 5),
                        'SPM was not elected on datacenter %s'
                        % config.STORAGE_TYPE)

        logger.info('Waiting for disk %s to be OK after rollback',
                    self.disk_name)
        self.assertTrue(waitForDisksState([self.disk_name]))

    def setUp(self):
        """
        Create preallocated disk
        """
        self.disk_types = (PREALLOCATED)
        self.disk_sizes = (5 * config.GB,)
        self.disk_domains = (self.master_domain,)
        self.disk_name = 'preallocated_disk'
        self.disk_names = [self.disk_name]
        self.create_disks()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_rollback_disk_move(self):
        """
        Start disk move and fail it, then check details after rollback
        """
        self.run_scenario()
