"""
Testing disk permissions feauture.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Testing if permissions are correctly assigned/removed/viewed on disks.
"""
import logging
import time
import pytest

import art.test_handler.exceptions as errors
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.high_level import (
    disks as hl_disks,
    storagedomains as hl_sd
)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sd,
    mla,
    vms
)
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import bz, polarion
from art.unittest_lib import attr

from rhevmtests.system.user_tests.mla import common, config

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup(request):
    def finalize():
        common.login_as_admin()

        common.remove_user(True, config.USER_NAMES[0])

        if not config.GOLDEN_ENV:
            test_utils.wait_for_tasks(
                config.VDC_HOST,
                config.VDC_ROOT_PASSWORD,
                config.DC_NAME[0],
            )
            hl_sd.remove_storage_domain(
                config.STORAGE_NAME[1],
                config.DC_NAME[0],
                config.HOSTS[0],
            )

    request.addfinalizer(finalize)

    common.add_user(
        True,
        user_name=config.USER_NAMES[0],
        domain=config.USER_DOMAIN
    )
    if not config.GOLDEN_ENV:
        hl_sd.addNFSDomain(
            config.HOSTS[0],
            config.STORAGE_NAME[1],
            config.DC_NAME[0],
            config.ADDRESS[1],
            config.PATH[1],
        )


@attr(tier=2)
class DPCase147121(common.BaseTestCase):
    """
    Check if SD has assigned permissions, then all disks in SD has inherit
    these permissions, Also check if disks is attached to VM, then disks,
    of vm inherit vm's permissions.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147121, cls).setup_class(request)

        def finalize():
            vms.removeVm(True, config.VM_NO_DISK)
            hl_disks.delete_disks([config.DISK_NAME])
            mla.removeUserPermissionsFromSD(
                True,
                config.MASTER_STORAGE,
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        ll_disks.addDisk(
            True,
            alias=config.DISK_NAME,
            interface='virtio',
            format='cow',
            provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE
        )
        ll_disks.wait_for_disks_status(config.DISK_NAME)
        mla.addStoragePermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.MASTER_STORAGE,
            role=config.role.DiskOperator
        )

        vms.createVm(
            positive=True,
            vmName=config.VM_NO_DISK,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NO_DISK
        )

    @polarion("RHEVM3-7613")
    def test_disk_inherited_permissions(self):
        """ Check inheritance of disk permissions """
        # Check inheritance from SD
        assert mla.hasUserPermissionsOnObject(
            config.USERS[0],
            ll_disks.DISKS_API.find(config.DISK_NAME),
            role=config.role.DiskOperator
        ), "Permissions from SD was not delegated to disk."
        logger.info("Disk inherit permissions from SD.")
        # Check inheritance from vm
        disk_name = "{0}{1}".format(config.VM_NO_DISK, "_Disk1")
        assert vms.addDisk(
            True,
            config.VM_NO_DISK,
            config.GB,
            storagedomain=config.MASTER_STORAGE,
            interface='virtio',
            format='cow'
        ), "Unable to attach disk to vm."
        assert mla.hasUserPermissionsOnObject(
            config.USERS[0],
            ll_disks.DISKS_API.find(disk_name),
            role=config.role.UserVmManager
        ), "Permissions from vm was not delegated to disk."
        logger.info("Disk inherit permissions from vm.")


@attr(tier=2)
class DPCase14722_2(common.BaseTestCase):
    """
    User should not be able to create disk if he has not create disk AG
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase14722_2, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            try:
                hl_disks.delete_disks([config.DISK_NAME])
            except EntityNotFound:
                pass
            mla.removeUserPermissionsFromSD(
                True,
                config.MASTER_STORAGE,
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        mla.addStoragePermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.MASTER_STORAGE,
            role=config.role.UserRole
        )
        common.login_as_user()

    @polarion("RHEVM3-12079")
    def test_create_disk_without_permissions(self):
        """ Create disk without permissions """
        # Check if user has not StorageAdmin perms on SD he can't create Disk
        assert ll_disks.addDisk(
            False,
            alias=config.DISK_NAME,
            interface='virtio',
            format='cow',
            provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE
        ), "User without StorageAdmin permissions can create disk."
        logger.info("User without StorageAdmin perms on SD can't create disk.")


