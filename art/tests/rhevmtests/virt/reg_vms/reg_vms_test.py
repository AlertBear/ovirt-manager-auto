"""
Regression Vms Test - Basic tests to check vms functionality
"""

from rhevmtests.virt import config
import logging
from art.unittest_lib import VirtTest as TestCase
from nose.tools import istest
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
import art.rhevm_api.tests_lib.low_level.vmpools as vm_pool_api
import art.rhevm_api.tests_lib.low_level.storagedomains as sd_api
import art.rhevm_api.tests_lib.low_level.templates as template_api
from art.rhevm_api.tests_lib.low_level import storagedomains
import art.rhevm_api.tests_lib.high_level.storagedomains as high_sd_api
from art.rhevm_api.utils.test_utils import update_vm_status_in_database
from art.rhevm_api.tests_lib.low_level.mla import addVmPoolPermissionToUser
from art.unittest_lib import attr

MB = 1024 * 1024
GB = 1024 * MB
VM_DSC = 'reg_vms'
NIC_NAME = 'nic'
ENUMS = opts['elements_conf']['RHEVM Enums']
ANY_HOST = ENUMS['placement_host_any_host_in_cluster']
SPICE = ENUMS['display_type_spice']
VNC = ENUMS['display_type_vnc']
WIN_TZ = ENUMS['timezone_win_gmt_standard_time']
RHEL_TZ = ENUMS['timezone_rhel_etc_gmt']
# Timeout for VM creation in Vmpool
VMPOOL_TIMEOUT = 30

logger = logging.getLogger(__name__)


class BaseVm(TestCase):
    """
    Base vm class to create and remove vm
    """
    __test__ = False
    vm_name = None
    template_name = None

    @classmethod
    def setup_class(cls):
        """
        Add new vm with given name
        """
        logger.info("Add new vm %s", cls.vm_name)
        if not vm_api.addVm(True, name=cls.vm_name,
                            cluster=config.CLUSTER_NAME[0],
                            memory=1536 * MB):
            raise errors.VMException("Failed to create vm %s" % cls.vm_name)

    @classmethod
    def teardown_class(cls):
        """
        Remove all vms from cluster
        """
        logger.info("Remove all vms")
        if not vm_api.remove_all_vms_from_cluster(config.CLUSTER_NAME[0],
                                                  config.VM_NAME):
            raise errors.VMException("Failed to remove all vms")


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
        if not vm_api.addDisk(True, vm=cls.vm_name, size=GB,
                              storagedomain=config.STORAGE_NAME[0],

                              type=ENUMS['disk_type_system'],
                              format=ENUMS['format_cow'],
                              interface=ENUMS['interface_virtio']):
            raise errors.VMException("Failed to add disk to vm %s" %
                                     cls.vm_name)

    @classmethod
    def teardown_class(cls):
        """
        Remove vm disk and vm
        """
        if not vm_api.removeDisks(True, vm=cls.vm_name, num_of_disks=1):
            raise errors.DiskException("Failed to remove disk from vm %s" %
                                       cls.vm_name)
        super(BaseVmWithDisk, cls).teardown_class()


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
        if not template_api.createTemplate(True, vm=cls.vm_name,
                                           name=cls.template_name):
            raise errors.VMException("Failed to create template")

    @classmethod
    def teardown_class(cls):
        """
        Remove created vm and remove template
        """
        super(BaseVmWithDiskTemplate, cls).teardown_class()
        logger.info("Remove template %s", cls.template_name)
        if not template_api.removeTemplate(True, cls.template_name):
            raise errors.TemplateException("Failed to remove template")


