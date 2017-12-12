"""
Testing working with permissions.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Tests if permissions are correctly inherited/viewed/assigned/removed.
"""
import logging
import pytest

from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.high_level import (
    vmpools as hl_vmpools
)
from art.rhevm_api.tests_lib.low_level import (
    disks, hosts, mla, storagedomains,
    templates, users, vms,
    vmpools as ll_vmpools,
    datacenters as ll_dc,
    clusters as ll_cluster
)
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion
from art.unittest_lib import tier1, tier2, testflow

import common
import config

# Predefined role for creation of VM as non-admin user
VM_PREDEFINED = config.role.UserVmManager
# Predefined role for creation of Disk as non-admin user
DISK_PREDEFINED = config.role.DiskOperator
# Predefined role for creation of Template as non-admin user
TEMPLATE_PREDEFINED = config.role.TemplateOwner

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        testflow.teardown("Log in as admin.")
        common.login_as_admin()

        for user_name in config.USER_NAMES[:3]:
            testflow.teardown("Removing user %s.", user_name)
            users.removeUser(True, user_name)

        testflow.teardown("Removing VM %s.", config.VM_NAME)
        vms.removeVm(True, config.VM_NAME, wait=True)

        testflow.teardown("Removing disk %s.", config.DISK_NAME)
        disks.deleteDisk(True, config.DISK_NAME, async=False)
        disks.waitForDisksGone(True, config.DISK_NAME)

        testflow.teardown("Removing pool %s.", config.VMPOOL_NAME)
        hl_vmpools.remove_whole_vm_pool(config.VMPOOL_NAME)

        testflow.teardown("Removing template %s.", config.TEMPLATE_NAMES[0])
        templates.remove_template(True, config.TEMPLATE_NAMES[0])

        testflow.teardown("Waiting for async tasks.")
        test_utils.wait_for_tasks(config.ENGINE, config.DC_NAME[0])

    request.addfinalizer(finalize)

    testflow.setup("Log in as admin.")
    common.login_as_admin()

    for user_name in config.USER_NAMES[:3]:
        testflow.setup("Adding user %s.", user_name)
        common.add_user(
            True,
            user_name=user_name,
            domain=config.USER_DOMAIN
        )

    testflow.setup("Creating VM %s.", config.VM_NAME)
    vms.createVm(
        positive=True,
        vmName=config.VM_NAME,
        cluster=config.CLUSTER_NAME[0],
        storageDomainName=config.STORAGE_NAME[0],
        provisioned_size=config.GB,
        network=config.MGMT_BRIDGE
    )

    testflow.setup("Creating template %s.", config.TEMPLATE_NAMES[0])
    templates.createTemplate(
        True,
        vm=config.VM_NAME,
        name=config.TEMPLATE_NAMES[0],
        cluster=config.CLUSTER_NAME[0]
    )

    testflow.setup("Adding pool %s.", config.VMPOOL_NAME)
    ll_vmpools.addVmPool(
        True,
        name=config.VMPOOL_NAME,
        size=1,
        cluster=config.CLUSTER_NAME[0],
        template=config.TEMPLATE_NAMES[0]
    )
    vms.wait_for_vm_states(
        "{0}-{1}".format(config.VMPOOL_NAME, 1),
        states=[
            common.ENUMS["vm_state_down"]
        ]
    )

    testflow.setup("Adding disk %s.", config.DISK_NAME)
    disks.addDisk(
        True,
        alias=config.DISK_NAME,
        interface='virtio',
        format='cow',
        provisioned_size=config.GB,
        storagedomain=config.STORAGE_NAME[0]
    )
    disks.wait_for_disks_status(config.DISK_NAME)


