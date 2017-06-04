"""
Test Allocation/Total size properties

https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/2_3_Storage_Data_Domains_General
"""
import pytest
import logging
import config
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    templates as ll_templates,
)
from art.rhevm_api.utils.test_utils import restartVdsmd
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
    tier4,
)
from art.unittest_lib import StorageTest as TestCase, testflow
from rhevmtests.storage.fixtures import (
    delete_disks, create_storage_domain, remove_vms, remove_templates
)
from rhevmtests.storage import helpers as storage_helpers
from rhevmtests.storage.storage_full_disk_sanity.fixtures import (
    check_initial_storage_domain_params, create_disks_fixture, lun_size_calc,
    create_2_vms_pre_disk_thin_disk,
)
from art.test_handler.tools import bz

logger = logging.getLogger(__name__)

VM_DISK_SIZE = 2 * config.GB


MIN_UNUSED_LUNS = 1
DISK_CREATION_TIMEOUT = 600
# The delta between the expected storage domain size and the actual size (
# given that engine returns the SD total size in GB as an integer)
SD_SIZE_DELTA = 1 * config.GB + 10 * config.MB
ISCSI = config.STORAGE_TYPE_ISCSI


@pytest.mark.usefixtures(check_initial_storage_domain_params.__name__)
class BaseCase(TestCase):
    """
    Base class. Ensures environment is running and checks, creates disks
    and checks for the disk's value
    """
    __test__ = False

    domains = []
    vm_names = []
    templates_names = []
    disk_types = [config.THIN_PROVISION, config.PREALLOCATED]
    disk_sizes = [160 * config.GB, 7 * config.GB]

    current_allocated_size = {}
    current_total_size = {}
    current_used_size = {}

    expected_allocated_size = {}
    expected_total_size = {}

    @classmethod
    def create_disks(cls):
        """
        Creates disks of given types and sizes and updates expected details
        """
        cls.disk_names = []
        for disk_type, disk_size, domain in zip(
                cls.disk_types, cls.disk_sizes, cls.disk_domains
        ):
            disk_name = '%s_disk' % disk_type
            testflow.setup(
                'Creating a %s GB %s disk on domain %s',
                disk_size, disk_type, domain
            )
            disk_args = {
                'positive': True,
                'provisioned_size': disk_size,
                'storagedomain': domain,
                'bootable': False,
                'interface': config.VIRTIO_BLK,
                'alias': disk_name,
                'sparse': disk_type == config.THIN_PROVISION,
                'format': config.RAW_DISK if disk_type == config.PREALLOCATED
                else config.COW_DISK
            }
            ll_disks.addDisk(**disk_args)
            cls.expected_allocated_size[domain] += disk_size
            logger.info('Updating expected allocated size to: %s',
                        cls.expected_allocated_size)
            cls.disk_names.append(disk_name)
        logger.info('Waiting for disks to be OK')
        # Storage may take more than the default of 3 minutes to create a 7GB
        # Raw disk, increased the timeout to 5 minutes
        assert ll_disks.wait_for_disks_status(
            cls.disk_names, timeout=DISK_CREATION_TIMEOUT
        )
        cls.disks_to_remove = cls.disk_names

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
        testflow.step(
            "Checking storage domain info: actual size, allocated size and "
            "total size"
        )
        for domain in self.domains:
            logger.info('Checking info for domain %s', domain)
            allocated_size = ll_sd.get_allocated_size(domain)
            logger.info(
                'Allocated size for domain %s is %s', domain, allocated_size
            )
            assert allocated_size == self.expected_allocated_size[domain], (
                'Allocated size is: %s, expected is %s' %
                (allocated_size, self.expected_allocated_size[domain])
            )
            total_size = ll_sd.get_total_size(domain, config.DATA_CENTER_NAME)
            logger.info('total size for domain %s is %s', domain, total_size)

            size_difference = abs(
                total_size - self.expected_total_size[domain]
            )
            logger.info(
                "The difference in SD size between the expected and actual"
                " is: '%s'", str(size_difference)
            )
            # A SD size delta is necessary for a comparison between the actual
            # and expected sizes, since the API returns the SD size in GB as
            # an integer
            assert size_difference <= SD_SIZE_DELTA, (
                "Total size is: %s, expected is '%s'" %
                (str(total_size), str(self.expected_total_size[domain]))
            )


