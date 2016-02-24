"""
Regression Vms Test - Basic tests to check vms functionality
"""
from rhevmtests.virt import config
import logging
import unittest2
import art.unittest_lib.common as common
from art.unittest_lib import VirtTest as TestCase
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.storagedomains as sd_api
import art.rhevm_api.tests_lib.low_level.templates as template_api
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.utils.test_utils import update_vm_status_in_database
from art.unittest_lib import attr

TWO_GB = 2 * config.GB
NIC_NAME = 'nic'
ENUMS = config.ENUMS
ANY_HOST = ENUMS['placement_host_any_host_in_cluster']
SPICE = ENUMS['display_type_spice']
VNC = ENUMS['display_type_vnc']
WIN_TZ = ENUMS['timezone_win_gmt_standard_time']
RHEL_TZ = ENUMS['timezone_rhel_etc_gmt']
# Timeout for VM creation in Vmpool
VMPOOL_TIMEOUT = 30
RHEL6_64 = ENUMS['rhel6x64']
WIN_XP = ENUMS['windowsxp']
WIN_7 = ENUMS['windows7']
logger = logging.getLogger(__name__)


class BaseVm(TestCase):
    """
    Base vm class to create and remove vm
    """
    __test__ = False
    vm_name = None
    template_name = None
    master_domain = None
    non_master_domain = None

    @classmethod
    def setup_class(cls):
        """
        Add new vm with given name
        """
        cls.master_domain = (
            sd_api.get_master_storage_domain_name(config.DC_NAME[0])
        )
        non_master_domains = (
            sd_api.findNonMasterStorageDomains(
                True, config.DC_NAME[0]
            )[1]
        )
        cls.non_master_domain = non_master_domains['nonMasterDomains'][0]
        logger.info("Add new vm %s", cls.vm_name)
        if not vm_api.addVm(
            True, name=cls.vm_name,
            cluster=config.CLUSTER_NAME[0],
            memory=1536 * config.MB,
            os_type=config.VM_OS_TYPE,
            type=config.VM_TYPE,
            display_type=config.VM_DISPLAY_TYPE

        ):
            raise errors.VMException("Failed to create vm %s" % cls.vm_name)

    @classmethod
    def teardown_class(cls):
        """
        Remove all vms from cluster
        """
        logger.info("Remove all vms")
        if not vm_api.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0],
            config.VM_NAME
        ):
            logger.error("Failed to remove all vms")


class BaseVmWithDisk(BaseVm):
    """
    Base vm class to create and remove vm with disk
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Create new vm with disk
        """
        super(BaseVmWithDisk, cls).setup_class()
        logger.info("Add disk to vm %s", cls.vm_name)
        if not vm_api.addDisk(
            True,
            vm=cls.vm_name,
            size=config.GB,
            storagedomain=cls.master_domain,
            type=type,
            format=config.DISK_FORMAT_COW,
            interface=config.INTERFACE_VIRTIO
        ):
            raise errors.VMException(
                "Failed to add disk to vm %s" % cls.vm_name
            )


class BaseVmWithDiskTemplate(BaseVmWithDisk):
    """
    Base vm class to create vm with disk and template from it and remove it
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Create new vm and after it create new template from it
        """
        super(BaseVmWithDiskTemplate, cls).setup_class()
        logger.info("Create new template from vm %s", cls.vm_name)
        if not template_api.createTemplate(
                True, vm=cls.vm_name, name=cls.template_name
        ):
            raise errors.VMException("Failed to create template")

    @classmethod
    def teardown_class(cls):
        """
        Remove created vm and remove template
        """
        super(BaseVmWithDiskTemplate, cls).teardown_class()
        logger.info("Remove template %s", cls.template_name)
        if not template_api.removeTemplate(True, cls.template_name):
            logger.error("Failed to remove template %s", cls.template_name)


