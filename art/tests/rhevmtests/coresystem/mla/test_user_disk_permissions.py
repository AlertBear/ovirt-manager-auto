"""
Testing disk permissions feature.
Testing if permissions are correctly assigned/removed/viewed on disks.
"""
import logging
import pytest

import art.test_handler.exceptions as errors
from art.core_api.apis_exceptions import EntityNotFound

from art.rhevm_api.tests_lib.high_level import (
    disks as hl_disks
)
from art.rhevm_api.tests_lib.low_level import (
    jobs as ll_jobs,
    disks as ll_disks,
    storagedomains as ll_sd,
    mla, vms, users
)
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import testflow

from rhevmtests.coresystem.mla import common, config

USER_NAME = config.USER_NAMES[0]
CLUSTER = config.CLUSTER_NAME[0]

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup(request):

    def finalize():
        testflow.teardown("Log in as admin.")
        common.login_as_admin()

        testflow.teardown("Removing user %s.", USER_NAME)
        assert users.removeUser(True, USER_NAME)

    request.addfinalizer(finalize)

    testflow.setup("Adding user %s.", USER_NAME)
    assert common.add_user(
        positive=True,
        user_name=USER_NAME,
        domain=config.USER_DOMAIN
    )


@tier2
class TestDiskTemplate(common.BaseTestCase):
    disk_name = "{0}{1}".format(config.VM_NAME, "_Disk1")

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            for disk in [config.DISK_NAME, cls.disk_name]:
                try:
                    testflow.teardown("Removing disk %s.", disk)
                    hl_disks.delete_disks([disk])
                except EntityNotFound as err:
                    logger.warning(err)

            for vm in [config.VM_NAME, config.VM_NO_DISK]:
                try:
                    testflow.teardown("Removing VM %s.", vm)
                    vms.removeVm(True, vm)
                except EntityNotFound as err:
                    logger.warning(err)

            testflow.teardown(
                "Removing user permissions from storage domain."
            )
            assert mla.removeUserPermissionsFromSD(
                positive=True,
                storage_domain=config.STORAGE_NAME[0],
                user_name=USER_NAME
            )

        request.addfinalizer(finalize)


class TestDiskInheritedPermissions(TestDiskTemplate):
    """
    Check if SD has assigned permissions, then all disks in SD has inherit
    these permissions, Also check if disks is attached to VM, then disks,
    of vm inherit vm's permissions.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestDiskInheritedPermissions, cls).setup_class(request)

        testflow.setup("Adding disk %s.", config.DISK_NAME)
        assert ll_disks.addDisk(
            positive=True,
            alias=config.DISK_NAME,
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0]
        )

        testflow.setup("Waiting for disk status ok.")
        assert ll_disks.wait_for_disks_status(config.DISK_NAME)

        testflow.setup("Adding DiskOperator permissions to user.")
        assert mla.addStoragePermissionsToUser(
            positive=True,
            user=USER_NAME,
            storage=config.STORAGE_NAME[0],
            role=config.role.DiskOperator
        )

        testflow.setup("Creating VM %s.", config.VM_NO_DISK)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NO_DISK,
            cluster=CLUSTER,
            network=config.MGMT_BRIDGE
        )

        testflow.setup("Adding VM permissions to user.")
        assert mla.addVMPermissionsToUser(
            positive=True,
            user=USER_NAME,
            vm=config.VM_NO_DISK
        )

    @polarion("RHEVM3-7613")
    def test_disk_inherited_permissions(self):
        """ Check inheritance of disk permissions """
        testflow.step("Checking if user has permissions on disk.")
        assert mla.has_user_permissions_on_object(
            user_name=config.USERS[0],
            obj=ll_disks.DISKS_API.find(config.DISK_NAME),
            role=config.role.DiskOperator
        ), "Permissions from SD was not delegated to disk."

        testflow.step("Adding disk %s.", self.disk_name)
        assert vms.addDisk(
            positive=True,
            vm=config.VM_NO_DISK,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0],
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW,
            alias=self.disk_name
        ), "Unable to attach disk to vm."

        testflow.step("Checking if user has permissions on disk.")
        assert mla.has_user_permissions_on_object(
            user_name=config.USERS[0],
            obj=ll_disks.DISKS_API.find(self.disk_name),
            role=config.role.UserVmManager
        ), "Permissions from vm was not delegated to disk."


class TestCreateDiskNegative(TestDiskTemplate):
    """
    User should not be able to create disk if he has not create disk AG
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestCreateDiskNegative, cls).setup_class(request)

        testflow.setup("Adding storage permissions to user.")
        assert mla.addStoragePermissionsToUser(
            positive=True,
            user=USER_NAME,
            storage=config.STORAGE_NAME[0],
            role=config.role.UserRole
        )

    @polarion("RHEVM3-12079")
    def test_create_disk_without_permissions(self):
        """ Create disk without permissions """
        testflow.step("Log in as user without required pemissions.")
        common.login_as_user()

        testflow.step("Adding disk %s.", config.DISK_NAME)
        assert ll_disks.addDisk(
            positive=False,
            alias=config.DISK_NAME,
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0]
        ), "User without StorageAdmin permissions can create disk."