@pytest.mark.usefixtures(delete_disks.__name__)
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
        testflow.step("Create a preallocated and a thin provision disk")
        self.create_disks()

    @polarion("RHEVM3-11536")
    @tier1
    def test_create_disks_and_check_size(self):
        """
        Create preallocated and thin provision disk then check if storage
        domain details are updated accordingly
        """
        self.domains = [self.domains[0]]
        self.run_scenario()


@pytest.mark.usefixtures(create_disks_fixture.__name__)
class TestCase11537(BaseCase):
    """
    Polarion Test Case 11537 - Delete disk and check storage details
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_Data_Domains_General
    """
    __test__ = True
    polarion_test_case = '11537'

    @polarion("RHEVM3-11537")
    @tier2
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
            testflow.step('Removing disk %s', disk.get_alias())
            assert ll_disks.deleteDisk(True, disk.get_alias())
            provisioned_size = disk.get_provisioned_size()
            self.expected_allocated_size[self.domains[0]] -= provisioned_size


@pytest.mark.usefixtures(
    create_disks_fixture.__name__,
    delete_disks.__name__
)
class TestCase11547(BaseCase):
    """
    Polarion Test Case 11547 - Move disks and check storage details of both
    domains
    """

    __test__ = True
    polarion_test_case = '11547'

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
            assert ll_disks.move_disk(
                disk_name=disk.get_alias(), target_domain=self.domains[1],
                timeout=config.DEFAULT_DISK_TIMEOUT
            )
            provisioned_size = disk.get_provisioned_size()
            self.expected_allocated_size[self.domains[0]] -= provisioned_size
            self.expected_allocated_size[self.domains[1]] += provisioned_size

    @polarion("RHEVM3-11547")
    @tier2
    def test_move_disks(self):
        """
        Move disks and check domain details
        """
        self.run_scenario()


@pytest.mark.usefixtures(
    lun_size_calc.__name__,
    create_storage_domain.__name__,
)
class TestCase11546(BaseCase):
    """
    Polarion Test Case 11546 - Extend domain with lun and check storage details
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_Data_Domains_General
    """
    # test case only relevant to iscsi domains
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([ISCSI])

    # When creating or extending a storage domain, each LUN loses about
    # 380 MB of its physical usable space.  In addition, when first
    # creating a storage domain, 4 GB of free space is taken out for
    # metadata, headers and other internal usage

    polarion_test_case = '11546'

    def perform_action(self):
        """
        Extend added domain
        """
        self.domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        for domain in self.domains:
            self.current_allocated_size[domain] = (
                ll_sd.get_allocated_size(domain)
            )
            self.current_total_size[domain] = (
                ll_sd.get_total_size(domain, config.DATA_CENTER_NAME)
            )
            self.current_used_size[domain] = (
                ll_sd.get_used_size(domain)
            )
            logger.debug(
                "Allocated size for %s is %d Total size is %d",
                domain, self.current_allocated_size[domain],
                self.current_total_size[domain]
            )
            self.expected_total_size[domain] = self.current_total_size[domain]
            self.expected_allocated_size[domain] = self.current_allocated_size[
                domain
            ]

        self.spm_host = ll_hosts.get_spm_host(config.HOSTS)
        assert len(config.EXTEND_LUNS) >= MIN_UNUSED_LUNS, (
            "There are less than %s unused Extend LUNs, aborting test" %
            MIN_UNUSED_LUNS
        )
        current_sd_size = ll_sd.get_total_size(
            self.new_storage_domain, config.DATA_CENTER_NAME
        )
        logger.info("The current SD size is: '%s'", current_sd_size)

        extend_lun = config.EXTEND_LUNS.pop()
        lun_size_unused, lun_free_space_unused = (
            storage_helpers.get_lun_storage_info(extend_lun["lun_list"][0])
        )
        logger.info("LUN size is '%s' and its free space is '%s'",
                    str(lun_size_unused), str(lun_free_space_unused))

        logger.info("Extending domain '%s'", self.new_storage_domain)
        hl_sd.extend_storage_domain(
            self.new_storage_domain, config.STORAGE_TYPE_ISCSI, self.spm_host,
            **extend_lun
        )

        # Waits until total size changes (extend is done)
        # wait_for_tasks_deprecated doesn't work
        # (value is not updated correctly)
        ll_sd.wait_for_change_total_size(
            self.new_storage_domain, config.DATA_CENTER_NAME,
            self.current_total_size[self.new_storage_domain]
        )

        extended_sd_size = ll_sd.get_total_size(
            self.new_storage_domain, config.DATA_CENTER_NAME
        )
        logger.info("The updated SD size after the extend has completed is: "
                    "'%s'", extended_sd_size)

        lun_size_sd, lun_free_space_sd = (
            storage_helpers.get_lun_storage_info(extend_lun["lun_list"][0])
        )
        logger.info("LUN size is '%s' and its free space is '%s'",
                    str(lun_size_sd), str(lun_free_space_sd))

        self.expected_total_size[self.new_storage_domain] += lun_size_sd
        logger.info(
            "The new expected domain size with the Raw LUN size is '%s'",
            str(self.expected_total_size[self.new_storage_domain])
        )

        # Assert size hasn't changed during the extend
        assert self.current_used_size[self.new_storage_domain] == (
            ll_sd.get_used_size(self.new_storage_domain)
        )

    @polarion("RHEVM3-11546")
    @tier2
    def test_extend_domain_and_check_details(self):
        """
        Extend storage domain and check if total size is updated
        """
        self.run_scenario()


