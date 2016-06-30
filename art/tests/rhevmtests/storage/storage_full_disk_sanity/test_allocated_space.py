"""
Test Allocation/Total size properties

https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/2_3_Storage_Data_Domains_General
"""
import logging

import config
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.rhevm_api.utils.test_utils import restartVdsmd
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion
from art.unittest_lib import attr, StorageTest as TestCase
from rhevmtests.storage import helpers as storage_helpers

logger = logging.getLogger(__name__)

VM_DISK_SIZE = 2 * config.GB

THIN_PROVISION = 'thin_provision'
PREALLOCATED = 'preallocated'
MIN_UNUSED_LUNS = 1
DISK_CREATION_TIMEOUT = 600
# The delta between the expected storage domain size and the actual size (
# given that engine returns the SD total size in GB as an integer)
SD_SIZE_DELTA = 1 * config.GB + 10 * config.MB
ISCSI = config.STORAGE_TYPE_ISCSI


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
        for disk_type, disk_size, domain in zip(
                self.disk_types, self.disk_sizes, self.disk_domains
        ):
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
            ll_disks.addDisk(**disk_args)
            self.expected_allocated_size[domain] += disk_size
            logger.info('Updating expected allocated size to: %s',
                        self.expected_allocated_size)
            self.disk_names.append(disk_name)
        logger.info('Waiting for disks to be OK')
        # Storage may take more than the default of 3 minutes to create a 7GB
        # Raw disk, increased the timeout to 5 minutes
        self.assertTrue(
            ll_disks.wait_for_disks_status(
                self.disk_names, timeout=DISK_CREATION_TIMEOUT
            )
        )

    @classmethod
    def setup_class(cls):
        """
        Ensure host + DC up
        """
        logger.info('Checking that host %s is up', config.HOSTS[0])
        assert ll_hosts.waitForHostsStates(True, config.HOSTS[0])

        logger.info('Waiting for DC %s to be up', config.DATA_CENTER_NAME)
        assert ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)

        cls.domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage
        )

        logger.info('Found data domains of type %s: %s', cls.storage,
                    cls.domains)

        # by default create both disks on the same domain
        cls.disk_domains = [cls.domains[0], cls.domains[0]]

        # set up parameters used by test
        for domain in cls.domains:
            cls.current_allocated_size[domain] = (
                ll_sd.get_allocated_size(domain)
            )
            cls.current_total_size[domain] = (
                ll_sd.get_total_size(domain)
            )
            cls.current_used_size[domain] = (
                ll_sd.get_used_size(domain)
            )

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
            allocated_size = ll_sd.get_allocated_size(domain)
            logger.info('Allocated size for domain %s is %s', domain,
                        allocated_size)
            self.assertEqual(allocated_size,
                             self.expected_allocated_size[domain],
                             'Allocated size is: %s, expected is %s'
                             % (allocated_size,
                                self.expected_allocated_size[domain]))
            total_size = ll_sd.get_total_size(domain)
            logger.info('total size for domain %s is %s', domain, total_size)

            size_difference = abs(
                total_size - self.expected_total_size[domain]
            )
            logger.info("The difference in SD size between the expected and "
                        "actual is: '%s'", str(size_difference))
            # A SD size delta is necessary for a comparison between the actual
            # and expected sizes, since the API returns the SD size in GB as
            # an integer
            self.assertTrue(
                size_difference <= SD_SIZE_DELTA,
                "Total size is: %s, expected is '%s'" % (
                    str(total_size), str(self.expected_total_size[domain]))
            )


@attr(tier=1)
class TestCase11536(BaseCase):
    """
    Polarion Test Case 11536 - Create new disk and check storage details
    """
    __test__ = True
    polarion_test_case = '11536'

    def perform_action(self):
        """
        Create a preallocated and a thin provision disk
        """
        self.create_disks()

    @polarion("RHEVM3-11536")
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
            self.assertTrue(ll_disks.deleteDisk(True, name))


@attr(tier=2)
class TestCase11537(BaseCase):
    """
    Polarion Test Case 11537 - Delete disk and check storage details
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_Data_Domains_General
    """
    __test__ = True
    polarion_test_case = '11537'

    def setUp(self):
        """
        Create preallocated and thin provision disks
        """
        self.create_disks()

    @polarion("RHEVM3-11537")
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
            disk = ll_disks.get_disk_obj(disk_name)
            logger.info('Removing disk %s', disk.get_alias())
            self.assertTrue(ll_disks.deleteDisk(True, disk.get_alias()))
            self.expected_allocated_size[self.domains[0]] -= disk.get_size()