class TestCreateDisk(TestDiskTemplate):
    """
    If user want create disks, he needs to have permissions on SD.
    Try to assign permissions on SD and create disk
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestCreateDisk, cls).setup_class(request)

        testflow.setup("Adding required storage domain permissions to user.")
        assert mla.addStoragePermissionsToUser(
            positive=True,
            user=USER_NAME,
            storage=config.STORAGE_NAME[0],
            role=config.role.StorageAdmin
        )

    @polarion("RHEVM3-7625")
    def test_create_disk(self):
        """ Create disk with permissions """
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Adding disk %s.", config.DISK_NAME)
        assert ll_disks.addDisk(
            positive=True,
            alias=config.DISK_NAME,
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0]
        ), "User with StorageAdmin permissions can't create disk."

        testflow.step("Waiting for disk status 'ok'.")
        assert ll_disks.wait_for_disks_status([config.DISK_NAME])

        testflow.step("Deleting disk %s.", config.DISK_NAME)
        assert ll_disks.deleteDisk(
            positive=True,
            alias=config.DISK_NAME
        ), "User with StorageAdmin permissions can't delete disk."


class TestAttachDisk(TestDiskTemplate):
    """ Test attach disk """
    # Expected test outcomes (disk_role->vm_role->expected_result)
    outcomes = {
        config.role.DiskOperator: {
            config.role.UserRole: False,
            config.role.UserVmManager: True
        },
        config.role.UserRole: {
            config.role.UserVmManager: False
        }
    }

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestAttachDisk, cls).setup_class(request)

        testflow.setup("Adding disk %s.", config.DISK_NAME)
        assert ll_disks.addDisk(
            positive=True,
            alias=config.DISK_NAME,
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0]
        )

        testflow.setup("Waiting for disk status ok.")
        assert ll_disks.wait_for_disks_status(config.DISK_NAME)

        testflow.setup("Create VM %s.", config.VM_NO_DISK)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NO_DISK,
            cluster=CLUSTER,
            network=config.MGMT_BRIDGE
        )

    @polarion("RHEVM3-7626")
    def test_attach_disk_to_vm(self):
        """ Attach disk to vm """
        for disk_role, d in self.outcomes.items():
            for vm_role, outcome in d.items():
                testflow.step("Log in as admin.")
                common.login_as_admin()

                testflow.step("Adding %s role permissions to user.", disk_role)
                assert mla.addStoragePermissionsToUser(
                    positive=True,
                    user=USER_NAME,
                    storage=config.STORAGE_NAME[0],
                    role=disk_role
                )

                testflow.step("Adding %s role permissions to user.", vm_role)
                assert mla.addVMPermissionsToUser(
                    positive=True,
                    user=USER_NAME,
                    vm=config.VM_NO_DISK,
                    role=vm_role
                )

                testflow.step("Log in as user.")
                common.login_as_user()

                testflow.step("Attaching disk %s.", config.DISK_NAME)
                assert ll_disks.attachDisk(
                    positive=outcome,
                    alias=config.DISK_NAME,
                    vm_name=config.VM_NO_DISK
                )


class TestDetachDisk(TestDiskTemplate):
    """ Test detach disk """
    # Expected test outcomes (role->expected_result)
    outcomes = {config.role.UserRole: False, config.role.UserVmManager: True}

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestDetachDisk, cls).setup_class(request)

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=CLUSTER,
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

    @polarion("RHEVM3-7627")
    def test_detach_disk(self):
        """ Detach disk from vm """
        for role, outcome in self.outcomes.items():
            testflow.step("Log in as admin.")
            common.login_as_admin()

            testflow.step("Adding %s role to user.", role)
            assert mla.addVMPermissionsToUser(
                positive=True,
                user=USER_NAME,
                vm=config.VM_NAME,
                role=role
            )

            testflow.step("Log in as user.")
            common.login_as_user()

            testflow.step("Detaching disk %s.", self.disk_name)
            try:
                res = ll_disks.detachDisk(
                    positive=outcome,
                    alias=self.disk_name,
                    vmName=config.VM_NAME
                )
                assert res and outcome
            except AttributeError as err:
                assert not outcome, err.message


class TestActivateDeactivateDisk(TestDiskTemplate):
    """
    To activate/deactivate user must have an manipulate permissions on VM.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestActivateDeactivateDisk, cls).setup_class(request)

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=CLUSTER,
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        testflow.setup("Adding VM permissions to user.")
        assert mla.addVMPermissionsToUser(
            positive=True,
            user=USER_NAME,
            vm=config.VM_NAME
        )

    @polarion("RHEVM3-7628")
    def test_activate_deactivate_disk(self):
        """ Activate/Deactivate Disk """
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Deactivating disk %s.", self.disk_name)
        assert vms.deactivateVmDisk(
            positive=True,
            vm=config.VM_NAME,
            diskAlias=self.disk_name
        ), "User with UserVmManager role can't deactivate vm disk"

        testflow.step("Activating disk %s.", self.disk_name)
        assert vms.activateVmDisk(
            positive=True,
            vm=config.VM_NAME,
            diskAlias=self.disk_name
        ), "User with UserVmManager role can't activate vm disk"