@attr(tier=0)
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
        if not vm_api.remove_all_vms_from_cluster(config.CLUSTER_NAME[0],
                                                  config.VM_NAME):
            raise errors.VMException("Failed to remove all vms")

    @istest
    def add_vm_with_custom_boot_sequence(self):
        """
        Add vm with custom boot sequence
        """
        vm_name = 'boot_vm'
        if not vm_api.addVm(True, name=vm_name, cluster=config.CLUSTER_NAME[0],
                            os_type=ENUMS['rhel6x64'],
                            boot=['network', 'hd']):
            raise errors.VMException("Failed to add vm")
        logger.info("Check if network first and hard disk second"
                    " in boot sequence on vm %s", vm_name)
        boot_list = vm_api.get_vm_boot_sequence(vm_name)
        self.assertTrue(boot_list[0] == ENUMS['boot_sequence_network'] and
                        boot_list[1] == ENUMS['boot_sequence_hd'])

    @istest
    @tcms('13398', '366252')
    def add_default_vm_without_special_parameters(self):
        """
        Positive: Add default vm without special parameters
        """
        vm_name = 'default_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     cluster=config.CLUSTER_NAME[0]))

    @istest
    def add_ha_server_vm(self):
        """
        Positive: Add HA server vm
        """
        vm_name = 'ha_server_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     highly_available='true',
                                     type=ENUMS['vm_type_server'],
                                     cluster=config.CLUSTER_NAME[0]))

    @istest
    def add_stateless_vm(self):
        """
        Positive: Add stateless vm
        """
        vm_name = 'stateless_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name, stateless='true',
                                     cluster=config.CLUSTER_NAME[0]))

    @istest
    def add_vm_with_custom_property(self):
        """
        Positive: Add vm with custom property
        """
        vm_name = 'custom_property_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     cluster=config.CLUSTER_NAME[0],
                                     custom_properties='sndbuf=111'))

    @istest
    def add_vm_with_guranteed_memory(self):
        """
        Positive: Add vm with guaranteed memory
        """
        vm_name = 'guaranteed_memory_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     cluster=config.CLUSTER_NAME[0],
                                     memory=2*GB, memory_guaranteed=2*GB))

    @tcms('13398', '366252')
    @istest
    def add_vm_with_disk(self):
        """
        Positive: Add vm with disk
        """
        vm_name = 'disk_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     cluster=config.CLUSTER_NAME[0],
                                     disk_type=ENUMS['disk_type_data'],
                                     size=2*GB, format=ENUMS['format_cow'],
                                     interface=ENUMS['interface_virtio']))

    @istest
    def add_vm_with_os_parameters(self):
        """
        Positive: Add vm with OS parameters
        """
        vm_name = 'os_parameters_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     cluster=config.CLUSTER_NAME[0],
                                     kernel='/kernel-path',
                                     initrd='/initrd-path',
                                     cmdline='rd_NO_LUKS rd_NO_MD'))

    @istest
    def add_vm_with_rhel_os_type(self):
        """
        Positive: Add vm with Rhel OS type
        """
        vm_name = 'rhel_vm'
        logger.info("Positive: Add vm with Rhel OS type")
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     cluster=config.CLUSTER_NAME[0],
                                     os_type=ENUMS['rhel6x64']))

    @istest
    def add_vm_with_windows_xp_os_type(self):
        """
        Positive: Add vm with Windows XP OS type
        """
        vm_name = 'xp_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     cluster=config.CLUSTER_NAME[0],
                                     os_type=ENUMS['windowsxp']))

    @istest
    def add_vm_with_disk_on_specific_storage_domain(self):
        """
        Positive: Add vm with disk on specific storage domain
        """
        vm_name = 'disk_specific_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     cluster=config.CLUSTER_NAME[0],
                                     storagedomain=config.STORAGE_NAME[0],
                                     disk_type=ENUMS['disk_type_data'],
                                     size=2*GB, format=ENUMS['format_cow'],
                                     interface=ENUMS['interface_virtio']))

    @istest
    def add_vm_with_specific_domain(self):
        """
        Positive: Add vm with specific domain
        """
        vm_name = 'domain_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     domainName=config.VDC_ADMIN_DOMAIN,
                                     cluster=config.CLUSTER_NAME[0]))

    @istest
    def add_vm_with_name_that_already_exist(self):
        """
        Negative: Add vm with name that already in use
        """
        vm_name = 'vm_name_negative'
        logger.info("Add vm %s", vm_name)
        if not vm_api.addVm(True, name=vm_name,
                            cluster=config.CLUSTER_NAME[0]):
            raise errors.VMException("Failed to add vm")
        logger.info("Create vm with name that already exist")
        self.assertFalse(vm_api.addVm(True, name=vm_name,
                                      cluster=config.CLUSTER_NAME[0]))

    @istest
    def add_vm_with_wrong_number_of_displays(self):
        """
        Negative: Add vm with wrong number of displays
        """
        vm_name = 'display_vm_negative'
        self.assertFalse(vm_api.addVm(True, name=vm_name, display_monitors=36,
                                      cluster=config.CLUSTER_NAME[0]))


