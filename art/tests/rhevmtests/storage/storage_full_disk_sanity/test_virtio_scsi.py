"""
Virtio iSCSI Test suit
"""
from concurrent.futures.thread import ThreadPoolExecutor
from art.unittest_lib import StorageTest as TestCase, attr
from art.rhevm_api.tests_lib.high_level.vms import add_disk_to_machine
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    findMasterStorageDomain)
from art.rhevm_api.tests_lib.low_level.templates import createTemplate, \
    removeTemplate
from art.rhevm_api.tests_lib.low_level.vms import (
    createVm,
    stopVm,
    removeVm,
    checkVmState,
    startVm,
    waitForIP,
    migrateVm,
    cloneVmFromTemplate,
    addSnapshot,
    addVm,
    waitForVmsDisks,
    getVmHost)
from art.rhevm_api.utils.test_utils import setPersistentNetwork
from art.test_handler.tools import tcms, bz
import config
import logging


logger = logging.getLogger(__name__)
TCMS_PLAN_ID = '9456'

# Use specfic test config here | move to config
VM_NAMES = ["ful_disk_vm", ]
DISK_SIZE = 10 * config.GB
MAX_WORKERS = 10


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
        'volumeFormat': config.ENUMS['format_cow'],
        'cluster': config.CLUSTER_NAME,
        'storageDomainName': storage_domain,
        'installation': install_os,
        'size': DISK_SIZE
    }

    if install_os:
        vmArgs.update({
            'nic': 'nic1',
            'image': config.COBBLER_PROFILE,
            'useAgent': True,
            'os_type': config.ENUMS['rhel6'],
            'user': config.VMS_LINUX_USER,
            'password': config.VMS_LINUX_PW
        })

    logger.info('Creating vm %s', vm_name)
    assert createVm(**vmArgs)

    if install_os:
        vm_ip = waitForIP(vm=vm_name)[1]['ip']
        logger.info('Got IP %s for vm %s', vm_ip, vm_name)
        logger.info('Setting persistent network on vm %s', vm_name)
        assert setPersistentNetwork(vm_ip, config.VMS_LINUX_PW)
        logger.info('Stopping vm %s', vm_name)
        assert stopVm(True, vm_name)


class ClassWithOneVM(TestCase):
    """
    Base test class that ensures master domain is active and creates
    vms as specificied in vm_names with interfaces per disk
    """

    __test__ = False
    vm_names = VM_NAMES
    disk_interfaces = [config.VIRTIO_SCSI]
    installations = [True]
    master_domain = None

    @classmethod
    def setup_class(cls):
        logger.info('Finding master domain name')
        master_domain = findMasterStorageDomain(True, config.DATA_CENTER_NAME)
        assert master_domain[0]
        cls.master_domain = master_domain[1]['masterDomain']
        assert cls.master_domain
        logger.info('Found master domain: %s', cls.master_domain)

        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            logger.info('Creating all vms: %s', cls.vm_names)
            for vm, disk_interface, installation in zip(cls.vm_names,
                                                        cls.disk_interfaces,
                                                        cls.installations):
                results.append(executor.submit(_create_vm,
                                               vm,
                                               cls.master_domain,
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


# TBD: Remove this when is implemented in the main story, storage sanity
# http://rhevm-qe-storage.pad.engineering.redhat.com/11?
# class TestCase272386(ClassWithOneVM):
#     """
#     TCMS test case 272386 - Create vm with virtio-scsi bootable disk
#     Test creates a vm with a single virtio-scsi disk as bootable disk
#     and installs an OS on the vm
#
#     https://tcms.engineering.redhat.com/case/272386/?from_plan=9456
#     """


@attr(tier=0)
class TestCase272383(ClassWithOneVM):
    """
    TCMS test case 272383 - Create template from vm with virtio-scsi disk
    Test creates a vm with virtio-scsi disk, installs OS, creates template
    from the vm and then creates a new vm from the template.
    """

    cloned_vm_name = None
    tcms_case = '272383'

    __test__ = True

    @classmethod
    def setup_class(cls):
        super(TestCase272383, cls).setup_class()
        logger.info('Adding virtio disk to vm %s', cls.vm_names[0])
        add_disk_to_machine(cls.vm_names[0],
                            config.VIRTIO_SCSI,
                            config.ENUMS['format_cow'],
                            True,
                            storage_domain=cls.master_domain)
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


# TBD: Remove this when is implemented in the main story, storage sanity
# http://rhevm-qe-storage.pad.engineering.redhat.com/11?
# class TestCase272390(ClassWithOneVM):
#     """
#     TCMS case 272390 - Remove vm with virtio-scsi disk
#     Attempt to remove vm with virtio-scsi disk
#
#     https://tcms.engineering.redhat.com/case/272390/?from_plan=9456
#     """
#
@attr(tier=0)
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
        assert startVm(True, cls.vm_names[0], wait_for_ip=True)
        logger.info('Checking which host vm is currently running on')
        status, vm_host = getVmHost(cls.vm_names[0])
        assert status

    @tcms(TCMS_PLAN_ID, tcms_case)
    @bz('996146')
    def test_migrate_vm_with_virtio_scsi_disk(self):
        """
        Migrate a vm from the host it is currently running on to another host
        """
        logger.info('Migrating VM %s', self.vm_names[0])
        self.assertTrue(migrateVm(True, self.vm_names[0]),
                        'Error during migration of vm %s' % self.vm_names[0])


@attr(tier=0)
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
    @bz('1003523')
    def test_clone_vm_with_virtio_scsi_disk_from_snapshot(self):
        """
        Clones a vm from a snapshot that has a virtio-scsi disk
        """
        logger.info('Cloning vm %s from snapshot %s',
                    self.vm_names[0], self.snapshot_name)
        self.assertTrue(addVm(True,
                              name=self.cloned_vm_name,
                              description=self.cloned_vm_name,
                              snapshot=self.snapshot_name,
                              cluster=config.CLUSTER_NAME))
        self.vm_names.append(self.cloned_vm_name)
        self.assertTrue(waitForVmsDisks(self.cloned_vm_name))
        logger.info('Vm %s cloned. Starting it', self.cloned_vm_name)
        self.assertTrue(startVm(True, self.cloned_vm_name, wait_for_ip=True))


@attr(tier=0)
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
                            cls.master_domain)

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