@attr(tier=1)
class AddVm(TestCase):
    """
    Add vms with different parameters test cases
    """
    __test__ = True

    @classmethod
    def teardown_class(cls):
        """
        Remove all created vms
        """
        logger.info("Remove all vms")
        if not vm_api.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0],
            config.VM_NAME
        ):
            logger.error("Failed to remove all vms")

    @polarion("RHEVM3-12382")
    def test_add_vm_with_custom_boot_sequence(self):
        """
        Add vm with custom boot sequence
        """
        vm_name = 'boot_vm'
        if not vm_api.addVm(
            True,
            name=vm_name,
            cluster=config.CLUSTER_NAME[0],
            boot=['network', 'hd'],
            os_type=config.VM_OS_TYPE,
            type=config.VM_TYPE,
            display_type=config.VM_DISPLAY_TYPE
        ):
            raise errors.VMException("Failed to add vm")
        logger.info(
            "Check if network first and hard disk second "
            "in boot sequence on vm %s", vm_name
        )
        boot_list = vm_api.get_vm_boot_sequence(vm_name)
        self.assertTrue(
            boot_list[0] == ENUMS['boot_sequence_network'] and
            boot_list[1] == ENUMS['boot_sequence_hd']
        )

    @polarion("RHEVM3-10087")
    def test_add_default_vm_without_special_parameters(self):
        """
        Positive: Add default vm without special parameters
        """
        vm_name = 'default_vm'
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                os_type=config.VM_OS_TYPE,
                type=config.VM_TYPE,
                display_type=config.VM_DISPLAY_TYPE
            )
        )

    @polarion("RHEVM3-12361")
    def test_add_ha_server_vm(self):
        """
        Positive: Add HA server vm
        """
        vm_name = 'ha_server_vm'
        self.assertTrue(
            vm_api.addVm(
                True, name=vm_name,
                highly_available='true',
                type=ENUMS['vm_type_server'],
                cluster=config.CLUSTER_NAME[0],
                os_type=config.VM_OS_TYPE,
                display_type=config.VM_DISPLAY_TYPE
            )
        )

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12362")
    def test_add_stateless_vm(self):
        """
        Positive: Add stateless vm
        """
        vm_name = 'stateless_vm'
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                stateless='true',
                cluster=config.CLUSTER_NAME[0]
            )
        )

    @polarion("RHEVM3-12363")
    def test_add_vm_with_custom_property(self):
        """
        Positive: Add vm with custom property
        """
        vm_name = 'custom_property_vm'
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                custom_properties='sndbuf=111',
                os_type=config.VM_OS_TYPE,
                type=config.VM_TYPE,
                display_type=config.VM_DISPLAY_TYPE
            )
        )

    @polarion("RHEVM3-12385")
    def test_add_vm_with_guranteed_memory(self):
        """
        Positive: Add vm with guaranteed memory
        """
        vm_name = 'guaranteed_memory_vm'
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                memory=TWO_GB,
                memory_guaranteed=TWO_GB,
                os_type=config.VM_OS_TYPE,
                type=config.VM_TYPE,
                display_type=config.VM_DISPLAY_TYPE
            )
        )

    @polarion("RHEVM3-12383")
    def test_add_vm_with_disk(self):
        """
        Positive: Add vm with disk
        """
        vm_name = 'disk_vm'
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                disk_type=config.DISK_TYPE_DATA,
                size=TWO_GB,
                format=config.DISK_FORMAT_COW,
                interface=config.INTERFACE_VIRTIO,
                os_type=config.VM_OS_TYPE,
                type=config.VM_TYPE,
                display_type=config.VM_DISPLAY_TYPE
            )
        )

    @polarion("RHEVM3-12517")
    def test_add_vm_with_linux_boot_options(self):
        """
        Positive: Add vm with linux_boot_options
        """
        vm_name = 'linux_boot_options_vm'
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                kernel='/kernel-path',
                initrd='/initrd-path',
                cmdline='rd_NO_LUKS rd_NO_MD',
                os_type=config.VM_OS_TYPE,
                type=config.VM_TYPE,
                display_type=config.VM_DISPLAY_TYPE
            )
        )

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12518")
    def test_add_vm_with_rhel_os_type(self):
        """
        Positive: Add vm with Rhel OS type
        """
        vm_name = 'rhel_vm'
        logger.info("Positive: Add vm with Rhel OS type")
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                os_type=RHEL6_64
            )
        )

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12520")
    def test_add_vm_with_windows_xp_os_type(self):
        """
        Positive: Add vm with Windows XP OS type
        """
        vm_name = 'xp_vm'
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                os_type=WIN_XP
            )
        )

    @polarion("RHEVM3-12384")
    def test_add_vm_with_disk_on_specific_storage_domain(self):
        """
        Positive: Add vm with disk on specific storage domain
        """
        vm_name = 'disk_specific_vm'
        master_domain = (
            sd_api.get_master_storage_domain_name(config.DC_NAME[0])
        )
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                storagedomain=master_domain,
                disk_type=config.DISK_TYPE_DATA,
                size=TWO_GB,
                format=config.DISK_FORMAT_COW,
                interface=config.INTERFACE_VIRTIO,
                os_type=config.VM_OS_TYPE,
                type=config.VM_TYPE,
                display_type=config.VM_DISPLAY_TYPE
            )
        )

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12519")
    def test_add_vm_with_specific_domain(self):
        """
        Positive: Add vm with specific domain
        """
        vm_name = 'domain_vm'
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                os_type=WIN_XP,
                domainName=config.VDC_ADMIN_DOMAIN,
                cluster=config.CLUSTER_NAME[0],
            )
        )

    @polarion("RHEVM3-12386")
    def test_add_vm_with_name_that_already_exist(self):
        """
        Negative: Add vm with name that already in use
        """
        vm_name = 'vm_name_negative'
        logger.info("Add vm %s", vm_name)
        if not vm_api.addVm(
            True,
            name=vm_name,
            cluster=config.CLUSTER_NAME[0],
            os_type=config.VM_OS_TYPE,
            type=config.VM_TYPE,
            display_type=config.VM_DISPLAY_TYPE
        ):
            raise errors.VMException("Failed to add vm")
        logger.info("Create vm with name that already exist")
        self.assertFalse(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                os_type=config.VM_OS_TYPE,
                type=config.VM_TYPE,
                display_type=config.VM_DISPLAY_TYPE
            )
        )

    @polarion("RHEVM3-12521")
    def test_add_vm_with_wrong_number_of_displays(self):
        """
        Negative: Add vm with wrong number of displays
        """
        vm_name = 'display_vm_negative'
        self.assertFalse(
            vm_api.addVm(
                True,
                name=vm_name,
                display_monitors=36,
                cluster=config.CLUSTER_NAME[0],
                os_type=config.VM_OS_TYPE,
                type=config.VM_TYPE,
                display_type=config.VM_DISPLAY_TYPE
            )
        )


