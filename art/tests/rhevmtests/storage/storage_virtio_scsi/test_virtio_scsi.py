from concurrent.futures.thread import ThreadPoolExecutor
from art.unittest_lib import attr
from art.unittest_lib import StorageTest as TestCase
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.high_level.vms import add_disk_to_machine
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType, cleanDataCenter,
)
from art.rhevm_api.tests_lib.low_level.templates import (
    createTemplate, removeTemplate,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    createVm, stopVm, removeVm, checkVmState, getVmHost, startVm, waitForIP,
    migrateVm, cloneVmFromTemplate, addSnapshot, waitForVmsDisks,
    getVmDisks, cloneVmFromSnapshot,
)
from art.rhevm_api.tests_lib.low_level.disks import getStorageDomainDisks
from art.rhevm_api.utils.test_utils import setPersistentNetwork
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
import config
import logging


logger = logging.getLogger(__name__)
TCMS_PLAN_ID = '9456'


def setup_module():
    """
    Build setup accoridng to conf file
    """
    if not config.GOLDEN_ENV:
        build_setup(config.PARAMETERS,
                    config.PARAMETERS,
                    config.STORAGE_TYPE,
                    config.TESTNAME)


def teardown_module():
    """
    Clean datacenter
    """
    if not config.GOLDEN_ENV:
        cleanDataCenter(True,
                        config.DATA_CENTER_NAME,
                        vdc=config.VDC,
                        vdc_password=config.VDC_PASSWORD)


def _create_vm(vm_name, storage_domain, interface, install_os):
    """
    Description: creates a vm in the given storage domain with a disk of a
    specific interface. installs os if install_os is True
    Parameters:
        * vm_name: name of the vm_name
        * storage_domain: storage domain name on which disk will be created
        * interface: interface of disk (virtio-blk, virtio-scsi, ide)
        * install_os: True to install_os
    """

    vmArgs = {
        'positive': True,
        'vmName': vm_name,
        'vmDescription': vm_name,
        'diskInterface': interface,
        'volumeFormat': config.DISK_FORMAT_COW,
        'cluster': config.CLUSTER_NAME,
        'storageDomainName': storage_domain,
        'installation': install_os,
        'size': config.DISK_SIZE
    }

    if install_os:
        vmArgs.update({
            'nic': config.NIC_NAME[0],
            'image': config.COBBLER_PROFILE,
            'useAgent': True,
            'os_type': config.ENUMS['rhel6'],
            'user': config.VM_USER,
            'password': config.VM_PASSWORD,
            'network': config.MGMT_BRIDGE,
        })

    logger.info('Creating vm %s', vm_name)
    assert createVm(**vmArgs)

    if install_os:
        vm_ip = waitForIP(vm=vm_name)[1]['ip']
        logger.info('Got IP %s for vm %s', vm_ip, vm_name)
        logger.info('Setting persistent network on vm %s', vm_name)
        assert setPersistentNetwork(vm_ip, config.VM_PASSWORD)
        logger.info('Stopping vm %s', vm_name)
        assert stopVm(True, vm_name)


class ClassWithOneVM(TestCase):
    """
    Base test class that ensures master domain is active and creates
    vms as specificied in vm_names with interfaces per disk
    """

    __test__ = True
    disk_interfaces = [config.VIRTIO_SCSI]
    installations = [True]
    storage_domain = None

    @classmethod
    def setup_class(cls):
        cls.vm_names = [config.VM_NAMES[0]]
        cls.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]

        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            logger.info('Creating all vms: %s', cls.vm_names)
            for vm, disk_interface, installation in zip(cls.vm_names,
                                                        cls.disk_interfaces,
                                                        cls.installations):
                results.append(executor.submit(_create_vm,
                                               vm,
                                               cls.storage_domain,
                                               disk_interface,
                                               installation))

        for result in results:
            exception = result.exception()
            if exception is not None:
                raise exception
        logger.info('All vms created')

    @classmethod
    def teardown_class(cls):
        logger.info('Removing vms: %s', cls.vm_names)
        for vm in cls.vm_names:
            if checkVmState(True, vm, config.ENUMS['vm_state_up']):
                logger.info('Stopping vm %s', vm)
                assert stopVm(True, vm)
            logger.info('Removing vm %s', vm)
            assert removeVm(True, vm)