@pytest.mark.usefixtures(
    create_2_vms_pre_disk_thin_disk.__name__,
    remove_templates.__name__,
    remove_vms.__name__,
)
class TestCase11541(BaseCase):
    """
    Polarion Test Case 11541 - Create template and check storage details
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_Data_Domains_General
    """
    __test__ = True
    polarion_test_case = '11541'

    def perform_action(self):
        """
        Create templates from VM's (one with preallocated disk, one with thin
        provision disk)
        """

        for vm_name, template_name in zip(self.vm_names, self.templates_names):
            logger.info('Creating template %s from vm %s', vm_name,
                        template_name)
            template_args = {
                'positive': True,
                'name': template_name,
                'vm': vm_name,
                'storagedomains': self.domains[0]
            }
            assert ll_templates.createTemplate(**template_args), (
                "Unable to create template %s" % template_name
            )

            # For block devices, the allocated size is increased to the real
            # size in ranges of 1 GB with a minimum of 1 GB for thin
            # provisioned type. For preallocated type, the allocated size is
            # the whole preallocated size of the disk
            # For file devices, the allocated size for both disk types is
            # the same as the real size of the disk. In this case the template
            # is created from an empty VM so there's no increase in the
            # allocated size
            if self.storage in config.BLOCK_TYPES:
                if vm_name == self.vm_names[0]:
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
    @tier3
    def test_create_templates(self):
        """
        Create templates and check storage domain details
        """
        self.run_scenario()


@bz({'1417456': {}})
@pytest.mark.usefixtures(
    create_disks_fixture.__name__,
    delete_disks.__name__
)
class TestCase11545(BaseCase):
    """
    Polarion Test Case 11545 - Check  storage domain details after rollback
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_Data_Domains_General
    """
    __test__ = True
    polarion_test_case = '11545'

    disk_types = [config.PREALLOCATED, ]
    disk_sizes = [10 * config.GB, ]

    def perform_action(self):
        """
        Start moving disk, then restart VDSM and wait for action to fail
        """
        self.disk_name = self.disk_names[0]
        logger.info('Starting to move disk %s', self.disk_name)
        assert ll_disks.move_disk(
            disk_name=self.disk_name, target_domain=self.domains[1],
            wait=False, timeout=config.DEFAULT_DISK_TIMEOUT
        )
        assert ll_disks.wait_for_disks_status(
            [self.disk_name], status=config.DISK_LOCKED
        ), 'Disk {0} never moved to locked status'.format(self.disk_name)

        self.spm = ll_hosts.get_spm_host(config.HOSTS)
        self.spm_ip = ll_hosts.get_host_ip(self.spm)
        logger.info('Restarting vdsm on host %s [%s]', self.spm, self.spm_ip)
        assert restartVdsmd(self.spm_ip, config.HOSTS_PW), (
            'Unable to restart vdsm on host %s' % self.spm
        )

        logger.info('Waiting for host to come back up')
        assert ll_hosts.wait_for_spm(config.DATA_CENTER_NAME, 60, 5), (
            'SPM was not elected on datacenter %s' % config.DATA_CENTER_NAME
        )

        logger.info('Waiting for disk %s to be OK after rollback',
                    self.disk_name)
        assert ll_disks.wait_for_disks_status([self.disk_name])

    @polarion("RHEVM3-11545")
    @tier4
    def test_rollback_disk_move(self):
        """
        Start disk move and fail it, then check details after rollback
        """
        self.run_scenario()