@attr(tier=0)
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

    @classmethod
    def setup_class(cls):
        """
        Add vms for test
        """
        logger.info("Add new vm %s with rhel os parameter", cls.rhel_to_xp_vm)
        if not vm_api.addVm(True, name=cls.rhel_to_xp_vm,
                            cluster=config.CLUSTER_NAME[0],
                            os_type=ENUMS['rhel6x64']):
            raise errors.VMException("Failed to add vm")
        logger.info("Add new vm %s with rhel os parameter", cls.rhel_to_7_vm)
        if not vm_api.addVm(True, name=cls.rhel_to_7_vm,
                            cluster=config.CLUSTER_NAME[0],
                            os_type=ENUMS['rhel6x64']):
            raise errors.VMException("Failed to add vm")
        logger.info("Add new vm %s with rhel os parameter", cls.xp_to_rhel_vm)
        if not vm_api.addVm(True, name=cls.xp_to_rhel_vm,
                            cluster=config.CLUSTER_NAME[0],
                            os_type=ENUMS['windowsxp']):
            raise errors.VMException("Failed to add vm")
        logger.info("Add new vm %s with rhel os parameter, for neg tests",
                    cls.rhel_to_7_vm_neg)
        if not vm_api.addVm(True, name=cls.rhel_to_7_vm_neg,
                            cluster=config.CLUSTER_NAME[0],
                            os_type=ENUMS['rhel6x64']):
            raise errors.VMException("Failed to add vm")
        super(UpdateVm, cls).setup_class()

    @istest
    def update_vm_os_type_from_rhel_to_windows_xp(self):
        """
        Negative: Update vm OS type from rhel to Windows XP
        """
        self.assertFalse(vm_api.updateVm(True, self.rhel_to_xp_vm,
                                         timezone=WIN_TZ,
                                         os_type=ENUMS['windowsxp']))

    @istest
    def update_vm_os_type_from_rhel_to_windows_7(self):
        """
        Positive: Update vm OS type from rhel to Windows 7
        """
        self.assertTrue(vm_api.updateVm(True, self.rhel_to_7_vm,
                                        timezone=WIN_TZ,
                                        os_type=ENUMS['windows7']))

    @istest
    def update_vm_os_type_from_xp_to_rhel(self):
        """
        Positive: Update vm OS type from Windows XP to RHEL
        """
        self.assertTrue(vm_api.updateVm(True, self.xp_to_rhel_vm,
                                        timezone=RHEL_TZ,
                                        os_type=ENUMS['rhel6x64']))

    @istest
    def update_vm_os_type_from_rhel_to_windows_7_neg(self):
        """
        Negative: Update vm OS type from rhel to Windows 7, no timezone update
        """
        self.assertFalse(vm_api.updateVm(True, self.rhel_to_7_vm_neg,
                                         os_type=ENUMS['windows7']))

    @istest
    def update_vm_os_parameters(self):
        """
        Positive: Update vm OS parameters
        """
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        kernel='/kernel-new-path',
                                        initrd='/initrd-new-path',
                                        cmdline='rd_NO_LUKS'))

    @tcms('13398', '377892')
    @istest
    def update_vm_name(self):
        """
        Positive: Update vm name
        """
        vm_update = 'some_name'
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        name=vm_update))
        self.assertTrue(vm_api.updateVm(True, vm_update,
                                        name=self.vm_name))

    @attr(tier=1)
    @istest
    def update_vm_affinity_to_migratable_with_host(self):
        """
        Positive: Update vm affinity to migratable with host
        """
        affinity = ENUMS['vm_affinity_migratable']
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        placement_affinity=affinity,
                                        placement_host=config.HOSTS[0]))

    @attr(tier=1)
    @istest
    def update_vm_affinity_to_user_migratable_with_host(self):
        """
        Positive: Update vm affinity to user migratable with host
        """
        affinity = ENUMS['vm_affinity_user_migratable']
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        placement_affinity=affinity,
                                        placement_host=config.HOSTS[0]))

    @attr(tier=1)
    @istest
    def update_vm_affinity_to_pinned_with_host(self):
        """
        Positive: Update vm affinity to pinned with host
        """
        affinity = ENUMS['vm_affinity_pinned']
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        placement_affinity=affinity,
                                        placement_host=config.HOSTS[0]))

    @attr(tier=1)
    @istest
    def update_vm_affinity_to_migratable_to_any_host(self):
        """
        Positive: Update vm affinity to migratable on any host
        """
        affinity = ENUMS['vm_affinity_migratable']
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        placement_host=ANY_HOST,
                                        placement_affinity=affinity))

    @attr(tier=1)
    @istest
    def update_vm_affinity_to_user_migratable_to_any_host(self):
        """
        Positive: Update vm affinity to user migratable on any host
        """
        affinity = ENUMS['vm_affinity_user_migratable']
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        placement_host=ANY_HOST,
                                        placement_affinity=affinity))

    @tcms('13398', '377892')
    @istest
    def update_vm_description(self):
        """
        Positive: Update vm description
        """
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        description="TEST"))

    @bz({'1158458': {'engine': None, 'version': None}})
    @istest
    def update_vm_cluster(self):
        """
        Update vm cluster
        """
        logger.info("Turn VM %s back to being migratable", self.vm_name)
        affinity = ENUMS['vm_affinity_migratable']
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        placement_host=ANY_HOST,
                                        placement_affinity=affinity))
        cluster = config.CLUSTER_NAME[1]
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        cluster=cluster))
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        cluster=config.CLUSTER_NAME[0]))

    @istest
    def update_vm_memory(self):
        """
        Update vm memory
        """
        self.assertTrue(vm_api.updateVm(True, self.vm_name, memory=2*GB))

    @istest
    def update_vm_guranteed_memory(self):
        """
        Positive: Update vm guaranteed memory
        """
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        memory_guaranteed=1280*MB))

    @istest
    def update_vm_number_of_cpu_sockets(self):
        """
        Positive: Update vm number of CPU sockets
        """
        self.assertTrue(vm_api.updateVm(True, self.vm_name, cpu_socket=2))

    @istest
    def update_vm_number_of_cpu_cores(self):
        """
        Positive: Update vm number of CPU cores
        """
        self.assertTrue(vm_api.updateVm(True, self.vm_name, cpu_cores=2))

    @istest
    def update_vm_display_type_to_spice(self):
        """
        Positive: Update vm display type to SPICE
        """
        display_type = ENUMS['display_type_vnc']
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        display_type=display_type))

    @istest
    def update_spice_vm_number_of_monitors(self):
        """
        Positive: Update spice display type vm number of monitors
        """
        display_type = ENUMS['display_type_spice']
        logger.info("Update vm %s display type to %s",
                    self.vm_name, display_type)
        if not vm_api.updateVm(True, self.vm_name, display_type=display_type):
            raise errors.VMException("Failed to update vm")
        logger.info("Positive: Update vm number of monitors to 2")
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        display_monitors=2))
        logger.info("Positive: Update vm number of monitors to 1")
        self.assertTrue(vm_api.updateVm(True, self.vm_name,
                                        display_monitors=1))

    @istest
    def update_vnc_vm_number_of_monitors(self):
        """
        Positive & Negative: Update vnc display type & num of monitors
        """
        display_type = ENUMS['display_type_vnc']
        logger.info("Update vm %s display type to %s",
                    self.vm_name, display_type)
        if not vm_api.updateVm(True, self.vm_name, display_type=display_type):
            raise errors.VMException("Failed to update vm")
        logger.info("Negative: Update vm number of monitors to 2")
        self.assertFalse(vm_api.updateVm(True, self.vm_name,
                                         display_monitors=2))

    @istest
    def update_vm_name_to_existing_one(self):
        """
        Negative: Update vm name to existing one
        """
        vm_exist_name = 'exist_vm'
        logger.info("Add new vm %s", vm_exist_name)
        if not vm_api.addVm(True, name=vm_exist_name,
                            cluster=config.CLUSTER_NAME[0]):
            raise errors.VMException("Failed to add vm")
        logger.info("Update vm name to existing one")
        self.assertFalse(vm_api.updateVm(True, self.vm_name,
                                         name=vm_exist_name))

    @istest
    def update_vm_with_too_many_sockets(self):
        """
        Negative: Update vm with too many CPU sockets
        """
        self.assertFalse(vm_api.updateVm(True, self.vm_name, cpu_socket=40))

    @istest
    def update_vm_with_guranteed_memory_less_than_memory(self):
        """
        Negative: Update vm memory, to be less than guaranteed memory,
        that equal to 1gb
        """
        self.assertFalse(vm_api.updateVm(True, self.vm_name, memory=512*MB))