class TestRemoveDisk(TestDiskTemplate):
    """
    User has to have delete_disk action group in order to remove disk.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestRemoveDisk, cls).setup_class(request)

        testflow.setup("Adding disk %s.", config.DISK_NAME)
        assert ll_disks.addDisk(
            positive=True,
            alias=config.DISK_NAME,
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0]
        )

        testflow.setup("Waiting for disk status 'ok'.")
        assert ll_disks.wait_for_disks_status(config.DISK_NAME)

        testflow.setup(
            "Adding storage domain UserRole role permissions to user."
        )
        assert mla.addStoragePermissionsToUser(
            positive=True,
            user=USER_NAME,
            storage=config.STORAGE_NAME[0],
            role=config.role.UserRole
        )

    @polarion("RHEVM3-7629")
    def test_remove_disk(self):
        """ Remove disk as user with and without permissions """
        testflow.step("Log in as user without required permissions.")
        common.login_as_user()

        testflow.teardown("Removing disk %s.", config.DISK_NAME)
        assert ll_disks.deleteDisk(
            positive=False,
            alias=config.DISK_NAME
        ), "User without delete_disk action group can remove disk."

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step("Adding DiskOperator permissions to user.")
        assert mla.addStoragePermissionsToUser(
            positive=True,
            user=USER_NAME,
            storage=config.STORAGE_NAME[0],
            role=config.role.DiskOperator
        )

        testflow.step("Log in as user with all required permissions.")
        common.login_as_user()

        testflow.step("Removing disk %s.", config.DISK_NAME)
        assert ll_disks.deleteDisk(
            positive=True,
            alias=config.DISK_NAME
        ), "User with delete_disk action group can't remove disk."


class TestUpdateDisk(TestDiskTemplate):
    """
    User has to have edit_disk_properties action group in order to remove disk.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestUpdateDisk, cls).setup_class(request)

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=CLUSTER,
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        testflow.setup("Adding VM permissions to user.")
        assert mla.addVMPermissionsToUser(
            positive=True,
            user=USER_NAME,
            vm=config.VM_NAME
        )

    @polarion("RHEVM3-7630")
    def test_update_vm_disk(self):
        """ Update vm disk """
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Updating disk %s.", self.disk_name)
        assert ll_disks.updateDisk(
            positive=True,
            vmName=config.VM_NAME,
            alias=self.disk_name,
            interface=config.INTERFACE_IDE
        ), "User can't update VMs disk."


