'''
Testing disk permissions feauture.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Testing if permissions are correctly assigned/removed/viewed on disks.
'''

__test__ = True

import logging
import time
import art.test_handler.exceptions as errors
from art.core_api.apis_exceptions import EntityNotFound

from rhevmtests.system.user_tests.mla import config, common
from rhevmtests.system.user_tests.mla.roles import role
from art.unittest_lib import attr, CoreSystemTest as TestCase

from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.rhevm_api.tests_lib.high_level import storagedomains
from art.rhevm_api.tests_lib.high_level import disks as h_disks
from art.rhevm_api.tests_lib.low_level import users, vms, disks, mla
from art.rhevm_api.tests_lib.low_level import storagedomains as low_sd
from art.rhevm_api.utils import test_utils


LOGGER = logging.getLogger(__name__)


def loginAsAdmin():
    users.loginAsUser(
        config.VDC_ADMIN_USER,
        config.VDC_ADMIN_DOMAIN,
        config.VDC_PASSWORD,
        filter=False
    )


def setUpModule():
    common.addUser(True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)
    if not config.GOLDEN_ENV:
        storagedomains.addNFSDomain(
            config.HOSTS[0],
            config.STORAGE_NAME[1],
            config.DC_NAME[0],
            config.ADDRESS[1],
            config.PATH[1],
        )


def tearDownModule():
    loginAsAdmin()
    common.removeUser(True, config.USER_NAME)
    if not config.GOLDEN_ENV:
        test_utils.wait_for_tasks(
            config.VDC_HOST,
            config.VDC_ROOT_PASSWORD,
            config.DC_NAME[0],
        )
        storagedomains.remove_storage_domain(
            config.STORAGE_NAME[1],
            config.DC_NAME[0],
            config.HOSTS[0],
        )


@attr(tier=2)
class DPCase147121(TestCase):
    """
    Check if SD has assigned permissions, then all disks in SD has inherit
    these permissions, Also check if disks is attached to VM, then disks,
    of vm inherit vm's permissions.
    """
    __test__ = True

    def setUp(self):
        disks.addDisk(
            True, alias=config.DISK_NAME, interface='virtio',
            format='cow', provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE
        )
        disks.wait_for_disks_status(config.DISK_NAME)
        mla.addStoragePermissionsToUser(
            True, config.USER_NAME, config.MASTER_STORAGE,
            role=role.DiskOperator
        )
        vms.createVm(
            True, config.VM_NO_DISK, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NO_DISK)

    @polarion("RHEVM3-7613")
    def test_diskInheritedPermissions(self):
        """ Check inheritance of disk permissions """
        # Check inheritance from SD
        self.assertTrue(
            mla.hasUserPermissionsOnObject(
                config.USER1, disks.DISKS_API.find(config.DISK_NAME),
                role=role.DiskOperator
            ),
            "Permissions from SD was not delegated to disk."
        )
        LOGGER.info("Disk inherit permissions from SD.")
        # Check inheritance from vm
        disk_name = "%s%s" % (config.VM_NO_DISK, '_Disk1')
        self.assertTrue(
            vms.addDisk(
                True, config.VM_NO_DISK, config.GB,
                storagedomain=config.MASTER_STORAGE,
                interface='virtio', format='cow'
            ),
            "Unable to attach disk to vm."
        )
        self.assertTrue(
            mla.hasUserPermissionsOnObject(
                config.USER1, disks.DISKS_API.find(disk_name),
                role=role.UserVmManager
            ),
            "Permissions from vm was not delegated to disk."
        )
        LOGGER.info("Disk inherit permissions from vm.")

    def tearDown(self):
        vms.removeVm(True, config.VM_NO_DISK)
        h_disks.delete_disks([config.DISK_NAME])
        mla.removeUserPermissionsFromSD(
            True, config.MASTER_STORAGE, config.USER1
        )