@attr(tier=1)
class UpdateVm(BaseVm):
    """
    Upgrade vms with different parameters test cases
    """
    __test__ = True
    vm_name = 'update_vm'
    rhel_to_xp_vm = 'rhel_to_xp_vm'
    rhel_to_7_vm = 'rhel_to_7_vm'
    rhel_to_7_vm_neg = 'rhel_to_7_vm_neg'
    xp_to_rhel_vm = 'xp_to_rhel_vm'
    new_mem = 1280 * config.MB
    half_GB = 512 * config.MB

    @classmethod
    def setup_class(cls):
        """
        Add vms for test
        """
        if not config.PPC_ARCH:
            logger.info(
                "Add new vm %s with rhel os parameter",
                cls.rhel_to_xp_vm
            )
            if not vm_api.addVm(
                    True,
                    name=cls.rhel_to_xp_vm,
                    cluster=config.CLUSTER_NAME[0]
            ):
                raise errors.VMException("Failed to add vm")
            logger.info(
                "Add new vm %s with rhel os parameter",
                cls.rhel_to_7_vm
            )
            if not vm_api.addVm(
                    True,
                    name=cls.rhel_to_7_vm,
                    cluster=config.CLUSTER_NAME[0]
            ):
                raise errors.VMException("Failed to add vm")
            logger.info(
                "Add new vm %s with rhel os parameter",
                cls.xp_to_rhel_vm
            )
            if not vm_api.addVm(
                    True,
                    name=cls.xp_to_rhel_vm,
                    cluster=config.CLUSTER_NAME[0],
                    os_type=WIN_XP
            ):
                raise errors.VMException("Failed to add vm")
            logger.info("Add new vm %s with rhel os parameter, for neg tests",
                        cls.rhel_to_7_vm_neg)
            if not vm_api.addVm(
                    True,
                    name=cls.rhel_to_7_vm_neg,
                    cluster=config.CLUSTER_NAME[0],
                    os_type=RHEL6_64
            ):
                raise errors.VMException("Failed to add vm")
        super(UpdateVm, cls).setup_class()

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12563")
    def test_update_vm_os_type_from_rhel_to_windows_xp(self):
        """
        Negative: Update vm OS type from rhel to Windows XP
        """
        self.assertFalse(
            vm_api.updateVm(
                True,
                self.rhel_to_xp_vm,
                timezone=WIN_TZ,
                os_type=WIN_XP
            )
        )

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12561")
    def test_update_vm_os_type_from_rhel_to_windows_7(self):
        """
        Positive: Update vm OS type from rhel to Windows 7
        """
        self.assertTrue(
            vm_api.updateVm(
                True,
                self.rhel_to_7_vm,
                timezone=WIN_TZ,
                os_type=WIN_7
            )
        )

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12564")
    def test_update_vm_os_type_from_xp_to_rhel(self):
        """
        Positive: Update vm OS type from Windows XP to RHEL
        """
        self.assertTrue(
            vm_api.updateVm(
                True,
                self.xp_to_rhel_vm,
                timezone=RHEL_TZ,
                os_type=RHEL6_64
            )
        )

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12562")
    def test_update_vm_os_type_from_rhel_to_windows_7_neg(self):
        """
        Negative: Update vm OS type from rhel to Windows 7, no timezone update
        """
        self.assertFalse(
            vm_api.updateVm(
                True,
                self.rhel_to_7_vm_neg,
                os_type=WIN_7
            )
        )

    @polarion("RHEVM3-12560")
    def test_update_vm_linux_boot_options(self):
        """
        Positive: Update vm OS parameters
        """
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                kernel='/kernel-new-path',
                initrd='/initrd-new-path',
                cmdline='rd_NO_LUKS'
            )
        )

    @polarion("RHEVM3-10098")
    def test_update_vm_name(self):
        """
        Positive: Update vm name
        """
        vm_update = 'some_name'
        self.assertTrue(vm_api.updateVm(True, self.vm_name, name=vm_update))
        self.assertTrue(vm_api.updateVm(True, vm_update, name=self.vm_name))

    @attr(tier=2)
    @polarion("RHEVM3-12528")
    @bz({'1260732': {'engine': None, 'version': ['3.6']}})
    def test_update_vm_affinity_to_migratable_with_host(self):
        """
        Positive: Update vm affinity to migratable with host
        """
        affinity = ENUMS['vm_affinity_migratable']
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                placement_affinity=affinity,
                placement_host=config.HOSTS[0]
            )
        )

    @attr(tier=2)
    @polarion("RHEVM3-12531")
    @bz({'1260732': {'engine': None, 'version': ['3.6']}})
    def test_update_vm_affinity_to_user_migratable_with_host(self):
        """
        Positive: Update vm affinity to user migratable with host
        """
        affinity = ENUMS['vm_affinity_user_migratable']
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                placement_affinity=affinity,
                placement_host=config.HOSTS[0]
            )
        )

    @attr(tier=2)
    @polarion("RHEVM3-12529")
    @bz({'1260732': {'engine': None, 'version': ['3.6']}})
    def test_update_vm_affinity_to_pinned_with_host(self):
        """
        Positive: Update vm affinity to pinned with host
        """
        affinity = ENUMS['vm_affinity_pinned']
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        placement_affinity=affinity,
                                        placement_host=config.HOSTS[0]))

    @attr(tier=2)
    @polarion("RHEVM3-12527")
    @bz({'1260732': {'engine': None, 'version': ['3.6']}})
    def test_update_vm_affinity_to_migratable_to_any_host(self):
        """
        Positive: Update vm affinity to migratable on any host
        """
        affinity = ENUMS['vm_affinity_migratable']
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                placement_host=ANY_HOST,
                placement_affinity=affinity
            )
        )

    @attr(tier=2)
    @polarion("RHEVM3-12530")
    @bz({'1260732': {'engine': None, 'version': ['3.6']}})
    def test_update_vm_affinity_to_user_migratable_to_any_host(self):
        """
        Positive: Update vm affinity to user migratable on any host
        """
        affinity = ENUMS['vm_affinity_user_migratable']
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                placement_host=ANY_HOST,
                placement_affinity=affinity
            )
        )

    @polarion("RHEVM3-12533")
    def test_update_vm_description(self):
        """
        Positive: Update vm description
        """
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                description="TEST"
            )
        )

    @bz({'1218528': {'engine': ['java', 'sdk', 'cli'], 'version': None}})
    @polarion("RHEVM3-12532")
    def test_update_vm_cluster(self):
        """
        Update vm cluster
        """
        logger.info("Turn VM %s back to being migratable", self.vm_name)
        affinity = ENUMS['vm_affinity_migratable']
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                placement_host=ANY_HOST,
                placement_affinity=affinity
            )
        )
        cluster = config.CLUSTER_NAME[1]
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                cluster=cluster,
                cpu_profile=None
            )
        )
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                cluster=config.CLUSTER_NAME[0],
                cpu_profile=None
            )
        )
        logger.info("Update cluster to: %s", cluster)

    @polarion("RHEVM3-12556")
    def test_update_vm_memory(self):
        """
        Update vm memory
        """
        self.assertTrue(vm_api.updateVm(True, self.vm_name, memory=TWO_GB))

    @polarion("RHEVM3-12555")
    def test_update_vm_guranteed_memory(self):
        """
        Positive: Update vm guaranteed memory
        """
        self.assertTrue(
            vm_api.updateVm(
                True,
                self.vm_name,
                memory_guaranteed=self.new_mem
            )
        )

    @polarion("RHEVM3-12559")
    def test_update_vm_number_of_cpu_sockets(self):
        """
        Positive: Update vm number of CPU sockets
        """
        self.assertTrue(vm_api.updateVm(True, self.vm_name, cpu_socket=2))

    @polarion("RHEVM3-12558")
    def test_update_vm_number_of_cpu_cores(self):
        """
        Positive: Update vm number of CPU cores
        """
        self.assertTrue(vm_api.updateVm(True, self.vm_name, cpu_cores=2))

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12534")
    def test_update_vm_display_type_to_vnc(self):
        """
        Positive: Update vm display type to VNC
        """
        display_type = ENUMS['display_type_vnc']
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                display_type=display_type
            )
        )

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12526")
    def test_update_spice_vm_number_of_monitors(self):
        """
        Positive: Update spice display type vm number of monitors
        """
        display_type = ENUMS['display_type_spice']
        logger.info(
            "Update vm %s display type to %s",
            self.vm_name, display_type
        )
        if not vm_api.updateVm(True, self.vm_name, display_type=display_type):
            raise errors.VMException("Failed to update vm")
        logger.info("Positive: Update vm number of monitors to 2")
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                display_monitors=2
            )
        )
        logger.info("Positive: Update vm number of monitors to 1")
        self.assertTrue(
            vm_api.updateVm(
                True, self.vm_name,
                display_monitors=1
            )
        )

    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12567")
    def test_update_vnc_vm_number_of_monitors(self):
        """
        Positive & Negative: Update vnc display type & num of monitors
        """
        display_type = ENUMS['display_type_vnc']
        logger.info(
            "Update vm %s display type to %s",
            self.vm_name, display_type
        )
        if not vm_api.updateVm(True, self.vm_name, display_type=display_type):
            raise errors.VMException("Failed to update vm")
        logger.info("Negative: Update vm number of monitors to 2")
        self.assertFalse(
            vm_api.updateVm(
                True, self.vm_name,
                display_monitors=2
            )
        )

    @polarion("RHEVM3-12557")
    def test_update_vm_name_to_existing_one(self):
        """
        Negative: Update vm name to existing one
        """
        vm_exist_name = 'exist_vm'
        logger.info("Add new vm %s", vm_exist_name)
        if not vm_api.addVm(
            True, name=vm_exist_name,
            cluster=config.CLUSTER_NAME[0],
            os_type=config.VM_OS_TYPE,
            type=config.VM_TYPE,
            display_type=config.VM_DISPLAY_TYPE
        ):
            raise errors.VMException("Failed to add vm")
        logger.info("Update vm name to existing one")
        self.assertFalse(
            vm_api.updateVm(
                True, self.vm_name,
                name=vm_exist_name
            )
        )

    @polarion("RHEVM3-12566")
    def test_update_vm_with_too_many_sockets(self):
        """
        Negative: Update vm with too many CPU sockets
        """
        self.assertFalse(vm_api.updateVm(True, self.vm_name, cpu_socket=40))

    @polarion("RHEVM3-12565")
    def test_update_vm_with_guranteed_memory_less_than_memory(self):
        """
        Negative: Update vm memory, to be less than guaranteed memory,
        that equal to 1gb
        """
        self.assertFalse(
            vm_api.updateVm(
                True,
                self.vm_name,
                memory=self.half_GB)
        )