@attr(tier=0)
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
        if not vm_api.startVm(True, cls.vm_name,
                              wait_for_status=ENUMS['vm_state_up']):
            raise errors.VMException("Failed to start VM")

    @classmethod
    def teardown_class(cls):
        """
        Stop VM.
        """
        logger.info("Stopping VM %s", cls.vm_name)
        if not vm_api.stopVm(True, cls.vm_name):
            raise errors.VMException("Failed to stop VM")
        super(UpdateRunningVm, cls).teardown_class()


@attr(tier=0)
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
        if not vm_api.remove_all_vms_from_cluster(config.CLUSTER_NAME[0],
                                                  config.VM_NAME):
            raise errors.VMException("Failed to remove all vms")

    @attr(tier=1)
    @istest
    def remove_locked_vm(self):
        """
        Change vm status in database to locked and try to remove it
        """
        vm_name = 'locked_vm'
        logger.info("Add new vm %s", vm_name)
        if not vm_api.addVm(True, name=vm_name,
                            cluster=config.CLUSTER_NAME[0]):
            raise errors.VMException("Failed to create vm")
        update_vm_status_in_database(vm_name, vdc=config.VDC_HOST,
                                     status=int(ENUMS['vm_status_locked_db']),
                                     vdc_pass=config.VDC_ROOT_PASSWORD)
        self.assertTrue(vm_api.remove_locked_vm(vm_name, vdc=config.VDC_HOST,
                        vdc_pass=config.VDC_ROOT_PASSWORD))

    @istest
    def check_vm_cdrom(self):
        """
        Add new vm and check that vm have attached cdrom
        """
        vm_name = 'cdrom_vm'
        logger.info("Add new vm %s", vm_name)
        if not vm_api.addVm(True, name=vm_name,
                            cluster=config.CLUSTER_NAME[0]):
            raise errors.VMException("Failed to create vm")
        logger.info("Check if vm %s have cdrom", vm_name)
        self.assertTrue(vm_api.checkVmHasCdromAttached(True, vm_name))

    @attr(tier=1)
    @istest
    def retrieve_vm_statistics(self):
        """
        Add vm and check vm stats
        """
        vm_name = 'statistic_vm'
        logger.info("Add new vm %s", vm_name)
        if not vm_api.addVm(True, name=vm_name,
                            cluster=config.CLUSTER_NAME[0]):
            raise errors.VMException("Failed to create vm")
        logger.info("Check vm %s statistics", vm_name)
        self.assertTrue(vm_api.checkVmStatistics(True, vm_name))


@attr(tier=1)
class VmNetwork(BaseVm):
    """
    Add, update and remove network from vm
    """
    __test__ = True
    vm_name = 'network_vm'
    nics = ["%s_%d" % (NIC_NAME, i) for i in range(3)]

    @istest
    def crud_vm_nic(self):
        """
        Create, update and remove vm nic
        """
        logger.info("Add nic %s to vm %s", self.nics[0], self.vm_name)
        self.assertTrue(vm_api.addNic(True, vm=self.vm_name,
                                      name=self.nics[0],
                                      network=config.MGMT_BRIDGE))
        logger.info("Add additional nic %s to vm %s",
                    self.nics[1], self.vm_name)
        self.assertTrue(vm_api.addNic(True, vm=self.vm_name,
                                      name=self.nics[1],
                                      network=config.MGMT_BRIDGE))
        logger.info("Update nic %s name to %s", self.nics[1], self.nics[2])
        self.assertTrue(vm_api.updateNic(True, vm=self.vm_name,
                                         nic=self.nics[1], name=self.nics[2]))
        logger.info("Remove nic %s from vm %s", self.nics[2], self.vm_name)
        self.assertTrue(vm_api.removeNic(True, vm=self.vm_name,
                                         nic=self.nics[2]))