class TestMoveOrCopyDisk(TestDiskTemplate):
    """
    Move or copy disk requires permissions on the disk and on the target sd.
    """
    source_storage_domain = config.STORAGE_NAME[0]
    destination_storage_domain = config.STORAGE_NAME[1]
    storage_domains = [source_storage_domain, destination_storage_domain]

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestMoveOrCopyDisk, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown("Wait till move job ends.")
            ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])

        request.addfinalizer(finalize)

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=CLUSTER,
            storageDomainName=cls.source_storage_domain,
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        testflow.setup("Adding UserVmManager role permissions to user.")
        assert mla.addVMPermissionsToUser(
            positive=True,
            user=USER_NAME,
            vm=config.VM_NAME,
            role=config.role.UserVmManager
        )

    @polarion("RHEVM3-7631")
    @bz({'1503269': {}})
    def test_move_disk(self):
        """ Move disk with and without having permissions on sds """

        def move_disk():
            try:
                vms.move_vm_disk(
                    vm_name=config.VM_NAME,
                    disk_name=self.disk_name,
                    target_sd=self.destination_storage_domain
                )
                return True
            except errors.DiskException as err:
                logger.warning(err)
            return False

        testflow.step("Moving disk without permissions.")
        common.login_as_user()

        testflow.step("Moving disk %s.", self.disk_name)
        assert not move_disk(), (
            "User without permissions on storage domain can move disk."
        )

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step(
            "Adding StorageAdmin role permissions only "
            "on source storage domain."
        )
        assert mla.addStoragePermissionsToUser(
            positive=True,
            user=USER_NAME,
            storage=self.source_storage_domain
        )

        testflow.step("Log in as user without all required permissions.")
        common.login_as_user()

        testflow.step("Moving disk.")
        assert not move_disk(), (
            "User without permission on target "
            "storage domain can move disk."
        )

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step(
            "Adding StorageAdmin role permissions"
            "on destination storage domain."
        )
        assert mla.addStoragePermissionsToUser(
            positive=True,
            user=USER_NAME,
            storage=self.destination_storage_domain
        )

        testflow.step("Log in as user with all required permissions.")
        common.login_as_user()

        testflow.step("Moving disk.")
        assert move_disk(), (
            "User with all required permissions can't move disk!"
        )


class TestAddDiskToVM(TestDiskTemplate):
    """
    Add disk to VM requires both permissions on the VM and on the sd
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestAddDiskToVM, cls).setup_class(request)

        testflow.setup("Creating VM %s.", config.VM_NO_DISK)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NO_DISK,
            cluster=CLUSTER,
            network=config.MGMT_BRIDGE
        )

        testflow.setup("Adding UserRole role permissions to user.")
        assert mla.addVMPermissionsToUser(
            positive=True,
            user=USER_NAME,
            vm=config.VM_NO_DISK,
            role=config.role.UserRole
        )

    @polarion("RHEVM3-7632")
    def test_add_disk_to_vm(self):
        """ add disk to vm with and without permissions """
        testflow.step("Log in as user without required permissions.")
        common.login_as_user()

        testflow.step("Adding disk.")
        assert vms.addDisk(
            positive=False,
            vm=config.VM_NO_DISK,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0],
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW
        ), "UserRole can add disk to VM."

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step("Adding UserVmManager role permissions to user.")
        assert mla.addVMPermissionsToUser(
            positive=True,
            user=USER_NAME,
            vm=config.VM_NO_DISK,
            role=config.role.UserVmManager
        )

        testflow.step("Log in as user with only VM permissions.")
        common.login_as_user()

        testflow.step("Adding disk to VM.")
        assert vms.addDisk(
            positive=False,
            vm=config.VM_NO_DISK,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0],
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW
        ), "User without permissions on SD can add disk to VM."

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step("Adding DiskCreator role permissions to user.")
        assert mla.addStoragePermissionsToUser(
            positive=True,
            user=USER_NAME,
            storage=config.STORAGE_NAME[0],
            role=config.role.DiskCreator
        )

        testflow.step("Log in as user with all required permissions.")
        common.login_as_user()

        testflow.step("Adding disk to VM.")
        assert vms.addDisk(
            positive=True,
            vm=config.VM_NO_DISK,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0],
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW
        ), "User with permissions on SD and VM can't add disk to VM."


class TestRemoveVM(TestDiskTemplate):
    """
    If disks are marked for deletion requires permissions on the removed
    disks and on the vm.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestRemoveVM, cls).setup_class(request)

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=CLUSTER,
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        testflow.setup("Adding disk %s.", config.DISK_NAME)
        assert ll_disks.addDisk(
            positive=True,
            alias=config.DISK_NAME,
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_RAW,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0]
        )

        testflow.setup("Waiting for disk status 'ok'.")
        assert ll_disks.wait_for_disks_status([config.DISK_NAME])

        testflow.setup("Attaching disk.")
        assert ll_disks.attachDisk(
            positive=True,
            alias=config.DISK_NAME,
            vm_name=config.VM_NAME
        )

        testflow.setup("Adding cluster permissions for user.")
        assert mla.addClusterPermissionsToUser(
            positive=True,
            user=USER_NAME,
            cluster=CLUSTER,
            role=config.role.UserRole
        )

    @polarion("RHEVM3-7624")
    def test_remove_vm(self):
        """ remove vm with disk without/with having apprirate permissions """
        testflow.step(
            "Log in as user without having VM and Disks permissions."
        )
        common.login_as_user()

        testflow.step("Removing VM %s.", config.VM_NAME)
        assert vms.removeVm(
            positive=False,
            vm=config.VM_NAME
        ), "User can remove VM without any required permissions."

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step("Adding DiskOperator permissions for user.")
        assert mla.addVMPermissionsToUser(
            positive=True,
            user=USER_NAME,
            vm=config.VM_NAME,
            role=config.role.DiskOperator
        )

        testflow.step("Log in as user only with DiskOperator permissions.")
        common.login_as_user()

        testflow.step("Removing VM %s.", config.VM_NAME)
        assert vms.removeVm(
            positive=False,
            vm=config.VM_NAME
        ), "User can remove VM as DiskOperator."

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step("Adding UserVmManager permissions to user.")
        assert mla.addVMPermissionsToUser(
            positive=True,
            user=USER_NAME,
            vm=config.VM_NAME,
            role=config.role.UserVmManager
        )

        testflow.step("Log in as user with all required permissions.")
        common.login_as_user()

        testflow.step(
            "Removing VM %s with all required permissions.",
            config.VM_NAME
        )
        assert vms.removeVm(
            positive=True,
            vm=config.VM_NAME
        ), "User can't remove VM as DiskOperator and UserVmManager roles."