@attr(tier=1)
class UpdateRunningVm(BaseVmWithDisk):
    """
    Update parameters of a running VM.
    """
    __test__ = True
    vm_name = 'running_vm'

    @classmethod
    def setup_class(cls):
        """
        Start VM.
        """
        super(UpdateRunningVm, cls).setup_class()
        logger.info("Starting VM %s", cls.vm_name)
        if not vm_api.startVm(
            True, cls.vm_name,
            wait_for_status=ENUMS['vm_state_up']
        ):
            raise errors.VMException("Failed to start VM")

    @classmethod
    def teardown_class(cls):
        """
        Stop VM.
        """
        logger.info("Stopping VM %s", cls.vm_name)
        if not vm_api.stopVm(True, cls.vm_name):
            logger.error("Failed to stop VM %s", cls.vm_name)
        super(UpdateRunningVm, cls).teardown_class()


@attr(tier=1)
class DifferentVmTestCases(TestCase):
    """
    Create, update and delete vms with different parameters
    """
    __test__ = True

    @classmethod
    def teardown_class(cls):
        """
        Remove all created vms
        """
        if not vm_api.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0],
            config.VM_NAME,
        ):
            logger.error("Failed to remove all vms")

    @attr(tier=2)
    @polarion("RHEVM3-12587")
    def test_remove_locked_vm(self):
        """
        Change vm status in database to locked and try to remove it
        """
        vm_name = 'locked_vm'
        logger.info("Add new vm %s", vm_name)
        if not vm_api.addVm(
            True, name=vm_name,
            cluster=config.CLUSTER_NAME[0],
            os_type=config.VM_OS_TYPE,
            type=config.VM_TYPE,
            display_type=config.VM_DISPLAY_TYPE
        ):
            raise errors.VMException("Failed to create vm")
        update_vm_status_in_database(
            vm_name,
            vdc=config.VDC_HOST,
            status=int(ENUMS['vm_status_locked_db']),
            vdc_pass=config.VDC_ROOT_PASSWORD
        )
        self.assertTrue(
            vm_api.remove_locked_vm(
                vm_name,
                vdc=config.VDC_HOST,
                vdc_pass=config.VDC_ROOT_PASSWORD
            )
        )

    @polarion("RHEVM3-12523")
    def test_check_vm_cdrom(self):
        """
        Add new vm and check that vm have attached cdrom
        """
        vm_name = 'cdrom_vm'
        logger.info("Add new vm %s", vm_name)
        if not vm_api.addVm(
            True, name=vm_name,
            cluster=config.CLUSTER_NAME[0],
            os_type=config.VM_OS_TYPE,
            type=config.VM_TYPE,
            display_type=config.VM_DISPLAY_TYPE

        ):
            raise errors.VMException("Failed to create vm")
        logger.info("Check if vm %s have cdrom", vm_name)
        self.assertTrue(vm_api.checkVmHasCdromAttached(True, vm_name))

    @attr(tier=2)
    @polarion("RHEVM3-12524")
    def test_retrieve_vm_statistics(self):
        """
        Add vm and check vm stats
        """
        vm_name = 'statistic_vm'
        logger.info("Add new vm %s", vm_name)
        if not vm_api.addVm(
            True, name=vm_name,
            cluster=config.CLUSTER_NAME[0],
            os_type=config.VM_OS_TYPE,
            type=config.VM_TYPE,
            display_type=config.VM_DISPLAY_TYPE
        ):
            raise errors.VMException("Failed to create vm")
        logger.info("Check vm %s statistics", vm_name)
        self.assertTrue(vm_api.checkVmStatistics(True, vm_name))