@attr(tier=0)
class VmDisk(BaseVm):
    """
    Add different types of disks to vm
    """
    __test__ = True
    vm_name = 'disk_vm'
    disk_interfaces = [ENUMS['interface_virtio'], ENUMS['interface_ide']]
    disk_formats = [ENUMS['format_cow'], ENUMS['format_raw']]

    @attr(tier=1)
    @istest
    def add_raw_ide_disk_without_sparse(self):
        """
        Add raw virtio disk to vm without sparse
        """
        self.assertTrue(vm_api.addDisk(True, vm=self.vm_name, size=GB,
                                       storagedomain=config.STORAGE_NAME[0],
                                       type=ENUMS['disk_type_system'],
                                       format=ENUMS['format_raw'],
                                       interface=ENUMS['interface_virtio'],
                                       sparse=False))

    @attr(tier=1)
    @istest
    def add_bootable_cow_ide_data_disk(self):
        """
        Add bootable cow ide data disk to vm
        """
        self.assertTrue(vm_api.addDisk(True, vm=self.vm_name, size=GB,
                                       storagedomain=config.STORAGE_NAME[0],
                                       type=ENUMS['disk_type_data'],
                                       format=ENUMS['format_cow'],
                                       interface=ENUMS['interface_ide'],
                                       bootable=True,
                                       wipe_after_delete=True))

    @istest
    def sparse_cow_virtio_data_disk(self):
        """
        Add sparse cow virtio data disk to vm
        """
        self.assertTrue(vm_api.addDisk(True, vm=self.vm_name, size=GB,
                                       storagedomain=config.STORAGE_NAME[0],
                                       type=ENUMS['disk_type_data'],
                                       format=ENUMS['format_cow'],
                                       interface=ENUMS['interface_virtio'],
                                       sparse=True))

    @attr(tier=1)
    @istest
    def add_disks_with_different_interfaces_and_formats(self):
        """
        Add disks to vm with different interfaces and formats
        """
        for disk_interface in self.disk_interfaces:
            for disk_format in self.disk_formats:
                logger.info("Add data disk to vm %s with"
                            " format %s and interface %s",
                            self.vm_name, disk_format, disk_interface)
                result = vm_api.addDisk(True, vm=self.vm_name, size=GB,
                                        storagedomain=config.STORAGE_NAME[0],
                                        type=ENUMS['disk_type_data'],
                                        format=disk_format,
                                        interface=disk_interface)
                self.assertTrue(result)

    @classmethod
    def teardown_class(cls):
        """
        Remove all disks from vm
        """
        logger.info("Remove all disks from vm %s", cls.vm_name)
        if not vm_api.remove_vm_disks(cls.vm_name):
            raise errors.DiskException("Failed to remove disks")
        super(VmDisk, cls).teardown_class()


@attr(tier=0)
class BasicVmActions(BaseVmWithDisk):
    """
    Check basic vm operations, like start, suspend, stop and ticket
    """
    __test__ = True
    vm_name = 'basic_actions'
    template_name = 'vm_template'
    ticket_expire_time = 120

    @istest
    def basic_vm_actions(self):
        """
        Start vm, suspend, ticket and stop vm
        """
        logger.info("Start vm %s", self.vm_name)
        self.assertTrue(vm_api.startVm(True, self.vm_name,
                                       wait_for_status=ENUMS['vm_state_up']))
        logger.info("Ticket running vm %s", self.vm_name)
        self.assertTrue(vm_api.ticketVm(True, self.vm_name,
                                        self.ticket_expire_time))
        logger.info("Negative: Create template from running vm %s",
                    self.vm_name)
        self.assertFalse(template_api.createTemplate(True, vm=self.vm_name,
                                                     name=self.template_name))
        logger.info("Suspend vm %s", self.vm_name)
        self.assertTrue(vm_api.suspendVm(True, self.vm_name))
        logger.info("Stop suspended vm %s", self.vm_name)
        self.assertTrue(vm_api.stopVms([self.vm_name]))
        logger.info("Negative: Ticket stopped vm %s", self.vm_name)
        self.assertFalse(vm_api.ticketVm(True, self.vm_name,
                                         self.ticket_expire_time))


@attr(tier=0)
class AutomaticManualVmMigration(BaseVmWithDisk):
    """
    Check manual and automatic vm migration
    """
    __test__ = True
    vm_name = 'migration_vm'
    vm_host = None

    @istest
    def automatic_and_manual_vm_migration(self):
        """
        Put host with vm to maintenance, vm must migrate on other host,
        after it migrate vm back
        """
        logger.info("Start vm %s", self.vm_name)
        if not vm_api.startVm(True, self.vm_name):
            raise errors.VMException("Failed to start vm")
        status, self.vm_host = vm_api.getVmHost(self.vm_name)
        self.__class__.vm_host = self.vm_host
        if not status:
            raise errors.VMException("Failed to receive vm %s host" %
                                     self.vm_host.get('vmHoster'))
        logger.info("Put host %s to maintenance state",
                    self.vm_host.get('vmHoster'))
        if not host_api.deactivateHost(True, self.vm_host.get('vmHoster')):
            raise errors.HostException("Failed to put host to maintenance")
        logger.info("Check that vm %s up", self.vm_name)
        self.assertTrue(vm_api.waitForVMState(self.vm_name))
        logger.info("Activate host %s", self.vm_host.get('vmHoster'))
        if not host_api.activateHost(True, self.vm_host.get('vmHoster')):
            raise errors.HostException("Failed to activate host")
        logger.info("Migrate vm %s on activated host %s",
                    self.vm_name, self.vm_host.get('vmHoster'))
        self.assertTrue(vm_api.migrateVm(True, self.vm_name))
        logger.info("Stop vm %s", self.vm_name)
        self.assertTrue(vm_api.stopVms([self.vm_name]))

    @classmethod
    def teardown_class(cls):
        """
        If need activate host and remove vm
        """
        if cls.vm_host:
            host = cls.vm_host.get('vmHoster')
            logger.info("Activate host %s", host)
            if host_api.isHostInMaintenance(True, host):
                logger.info("Activate host %s", host)
                if not host_api.activateHost(True, host):
                    raise errors.HostException("Failed to activate host")
        super(AutomaticManualVmMigration, cls).teardown_class()