@attr(tier=2)
class DPCase14722_2(TestCase):
    """
    User should not be able to create disk if he has not create disk AG
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        mla.addStoragePermissionsToUser(
            True, config.USER_NAME, config.MASTER_STORAGE, role=role.UserRole
        )
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )

    @polarion("RHEVM3-12079")
    def test_createDiskWithoutPermissions(self):
        """ Create disk without permissions """
        # Check if user has not StorageAdmin perms on SD he can't create Disk
        self.assertTrue(
            disks.addDisk(
                False, alias=config.DISK_NAME, interface='virtio',
                format='cow', provisioned_size=config.GB,
                storagedomain=config.MASTER_STORAGE
            ),
            "User without StorageAdmin permissions can create disk."
        )
        LOGGER.info("User without StorageAdmin perms on SD can't create disk.")

    def tearDown(self):
        loginAsAdmin()
        try:
            h_disks.delete_disks([config.DISK_NAME])
        except EntityNotFound:
            pass
        mla.removeUserPermissionsFromSD(
            True, config.MASTER_STORAGE, config.USER1
        )


@attr(tier=2)
class DPCase147122(TestCase):
    """
    If user want create disks, he needs to have permissions on SD.
    Try to assign permissions on SD and create disk
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        mla.addStoragePermissionsToUser(
            True, config.USER_NAME, config.MASTER_STORAGE,
            role=role.StorageAdmin
        )

    def setUp(self):
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=False
        )

    @polarion("RHEVM3-7625")
    def test_createDisk(self):
        """ Create disk with permissions """
        # Check if user has StorageAdmin perms on SD he can create Disk
        self.assertTrue(
            disks.addDisk(
                True, alias=config.DISK_NAME, interface='virtio',
                format='cow', provisioned_size=config.GB,
                storagedomain=config.MASTER_STORAGE
            ),
            "User with StorageAdmin permissions can't create disk."
        )
        h_disks.delete_disks([config.DISK_NAME])
        LOGGER.info("User with StorageAdmin perms on SD can create disk.")

    def tearDown(self):
        # Remove permissions from SD
        loginAsAdmin()
        if disks.checkDiskExists(True, config.DISK_NAME):
            h_disks.delete_disks([config.DISK_NAME])
        mla.removeUserPermissionsFromSD(
            True, config.MASTER_STORAGE, config.USER1
        )


@attr(tier=2)
class DPCase147123(TestCase):
    """ General subcalss for TestCase 147123 """
    __test__ = False
    disk_role = None
    vm_role = None
    pos = None

    def setUp(self):
        disks.addDisk(
            True, alias=config.DISK_NAME, interface='virtio',
            format='cow', provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE
        )
        disks.wait_for_disks_status(config.DISK_NAME)
        mla.addStoragePermissionsToUser(
            True, config.USER_NAME, config.MASTER_STORAGE, role=self.disk_role
        )
        vms.createVm(
            True, config.VM_NO_DISK, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NO_DISK, role=self.vm_role
        )

    @polarion("RHEVM3-7626")
    def test_attachDiskToVM(self):
        """ Attach disk to vm """
        # Attach disk need perm on disk and on VM.
        msg = (
            'User with UserVmManager on vm and DiskOperator on disk can'
            'attach disk.'
        )
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            disks.attachDisk(
                self.pos, config.DISK_NAME, config.VM_NO_DISK
            ),
            "Unable to attach disk to vm."
        )
        LOGGER.info(msg)

    def tearDown(self):
        loginAsAdmin()
        h_disks.delete_disks([config.DISK_NAME])
        vms.removeVm(True, config.VM_NO_DISK)
        mla.removeUserPermissionsFromSD(
            True, config.MASTER_STORAGE, config.USER1
        )


class DPCase147123_1(DPCase147123):
    """
    User should not be able to attach disk to vm if he has not perms on vm
    """
    __test__ = True
    disk_role = role.DiskOperator
    vm_role = role.UserRole
    pos = False


class DPCase147123_2(DPCase147123):
    """
    User should not be able to attach disk to vm if he has not perms on disk
    """
    __test__ = True
    disk_role = role.UserRole
    vm_role = role.UserVmManager
    pos = False