@attr(tier=2)
class VmNetwork(BaseVm):
    """
    Add, update and remove network from vm
    """
    __test__ = True
    vm_name = 'network_vm'
    nics = ["%s_%d" % (NIC_NAME, i) for i in range(3)]

    @polarion("RHEVM3-12577")
    def test_crud_vm_nic(self):
        """
        Create, update and remove vm nic
        """
        logger.info("Add nic %s to vm %s", self.nics[0], self.vm_name)
        self.assertTrue(
            vm_api.addNic(
                True, vm=self.vm_name,
                name=self.nics[0],
                network=config.MGMT_BRIDGE
            )
        )
        logger.info(
            "Add additional nic %s to vm %s",
            self.nics[1], self.vm_name
        )
        self.assertTrue(
            vm_api.addNic(
                True, vm=self.vm_name,
                name=self.nics[1],
                network=config.MGMT_BRIDGE
            )
        )
        logger.info("Update nic %s name to %s", self.nics[1], self.nics[2])
        self.assertTrue(
            vm_api.updateNic(
                True, vm=self.vm_name,
                nic=self.nics[1], name=self.nics[2]
            )
        )
        logger.info("Remove nic %s from vm %s", self.nics[2], self.vm_name)
        self.assertTrue(
            vm_api.removeNic(
                True, vm=self.vm_name,
                nic=self.nics[2]
            )
        )