@tier1
class TestPermissionsCase54408(common.BaseTestCase):
    """ objects and user permissions """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPermissionsCase54408, cls).setup_class(request)

        # Test these object for adding/removing/viewing perms on it
        cls.objects = {
            config.VM_NAME: vms.VM_API,
            config.TEMPLATE_NAMES[0]: templates.TEMPLATE_API,
            config.DISK_NAME: disks.DISKS_API,
            config.VMPOOL_NAME: ll_vmpools.UTIL,
            config.CLUSTER_NAME[0]: ll_cluster.util,
            config.DC_NAME[0]: ll_dc.util,
            config.HOSTS[0]: hosts.HOST_API,
            config.STORAGE_NAME[0]: storagedomains.util
        }

    # Check that there are two types of Permissions sub-tabs in the system:
    # for objects on which you can define permissions and for users.
    @polarion("RHEVM3-7168")
    def test_objects_and_user_permissions(self):
        """ objects and user permissions """
        for k in self.objects.keys():
            obj = self.objects[k].find(k)
            href = "{}/permissions".format(obj.get_href())
            testflow.step(
                "Check if %s has permissions subcollection.", obj.get_name()
            )
            assert self.objects[k].get(href=href) is not None


@tier1
class TestPermissionsCase54409(common.BaseTestCase):
    """" permissions inheritance """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPermissionsCase54409, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown("Removing user %s.", config.USER_NAMES[0])
            users.removeUser(True, config.USER_NAMES[0])

            testflow.teardown("Adding user %s.", config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

        testflow.setup(
            "Adding role %s to user %s.",
            config.role.ClusterAdmin, config.USER_NAMES[0]
        )
        users.addRoleToUser(
            True,
            config.USER_NAMES[0],
            config.role.ClusterAdmin
        )

    @polarion("RHEVM3-7185")
    def test_permissions_inheritance(self):
        """ permissions inheritance """
        testflow.step("Log in as user.")
        common.login_as_user(filter_=False)

        testflow.step("Creating VM %s.", config.VM_NAMES[0])
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        testflow.step("Removing VM %s.", config.VM_NAMES[0])
        assert vms.removeVm(True, config.VM_NAMES[0])

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step("Removing user %s.", config.USER_NAMES[0])
        users.removeUser(True, config.USER_NAMES[0])

        testflow.step("Adding user %s.", config.USER_NAMES[0])
        common.add_user(
            True,
            user_name=config.USER_NAMES[0],
            domain=config.USER_DOMAIN
        )
        # To be able login
        testflow.step(
            "Adding cluster permissions for user %s.", config.USER_NAMES[0]
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[0],
            config.role.UserRole
        )

        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Creating VM %s.", config.VM_NAMES[0])
        assert vms.createVm(
            positive=False,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )


# Check that in the object Permissions sub tab you will see all permissions
# that were associated with the selected object in the main grid or one of
# its ancestors.
@tier1
class TestPermissionsCase5441054414(common.BaseTestCase):
    """" permissions subtab """
    @polarion("RHEVM3-7186")  # Also RHEVM3-7187, can not have multiple IDs
    def test_permissions_sub_tab(self):
        """ permissions subtab """
        # Try to add UserRole and AdminRole to object, then
        # check if both roles are visible via /api/objects/objectid/permissions
        testflow.step("Getting users ids.")
        user_ids = [users.util.find(u).get_id() for u in config.USER_NAMES[:2]]

        for user_name in config.USER_NAMES[:2]:
            testflow.step("Adding VM permissions to user %s.", user_name)
            assert mla.addVMPermissionsToUser(
                True,
                user_name,
                config.VM_NAME,
                role=config.role.UserRole
            )

        testflow.step("Getting %s VM permissions for users.", config.VM_NAME)
        vm = vms.VM_API.find(config.VM_NAME)
        role_permits = mla.permisUtil.getElemFromLink(vm, get_href=False)
        users_id = [perm.user.get_id() for perm in role_permits if perm.user]
        # for user_id in user_ids:
        # assert user_id in users_id
        testflow.step("Checking if all associated permissions are visible.")
        assert set(user_ids).issubset(set(users_id))

        for user_name in config.USERS[:2]:
            testflow.step("Removing user %s permissions from VM.", user_name)
            mla.removeUserPermissionsFromVm(
                True,
                config.VM_NAME,
                user_name
            )


# Assuming that there is always Super-Admin user on RHEV-M.
# Try to remove last permission on certain object.
# This also tests 54410
# It should be impossible to remove last Super-admin user with permission on
# system object.
# Try to remove last super-admin user with permission on system object.
# Try to remove super-admin + system permission from the user.
@tier2
class TestPermissionsCase5441854419(common.BaseTestCase):
    """ last permission on object and test removal of SuperUser """
    @polarion("RHEVM3-7188")
    def test_last_permission_on_object(self):
        """ last permission on object """
        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step(
            "Adding VM permissions to user %s.", config.USER_NAMES[0]
        )
        mla.addVMPermissionsToUser(True, config.USER_NAMES[0], config.VM_NAME)

        testflow.step(
            "Removing user %s permissions from VM.", config.USER_NAMES[0]
        )
        mla.removeUserPermissionsFromVm(True, config.VM_NAME, config.USERS[0])

    @polarion("RHEVM3-7189")
    def test_removal_of_super_user(self):
        """ test removal of SuperUser """
        testflow.step("Removing super user.")
        assert users.removeUser(False, 'admin@internal', 'internal')

        testflow.step("Removing super user role.")
        assert mla.removeUserRoleFromDataCenter(
            False,
            config.DC_NAME[0],
            'admin@internal',
            config.role.SuperUser
        )


# Try to add a permission associated with an
# administrator Role (i.e. "Administrator Permission") to another user when
# you don't have "Super-Admin" permission on the "System" object". - FAILED
# When you're user/super user ,try to delegate permission to another
# user/super user. - SUCCESS
@tier2
class TestPermissionsCase54425(common.BaseTestCase):
    """ test delegate perms """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPermissionsCase54425, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown("Removing VM %s", config.VM_NAMES[0])
            vms.removeVm(True, config.VM_NAMES[0])

            testflow.teardown("Removing user %s.", config.USER_NAMES[0])
            users.removeUser(True, config.USER_NAMES[0])

            testflow.teardown("Adding user %s.", config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

        testflow.teardown("Creating VM %s.", config.VM_NAMES[0])
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

    @polarion("RHEVM3-7191")
    def test_delegate_permissions(self):
        """ delegate permissions """
        # Test SuperUser that he can add permissions
        for role_obj in mla.util.get(abs_link=False):
            testflow.step("Log in as admin.")
            common.login_as_admin()

            testflow.step("Getting role name.")
            role_name = role_obj.get_name()

            testflow.step("Getting role %s permits.", role_name)
            role_permits = mla.util.getElemFromLink(
                role_obj,
                link_name='permits',
                attr='permit',
                get_href=False
            )

            testflow.step("Getting permits names.")
            permits = [p.get_name() for p in role_permits]
            if 'login' not in permits:
                logger.info("User not tested, because don't have login perms.")
                continue

            assert users.addRoleToUser(True, config.USER_NAMES[0], role_name)
            assert mla.addVMPermissionsToUser(
                True, config.USER_NAMES[0], config.VM_NAMES[0], role_name
            )

            # For know if login as User/Admin
            testflow.step("Checking if role is administrative.")
            _filter = not role_obj.administrative

            # login as user with role
            testflow.step("Log in as user.")
            common.login_as_user(filter_=_filter)

            # Test if user with role can/can't manipulate perms
            if 'manipulate_permissions' in permits:
                if _filter or config.role.SuperUser != role_name:
                    try:
                        testflow.step(
                            "Adding VM permissions to user %s.",
                            config.USER_NAMES[0]
                        )
                        assert mla.addVMPermissionsToUser(
                            False,
                            config.USER_NAMES[0],
                            config.VM_NAMES[0],
                            config.role.TemplateAdmin
                        )
                    except EntityNotFound as e:
                        logger.warning(e)
                        pass

                else:
                    testflow.step(
                        "Adding VM permissions to user %s.",
                        config.USER_NAMES[0]
                    )
                    assert mla.addVMPermissionsToUser(
                        True,
                        config.USER_NAMES[0],
                        config.VM_NAMES[0],
                        config.role.UserRole
                    )

                    testflow.step(
                        "Adding VM permissions to user %s.",
                        config.USER_NAMES[0]
                    )
                    assert mla.addVMPermissionsToUser(
                        True,
                        config.USER_NAMES[0],
                        config.VM_NAMES[0],
                        config.role.TemplateAdmin
                    )
            else:
                try:
                    testflow.step(
                        "Adding VM permissions to user %s.",
                        config.USER_NAMES[0]
                    )
                    mla.addVMPermissionsToUser(
                        False,
                        config.USER_NAMES[0],
                        config.VM_NAMES[0],
                        config.role.UserRole
                    )
                except EntityNotFound as e:
                    logger.warning(e)
                    pass

            testflow.step("Log in as admin.")
            common.login_as_admin()

            testflow.step("Removing user %s.", config.USER_NAMES[0])
            users.removeUser(True, config.USER_NAMES[0])

            testflow.step("Adding user %s.", config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

    # in order ro add new object you will need the appropriate permission on
    # the ancestor (e.g. to create a new storage domain you'll need a "add
    # storage domain" permission on the "system" object,to create a new Host/VM
    # you will need appropriate permission on the relevant cluster.
    @polarion("RHEVM3-7192")
    def test_new_object_check_permissions(self):
        """ Adding new business entity/new object. """
        msg = "This functionality tests modules admin_tests and user_tests"
        logger.info(msg)


# Check if user is under some Group if it has permissions of its group
@tier2
class TestPermissionsCase54446(common.BaseTestCase):
    """ Check if user is under some Group if has permissions of its group """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPermissionsCase54446, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown("Removing VM %s.", config.VM_NAMES[0])
            vms.removeVm(True, config.VM_NAMES[0])

            testflow.teardown("Removing user %s.", config.GROUP_USER)
            try:
                users.removeUser(True, config.GROUP_USER)
            except EntityNotFound as err:
                logger.warning(err)

            testflow.teardown("Removing group %s.", config.GROUP_NAME)
            users.deleteGroup(True, config.GROUP_NAME)

        request.addfinalizer(finalize)

        testflow.setup("Adding group %s.", config.GROUP_NAME)
        users.addGroup(
            True,
            config.GROUP_NAME,
            config.USER_DOMAIN
        )

        testflow.setup(
            "Adding cluster permissions for group %s.", config.GROUP_NAME
        )
        mla.addClusterPermissionsToGroup(
            True,
            config.GROUP_NAME,
            config.CLUSTER_NAME[0],
            config.role.UserVmManager
        )

        mla.addTemplatePermissionsToGroup(
            True,
            config.GROUP_NAME,
            config.BLANK_TEMPLATE,
            config.role.UserRole
        )

    @polarion("RHEVM3-7193")
    def test_users_permissions(self):
        """ users permissions """
        testflow.step("Log in as user %s.", config.GROUP_USER_NAME)
        common.login_as_user(user_name=config.GROUP_USER_NAME)

        testflow.step("Creating VM %s.", config.VM_NAMES[0])
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        testflow.step("Creating template %s.", config.TEMPLATE_NAMES[1])
        assert templates.createTemplate(
            False,
            vm=config.VM_NAMES[0],
            name=config.TEMPLATE_NAMES[1],
            cluster=config.CLUSTER_NAME[0]
        )


# user API - createVm - should add perms UserVmManager on VM
# https://bugzilla.redhat.com/show_bug.cgi?id=881145
@tier2
class TestPermissionsCase54420(common.BaseTestCase):
    """ Object creating from User and Admin portal """
    @polarion("RHEVM3-7190")
    def test_object_admin_user(self):
        """ Object creating from User portal """
        result = True

        for role_name in [config.role.VmCreator, config.role.TemplateCreator]:
            testflow.step("Log in as admin.")
            common.login_as_admin()

            testflow.step("Getting role %s object.", role_name)
            role_obj = users.rlUtil.find(role_name)

            testflow.step("Getting role %s permits.", role_name)
            role_permits = mla.util.getElemFromLink(
                role_obj,
                link_name='permits',
                attr='permit',
                get_href=False
            )

            testflow.step("Getting role %s permits names.", role_name)
            role_permits_names = [p.get_name() for p in role_permits]

            testflow.step(
                "Adding role %s to user %s.", role_name, config.USER_NAMES[0]
            )
            users.addRoleToUser(True, config.USER_NAMES[0], role_name)

            testflow.step(
                "Adding cluster permissions to user %s.", config.USER_NAMES[0]
            )
            mla.addClusterPermissionsToUser(
                True,
                config.USER_NAMES[0],
                config.CLUSTER_NAME[0],
                config.role.UserRole
            )

            testflow.step(
                "Adding template permissions to user %s.", config.USER_NAMES[0]
            )
            mla.addPermissionsForTemplate(
                True,
                config.USER_NAMES[0],
                config.BLANK_TEMPLATE,
                config.role.UserRole
            )

            testflow.step("Log in as user.")
            common.login_as_user(filter_=not role_obj.administrative)

            testflow.step("Testing role - %s", role_name)

            # Create vm,template, disk and check permissions of it
            if 'create_vm' in role_permits_names:
                testflow.step("Creating VM %s.", config.VM_NAMES[0])
                vms.createVm(
                    positive=True,
                    vmName=config.VM_NAMES[0],
                    cluster=config.CLUSTER_NAME[0],
                    network=config.MGMT_BRIDGE
                )

                testflow.step(
                    "Checking if VM %s has role %s.",
                    config.VM_NAMES[0], VM_PREDEFINED
                )
                result = result and common.check_if_object_has_role(
                    vms.VM_API.find(config.VM_NAMES[0]),
                    VM_PREDEFINED,
                    role_obj.administrative
                )

                testflow.step("Log in as admin.")
                common.login_as_admin()

                testflow.step("Removing VM %s.", config.VM_NAMES[0])
                vms.removeVm(True, config.VM_NAMES[0])

            if 'create_template' in role_permits_names:
                testflow.step(
                    "Creating template %s.", config.TEMPLATE_NAMES[1]
                )
                templates.createTemplate(
                    True,
                    vm=config.VM_NAME,
                    name=config.TEMPLATE_NAMES[1],
                    cluster=config.CLUSTER_NAME[0]
                )

                testflow.step(
                    "Checking if template %s has role %s.",
                    config.TEMPLATE_NAMES[1], TEMPLATE_PREDEFINED
                )
                result = result and common.check_if_object_has_role(
                    templates.TEMPLATE_API.find(config.TEMPLATE_NAMES[1]),
                    TEMPLATE_PREDEFINED,
                    role_obj.administrative
                )

                testflow.step("Log in as admin.")
                common.login_as_admin()

                testflow.step(
                    "Removing template %s.", config.TEMPLATE_NAMES[1]
                )
                templates.remove_template(True, config.TEMPLATE_NAMES[1])

            if 'create_disk' in role_permits_names:
                testflow.step("Adding disk %s.", config.DISK_NAME1)
                disks.addDisk(
                    True,
                    alias=config.DISK_NAME1,
                    interface='virtio',
                    format='cow',
                    provisioned_size=config.GB,
                    storagedomain=config.STORAGE_NAME[0]
                )

                testflow.step("Waiting for disk %s.", config.DISK_NAME1)
                disks.wait_for_disks_status(config.DISK_NAME1)

                testflow.step(
                    "Checking if disk %s has role %s.",
                    config.DISK_NAME1, DISK_PREDEFINED
                )
                result = result and common.check_if_object_has_role(
                    disks.DISKS_API.find(config.DISK_NAME1),
                    DISK_PREDEFINED,
                    role_obj.administrative
                )

                testflow.step("Log in as admin.")
                common.login_as_admin()

                testflow.step("Removing disk %s.", config.DISK_NAME1)
                disks.deleteDisk(True, config.DISK_NAME1)

                testflow.step("Waiting until disk %s gone.", config.DISK_NAME1)
                disks.waitForDisksGone(True, config.DISK_NAME1)

            testflow.step("Removing user %s.", config.USER_NAMES[0])
            users.removeUser(True, config.USER_NAMES[0])

            testflow.step("Adding user %s.", config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )
        testflow.step("Checking if all tests above were ok.")
        assert result


# add a group of users from AD to the system (give it some admin permission)
# login as user from group, remove the user
# Check that group still exist in the Configure-->System.
# Check that group's permissions still exist
@tier2
class TestPermissionsCase108233(common.BaseTestCase):
    """ Removing user that part of the group. """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPermissionsCase108233, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown("Removing user %s.", config.GROUP_USER_NAME)
            users.removeUser(True, config.GROUP_USER_NAME)

            testflow.teardown("Removing group %s.", config.GROUP_NAME)
            users.deleteGroup(True, config.GROUP_NAME)

        request.addfinalizer(finalize)

        testflow.setup("Adding group %s.", config.GROUP_NAME)
        users.addGroup(
            True,
            config.GROUP_NAME,
            config.USER_DOMAIN
        )

        testflow.setup(
            "Adding cluster permissions to group %s.", config.GROUP_NAME
        )
        mla.addClusterPermissionsToGroup(
            True,
            config.GROUP_NAME,
            config.CLUSTER_NAME[0]
        )

        testflow.setup("Adding user %s.", config.GROUP_USER_NAME)
        common.add_user(
            True,
            user_name=config.GROUP_USER_NAME,
            domain=config.USER_DOMAIN
        )

    @polarion("RHEVM3-7169")
    def test_remove_user_from_group(self):
        """ Removing user that part of the group. """
        testflow.step("Log in as user %s.", config.GROUP_USER_NAME)
        common.login_as_user(
            user_name=config.GROUP_USER_NAME,
            filter_=False
        )

        testflow.step("Check if user could see VM %s.", config.VM_NAME)
        assert vms.VM_API.find(config.VM_NAME)

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step("Finding user %s.", config.GROUP_USER_NAME)
        assert users.util.find(config.GROUP_USER_NAME)


# Check that data-center has a user with UserRole permission
# Create new desktop pool
# Check that permission was inherited from data-center
# Ensure that user can take a machine from created pool
@tier2
class TestPermissionsCase109086(common.BaseTestCase):
    """ Permission inheritance for desktop pool """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPermissionsCase109086, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown("Removing user permissions from datacenter.")
            mla.removeUserPermissionsFromDatacenter(
                True,
                config.DC_NAME[0],
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        testflow.setup("Adding datacenter permissions.")
        mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            config.role.UserRole
        )

    @polarion("RHEVM3-7170")
    def test_permissions_inheritance_for_vm_pools(self):
        """ Permission inheritance for desktop pools """
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Allocating VM from pool %s.", config.VMPOOL_NAME)
        assert ll_vmpools.allocateVmFromPool(True, config.VMPOOL_NAME)

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step("Waiting for VM %s-1.", config.VMPOOL_NAME)
        vms.wait_for_vm_states(
            "{0}-{1}".format(config.VMPOOL_NAME, 1)
        )

        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Stopping pool %s.", config.VMPOOL_NAME)
        assert hl_vmpools.stop_vm_pool(config.VMPOOL_NAME)

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step("Waiting for VM %s-1.", config.VMPOOL_NAME)
        vms.wait_for_vm_states(
            "{0}-{1}".format(config.VMPOOL_NAME, 1),
            states=[common.ENUMS["vm_state_down"]]
        )


@tier1
class TestAdminPropertiesOfTemplate(common.BaseTestCase):
    """
    Test create of vm as PowerUserRole from template which has set
    administrator properties. He should be able to create such vm.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestAdminPropertiesOfTemplate, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown("Update template %s.", config.TEMPLATE_NAME[0])
            templates.updateTemplate(
                True,
                config.TEMPLATE_NAME[0],
                custom_properties='clear',
            )

            testflow.teardown("Removing user permissions from datacenter.")
            mla.removeUserPermissionsFromDatacenter(
                True,
                config.DC_NAME[0],
                config.USERS[0],
            )

            testflow.step("Removing user permissions from template.")
            mla.removeUserPermissionsFromTemplate(
                True,
                config.TEMPLATE_NAME[0],
                config.USERS[0],
            )

        request.addfinalizer(finalize)

        testflow.setup("Updating template %s.", config.TEMPLATE_NAME[0])
        assert templates.updateTemplate(
            True,
            config.TEMPLATE_NAME[0],
            custom_properties='sndbuf=10',
        )

        testflow.setup("Adding permissions for datacenter.")
        assert mla.addPermissionsForDataCenter(
            positive=True,
            user=config.USER_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.PowerUserRole,
        )

        testflow.setup("Adding permissions for template.")
        assert mla.addPermissionsForTemplate(
            positive=True,
            user=config.USER_NAMES[0],
            template=config.TEMPLATE_NAME[0],
            role=config.role.UserTemplateBasedVm,
        )

    @polarion('RHEVM3-14560')
    def test_create_vm_from_template_with_admin_props(self):
        """ Test create vm from template with admin properties set """
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Creating VM %s.", config.VM_NAMES[0])
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0],
        )

        testflow.step("Removing VM %s.", config.VM_NAMES[0])
        assert vms.removeVm(True, config.VM_NAMES[0])
