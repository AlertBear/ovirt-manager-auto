"""
Testing rhevm roles.
1 Host, 1 SD, 1 DC, 1 cluster will be created for test.
This will cover scenario for create/remove/editing/using roles.
"""
import logging
import pytest

from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.high_level import vmpools as hl_vmpools
from art.rhevm_api.tests_lib.low_level import (
    disks, mla, templates, users, vms,
    vmpools as ll_vmpools
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import testflow

import common
import config

INVALID_CHARS = '&^$%#*+/\\`~\"\':?!()[]}{=|><'

CANT_LOGIN = "Role %s not tested, because don't have login permissions."
ROLE_INFO = "Role named ({0}/{1}): {2}"

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        testflow.teardown("Log in as admin.")
        common.login_as_admin()

        testflow.teardown(
            "Removing user %s@%s.", config.USER_NAMES[0], config.USER_DOMAIN
        )
        users.removeUser(True, config.USER_NAMES[0])

        for vm_name in [config.VM_NAME, config.VM_NO_DISK]:
            testflow.teardown("Removing VM %s.", vm_name)
            vms.removeVm(True, vm_name)

        testflow.teardown("Removing disk %s.", config.DISK_NAME)
        disks.deleteDisk(True, config.DISK_NAME)
        disks.waitForDisksGone(True, config.DISK_NAME)

        testflow.teardown("Removing pool %s.", config.VMPOOL_NAME)
        hl_vmpools.remove_whole_vm_pool(config.VMPOOL_NAME)

        for template in [config.TEMPLATE_NAMES[0], config.TEMPLATE_NO_DISK]:
            testflow.teardown("Removing template %s.", template)
            templates.remove_template(True, template)

    request.addfinalizer(finalize)

    testflow.setup(
        "Adding user %s@%s.", config.USER_NAMES[0], config.USER_DOMAIN
    )
    common.add_user(
        True,
        user_name=config.USER_NAMES[0],
        domain=config.USER_DOMAIN
    )

    testflow.setup("Creating VM %s.", config.VM_NO_DISK)
    vms.createVm(
        positive=True,
        vmName=config.VM_NO_DISK,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE
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

    testflow.setup("Creating template %s.", config.TEMPLATE_NO_DISK)
    templates.createTemplate(
        True,
        vm=config.VM_NO_DISK,
        name=config.TEMPLATE_NO_DISK,
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
        states=[common.ENUMS["vm_state_down"]]
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


def retrieve_current_role(curr_role):
    return [
        temp_role for temp_role in mla.util.get(abs_link=False)
        if temp_role.name == curr_role.name
        ][0]


def get_role_permits(curr_role):
    return mla.util.getElemFromLink(
        curr_role,
        link_name='permits',
        attr='permit',
        get_href=False
    )


@tier2
class TestRoleCase54413(common.BaseTestCase):
    """
    Check that only users which are permitted to create role, can create role.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestRoleCase54413, cls).setup_class(request)

        def finalize():
            """ Recreate user """
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown(
                "Removing user %s@%s.",
                config.USER_NAMES[0],
                config.USER_DOMAIN,
            )
            try:
                users.removeUser(True, config.USER_NAMES[0])
            except EntityNotFound as err:
                logger.warning(err)

            testflow.teardown(
                "Adding user %s@%s.",
                config.USER_NAMES[0],
                config.USER_DOMAIN,
            )
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

    @polarion("RHEVM3-7141")
    def test_create_role_permissions(self):
        """ Check if user can add/del role if he has permissions for it """
        testflow.step("Getting roles.")
        roles = mla.util.get(abs_link=False)

        for index, curr_role in enumerate(roles, start=1):
            testflow.step("Log in as admin.")
            common.login_as_admin()

            testflow.step(
                "Adding user %s@%s.", config.USER_NAMES[0], config.USER_DOMAIN
            )
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )
            # need to retrieve the roles again since inside the loop we logout
            # which means disconnect from the server and reconnect again
            testflow.step("Getting current role.")
            curr_role = retrieve_current_role(curr_role)
            curr_role_name = curr_role.get_name()

            testflow.step(
                "Getting current role %s permissions.", curr_role.get_name()
            )
            role_permits = get_role_permits(curr_role)
            permit_list = [temp_role.get_name() for temp_role in role_permits]
            if 'login' not in permit_list:
                logger.info(CANT_LOGIN, curr_role_name)
                continue

            testflow.step(
                "Adding role %s to user %s@%s.",
                curr_role_name, config.USER_NAMES[0], config.USER_DOMAIN
            )
            assert users.addRoleToUser(
                True,
                config.USER_NAMES[0],
                curr_role_name
            )

            testflow.step("Log in as user.")
            common.login_as_user(filter_=not curr_role.administrative)
            if 'manipulate_roles' in permit_list:
                testflow.step("Adding role %s.", config.USER_ROLE)
                assert mla.addRole(
                    True,
                    name=config.USER_ROLE,
                    permits='login'
                )

                testflow.step("Removing role %s.", config.USER_ROLE)
                assert mla.removeRole(True, config.USER_ROLE)

                testflow.step("Adding role %s.", config.ADMIN_ROLE)
                assert mla.addRole(
                    True,
                    name=config.ADMIN_ROLE,
                    permits='login',
                    administrative='true'
                )

                testflow.step("Removing role %s.", config.ADMIN_ROLE)
                assert mla.removeRole(True, config.ADMIN_ROLE)
            else:
                testflow.step("Adding role %s.", config.USER_ROLE)
                assert mla.addRole(
                    False,
                    name=config.USER_ROLE,
                    permits='login'
                )

                testflow.step("Adding role %s.", config.ADMIN_ROLE)
                assert mla.addRole(
                    False,
                    name=config.ADMIN_ROLE,
                    permits='login'
                )

            testflow.step("Log in as admin.")
            common.login_as_admin()

            testflow.step(
                "Removing user %s@%s.",
                config.USER_NAMES[0], config.USER_DOMAIN
            )
            users.removeUser(True, config.USER_NAMES[0])


@tier2
class TestRoleCase54401(common.BaseTestCase):
    """
    Assign new role to users, check that role behave correctly after update.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestRoleCase54401, cls).setup_class(request)

        def finalize():
            """ Recreate user """
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            for user_name in config.USER_NAMES:
                try:
                    testflow.teardown(
                        "Removing user %s@%s.",
                        user_name,
                        config.USER_DOMAIN,
                    )
                    users.removeUser(True, user_name)
                except EntityNotFound as err:
                    logger.warning(err)

            testflow.teardown("Removing role %s.", config.USER_ROLE)
            mla.removeRole(True, config.USER_ROLE)

        request.addfinalizer(finalize)

        testflow.setup(
            "Adding user %s@%s.",
            config.USER_NAMES[0],
            config.USER_DOMAIN,
        )
        assert common.add_user(
            True,
            user_name=config.USER_NAMES[0],
            domain=config.USER_DOMAIN
        )

    @polarion("RHEVM3-7146")
    def test_edit_role(self):
        """ Try to update role and check if role is updated correctly """
        testflow.step("Adding role %s.", config.USER_ROLE)
        mla.addRole(True, name=config.USER_ROLE, permits='login')

        testflow.step(
            "Adding user %s@%s.", config.USER_NAMES[1], config.USER_DOMAIN
        )
        common.add_user(
            True,
            user_name=config.USER_NAMES[1],
            domain=config.USER_DOMAIN
        )
        # 1. Edit created role.
        testflow.step("Updating role %s.", config.USER_ROLE)
        assert mla.updateRole(
            True,
            config.USER_ROLE,
            description=config.USER_ROLE
        )

        # 2.Create several users and associate them with certain role.
        testflow.step(
            "Adding role %s to user %s@%s.",
            config.USER_ROLE, config.USER_NAMES[0], config.USER_DOMAIN
        )
        assert users.addRoleToUser(
            True,
            config.USER_NAMES[0],
            config.USER_ROLE
        )

        testflow.step(
            "Adding role %s to user %s@%s.",
            config.USER_NAMES[1], config.USER_ROLE, config.USER_DOMAIN
        )
        assert users.addRoleToUser(
            True,
            config.USER_NAMES[1],
            config.USER_ROLE
        )

        # 3.Create a new user and associate it with the role.
        testflow.step(
            "Adding user %s@%s.", config.USER_NAMES[2], config.USER_DOMAIN
        )
        assert common.add_user(
            True,
            user_name=config.USER_NAMES[2],
            domain=config.USER_DOMAIN
        )

        testflow.step(
            "Adding role %s to user %s@%s.",
            config.USER_ROLE, config.USER_NAMES[2], config.USER_DOMAIN
        )
        assert users.addRoleToUser(
            True,
            config.USER_NAMES[2],
            config.USER_ROLE
        )

        # 4.Edit new user's role.
        testflow.step("Log in as user.")
        common.login_as_user()

        with pytest.raises(EntityNotFound):
            testflow.step("Starting VM %s.", config.VM_NAME)
            vms.startVm(False, config.VM_NAME)

        testflow.step("Log in as admin.")
        common.login_as_admin()

        for permission in ['run_vm', 'stop_vm']:
            testflow.step(
                "Adding permission %s to role %s.",
                permission, config.USER_ROLE
            )
            assert mla.add_permission_to_role(
                positive=True,
                permission=permission,
                role=config.USER_ROLE
            )

        # 5.Check that after editing(changing) a role effect will be immediate.
        # User should operate vm now
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Starting VM %s.", config.VM_NAME)
        assert vms.startVm(True, config.VM_NAME)

        testflow.step("Stopping VM %s.", config.VM_NAME)
        assert vms.stopVm(True, config.VM_NAME)

        testflow.step(
            "Log in as user %s@%s.", config.USER_NAMES[2], config.USER_DOMAIN
        )
        common.login_as_user(user_name=config.USER_NAMES[2])

        testflow.step("Starting VM %s.", config.VM_NAME)
        assert vms.startVm(True, config.VM_NAME)

        testflow.step("Stopping VM %s.", config.VM_NAME)
        assert vms.stopVm(True, config.VM_NAME)


@tier2
class TestRoleCase54415(common.BaseTestCase):
    """ Try to get list of roles as user and non-admin user """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestRoleCase54415, cls).setup_class(request)

        def finalize():
            """ Recreate user """
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown(
                "Adding user %s@%s.", config.USER_NAMES[0], config.USER_DOMAIN
            )
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

    @polarion("RHEVM3-7140")
    def test_list_of_roles(self):
        """ Check if user can see all roles in system """
        testflow.step("Getting roles.")
        all_roles = mla.util.get(abs_link=False)
        non_admin_roles = [r for r in all_roles if not r.administrative]
        all_roles_size = len(all_roles)
        non_admin_size = len(non_admin_roles)

        for _, curr_role in enumerate(all_roles, start=1):
            testflow.step("Log in as admin.")
            common.login_as_admin()

            # need to retrieve the roles again since inside the loop we logout
            # which means disconnect from the server and reconnect again
            testflow.step("Getting current role.")
            curr_role = retrieve_current_role(curr_role)
            curr_role_name = curr_role.get_name()

            testflow.step("Getting permissions of current role")
            role_permits = get_role_permits(curr_role)

            def assertion_error():
                return "Something gone wrong with role role {0}".format(
                    curr_role_name
                )

            if 'login' not in [p.get_name() for p in role_permits]:
                continue

            # Create new user and assign current role
            testflow.step(
                "Adding user %s@%s.", config.USER_NAMES[0], config.USER_DOMAIN
            )
            assert common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

            testflow.step(
                "Adding role %s to user %s@%s",
                curr_role_name, config.USER_NAMES[0], config.USER_DOMAIN
            )
            assert users.addRoleToUser(
                True,
                config.USER_NAMES[0],
                curr_role_name
            )

            testflow.step("Logging as user.")
            common.login_as_user(filter_=not curr_role.administrative)

            # https://bugzilla.redhat.com/show_bug.cgi?id=1369219#c3
            if not curr_role.administrative:
                testflow.step(
                    "Checking if user can see all non administrative roles."
                )
                assert len(mla.util.get(abs_link=False)) == non_admin_size, (
                    assertion_error()
                )
            else:
                testflow.step(
                    "Checking if user can see all administrative roles."
                )
                assert len(mla.util.get(abs_link=False)) == all_roles_size, (
                    assertion_error()
                )

            testflow.step("Log in as admin.")
            common.login_as_admin()

            testflow.step(
                "Removing user %s@%s.",
                config.USER_NAMES[0], config.USER_DOMAIN
            )
            assert users.removeUser(True, config.USER_NAMES[0])


@tier2
class TestRoleCase54402(common.BaseTestCase):
    """
    Try to remove role which is assigned to user and that is not assigned
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestRoleCase54402, cls).setup_class(request)

        def finalize():
            """ Recreate user """
            testflow.teardown(
                "Removing user %s@%s.",
                config.USER_NAMES[0], config.USER_DOMAIN
            )
            users.removeUser(True, config.USER_NAMES[0])

            testflow.teardown(
                "Adding user %s@%s.", config.USER_NAMES[0], config.USER_DOMAIN
            )
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

    @polarion("RHEVM3-7145")
    def test_remove_role(self):
        """ Try to remove roles which are associated to objects """
        testflow.step("Adding role %s.", config.USER_ROLE)
        assert mla.addRole(True, name=config.USER_ROLE, permits='login')

        testflow.step("Adding role %s.", config.ADMIN_ROLE)
        assert mla.addRole(
            True,
            name=config.ADMIN_ROLE,
            permits='login',
            administrative='true'
        )

        testflow.step(
            "Adding VM %s permissions to user %s@%s.",
            config.VM_NAME, config.USER_NAMES[0], config.USER_DOMAIN
        )
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME,
            config.USER_ROLE
        )

        # Try to remove role that has no association with users.
        testflow.step("Removing role %s.", config.ADMIN_ROLE)
        assert mla.removeRole(True, config.ADMIN_ROLE)

        # Try to remove role that is associated with user.
        testflow.step("Removing role %s.", config.USER_ROLE)
        assert mla.removeRole(False, config.USER_ROLE)

        testflow.step(
            "Removing user %s@%s permissions from VM %s.",
            config.USERS[0], config.USER_DOMAIN, config.VM_NAME
        )
        assert mla.removeUserPermissionsFromVm(
            True,
            config.VM_NAME,
            config.USERS[0]
        )

        testflow.step("Removing role %s.", config.USER_ROLE)
        assert mla.removeRole(True, config.USER_ROLE)


@tier2
class TestRoleCase54366(common.BaseTestCase):
    """ Try to create role with illegal characters. """
    @polarion("RHEVM3-7138")
    def test_role_creation(self):
        """ Try to create role name with invalid characters """
        for char in INVALID_CHARS:
            testflow.step("Adding role %s.", char)
            assert mla.addRole(False, name=char, permits='login')


@tier2
class TestRoleCase54540(common.BaseTestCase):
    """ Try to remove predefined roles """
    @polarion("RHEVM3-7147")
    def test_remove_predefined_roles(self):
        """ Test that pre-defined roles can not be removed. """
        for role in mla.util.get(abs_link=False):
            testflow.step("Removing role %s.", role.get_name())
            assert mla.util.delete(role, False)


@tier2
class TestRoleCase54411(common.BaseTestCase):
    """
    Check there are some predefined roles. Names could change in future, so
    test if engine returns still same roles.
    """
    @polarion("RHEVM3-7143")
    def test_predefined_roles(self):
        """ Check if rhevm return still same predefined roles """
        testflow.step("Getting predefined roles.")
        predefined_length = len(mla.util.get(abs_link=False))

        testflow.step("Checking if predefined roles are the same.")
        assert len(mla.util.get(abs_link=False)) == predefined_length


@tier2
class TestRoleCase54403(common.BaseTestCase):
    """
    There is no support to copy role in REST.
    So testing copy role, as a get/add.
    """
    @polarion("RHEVM3-7144")
    def test_clone_role(self):
        """ Clone role """
        testflow.step("Adding role %s.", config.USER_ROLE)
        assert mla.addRole(True, name=config.USER_ROLE, permits='login')

        testflow.step("Removing role %s.", config.USER_ROLE)
        assert mla.removeRole(True, config.USER_ROLE)


@tier2
class TestRolesCase54412(common.BaseTestCase):
    """
    Assigning a Role to a object, means that the role apply to all the
    objects that are contained within object hierarchy.
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestRolesCase54412, cls).setup_class(request)

        def finalize():
            """ Recreate user """
            try:
                testflow.teardown(
                    "Removing user %s@%s.",
                    config.USER_NAMES[0], config.USER_DOMAIN
                )
                users.removeUser(True, config.USER_NAMES[0])
            except EntityNotFound as err:
                logger.warning(err)
            testflow.teardown(
                "Adding user %s@%s.", config.USER_NAMES[0], config.USER_DOMAIN
            )
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

    @polarion("RHEVM3-7142")
    def test_roles_hierarchy(self):
        """ Check if permissions are correctly inherited from objects """
        low_level = {
            config.CLUSTER_NAME[0]: vms.CLUSTER_API,
            config.DC_NAME[0]: vms.DC_API,
            config.STORAGE_NAME[0]: vms.STORAGE_DOMAIN_API,
        }
        high_level = {
            config.CLUSTER_NAME[0]:
                {
                    config.HOSTS[0]: vms.HOST_API,
                    config.VM_NAME: vms.VM_API,
                    config.VMPOOL_NAME: ll_vmpools.UTIL,
                    config.VM_NO_DISK: vms.VM_API
                },
            config.STORAGE_NAME[0]:
                {
                    config.DISK_NAME: vms.DISKS_API
                },
            config.DC_NAME[0]:
                {
                    config.HOSTS[0]: vms.HOST_API,
                    config.VM_NAME: vms.VM_API,
                    config.VMPOOL_NAME: ll_vmpools.UTIL,
                    config.TEMPLATE_NAMES[0]: vms.TEMPLATE_API,
                    config.VM_NO_DISK: vms.VM_API,
                }
        }

        for ll_key in low_level.keys():
            testflow.step("Testing propagated permissions from %s.", ll_key)
            testflow.step(
                "Adding user %s permissions for object %s.",
                config.USERS[0], ll_key
            )
            assert mla.addUserPermitsForObj(
                True,
                config.USER_NAMES[0],
                config.role.UserRole,
                low_level[ll_key].find(ll_key)
            )

            for hl_key, hl_val in high_level[ll_key].items():
                testflow.step(
                    "Checking inherited permissions for "
                    "object %s and role %s.",
                    hl_key, config.role.UserRole
                )
                assert common.check_if_object_has_role(
                    hl_val.find(hl_key),
                    config.role.UserRole
                )

            testflow.step(
                "Removing user %s permission from object %s.",
                config.USERS[0], ll_key
            )
            assert mla.removeUsersPermissionsFromObject(
                True,
                low_level[ll_key].find(ll_key),
                [config.USERS[0]]
            )