@attr(tier=2)
class TestCase11547(BaseCase):
    """
    Polarion Test Case 11547 - Move disks and check storage details of both
    domains
    """
    # TODO: Move floating disk through REST not working development -
    # enable test once this feature works
    __test__ = False
    polarion_test_case = '11547'

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
            disk = ll_disks.get_disk_obj(disk_name)
            logger.info(
                'Moving disk %s from domain %s to domain %s',
                disk.get_alias(), self.domains[0], self.domains[1]
            )
            self.assertTrue(
                ll_disks.move_disk(
                    disk_name=disk.get_alias(), target_domain=self.domains[1]
                )
            )
            self.expected_allocated_size[self.domains[0]] -= disk.get_size()
            self.expected_allocated_size[self.domains[1]] += disk.get_size()

    @polarion("RHEVM3-11547")
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
            self.assertTrue(ll_disks.deleteDisk(True, name))


@attr(tier=2)
class TestCase11546(BaseCase):
    """
    Polarion Test Case 11546 - Extend domain and check storage details
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_Data_Domains_General
    """
    # test case only relevant to iscsi domains
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    # TODO: Why is this disabled for SDK?
    apis = BaseCase.apis - set(['sdk'])
    polarion_test_case = '11546'
    new_sd_name = "storage_domain_%s" % polarion_test_case

    @classmethod
    def setup_class(cls):
        """
        Add a new storage domain and extend it. Needed so that the original
        environment is not changed in case is run in a common environment,
        such as in the case of the golden environment or in a tiered approach
        """
        if not (len(config.UNUSED_LUNS) >= MIN_UNUSED_LUNS):
            raise exceptions.StorageDomainException(
                "A minimum of 1 free LUN is needed in order to create a new "
                "Storage domain"
            )
        cls.spm_host = ll_hosts.getSPMHost(config.HOSTS)
        cls.host_machine = storage_helpers.host_to_use()
        lun_size_orig, lun_free_space_orig = (
            cls.host_machine.get_lun_storage_info(config.EXTEND_LUN[0])
        )
        logger.info("LUN size to be used in SD creation is '%s' and its free "
                    "space is '%s'", str(lun_size_orig),
                    str(lun_free_space_orig))
        if not hl_sd.addISCSIDataDomain(
            cls.spm_host, cls.new_sd_name, config.DATA_CENTER_NAME,
            config.EXTEND_LUN[0], config.EXTEND_LUN_ADDRESS[0],
            config.EXTEND_LUN_TARGET[0], override_luns=True
        ):
            raise exceptions.StorageDomainException(
                "Adding iSCSI storage domain has failed"
            )
        assert ll_sd.wait_for_storage_domain_available_size(
            config.DATA_CENTER_NAME, cls.new_sd_name,
        )
        lun_size_sd, lun_free_space_sd = cls.host_machine.get_lun_storage_info(
            config.EXTEND_LUN[0])
        logger.info("LUN size after SD creation is '%s' and its free space is "
                    "'%s'", str(lun_size_sd), str(lun_free_space_sd))
        # When creating or extending a storage domain, each LUN loses about
        # 380 MB of its physical usable space.  In addition, when first
        # creating a storage domain, 4 GB of free space is taken out for
        # metadata, headers and other internal usage
        super(TestCase11546, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """Remove the added storage domain"""
        hl_sd.remove_storage_domain(
            cls.new_sd_name, config.DATA_CENTER_NAME, cls.spm_host, True
        )

    def perform_action(self):
        """
        Extend added domain
        """
        self.assertTrue(len(config.EXTEND_LUNS) >= MIN_UNUSED_LUNS,
                        "There are less than %s unused Extend LUNs, aborting "
                        "test" % MIN_UNUSED_LUNS)
        current_sd_size = ll_sd.get_total_size(self.new_sd_name)
        logger.info("The current SD size is: '%s'", current_sd_size)

        extend_lun = config.EXTEND_LUNS.pop()
        lun_size_unused, lun_free_space_unused = (
            self.host_machine.get_lun_storage_info(extend_lun["lun_list"][0])
        )
        logger.info("LUN size is '%s' and its free space is '%s'",
                    str(lun_size_unused), str(lun_free_space_unused))

        logger.info("Extending domain '%s'", self.new_sd_name)
        hl_sd.extend_storage_domain(
            self.new_sd_name, config.STORAGE_TYPE_ISCSI, self.spm_host,
            **extend_lun
        )

        # Waits until total size changes (extend is done)
        # wait_for_tasks doesn't work (value is not updated correctly)
        ll_sd.wait_for_change_total_size(
            self.new_sd_name, self.current_total_size[self.new_sd_name]
        )

        extended_sd_size = ll_sd.get_total_size(self.new_sd_name)
        logger.info("The updated SD size after the extend has completed is: "
                    "'%s'", extended_sd_size)

        lun_size_sd, lun_free_space_sd = (
            self.host_machine.get_lun_storage_info(extend_lun["lun_list"][0])
        )
        logger.info("LUN size is '%s' and its free space is '%s'",
                    str(lun_size_sd), str(lun_free_space_sd))

        self.expected_total_size[self.new_sd_name] += lun_size_sd
        logger.info("The new expected domain size with the Raw LUN size is "
                    "'%s'", str(self.expected_total_size[self.new_sd_name]))

        # Assert size hasn't changed during the extend
        self.assertEqual(
            self.current_used_size[self.new_sd_name],
            ll_sd.get_used_size(self.new_sd_name)
        )

    @polarion("RHEVM3-11546")
    def test_extend_domain_and_check_details(self):
        """
        Extend storage domain and check if total size is updated
        """
        self.run_scenario()


@attr(tier=2)
class TestCase11541(BaseCase):
    """
    Polarion Test Case 11541 - Create template and check storage details
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_Data_Domains_General
    """
    __test__ = True
    polarion_test_case = '11541'
    vms = (THIN_PROVISION, PREALLOCATED)

    def setUp(self):
        """
        Create 2 vms, one with preallocated and one with thin provision disks
        """
        for vm_name in self.vms:
            logger.info('Creating vm with %s disks', vm_name)
            is_thin_provision = vm_name == THIN_PROVISION
            disk_format = config.COW_DISK if is_thin_provision else (
                config.RAW_DISK
            )
            vm_args = {
                'positive': True,
                'vmName': vm_name,
                'vmDescription': vm_name,
                'cluster': config.CLUSTER_NAME,
                'storageDomainName': self.domains[0],
                'provisioned_size': VM_DISK_SIZE,
                'volumeType': is_thin_provision,
                'volumeFormat': disk_format,
                'display_type': config.DISPLAY_TYPE,
                'os_type': config.OS_TYPE,
                'type': config.VM_TYPE,
            }
            self.assertTrue(ll_vms.createVm(**vm_args),
                            'unable to create vm %s' % vm_name)
            self.expected_allocated_size[self.domains[0]] += VM_DISK_SIZE

        self.template_names = ['%s_template' % name for name in self.vms]

    def tearDown(self):
        """
        Remove vms and templates
        """
        for vm_name in self.vms:
            logger.info('Removing vm %s', vm_name)
            self.assertTrue(
                ll_vms.removeVm(True, vm_name),
                'Unable to remove vm %s' % vm_name
            )

        for template in self.template_names:
            logger.info('Removing template %s', template)
            self.assertTrue(ll_templates.removeTemplate(True, template))

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
                'storagedomains': self.domains[0]
            }
            self.assertTrue(
                ll_templates.createTemplate(**template_args),
                "Unable to create template %s" % template_name
            )

            # For block devices, the allocated size is increased to the real
            # size in ranges of 1 GB with a minimum of 1 GB for thin
            # provisioned type. For preallocated type, the allocated size is
            # the whole preallocated size of the disk
            # For file devices, the allocated size for both disk types is
            # the same as the real size of the disk. In this case the template
            # is created from an empty vm so there's no increase in the
            # allocated size
            if self.storage in config.BLOCK_TYPES:
                if vm_name == THIN_PROVISION:
                    # Thin provisioned templates only take up 1GB per disk,
                    # just as with snapshots
                    self.expected_allocated_size[self.domains[0]] += (
                        1 * config.GB
                    )
                else:
                    self.expected_allocated_size[self.domains[0]] += (
                        VM_DISK_SIZE
                    )

    @polarion("RHEVM3-11541")
    def test_create_templates(self):
        """
        Create templates and check storage domain details
        """
        self.run_scenario()