class TestDisk(TestDiskTemplate):
    """
    Create/attach/update/delete disk as DiskOperator.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestDisk, cls).setup_class(request)

        testflow.setup("Adding DiskOperator permissions to user.")
        assert mla.addStoragePermissionsToUser(
            positive=True,
            user=USER_NAME,
            storage=config.STORAGE_NAME[0],
            role=config.role.DiskOperator
        )

        testflow.setup("Creating VM %s.", config.VM_NO_DISK)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NO_DISK,
            cluster=CLUSTER,
            network=config.MGMT_BRIDGE
        )

        testflow.setup("Adding VM permissions for user.")
        assert mla.addVMPermissionsToUser(
            positive=True,
            user=USER_NAME,
            vm=config.VM_NO_DISK
        )

    @polarion("RHEVM3-7617")
    def test_floating_disk(self):
        """ Basic operations with floating disk """
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Adding floating disk %s.", config.DISK_NAME)
        assert ll_disks.addDisk(
            positive=True,
            alias=config.DISK_NAME,
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_RAW,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0]
        )

        testflow.step("Waiting for disk status 'ok'.")
        assert ll_disks.wait_for_disks_status([config.DISK_NAME])

        testflow.step("Attaching floating disk %s.", config.DISK_NAME)
        assert ll_disks.attachDisk(
            positive=True,
            alias=config.DISK_NAME,
            vm_name=config.VM_NO_DISK
        ), "Unable to attach disk to vm."

        testflow.step("Updating floating disk %s.", config.DISK_NAME)
        assert ll_disks.updateDisk(
            positive=True,
            vmName=config.VM_NO_DISK,
            alias=config.DISK_NAME,
            interface=config.INTERFACE_IDE
        ), "User can't update floating disk."

        testflow.step("Removing floating disk %s.", config.DISK_NAME)
        assert ll_disks.deleteDisk(
            positive=True,
            alias=config.DISK_NAME
        ), "User can't remove floating disk."

    @polarion("RHEVM3-7616")
    def test_shared_disk(self):
        """ Basic operations with shared disk """
        if ll_sd.get_storage_domain_storage_type(
                config.STORAGE_NAME[0]
        ) == config.STORAGE_TYPE_GLUSTER:
            pytest.skip(
                "Shareable disks are not supported on Gluster domains."
            )

        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Adding shared disk %s.", config.DISK_NAME)
        assert ll_disks.addDisk(
            positive=True,
            alias=config.DISK_NAME,
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_RAW,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0],
            shareable=True
        )

        testflow.step("Waiting for disk status 'ok'.")
        assert ll_disks.wait_for_disks_status([config.DISK_NAME])

        testflow.step("Attaching shared disk %s.", config.DISK_NAME)
        assert ll_disks.attachDisk(
            positive=True,
            alias=config.DISK_NAME,
            vm_name=config.VM_NO_DISK
        ), "Unable to attach disk to vm."

        testflow.step("Updating shared disk %s.", config.DISK_NAME)
        assert ll_disks.updateDisk(
            positive=True,
            vmName=config.VM_NO_DISK,
            alias=config.DISK_NAME,
            interface=config.INTERFACE_IDE
        ), "User can't update shared disk."

        testflow.step("Waiting for disk status 'ok'.")
        assert ll_disks.wait_for_disks_status([config.DISK_NAME])

        testflow.step("Removing shared disk %s.", config.DISK_NAME)
        assert ll_disks.deleteDisk(
            positive=True,
            alias=config.DISK_NAME
        ), "User can't remove shared disk."