@attr(tier=0)
class VmSnapshots(BaseVmWithDisk):
    """
    Create, restore and remove vm snapshots
    """
    __test__ = True
    vm_name = 'snapshot_vm'
    snapshot_dsc = ['snapshot_1', 'snapshot_2']

    @classmethod
    def teardown_class(cls):
        """ Remove the VM from export storage. """
        export_domain = storagedomains.findExportStorageDomains(
            config.DC_NAME[0])[0]
        if not vm_api.removeVmFromExportDomain(
                True, cls.vm_name, config.DC_NAME[0], export_domain):
            raise errors.VMException(
                "Failed to remove VM %s from export storage %s"
                % (cls.vm_name, export_domain))
        super(VmSnapshots, cls).teardown_class()

    @tcms('13398', '366363')
    @istest
    def basic_vm_snapshots(self):
        """
        Create, restore, export and remove snapshots
        """
        export_domain = storagedomains.findExportStorageDomains(
            config.DC_NAME[0])[0]
        logger.info("Create two new snapshots of vm %s", self.vm_name)
        for dsc in self.snapshot_dsc:
            self.assertTrue(vm_api.addSnapshot(True, self.vm_name, dsc))
        logger.info("Restore vm %s from snapshot %s",
                    self.vm_name, self.snapshot_dsc[1])
        self.assertTrue(vm_api.restoreSnapshot(True, self.vm_name,
                                               self.snapshot_dsc[1]))
        logger.info("Export vm %s with discarded snapshots", self.vm_name)
        self.assertTrue(vm_api.exportVm(True, self.vm_name,
                                        export_domain,
                                        discard_snapshots=True))
        logger.info("Remove snapshot %s of vm %s",
                    self.snapshot_dsc[0], self.vm_name)


@attr(tier=0)
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
            config.DC_NAME[0])[0]
        if not vm_api.removeVmFromExportDomain(
                True, cls.vm_name, config.DC_NAME[0], export_domain):
            raise errors.VMException(
                "Failed to remove VM %s from export storage %s"
                % (cls.vm_name, export_domain))
        super(ImportExportVm, cls).teardown_class()

    @istest
    def basic_import_export_vm(self):
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
        self.assertTrue(vm_api.exportVm(True, self.vm_name,
                                        export_domain))
        logger.info("Export vm %s, that override existing one", self.vm_name)
        self.assertTrue(vm_api.exportVm(True, self.vm_name,
                                        export_domain,
                                        exclusive=True))
        logger.info("Remove vm %s", self.vm_name)
        if not vm_api.removeVm(True, self.vm_name):
            raise errors.VMException("Failed to remove vm")
        logger.info("Import exported vm %s", self.vm_name)
        self.assertTrue(vm_api.importVm(True, self.vm_name,
                                        export_domain,
                                        config.STORAGE_NAME[0],
                                        config.CLUSTER_NAME[0]))
        logger.info("Negative: Import existed vm")
        self.assertFalse(vm_api.importVm(True, self.vm_name,
                                         export_domain,
                                         config.STORAGE_NAME[0],
                                         config.CLUSTER_NAME[0]))
        logger.info("Move vm to storage domain %s", config.nfs_storage_1)
        self.assertTrue(vm_api.moveVm(True, self.vm_name,
                                      config.STORAGE_NAME[1]))
        logger.info("Move vm to storage domain %s", config.STORAGE_NAME[0])
        self.assertTrue(vm_api.moveVm(True, self.vm_name,
                                      config.STORAGE_NAME[0]))


@attr(tier=0)
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
        for display_type in cls.display_types:
            vm_name = '%s_vm' % display_type
            logger.info("Add new vm %s", vm_name)
            if not vm_api.addVm(True, name=vm_name,
                                cluster=config.CLUSTER_NAME[0],
                                display_type=display_type):
                raise errors.VMException("Failed to add vm")
            if not vm_api.addDisk(True, vm=vm_name, size=GB,
                                  storagedomain=config.STORAGE_NAME[0],
                                  type=ENUMS['disk_type_system'],
                                  format=ENUMS['format_cow'],
                                  interface=ENUMS['interface_virtio']):
                raise errors.VMException("Failed to add disk to vm %s" %
                                         vm_name)
            logger.info("Start vm %s", vm_name)
            if not vm_api.startVm(True, vm_name):
                raise errors.VMException("Failed to start vm")

    @classmethod
    def teardown_class(cls):
        """
        Remove all vms
        """
        if not vm_api.stopVms(cls.vm_names):
            raise errors.VMException("Failed to stop vms")
        if not vm_api.removeVms(True, cls.vm_names):
            raise errors.VMException("Failed to remove vms")

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

    @istest
    def check_spice_parameters(self):
        """
        Check address and port parameters under display with type spice
        """
        self.assertTrue(self._check_display_parameters(self.vm_names[0],
                                                       SPICE))

    @istest
    def check_vnc_parameters(self):
        """
        Check address and port parameters under display with type spice
        """
        self.assertTrue(self._check_display_parameters(self.vm_names[1],
                                                       VNC))