class DPCase147123_3(DPCase147123):
    """
    In order to be able to attach disk to VM user must have a permission on
    disk and an appropriate permission on VM.
    """
    __test__ = True
    disk_role = role.DiskOperator
    vm_role = role.UserVmManager
    pos = True


@attr(tier=2)
class DPCase147124(TestCase):
    """
    General case for detach disk
    """
    __test__ = False
    tested_role = None
    pos = None

    def setUp(self):
        self.disk_name = '%s%s' % (config.VM_NAME, '_Disk1')
        vms.createVm(
            True, config.VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NAME, role=self.tested_role
        )

    @polarion("RHEVM3-7627")
    def test_detachDisk(self):
        """ Detach disk from vm """
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            disks.detachDisk(
                self.pos, self.disk_name, config.VM_NAME
            ),
            "User with UserVmManager can't detach disk from VM."
        )
        LOGGER.info("User who has UserVmManager perms on vm can detach disk.")

    def tearDown(self):
        loginAsAdmin()
        h_disks.delete_disks([self.disk_name])
        vms.removeVm(True, config.VM_NAME)


class DPCase147124_1(DPCase147124):
    """
    Detach disk from VM requires permissions on the VM only.
    """
    __test__ = True
    tested_role = role.UserVmManager
    pos = True


class DPCase147124_2(DPCase147124):
    """
    Negative: Detach disk from VM requires permissions on the VM only.
    """
    __test__ = True
    tested_role = role.UserRole
    pos = False


@attr(tier=2)
class DPCase147125(TestCase):
    """
    To activate/deactivate user must have an manipulate permissions on VM.
    """
    __test__ = True

    def setUp(self):
        self.disk_name = '%s%s' % (config.VM_NAME, '_Disk1')
        vms.createVm(
            True, config.VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME)

    @polarion("RHEVM3-7628")
    def test_activateDeactivateDisk(self):
        """ ActivateDeactivateDisk """
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            vms.deactivateVmDisk(
                True, config.VM_NAME, diskAlias=self.disk_name
            ),
            "User with UserVmManager role can't deactivate vm disk"
        )
        LOGGER.info("User with UserVmManager perms can deactivate vm disk.")
        self.assertTrue(
            vms.activateVmDisk(
                True, config.VM_NAME, diskAlias=self.disk_name
            ),
            "User with UserVmManager role can't activate vm disk"
        )
        LOGGER.info("User with UserVmManager permissions can active vm disk.")

    def tearDown(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME)


@attr(tier=2)
class DPCase147126(TestCase):
    """
    User has to have delete_disk action group in order to remove disk.
    """
    __test__ = True

    def setUp(self):
        disks.addDisk(
            True, alias=config.DISK_NAME, interface='virtio',
            format='cow', provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE
        )
        disks.wait_for_disks_status(config.DISK_NAME)
        mla.addStoragePermissionsToUser(
            True, config.USER_NAME, config.MASTER_STORAGE, role=role.UserRole
        )

    @polarion("RHEVM3-7629")
    def test_removeDisk(self):
        """ Remove disk as user with and without permissions """
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            disks.deleteDisk(False, config.DISK_NAME),
            "User without delete_disk action group can remove disk."
        )
        LOGGER.info("User without delete_disk action group can't remove disk.")

        loginAsAdmin()
        mla.addStoragePermissionsToUser(
            True, config.USER_NAME, config.MASTER_STORAGE,
            role=role.DiskOperator
        )
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            disks.deleteDisk(True, config.DISK_NAME),
            "User with delete_disk action group can't remove disk."
        )
        LOGGER.info("User with delete_disk action group can remove disk.")

    def tearDown(self):
        loginAsAdmin()
        if disks.checkDiskExists(True, config.DISK_NAME):
            disks.deleteDisk(True, config.DISK_NAME)
        disks.waitForDisksGone(True, config.DISK_NAME)
        mla.removeUserPermissionsFromSD(
            True, config.MASTER_STORAGE, config.USER1
        )