@attr(tier=1)
class VmDisk(BaseVm):
    """
    Add different types of disks to vm
    """
    __test__ = True
    vm_name = 'disk_vm'

    @attr(tier=2)
    @polarion("RHEVM3-12572")
    def test_add_raw_virtio_disk_without_sparse(self):
        """
        Add raw virtio disk to vm without sparse
        """
        self.assertTrue(
            vm_api.addDisk(
                True,
                vm=self.vm_name,
                size=config.GB,
                storagedomain=self.master_domain,
                type=config.DISK_TYPE_DATA,
                format=config.DISK_FORMAT_RAW,
                interface=config.INTERFACE_VIRTIO,
                sparse=False
            )
        )

    @attr(tier=2)
    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12568")
    def test_add_bootable_cow_ide_data_disk(self):
        """
        Add bootable cow ide data disk to vm
        """
        self.assertTrue(vm_api.addDisk(
            True,
            vm=self.vm_name,
            size=config.GB,
            storagedomain=self.master_domain,
            type=config.DISK_TYPE_DATA,
            format=config.DISK_FORMAT_COW,
            interface=config.INTERFACE_IDE,
            bootable=True,
            wipe_after_delete=True)
        )

    @polarion("RHEVM3-12573")
    def test_sparse_cow_virtio_data_disk(self):
        """
        Add sparse cow virtio data disk to vm
        """
        self.assertTrue(
            vm_api.addDisk(
                True,
                vm=self.vm_name,
                size=config.GB,
                storagedomain=self.master_domain,
                type=config.DISK_TYPE_DATA,
                format=config.DISK_FORMAT_COW,
                interface=config.INTERFACE_VIRTIO,
                sparse=True
            )
        )

    @attr(tier=2)
    @unittest2.skipIf(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12571")
    def test_add_disks_with_different_interfaces_and_formats(self):
        """
        Add disks to vm with different interfaces and formats
        """
        for disk_interface in [config.INTERFACE_VIRTIO, config.INTERFACE_IDE]:
            for disk_format in [
                config.DISK_FORMAT_COW,
                config.DISK_FORMAT_RAW
            ]:
                logger.info(
                    "Add data disk to vm %s with format %s and interface %s",
                    self.vm_name, disk_format, disk_interface
                )
                result = vm_api.addDisk(
                    True,
                    vm=self.vm_name,
                    size=config.GB,
                    storagedomain=self.master_domain,
                    type=config.DISK_TYPE_DATA,
                    format=disk_format,
                    interface=disk_interface
                )
                self.assertTrue(result)

    @classmethod
    def teardown_class(cls):
        """
        Remove all disks from vm
        """
        logger.info("Remove all disks from vm %s", cls.vm_name)
        if not vm_api.remove_vm_disks(cls.vm_name):
            logger.error("Failed to remove disks")
        super(VmDisk, cls).teardown_class()


@attr(tier=1)
class BasicVmActions(BaseVmWithDisk):
    """
    Check basic vm operations, like start, suspend, stop and ticket
    """
    __test__ = True
    vm_name = 'virt_basic_actions'
    template_name = 'virt_vm_template'
    ticket_expire_time = 120

    @polarion("RHEVM3-12522")
    def test_basic_vm_actions(self):
        """
        Start vm, suspend, ticket and stop vm
        """
        logger.info("Start vm %s", self.vm_name)
        self.assertTrue(
            vm_api.startVm(
                True, self.vm_name,
                wait_for_status=config.VM_UP
            )
        )
        logger.info("Ticket running vm %s", self.vm_name)
        self.assertTrue(
            vm_api.ticketVm(
                True, self.vm_name,
                self.ticket_expire_time
            )
        )
        logger.info(
            "Negative: Create template from running vm %s",
            self.vm_name
        )
        self.assertFalse(
            template_api.createTemplate(
                True, vm=self.vm_name,
                name=self.template_name
            )
        )
        logger.info("Suspend vm %s", self.vm_name)
        self.assertTrue(vm_api.suspendVm(True, self.vm_name))
        logger.info("Stop suspended vm %s", self.vm_name)
        self.assertTrue(vm_api.stopVms([self.vm_name]))
        logger.info("Negative: Ticket stopped vm %s", self.vm_name)
        self.assertFalse(
            vm_api.ticketVm(
                True, self.vm_name,
                self.ticket_expire_time
            )
        )


@attr(tier=1)
class VmSnapshots(BaseVmWithDisk):
    """
    Create, restore and remove vm snapshots
    """
    __test__ = True
    vm_name = 'snapshot_vm'
    snapshot_description = ['snapshot_1', 'snapshot_2']

    @classmethod
    def teardown_class(cls):
        """ Remove the VM from export storage. """
        export_domain = storagedomains.findExportStorageDomains(
            config.DC_NAME[0]
        )[0]
        if vm_api.export_domain_vm_exist(cls.vm_name, export_domain):
            if not vm_api.remove_vm_from_export_domain(
                True, cls.vm_name, config.DC_NAME[0], export_domain
            ):
                logger.error(
                    "Failed to remove VM %s from export storage %s",
                    cls.vm_name, export_domain
                )
        super(VmSnapshots, cls).teardown_class()

    @bz({'1253338': {'engine': None, 'version': ['3.6']}})
    @polarion("RHEVM3-10089")
    def test_basic_vm_snapshots(self):
        """
        Create, restore, export and remove snapshots
        """
        export_domain = storagedomains.findExportStorageDomains(
            config.DC_NAME[0]
        )[0]
        logger.info("Create two new snapshots of vm %s", self.vm_name)
        for description in self.snapshot_description:
            job_description = "Creating VM Snapshot %s for VM %s" % (
                description, self.vm_name
            )
            logger.info("add snapshot job description: %s", job_description)
            self.assertTrue(
                vm_api.addSnapshot(
                    positive=True,
                    vm=self.vm_name,
                    description=description,
                ), "Failed to add snapshot to VM."
            )
        logger.info(
            "Restore vm %s from snapshot %s",
            self.vm_name,
            self.snapshot_description[1]
        )
        self.assertTrue(
            vm_api.restore_snapshot(
                True,
                self.vm_name,
                self.snapshot_description[1]
            )
        )
        logger.info("Export vm %s with discarded snapshots", self.vm_name)
        self.assertTrue(
            vm_api.exportVm(
                True,
                self.vm_name,
                export_domain,
                discard_snapshots=True
            )
        )
        logger.info(
            "Remove snapshots %s and %s of vm %s",
            self.snapshot_description[0],
            self.snapshot_description[1],
            self.vm_name
        )
        for snapshot in self.snapshot_description:
            self.assertTrue(
                vm_api.removeSnapshot(
                    True,
                    self.vm_name,
                    snapshot
                )
            )

    @bz({'1253338': {'engine': None, 'version': ['3.6']}})
    @polarion("RHEVM3-12581")
    def test_basic_vm_snapshots_with_memory(self):
        """
        Create, restore, export and remove snapshots
        """
        logger.info("Starting vm: %s", self.vm_name)
        self.assertTrue(vm_api.startVm(True, self.vm_name))
        logger.info(
            "Create two new snapshots of vm %s with memory",
            self.vm_name
        )
        for description in self.snapshot_description:
            job_description = (
                "Creating VM Snapshot %s with memory from VM %s" %
                (description, self.vm_name)
            )
            logger.info("add snapshot job description: %s", job_description)
            self.assertTrue(
                vm_api.addSnapshot(
                    positive=True,
                    vm=self.vm_name,
                    description=description,
                    persist_memory=True,
                ), "Failed to add snapshot to VM."
            )
        logger.info(
            "Restore vm %s from snapshot %s",
            self.vm_name,
            self.snapshot_description[1]
        )
        self.assertTrue(
            vm_api.restore_snapshot(
                True,
                self.vm_name,
                self.snapshot_description[1],
                restore_memory=True,
                ensure_vm_down=True
            )
        )
        logger.info(
            "Remove snapshots %s and %s of vm %s",
            self.snapshot_description[0],
            self.snapshot_description[1],
            self.vm_name
        )
        for snapshot in self.snapshot_description:
            self.assertTrue(
                vm_api.removeSnapshot(
                    True,
                    self.vm_name,
                    snapshot
                )
            )


@attr(tier=1)
class ImportExportVm(BaseVmWithDisk):
    """
    Check different cases for import/export vm
    """
    __test__ = True
    vm_name = 'export_vm'

    @classmethod
    def teardown_class(cls):
        """ Remove the VM from export storage. """
        export_domain = storagedomains.findExportStorageDomains(
            config.DC_NAME[0]
        )[0]
        if not vm_api.remove_vm_from_export_domain(
            True,
            cls.vm_name, config.DC_NAME[0],
            export_domain
        ):
            logger.error(
                "Failed to remove VM %s from export storage %s",
                cls.vm_name, export_domain
            )

        super(ImportExportVm, cls).teardown_class()

    @polarion("RHEVM3-12525")
    def test_basic_import_export_vm(self):
        """
        Basic: Import Export test
            1) Export vm
            2) Export vm, that override existing one
            3) Import exported vm
            4) Move vm to another sd
            5) Negative: import existed vm
        """
        export_domain = storagedomains.findExportStorageDomains(
            config.DC_NAME[0])[0]
        logger.info("Export vm %s", self.vm_name)
        self.assertTrue(vm_api.exportVm(True, self.vm_name, export_domain))

        logger.info("Export vm %s, that override existing one", self.vm_name)
        self.assertTrue(
            vm_api.exportVm(
                True,
                self.vm_name,
                export_domain,
                exclusive=True
            )
        )
        logger.info("Remove vm %s", self.vm_name)
        if not vm_api.removeVm(True, self.vm_name):
            raise errors.VMException("Failed to remove vm")
        logger.info("Import exported vm %s", self.vm_name)
        self.assertTrue(
            vm_api.importVm(
                True,
                self.vm_name,
                export_domain,
                self.master_domain,
                config.CLUSTER_NAME[0]
            )
        )
        logger.info("Negative: Import existed vm")
        self.assertFalse(
            vm_api.importVm(
                True,
                self.vm_name,
                export_domain,
                self.master_domain,
                config.CLUSTER_NAME[0]
            )
        )
        logger.info("Move vm to storage domain %s", self.non_master_domain)
        self.assertTrue(
            vm_api.moveVm(
                True,
                self.vm_name,
                self.non_master_domain
            )
        )
        logger.info("Move vm to storage domain %s", self.master_domain)
        self.assertTrue(
            vm_api.moveVm(
                True,
                self.vm_name,
                self.master_domain
            )
        )


@attr(tier=1)
@common.skip_class_if(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
class VmDisplay(TestCase):
    """
    Create vms with different display types, run it and check
    if address and port appear under display options
    """
    __test__ = True
    display_types = [ENUMS['display_type_spice'], ENUMS['display_type_vnc']]
    vm_names = ['%s_vm' % display_type for display_type in display_types]

    @classmethod
    def setup_class(cls):
        """
        Create two new vms, one with vnc type display and
        second with spice type display
        """
        master_domain = (
            sd_api.get_master_storage_domain_name(config.DC_NAME[0])
        )
        for display_type in cls.display_types:
            vm_name = '%s_vm' % display_type
            logger.info("Add new vm %s", vm_name)
            if not vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                display_type=display_type
            ):
                raise errors.VMException("Failed to add vm")
            if not vm_api.addDisk(
                True,
                vm=vm_name,
                size=config.GB,
                storagedomain=master_domain,
                type=config.DISK_TYPE_DATA,
                format=config.DISK_FORMAT_COW,
                interface=config.INTERFACE_VIRTIO
            ):
                raise errors.VMException(
                    "Failed to add disk to vm %s" % vm_name
                )
            logger.info("Start vm %s", vm_name)
            if not vm_api.startVm(True, vm_name):
                raise errors.VMException("Failed to start vm")

    @classmethod
    def teardown_class(cls):
        """
        Remove all vms
        """
        logger.info("Remove all vms")
        if not vm_api.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0],
            config.VM_NAME
        ):
            logger.error("Failed to remove all vms")

    @classmethod
    def _check_display_parameters(cls, vm_name, display_type):
        """
        Start vm and check display parameters
        """
        if display_type != SPICE:
            logger.info("Check if display port exist")
            if not vm_api.get_vm_display_port(vm_name):
                logger.info("Vm %s display port does not exist", vm_name)
                return False
        logger.info("Check if display address exist")
        if not vm_api.get_vm_display_address(vm_name):
            logger.info("Vm %s display address does not exist", vm_name)
            return False
        return True

    @polarion("RHEVM3-12574")
    def test_check_spice_parameters(self):
        """
        Check address and port parameters under display with type spice
        """
        self.assertTrue(
            self._check_display_parameters(self.vm_names[0], SPICE)
        )

    @polarion("RHEVM3-12575")
    def test_check_vnc_parameters(self):
        """
        Check address and port parameters under display with type spice
        """
        self.assertTrue(self._check_display_parameters(self.vm_names[1], VNC))