@attr(tier=0)
class RunVmOnce(BaseVmWithDisk):
    """
    Run once vm with different parameters
    """
    __test__ = True
    vm_name = 'run_once_vm'

    @classmethod
    def setup_class(cls):
        """
        Add new vm with disk and also setup iso shared storage domain
        """
        nic_name = '%s_1' % NIC_NAME
        super(RunVmOnce, cls).setup_class()
        logger.info("Add nic %s to vm %s", nic_name, cls.vm_name)
        if not vm_api.addNic(True, vm=cls.vm_name,
                             name=nic_name,
                             network=config.MGMT_BRIDGE):
            raise errors.VMException("Failed to add nic to vm")
        if not config.GOLDEN_ENV:
            logger.info("Import iso storage domain %s:%s",
                        config.SHARED_ISO_DOMAIN_ADDRESS,
                        config.SHARED_ISO_DOMAIN_PATH)
            if not sd_api.importStorageDomain(
                    True, ENUMS['storage_dom_type_iso'],
                    ENUMS['storage_type_nfs'],
                    config.SHARED_ISO_DOMAIN_ADDRESS,
                    config.SHARED_ISO_DOMAIN_PATH,
                    config.HOSTS[0]):
                raise errors.StorageDomainException("Failed to add shared iso "
                                                    "domain storage")
        high_sd_api.attach_and_activate_domain(config.DC_NAME[0],
                                               config.SHARED_ISO_DOMAIN_NAME)

    @classmethod
    def teardown_class(cls):
        """
        Remove share iso domain, Stop and Remove VM
        """
        # Stop VM if required it is not down
        if vm_api.get_vm_state(cls.vm_name) not in (ENUMS['vm_state_down'],):
            logger.info("Stop %s vm", cls.vm_name)
            if not vm_api.stopVm(True, cls.vm_name):
                raise errors.VMException("Failed to stop vm")
        # Remove iso domain
        high_sd_api.detach_and_deactivate_domain(config.DC_NAME[0],
                                                 config.
                                                 SHARED_ISO_DOMAIN_NAME)
        if not config.GOLDEN_ENV:
            logger.info("Remove shared iso domain %s",
                        config.SHARED_ISO_DOMAIN_NAME)
            if not sd_api.removeStorageDomain(
                    True, config.SHARED_ISO_DOMAIN_NAME, config.HOSTS[0]):
                raise errors.StorageDomainException(
                    "Failed to remove iso domain")
        super(RunVmOnce, cls).teardown_class()

    @bz({'1117783': {'engine': None, 'version': None}})
    @istest
    def run_once_vm_with_specific_domain(self):
        """
        Run once vm with specific domain
        """
        logger.info("Run once vm %s with domain %s",
                    self.vm_name, config.VDC_ADMIN_DOMAIN)
        if not vm_api.runVmOnce(True, self.vm_name,
                                domainName=config.VDC_ADMIN_DOMAIN,
                                user_name=config.VDC_ADMIN_USER,
                                password=config.VDC_PASSWORD):
            raise errors.VMException("Failed to run vm")
        vm_obj = vm_api.get_vm_obj(self.vm_name)
        logger.info("Check if vm domain is correct")
        self.assertTrue(vm_obj.get_domain() == config.VDC_ADMIN_DOMAIN)
        logger.info("Stop vm %s", self.vm_name)
        if not vm_api.stopVm(True, self.vm_name):
            raise errors.VMException("Failed to stop vm")

    @istest
    def run_once_vm_boot_from_different_devices(self):
        """
        Run once vm boot from different devices
        """
        boot_deices = [ENUMS['boot_sequence_cdrom'],
                       ENUMS['boot_sequence_network']]
        for boot_device in boot_deices:
            logger.info("Run once vm %s boot from %s",
                        self.vm_name, boot_device)
            if not vm_api.runVmOnce(True, self.vm_name,
                                    cdrom_image=config.CDROM_IMAGE_1,
                                    boot_dev=boot_device):
                raise errors.VMException("Failed to run vm")
            logger.info("Check if vm first boot device is correct")
            boot_list = vm_api.get_vm_boot_sequence(self.vm_name)
            self.assertTrue(boot_list[0] == boot_device)
            logger.info("Stop vm %s", self.vm_name)
            if not vm_api.stopVm(True, self.vm_name):
                raise errors.VMException("Failed to stop vm")

    @istest
    def run_once_vm_with_pause_and_change_cd(self):
        """
        Run once vm with "Start in paused" enables, and when vm in pause mode,
        change vm cd
        """
        logger.info("Run once vm %s in pause mode with attached cd",
                    self.vm_name)
        if not vm_api.runVmOnce(True, self.vm_name,
                                cdrom_image=config.CDROM_IMAGE_1,
                                pause='true'):
            raise errors.VMException("Failed to run vm")
        logger.info("Check if vm state is paused")
        self.assertTrue(vm_api.waitForVMState(self.vm_name,
                                              state=ENUMS['vm_state_paused']))
        logger.info("Change vm %s cd", self.vm_name)
        self.assertTrue(vm_api.changeCDWhileRunning(self.vm_name,
                                                    config.CDROM_IMAGE_2))
        logger.info("Stop vm %s", self.vm_name)
        if not vm_api.stopVm(True, self.vm_name):
            raise errors.VMException("Failed to stop vm")

    @attr(tier=1)
    @istest
    def run_once_vm_with_attached_floppy(self):
        """
        Run once vm with attached floppy
        """
        logger.info("Run once vm %s with attached floppy %s",
                    self.vm_name, config.FLOPPY_IMAGE)
        self.assertTrue(vm_api.runVmOnce(True, self.vm_name,
                                         floppy_image=config.FLOPPY_IMAGE,
                                         pause='true'))
        logger.info("Stop vm %s", self.vm_name)
        if not vm_api.stopVm(True, self.vm_name):
            raise errors.VMException("Failed to stop vm")