@attr(tier=2)
class DPCase147122(common.BaseTestCase):
    """
    If user want create disks, he needs to have permissions on SD.
    Try to assign permissions on SD and create disk
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147122, cls).setup_class(request)

        def finalize():
            # Remove permissions from SD
            common.login_as_admin()
            if ll_disks.checkDiskExists(True, config.DISK_NAME):
                hl_disks.delete_disks([config.DISK_NAME])
            mla.removeUserPermissionsFromSD(
                True,
                config.MASTER_STORAGE,
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        mla.addStoragePermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.MASTER_STORAGE,
            role=config.role.StorageAdmin
        )

    @polarion("RHEVM3-7625")
    def test_create_disk(self):
        """ Create disk with permissions """
        # Check if user has StorageAdmin perms on SD he can create Disk
        common.login_as_user(filter_=False)
        assert ll_disks.addDisk(
            True,
            alias=config.DISK_NAME,
            interface='virtio',
            format='cow',
            provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE
        ), "User with StorageAdmin permissions can't create disk."
        hl_disks.delete_disks([config.DISK_NAME])
        logger.info("User with StorageAdmin perms on SD can create disk.")


@attr(tier=2)
class DPCase147123(common.BaseTestCase):
    """ General subcalss for TestCase 147123 """
    __test__ = False

    disk_role = None
    vm_role = None
    pos = None

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147123, cls).setup_class(request)

        def finalize():
            common.login_as_admin()

            hl_disks.delete_disks([config.DISK_NAME])

            vms.removeVm(True, config.VM_NO_DISK, wait=True)

            mla.removeUserPermissionsFromSD(
                True,
                config.MASTER_STORAGE,
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        ll_disks.addDisk(
            True,
            alias=config.DISK_NAME,
            interface='virtio',
            format='cow',
            provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE
        )
        ll_disks.wait_for_disks_status(config.DISK_NAME)

        mla.addStoragePermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.MASTER_STORAGE,
            role=cls.disk_role
        )

        vms.createVm(
            positive=True,
            vmName=config.VM_NO_DISK,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NO_DISK,
            role=cls.vm_role
        )

    @polarion("RHEVM3-7626")
    def test_attach_disk_to_vm(self):
        """ Attach disk to vm """
        # Attach disk need perm on disk and on VM.
        msg = (
            'User with UserVmManager on vm and DiskOperator on disk can'
            'attach disk.'
        )
        common.login_as_user()

        assert ll_disks.attachDisk(
            self.pos,
            config.DISK_NAME,
            config.VM_NO_DISK
        ), "Unable to attach disk to vm."
        logger.info(msg)


class DPCase147123_1(DPCase147123):
    """
    User should not be able to attach disk to vm if he has not perms on vm
    """
    __test__ = True

    disk_role = config.role.DiskOperator
    vm_role = config.role.UserRole
    pos = False


class DPCase147123_2(DPCase147123):
    """
    User should not be able to attach disk to vm if he has not perms on disk
    """
    __test__ = True

    disk_role = config.role.UserRole
    vm_role = config.role.UserVmManager
    pos = False


class DPCase147123_3(DPCase147123):
    """
    In order to be able to attach disk to VM user must have a permission on
    disk and an appropriate permission on VM.
    """
    __test__ = True
    disk_role = config.role.DiskOperator
    vm_role = config.role.UserVmManager
    pos = True


@attr(tier=2)
class DPCase147124(common.BaseTestCase):
    """
    General case for detach disk
    """
    __test__ = False
    tested_role = None
    positive = None

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147124, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            hl_disks.delete_disks([cls.disk_name])
            vms.removeVm(True, config.VM_NAME)

        request.addfinalizer(finalize)

        cls.disk_name = "{0}{1}".format(config.VM_NAME, "_Disk1")

        vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME,
            role=cls.tested_role
        )

    @polarion("RHEVM3-7627")
    def test_detach_disk(self):
        """ Detach disk from vm """
        common.login_as_user()
        assert ll_disks.detachDisk(
            self.positive,
            self.disk_name,
            config.VM_NAME
        ), "User with UserVmManager can't detach disk from VM."
        logger.info("User who has UserVmManager perms on vm can detach disk.")


class DPCase147124_1(DPCase147124):
    """
    Detach disk from VM requires permissions on the VM only.
    """
    __test__ = True
    tested_role = config.role.UserVmManager
    positive = True


class DPCase147124_2(DPCase147124):
    """
    Negative: Detach disk from VM requires permissions on the VM only.
    """
    __test__ = True
    tested_role = config.role.UserRole
    positive = False


@attr(tier=2)
class DPCase147125(common.BaseTestCase):
    """
    To activate/deactivate user must have an manipulate permissions on VM.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147125, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            vms.removeVm(True, config.VM_NAME)

        request.addfinalizer(finalize)

        cls.disk_name = "{0}{1}".format(config.VM_NAME, "_Disk1")

        vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        mla.addVMPermissionsToUser(True, config.USER_NAMES[0], config.VM_NAME)

    @polarion("RHEVM3-7628")
    def test_activate_deactivate_disk(self):
        """ Activate/Deactivate Disk """
        common.login_as_user()
        assert vms.deactivateVmDisk(
            True,
            config.VM_NAME,
            diskAlias=self.disk_name
        ), "User with UserVmManager role can't deactivate vm disk"
        logger.info("User with UserVmManager perms can deactivate vm disk.")

        assert vms.activateVmDisk(
            True,
            config.VM_NAME,
            diskAlias=self.disk_name
        ), "User with UserVmManager role can't activate vm disk"
        logger.info("User with UserVmManager permissions can active vm disk.")