@attr(tier=1)
class VmTemplate(BaseVmWithDiskTemplate):
    """
    Create vm from template with different parameters
    """
    __test__ = True
    vm_name = 'virt_template_vm'
    template_name = 'virt_basic_template'
    counter = 0

    @polarion("RHEVM3-12583")
    def test_create_vm_from_template(self):
        """
        Create vm from template
        """
        vm_name = 'virt_new_template_vm'
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                template=self.template_name
            )
        )

    @polarion("RHEVM3-12584")
    def test_create_vm_from_template_with_specific_sd(self):
        """
        Create new vm with specified storage domain
        """
        vm_name = 'storage_template_vm'
        self.assertTrue(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                template=self.template_name,
                storagedomain=self.master_domain
            )
        )

    @bz({'1082977': {'engine': ['cli'], 'version': None}})
    @polarion("RHEVM3-12585")
    def test_create_vm_from_template_with_wrong_sd(self):
        """
        Negative: Create new vm with wrong storage domain
        """
        vm_name = 'storage_negative_vm'
        self.assertFalse(
            vm_api.addVm(
                True,
                name=vm_name,
                cluster=config.CLUSTER_NAME[0],
                template=self.template_name,
                storagedomain=self.non_master_domain
            )
        )

    @polarion("RHEVM3-12582")
    def test_clone_vm_from_template(self):
        """
        Clone vm from template
        """
        vm_name = 'virt_clone_vm'
        self.assertTrue(
            vm_api.cloneVmFromTemplate(
                True,
                vm_name,
                self.template_name,
                config.CLUSTER_NAME[0]
            )
        )