@attr(tier=0)
class TestCase272386(ClassWithOneVM):
    """
    TCMS test case 272386 - Create vm with virtio-scsi bootable disk
    Test creates a vm with a single virtio-scsi disk as bootable disk
    and installs an OS on the vm

    https://tcms.engineering.redhat.com/case/272386/?from_plan=9456
    """

    __test__ = True
    vm_name = config.VM_NAMES[0]
    tcms_case = '272386'

    @classmethod
    def setup_class(cls):
        cls.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]
        cls.vm_names = []

    @tcms(TCMS_PLAN_ID, tcms_case)
    def test_start_vm_with_virtio_scsi_bootable_disk_and_remove_it(self):
        """
        Description: Create a vm with virtio-scsi disk as bootable device,
        install OS on it, check that OS boots and remove it
        """

        logger.info('Creating vm with virtio-scsi disk as bootable device')
        self.vm_names.append(self.vm_name)
        _create_vm(self.vm_name, self.storage_domain, config.VIRTIO_SCSI, True)
        logger.info('vm with virtio-scsi boot disk created successfully')

        vm_disks = [disk.get_id() for disk in getVmDisks(self.vm_name)]
        disks_before_removal = getStorageDomainDisks(
            self.storage_domain, False)
        disks_before_removal = [disk.get_id() for disk in disks_before_removal]
        logger.info('Removing vm %s', self.vm_name)
        self.assertTrue(removeVm(True, self.vm_name), "Failed to remove vm "
                                                      "%s" % self.vm_name)
        self.vm_names.pop(0)
        logger.info('Ensuring no disks remain')
        disks_after_removal = getStorageDomainDisks(self.storage_domain, False)
        disks_after_removal = [disk.get_id() for disk in disks_after_removal]
        self.assertEqual(
            disks_after_removal,
            [disk for disk in disks_before_removal if disk not in vm_disks],
            'found disks on storage domain: %s' % vm_disks
        )


@attr(tier=1)
class TestCase272383(ClassWithOneVM):
    """
    TCMS test case 272383 - Create template from vm with virtio-scsi disk
    Test creates a vm with virtio-scsi disk, installs OS, creates template
    from the vm and then creates a new vm from the template.
    """
    cloned_vm_name = None
    tcms_case = 272386

    __test__ = True

    @classmethod
    def setup_class(cls):
        super(TestCase272383, cls).setup_class()
        logger.info('Adding virtio disk to vm %s', cls.vm_names[0])
        add_disk_to_machine(cls.vm_names[0],
                            config.VIRTIO_SCSI,
                            config.ENUMS['format_cow'],
                            True,
                            storage_domain=cls.storage_domain)
        cls.cloned_vm_name = cls.vm_names[0] + '_cloned'
        cls.vm_names.append(cls.cloned_vm_name)

    @tcms(TCMS_PLAN_ID, tcms_case)
    def test_create_template_from_vm_with_virtio_scsi_disk(self):
        """
        Description: Create a template from existing vm that has virtio-scsi
        disk and then create vm from template
        """
        templateArgs = {
            'positive': True,
            'name': config.TEMPLATE_NAME,
            'vm': self.vm_names[0],
        }
        logger.info('Creating template %s from vm %s',
                    config.TEMPLATE_NAME, self.vm_names[0])
        self.assertTrue(createTemplate(**templateArgs),
                        'Error creating template %s from vm %s' %
                        (config.TEMPLATE_NAME, self.vm_names[0]))
        logger.info('Creating new vm %s from template %s',
                    self.cloned_vm_name, config.TEMPLATE_NAME)
        self.assertTrue(cloneVmFromTemplate(True,
                                            self.cloned_vm_name,
                                            config.TEMPLATE_NAME,
                                            config.CLUSTER_NAME),
                        'Error when cloning vm %s from template %s' %
                        (self.cloned_vm_name, config.TEMPLATE_NAME))
        logger.info('VM %s cloned. Starting it...', self.cloned_vm_name)
        self.assertTrue(startVm(True, self.cloned_vm_name, wait_for_ip=True),
                        'Error when booting vm %s' % self.cloned_vm_name)

    @classmethod
    def teardown_class(cls):
        super(TestCase272383, cls).teardown_class()
        logger.info('removing template %s', config.TEMPLATE_NAME)
        assert removeTemplate(True, config.TEMPLATE_NAME)