@attr(tier=2)
class DPCase147127(TestCase):
    """
    User has to have edit_disk_properties action group in order to remove disk.
    """
    __test__ = True

    def setUp(self):
        self.disk_name = '%s%s' % (config.VM_NAME, '_Disk1')
        vms.createVm(
            True, config.VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME)

    @polarion("RHEVM3-7630")
    def test_updateVmDisk(self):
        """ Update vm disk """
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            vms.updateVmDisk(
                True, config.VM_NAME, self.disk_name, interface='ide'
            ),
            "User can't update vm disk."
        )
        LOGGER.info("User can update vm disk.")

    def tearDown(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME)


@attr(tier=2)
class DPCase147128(TestCase):
    """
    Move or copy disk requires permissions on the disk and on the target sd.
    """
    __test__ = True

    def setUp(self):
        self.disk_name = '%s%s' % (config.VM_NAME, '_Disk1')
        vms.createVm(
            True, config.VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NAME, role=role.StorageAdmin
        )

    @polarion("RHEVM3-7631")
    @bz({'1209505': {}})
    def test_moveDisk(self):
        """ Move disk with and without having permissions on sds """
        # Move disk without permissions
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=False
        )

        try:
            vms.move_vm_disk(
                config.VM_NAME, self.disk_name, config.STORAGE_NAME[1]
            )
        except errors.DiskException:
            LOGGER.info("User without perms on sds can't move disk.")
        # Move disk with permissions only on destination sd
        loginAsAdmin()
        mla.addStoragePermissionsToUser(
            True, config.USER_NAME, config.MASTER_STORAGE,
            role=role.StorageAdmin
        )
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=False
        )
        try:
            vms.move_vm_disk(
                config.VM_NAME, self.disk_name, config.STORAGE_NAME[1]
            )
        except errors.DiskException:
            LOGGER.info("User without perms on target sd can't move disk.")

        # Move disk with permissions on both sds
        loginAsAdmin()
        mla.addStoragePermissionsToUser(
            True, config.USER_NAME, config.STORAGE_NAME[1],
            role=role.DiskCreator
        )

        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=False
        )
        vms.move_vm_disk(
            config.VM_NAME, self.disk_name,
            config.STORAGE_NAME[1]
        )
        time.sleep(5)
        disks.wait_for_disks_status(self.disk_name)
        test_utils.wait_for_tasks(
            config.VDC_HOST, config.VDC_ROOT_PASSWORD, config.DC_NAME[0]
        )
        LOGGER.info("User with perms on target sd and disk can move disk.")

    def tearDown(self):
        loginAsAdmin()
        low_sd.waitForStorageDomainStatus(
            True, config.DC_NAME[0], config.STORAGE_NAME[1], 'active'
        )
        h_disks.delete_disks([self.disk_name])
        vms.removeVm(True, config.VM_NAME)
        mla.removeUserPermissionsFromSD(
            True, config.MASTER_STORAGE, config.USER1
        )
        mla.removeUserPermissionsFromSD(
            True, config.STORAGE_NAME[1], config.USER1
        )
        test_utils.wait_for_tasks(
            config.VDC_HOST, config.VDC_ROOT_PASSWORD, config.DC_NAME[0]
        )