@attr(tier=0)
class VmPool(BaseVmWithDiskTemplate):
    """
    Basic test to check vm pools functionality
    """
    __test__ = True
    pool_name = 'vm_pool'
    template_name = 'template_for_vmpool'
    vm_name = 'vm_for_vmpool'
    new_vm_pool = 'new_vm_pool'
    new_vm = 'new_vm_pool-1'

    @tcms('13398', '366362')
    @istest
    def crud_vm_pool(self):
        """
        Create new pool, update and remove it
        """
        logger.info("Add new vm pool created from template %s",
                    self.template_name)
        self.assertTrue(vm_pool_api.addVmPool(True, name=self.pool_name,
                                              template=self.template_name,
                                              cluster=config.CLUSTER_NAME[0],
                                              size=2))
        logger.info("Add user role to vm pool %s", self.pool_name)
        self.assertTrue(
            addVmPoolPermissionToUser(True, user=config.USERNAME,
                                      vmpool=self.pool_name,
                                      role=ENUMS['role_name_user_role']))
        logger.info("Update vm pool %s with new parameters", self.pool_name)
        description = 'Pool Description'
        self.assertTrue(vm_pool_api.updateVmPool(True, self.pool_name,
                                                 name=self.new_vm_pool,
                                                 description=description,
                                                 size=3))
        # Following VM state check is essential for following actions
        logger.info("Verify added vm to pool, %s is in down state",
                    self.new_vm)
        self.assertTrue(vm_api.waitForVMState(vm=self.new_vm,
                                              state=ENUMS['vm_state_down'],
                                              timeout=VMPOOL_TIMEOUT))
        logger.info("Search for vms in vm pool %s", self.new_vm_pool)
        self.assertTrue(vm_api.searchForVm(True, query_key='name',
                                           query_val="%s*" % self.new_vm_pool,
                                           key_name='name'))
        logger.info("Search for vm pool %s", self.new_vm_pool)
        self.assertTrue(vm_pool_api.searchForVmPool(True,
                                                    query_key='description',
                                                    query_val='Pool*',
                                                    key_name='description'))
        logger.info("Negative: remove vm pool %s with attached vms",
                    self.new_vm_pool)
        self.assertFalse(vm_pool_api.removeVmPool(True, self.new_vm_pool))
        logger.info("Detach all vms from vm pool %s", self.new_vm_pool)
        vm_pool_api.detachVms(True, self.new_vm_pool)
        logger.info("Remove vm pool %s", self.new_vm_pool)
        vm_pool_api.removeVmPool(True, self.new_vm_pool)


@attr(tier=0)
class VmTemplate(BaseVmWithDiskTemplate):
    """
    Create vm from template with different parameters
    """
    __test__ = True
    vm_name = 'template_vm'
    template_name = 'basic_template'
    counter = 0

    @istest
    def create_vm_from_template(self):
        """
        Create vm from template
        """
        vm_name = 'new_template_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     cluster=config.CLUSTER_NAME[0],
                                     template=self.template_name))

    @istest
    def create_vm_from_template_with_specific_sd(self):
        """
        Create new vm with specified storage domain
        """
        vm_name = 'storage_template_vm'
        self.assertTrue(vm_api.addVm(True, name=vm_name,
                                     cluster=config.CLUSTER_NAME[0],
                                     template=self.template_name,
                                     storagedomain=config.STORAGE_NAME[0]))

    @bz({'1082977': {'engine': ['cli'], 'version': None}})
    @istest
    def create_vm_from_template_with_wrong_sd(self):
        """
        Negative: Create new vm with wrong storage domain
        """
        vm_name = 'storage_negative_vm'
        self.assertFalse(vm_api.addVm(True, name=vm_name,
                                      cluster=config.CLUSTER_NAME[0],
                                      template=self.template_name,
                                      storagedomain=config.STORAGE_NAME[1]))

    @istest
    def clone_vm_from_template(self):
        """
        Clone vm from template
        """
        vm_name = 'clone_vm'
        self.assertTrue(vm_api.cloneVmFromTemplate(True, vm_name,
                                                   self.template_name,
                                                   config.CLUSTER_NAME[0]))