@attr(tier=2)
class DPCase147126(common.BaseTestCase):
    """
    User has to have delete_disk action group in order to remove disk.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147126, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            if ll_disks.checkDiskExists(True, config.DISK_NAME):
                ll_disks.deleteDisk(True, config.DISK_NAME)
            ll_disks.waitForDisksGone(True, config.DISK_NAME)
            mla.removeUserPermissionsFromSD(
                True,
                config.MASTER_STORAGE,
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        ll_disks.addDisk(
            True,
            alias=config.DISK_NAME,
            interface='virtio',
            format='cow',
            provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE
        )
        ll_disks.wait_for_disks_status(config.DISK_NAME)
        mla.addStoragePermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.MASTER_STORAGE,
            role=config.role.UserRole
        )

    @polarion("RHEVM3-7629")
    def test_remove_disk(self):
        """ Remove disk as user with and without permissions """
        common.login_as_user()
        assert ll_disks.deleteDisk(
            False,
            config.DISK_NAME
        ), "User without delete_disk action group can remove disk."
        logger.info("User without delete_disk action group can't remove disk.")

        common.login_as_admin()
        mla.addStoragePermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.MASTER_STORAGE,
            role=config.role.DiskOperator
        )
        common.login_as_user()
        assert ll_disks.deleteDisk(
            True,
            config.DISK_NAME
        ), "User with delete_disk action group can't remove disk."
        logger.info("User with delete_disk action group can remove disk.")


@attr(tier=2)
class DPCase147127(common.BaseTestCase):
    """
    User has to have edit_disk_properties action group in order to remove disk.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147127, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            vms.removeVm(True, config.VM_NAME)

        request.addfinalizer(finalize)

        cls.disk_name = "{0}{1}".format(config.VM_NAME, "_Disk1")

        vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        mla.addVMPermissionsToUser(True, config.USER_NAMES[0], config.VM_NAME)

    @polarion("RHEVM3-7630")
    def test_update_vm_disk(self):
        """ Update vm disk """
        common.login_as_user()
        assert ll_disks.updateDisk(
            True,
            vmName=config.VM_NAME,
            alias=self.disk_name,
            interface='ide'
        ), "User can't update vm disk."
        logger.info("User can update vm disk.")


@attr(tier=2)
class DPCase147128(common.BaseTestCase):
    """
    Move or copy disk requires permissions on the disk and on the target sd.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147128, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            ll_sd.waitForStorageDomainStatus(
                True,
                config.DC_NAME[0],
                config.STORAGE_NAME[1],
                'active'
            )
            hl_disks.delete_disks([cls.disk_name])
            vms.removeVm(True, config.VM_NAME)
            mla.removeUserPermissionsFromSD(
                True,
                config.MASTER_STORAGE,
                config.USERS[0]
            )
            mla.removeUserPermissionsFromSD(
                True,
                config.STORAGE_NAME[1],
                config.USERS[0]
            )
            test_utils.wait_for_tasks(
                config.VDC_HOST,
                config.VDC_ROOT_PASSWORD,
                config.DC_NAME[0]
            )

        request.addfinalizer(finalize)

        cls.disk_name = "{0}{1}".format(config.VM_NAME, "_Disk1")

        vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME,
            role=config.role.StorageAdmin
        )

    @polarion("RHEVM3-7631")
    @bz({'1209505': {}})
    def test_move_disk(self):
        """ Move disk with and without having permissions on sds """
        # Move disk without permissions
        common.login_as_user(filter_=False)
        try:
            vms.move_vm_disk(
                config.VM_NAME,
                self.disk_name,
                config.STORAGE_NAME[1]
            )
        except errors.DiskException:
            logger.info("User without perms on sds can't move disk.")
        # Move disk with permissions only on destination sd
        common.login_as_admin()
        mla.addStoragePermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.MASTER_STORAGE,
            role=config.role.StorageAdmin
        )
        common.login_as_user(filter_=False)
        try:
            vms.move_vm_disk(
                config.VM_NAME,
                self.disk_name,
                config.STORAGE_NAME[1]
            )
        except errors.DiskException:
            logger.info("User without perms on target sd can't move disk.")

        # Move disk with permissions on both sds
        common.login_as_admin()
        mla.addStoragePermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.STORAGE_NAME[1],
            role=config.role.DiskCreator
        )

        common.login_as_user(filter_=False)
        vms.move_vm_disk(
            config.VM_NAME,
            self.disk_name,
            config.STORAGE_NAME[1]
        )
        time.sleep(5)
        ll_disks.wait_for_disks_status([self.disk_name])
        test_utils.wait_for_tasks(
            config.VDC_HOST,
            config.VDC_ROOT_PASSWORD,
            config.DC_NAME[0]
        )
        logger.info("User with perms on target sd and disk can move disk.")


@attr(tier=2)
class DPCase147129(common.BaseTestCase):
    """
    Add disk to VM requires both permissions on the VM and on the sd
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147129, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            vms.removeVm(True, config.VM_NO_DISK)
            mla.removeUserPermissionsFromSD(
                True,
                config.MASTER_STORAGE,
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        vms.createVm(
            positive=True,
            vmName=config.VM_NO_DISK,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NO_DISK,
            role=config.role.UserRole
        )

    @polarion("RHEVM3-7632")
    @bz({'1209505': {}})
    def test_add_disk_to_vm(self):
        """ add disk to vm with and without permissions """
        common.login_as_user()
        assert vms.addDisk(
            False,
            config.VM_NO_DISK,
            config.GB,
            storagedomain=config.MASTER_STORAGE,
            interface='virtio',
            format='cow'
        ), "UserRole can add disk to vm."
        logger.info("User without permissions on vm, can't add disk to vm.")

        common.login_as_admin()
        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NO_DISK,
            role=config.role.UserVmManager
        )

        common.login_as_user()
        assert vms.addDisk(
            False,
            config.VM_NO_DISK,
            config.GB,
            storagedomain=config.MASTER_STORAGE,
            interface='virtio',
            format='cow'
        ), "User without permissions on sd can add disk to vm."
        logger.info("User without permissions on sd, can't add disk to vm.")

        common.login_as_admin()
        mla.addStoragePermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.MASTER_STORAGE,
            role=config.role.DiskCreator
        )

        common.login_as_user()
        assert vms.addDisk(
            True,
            config.VM_NO_DISK,
            config.GB,
            storagedomain=config.MASTER_STORAGE,
            interface='virtio',
            format='cow'
        ), "User with permissions on sd and vm can't add disk to vm."
        logger.info("User with permissions on sd and vm, can add disk to vm.")