@attr(tier=2)
class DPCase147129(TestCase):
    """
    Add disk to VM requires both permissions on the VM and on the sd
    """
    __test__ = True

    def setUp(self):
        vms.createVm(
            True, config.VM_NO_DISK, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NO_DISK, role=role.UserRole
        )

    @polarion("RHEVM3-7632")
    @bz({'1209505': {}})
    def test_addDiskToVm(self):
        """ add disk to vm with and without permissions """
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            vms.addDisk(
                False, config.VM_NO_DISK, config.GB,
                storagedomain=config.MASTER_STORAGE,
                interface='virtio', format='cow'
            ),
            "UserRole can add disk to vm."
        )
        LOGGER.info("User without permissions on vm, can't add disk to vm.")

        loginAsAdmin()
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NO_DISK, role=role.UserVmManager
        )
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            vms.addDisk(
                False, config.VM_NO_DISK, config.GB,
                storagedomain=config.MASTER_STORAGE,
                interface='virtio', format='cow'
            ),
            "User without permissions on sd can add disk to vm."
        )
        LOGGER.info("User without permissions on sd, can't add disk to vm.")

        loginAsAdmin()
        mla.addStoragePermissionsToUser(
            True, config.USER_NAME, config.MASTER_STORAGE,
            role=role.DiskCreator
        )

        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            vms.addDisk(
                True, config.VM_NO_DISK, config.GB,
                storagedomain=config.MASTER_STORAGE,
                interface='virtio', format='cow'
            ),
            "User with permissions on sd and vm can't add disk to vm."
        )
        LOGGER.info("User with permissions on sd and vm, can add disk to vm.")

    def tearDown(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NO_DISK)
        mla.removeUserPermissionsFromSD(
            True, config.MASTER_STORAGE, config.USER1
        )


@attr(tier=2)
class DPCase147130(TestCase):
    """
    If disks are marked for deletion requires permissions on the removed
    disks and on the vm.
    """
    __test__ = True

    def setUp(self):
        vms.createVm(
            True, config.VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NAME, role=role.DiskOperator
        )
        mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.CLUSTER_NAME[0], role=role.UserRole
        )

    def tearDown(self):
        loginAsAdmin()
        vms.waitForVmsGone(True, config.VM_NAME)
        mla.removeUserPermissionsFromCluster(
            True, config.CLUSTER_NAME[0], config.USER1
        )

    @polarion("RHEVM3-7624")
    def test_removeVm(self):
        """ remove vm with disk without/with having apprirate permissions """
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            vms.removeVm(False, config.VM_NAME),
            "User can remove vm as DiskOperator."
        )
        LOGGER.info("User can't remove vm as DiskOperator.")

        loginAsAdmin()
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NAME, role=role.UserVmManager
        )

        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            vms.removeVm(True, config.VM_NAME, wait=False),
            "User can't remove vm as DiskOperator and UserVmManager on vm."
        )
        LOGGER.info("User can remove vm as UserVmManager, DiskOperator on vm")


@attr(tier=2)
class DPCase147137(TestCase):
    """
    Create/attach/edit/delete shared disk.
    """
    __test__ = True

    def setUp(self):
        disks.addDisk(
            True, alias=config.DISK_NAME, interface='virtio',
            format='raw', provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE,
            shareable=True
        )
        disks.wait_for_disks_status(config.DISK_NAME)
        mla.addStoragePermissionsToUser(
            True, config.USER_NAME, config.MASTER_STORAGE,
            role=role.DiskOperator
        )

        vms.createVm(
            True, config.VM_NO_DISK, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NO_DISK)

    @polarion("RHEVM3-7616")
    def test_sharedDisk(self):
        """ Basic operations with shared disk """
        users.loginAsUser(
            config.USER_NAME, config.PROFILE,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(
            disks.attachDisk(True, config.DISK_NAME, config.VM_NO_DISK),
            "Unable to attach disk to vm."
        )
        LOGGER.info("Shared disk was attached by user.")

        self.assertTrue(
            vms.updateVmDisk(
                True, config.VM_NO_DISK, config.DISK_NAME, interface='ide'
            ),
            "User can't update vm shared disk."
        )
        LOGGER.info("User can update vm shared disk.")

        self.assertTrue(
            disks.deleteDisk(True, config.DISK_NAME),
            "User can't remove shared disk."
        )
        LOGGER.info("User can remove shared disk.")

    def tearDown(self):
        loginAsAdmin()
        disks.waitForDisksGone(True, config.DISK_NAME)
        vms.removeVm(True, config.VM_NO_DISK),
        mla.removeUserPermissionsFromSD(
            True, config.MASTER_STORAGE, config.USER1
        )