@attr(tier=1)
class TestCase272388(ClassWithOneVM):
    """
    TCMS case 272388 - Migrate a vm with virtio-scsi disk

    https://tcms.engineering.redhat.com/case/272388/?from_plan=9456
    """

    vm_names = ['migratable_vm']
    tcms_case = '272388'

    __test__ = True

    @classmethod
    def setup_class(cls):
        super(TestCase272388, cls).setup_class()
        logger.info('Starting vm %s', cls.vm_names[0])
        assert startVm(True, cls.vm_names[0])
        logger.info('Waiting for OS to boot')
        assert waitForIP(cls.vm_names[0])
        logger.info('Checking which host vm is currently running on')
        status, vm_host = getVmHost(cls.vm_names[0])
        assert status

    @tcms(TCMS_PLAN_ID, tcms_case)
    def test_migrate_vm_with_virtio_scsi_disk(self):
        """
        Migrate a vm from the host it is currently running on to another host
        """
        logger.info('Migrating VM %s', self.vm_names[0])
        self.assertTrue(migrateVm(True, self.vm_names[0]),
                        'Error during migration of vm %s' % self.vm_names[0])


@attr(tier=1)
class TestCase272914(ClassWithOneVM):
    """
    TCMS case 272914 - Clone VM from virtio scsi disk

    Creates a vm with virtio-scsi disk, installs OS on it and creates a
    snapshot. Then attempts to clone a vm from the snapshot

    https://tcms.engineering.redhat.com/case/272914/?from_plan=9456
    """

    __test__ = True
    tcms_case = '272914'
    snapshot_name = None
    cloned_vm_name = None

    @classmethod
    def setup_class(cls):
        super(TestCase272914, cls).setup_class()
        logger.info('Creating snapshot for vm %s', cls.vm_names[0])
        cls.snapshot_name = config.SNAPSHOT_NAME
        cls.cloned_vm_name = cls.vm_names[0] + '_cloned'
        assert addSnapshot(True, cls.vm_names[0], cls.snapshot_name)

    @tcms(TCMS_PLAN_ID, tcms_case)
    @bz({"1178508": {'engine': ['rest', 'sdk'], 'version': ['3.5']}})
    def test_clone_vm_with_virtio_scsi_disk_from_snapshot(self):
        """
        Clones a vm from a snapshot that has a virtio-scsi disk
        """
        logger.info('Cloning vm %s from snapshot %s',
                    self.vm_names[0], self.snapshot_name)

        self.assertTrue(cloneVmFromSnapshot(True,
                                            name=self.cloned_vm_name,
                                            cluster=config.CLUSTER_NAME,
                                            vm=self.vm_names[0],
                                            snapshot=self.snapshot_name))
        self.vm_names.append(self.cloned_vm_name)
        self.assertTrue(waitForVmsDisks(self.cloned_vm_name))
        logger.info('Vm %s cloned. Starting it', self.cloned_vm_name)
        self.assertTrue(startVm(True, self.cloned_vm_name, wait_for_ip=True))


@attr(tier=1)
class TestCase293163(ClassWithOneVM):
    """
    TCMS case 293163 - VM with both virtio-scsi and virtio-blk disks

    https://tcms.engineering.redhat.com/case/293163/?from_plan=9456
    """

    __test__ = True
    tcms_case = '293163'

    @classmethod
    def setup_class(cls):
        super(TestCase293163, cls).setup_class()
        logger.info('Adding virtio-blk disk to vm %s', cls.vm_names[0])
        add_disk_to_machine(cls.vm_names[0],
                            config.VIRTIO_BLK,
                            config.ENUMS['format_cow'],
                            True,
                            cls.storage_domain)

    @tcms(TCMS_PLAN_ID, tcms_case)
    def test_vm_with_virtio_and_virtio_scsi_disk(self):
        """
        Attempts to boot a vm that has both a virtio-scsi and a virtio-blk
        disk
        """
        logger.info('Starting vm %s and waiting for OS to boot',
                    self.vm_names[0])
        self.assertTrue(startVm(True, self.vm_names[0], wait_for_ip=True),
                        'Error when booting vm %s' % self.vm_names[0])
        # TODO check OS can access both disks?