@attr(tier=4)
class TestCase11545(BaseCase):
    """
    Polarion Test Case 11545 - Check  storage domain details after rollback
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_Data_Domains_General
    """
    # TODO: Move floating disk through REST not working development -
    # enable test once this feature works
    __test__ = False
    polarion_test_case = '11545'

    def perform_action(self):
        """
        Start moving disk, then restart vdsm and wait for action to fail
        """
        logger.info('Starting to move disk %s', self.disk_name)
        self.assertTrue(
            ll_disks.move_disk(
                self.disk_name, self.domains[0], self.domains[1], wait=False
            )
        )
        self.assertTrue(
            ll_disks.wait_for_disks_status(
                [self.disk_name], status=config.DISK_LOCKED
            ), 'Disk {0} never moved to locked status'.format(self.disk_name)
        )

        self.spm = ll_hosts.getSPMHost(config.HOSTS)
        self.spm_ip = ll_hosts.getHostIP(self.spm)
        logger.info('Restarting vdsm on host %s [%s]', self.spm, self.spm_ip)
        self.assertTrue(restartVdsmd(self.spm_ip, config.HOSTS_PW),
                        'Unable to restart vdsm on host %s' % self.spm)

        logger.info('Waiting for host to come back up')
        self.assertTrue(
            ll_hosts.waitForSPM(config.DATA_CENTER_NAME, 60, 5),
            'SPM was not elected on datacenter %s' % config.DATA_CENTER_NAME
        )

        logger.info('Waiting for disk %s to be OK after rollback',
                    self.disk_name)
        self.assertTrue(ll_disks.wait_for_disks_status([self.disk_name]))

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

    @polarion("RHEVM3-11545")
    def test_rollback_disk_move(self):
        """
        Start disk move and fail it, then check details after rollback
        """
        self.run_scenario()