@attr(tier=2)
class DPCase147130(common.BaseTestCase):
    """
    If disks are marked for deletion requires permissions on the removed
    disks and on the vm.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147130, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            vms.waitForVmsGone(True, config.VM_NAME)
            mla.removeUserPermissionsFromCluster(
                True,
                config.CLUSTER_NAME[0],
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME,
            role=config.role.DiskOperator
        )
        mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[0],
            role=config.role.UserRole
        )

    @polarion("RHEVM3-7624")
    def test_remove_vm(self):
        """ remove vm with disk without/with having apprirate permissions """
        common.login_as_user()
        assert vms.removeVm(
            False,
            config.VM_NAME
        ), "User can remove vm as DiskOperator."
        logger.info("User can't remove vm as DiskOperator.")

        common.login_as_admin()
        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME,
            role=config.role.UserVmManager
        )

        common.login_as_user()
        assert vms.removeVm(
            True,
            config.VM_NAME,
            wait=False
        ), "User can't remove vm as DiskOperator and UserVmManager on vm."
        logger.info("User can remove vm as UserVmManager, DiskOperator on vm")


@attr(tier=2)
class DPCase147137(common.BaseTestCase):
    """
    Create/attach/edit/delete shared disk.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(DPCase147137, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            ll_disks.waitForDisksGone(True, config.DISK_NAME)
            vms.removeVm(True, config.VM_NO_DISK),
            mla.removeUserPermissionsFromSD(
                True,
                config.MASTER_STORAGE,
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        ll_disks.addDisk(
            True,
            alias=config.DISK_NAME,
            interface='virtio',
            format='raw',
            provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE,
            shareable=True
        )
        ll_disks.wait_for_disks_status(config.DISK_NAME)
        mla.addStoragePermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.MASTER_STORAGE,
            role=config.role.DiskOperator
        )

        vms.createVm(
            positive=True,
            vmName=config.VM_NO_DISK,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NO_DISK
        )

    @polarion("RHEVM3-7616")
    def test_shared_disk(self):
        """ Basic operations with shared disk """
        common.login_as_user()
        assert ll_disks.attachDisk(
            True,
            config.DISK_NAME,
            config.VM_NO_DISK
        ), "Unable to attach disk to vm."
        logger.info("Shared disk was attached by user.")

        assert ll_disks.updateDisk(
            True,
            vmName=config.VM_NO_DISK,
            alias=config.DISK_NAME,
            interface='ide'
        ), "User can't update vm shared disk."
        logger.info("User can update vm shared disk.")

        assert ll_disks.deleteDisk(
            True,
            config.DISK_NAME
        ), "User can't remove shared disk."
        logger.info("User can remove shared disk.")
