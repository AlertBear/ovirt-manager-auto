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
from art.unittest_lib import attr

from rhevmtests.system.user_tests.mla import common, config

INVALID_CHARS = '&^$%#*+/\\`~\"\':?!()[]}{=|><'

CANT_LOGIN = "Role %s not tested, because don't have login permissions."
ROLE_INFO = "Role named ({0}/{1}): {2}"

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        common.login_as_admin()

        common.remove_user(True, config.USER_NAMES[0])

        vms.removeVm(True, config.VM_NAME)
        vms.removeVm(True, config.VM_NO_DISK)

        disks.deleteDisk(True, config.DISK_NAME)
        disks.waitForDisksGone(True, config.DISK_NAME)

        hl_vmpools.detach_vms_from_pool(config.VMPOOL_NAME)
        vms.removeVm(True, "{0}-{1}".format(config.VMPOOL_NAME, 1))
        ll_vmpools.removeVmPool(True, config.VMPOOL_NAME)
        templates.remove_template(True, config.TEMPLATE_NAMES[0])
        templates.remove_template(True, config.TEMPLATE_NO_DISK)

    request.addfinalizer(finalize)

    common.add_user(
        True,
        user_name=config.USER_NAMES[0],
        domain=config.USER_DOMAIN
    )

    vms.createVm(
        positive=True,
        vmName=config.VM_NO_DISK,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE
    )

    vms.createVm(
        positive=True,
        vmName=config.VM_NAME,
        cluster=config.CLUSTER_NAME[0],
        storageDomainName=config.MASTER_STORAGE,
        provisioned_size=config.GB,
        network=config.MGMT_BRIDGE
    )

    templates.createTemplate(
        True,
        vm=config.VM_NAME,
        name=config.TEMPLATE_NAMES[0],
        cluster=config.CLUSTER_NAME[0]
    )

    templates.createTemplate(
        True,
        vm=config.VM_NO_DISK,
        name=config.TEMPLATE_NO_DISK,
        cluster=config.CLUSTER_NAME[0]
    )

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

    disks.addDisk(
        True,
        alias=config.DISK_NAME,
        interface='virtio',
        format='cow',
        provisioned_size=config.GB,
        storagedomain=config.MASTER_STORAGE
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


@attr(tier=2)
class RoleCase54413(common.BaseTestCase):
    """
    Check that only users which are permitted to create role, can create role.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(RoleCase54413, cls).setup_class(request)

        def finalize():
            """ Recreate user """
            common.login_as_admin()
            common.remove_user(True, config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

    @polarion("RHEVM3-7141")
    def test_create_role_permissions(self):
        """ Check if user can add/del role if he has permissions for it """
        testing_msg = "Testing if role %s can add new role."
        roles = mla.util.get(abs_link=False)
        size = len(roles)

        for index, curr_role in enumerate(roles, start=1):
            logger.info(ROLE_INFO.format(index, size, curr_role.get_name()))

            common.login_as_admin()
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )
            # need to retrieve the roles again since inside the loop we logout
            # which means disconnect from the server and reconnect again
            curr_role = retrieve_current_role(curr_role)
            curr_role_name = curr_role.get_name()
            role_permits = get_role_permits(curr_role)
            permit_list = [temp_role.get_name() for temp_role in role_permits]
            if 'login' not in permit_list:
                logger.info(CANT_LOGIN, curr_role_name)
                continue

            assert users.addRoleToUser(
                True,
                config.USER_NAMES[0],
                curr_role_name
            )
            logger.info(testing_msg, curr_role_name)

            common.login_as_user(filter_=not curr_role.administrative)
            if 'manipulate_roles' in permit_list:
                assert mla.addRole(
                    True,
                    name=config.USER_ROLE,
                    permits='login'
                )
                assert mla.removeRole(True, config.USER_ROLE)
                assert mla.addRole(
                    True,
                    name=config.ADMIN_ROLE,
                    permits='login',
                    administrative='true'
                )
                assert mla.removeRole(True, config.ADMIN_ROLE)
                logger.info(
                    "%s can manipulate with roles.",
                    curr_role.get_name()
                )
            else:
                assert mla.addRole(
                    False,
                    name=config.USER_ROLE,
                    permits='login'
                )
                assert mla.addRole(
                    False,
                    name=config.ADMIN_ROLE,
                    permits='login'
                )
                logger.info(
                    "%s can't manipulate with roles.",
                    curr_role.get_name()
                )
            common.login_as_admin()
            common.remove_user(True, config.USER_NAMES[0])


@attr(tier=2)
class RoleCase54401(common.BaseTestCase):
    """
    Assign new role to users, check that role behave correctly after update.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(RoleCase54401, cls).setup_class(request)

        def finalize():
            """ Recreate user """
            common.login_as_admin()
            common.remove_user(True, config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )
            common.remove_user(True, config.USER_NAMES[1])
            common.remove_user(True, config.USER_NAMES[2])
            mla.removeRole(True, config.USER_ROLE)

        request.addfinalizer(finalize)

    @polarion("RHEVM3-7146")
    def test_edit_role(self):
        """ Try to update role and check if role is updated correctly """
        mla.addRole(True, name=config.USER_ROLE, permits='login')
        common.add_user(
            True,
            user_name=config.USER_NAMES[1],
            domain=config.USER_DOMAIN
        )
        # 1. Edit created role.
        assert mla.updateRole(
            True,
            config.USER_ROLE,
            description=config.USER_ROLE
        )
        # 2.Create several users and associate them with certain role.
        assert users.addRoleToUser(
            True,
            config.USER_NAMES[0],
            config.USER_ROLE
        )
        assert users.addRoleToUser(
            True,
            config.USER_NAMES[1],
            config.USER_ROLE
        )
        # 3.Create a new user and associate it with the role.
        assert common.add_user(
            True,
            user_name=config.USER_NAMES[2],
            domain=config.USER_DOMAIN
        )
        assert users.addRoleToUser(
            True,
            config.USER_NAMES[2],
            config.USER_ROLE
        )
        # 4.Edit new user's role.
        common.login_as_user()
        with pytest.raises(EntityNotFound):
            vms.startVm(False, config.VM_NAME)

        common.login_as_admin()
        for permission in ['run_vm', 'stop_vm']:
            assert mla.add_permission_to_role(
                positive=True,
                permission=permission,
                role=config.USER_ROLE
            )

        # 5.Check that after editing(changing) a role effect will be immediate.
        # User should operate vm now
        common.login_as_user()
        assert vms.startVm(True, config.VM_NAME)
        assert vms.stopVm(True, config.VM_NAME)

        common.login_as_user(user_name=config.USER_NAMES[2])
        assert vms.startVm(True, config.VM_NAME)
        assert vms.stopVm(True, config.VM_NAME)


@attr(tier=2)
class RoleCase54415(common.BaseTestCase):
    """ Try to get list of roles as user and non-admin user """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(RoleCase54415, cls).setup_class(request)

        def finalize():
            """ Recreate user """
            common.login_as_admin()
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

    @polarion("RHEVM3-7140")
    def test_list_of_roles(self):
        """ Check if user can see all roles in system """
        msg = "Role %s is not tested because can't login."
        ok_adm_msg = "User with role %s can see all roles."
        ok_non_adm_msg = (
            "User with role %s can see only non administrative roles"
        )
        all_roles = mla.util.get(abs_link=False)
        non_admin_roles = [r for r in all_roles if not r.administrative]
        all_roles_size = len(all_roles)
        non_admin_size = len(non_admin_roles)

        for index, curr_role in enumerate(all_roles, start=1):
            logger.info(ROLE_INFO.format(
                index,
                all_roles_size,
                curr_role.get_name())
            )
            common.login_as_admin()

            # need to retrieve the roles again since inside the loop we logout
            # which means disconnect from the server and reconnect again
            curr_role = retrieve_current_role(curr_role)
            curr_role_name = curr_role.get_name()
            role_permits = get_role_permits(curr_role)

            def assertion_error():
                return "Something gone wrong with role role {0}".format(
                    curr_role_name
                )

            if 'login' not in [p.get_name() for p in role_permits]:
                logger.info(msg, curr_role_name)
                continue

            # Create new user and assign current role
            assert common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )
            assert users.addRoleToUser(
                True,
                config.USER_NAMES[0],
                curr_role.get_name()
            )

            common.login_as_user(filter_=not curr_role.administrative)

            # https://bugzilla.redhat.com/show_bug.cgi?id=1369219#c3
            if not curr_role.administrative:
                assert len(mla.util.get(abs_link=False)) == non_admin_size, \
                    assertion_error()
                logger.info(ok_non_adm_msg, curr_role_name)
            else:
                assert len(mla.util.get(abs_link=False)) == all_roles_size, \
                    assertion_error()
                logger.info(ok_adm_msg, curr_role_name)

            common.login_as_admin()
            assert common.remove_user(True, config.USER_NAMES[0])


@attr(tier=2)
class RoleCase54402(common.BaseTestCase):
    """
    Try to remove role which is assigned to user and that is not assigned
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(RoleCase54402, cls).setup_class(request)

        def finalize():
            """ Recreate user """
            common.remove_user(True, config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

    @polarion("RHEVM3-7145")
    def test_remove_role(self):
        """ Try to remove roles which are associated to objects """
        msg = "Role %s can't be removed. It is associated with user."
        assert mla.addRole(True, name=config.USER_ROLE, permits='login')
        assert mla.addRole(
            True,
            name=config.ADMIN_ROLE,
            permits='login',
            administrative='true'
        )

        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME,
            config.USER_ROLE
        )

        # Try to remove role that has no association with users.
        assert mla.removeRole(True, config.ADMIN_ROLE)

        # Try to remove role that is associated with user.
        assert mla.removeRole(False, config.USER_ROLE)

        logger.info(msg, config.USER_ROLE)

        assert mla.removeUserPermissionsFromVm(
            True,
            config.VM_NAME,
            config.USERS[0]
        )
        assert mla.removeRole(True, config.USER_ROLE)


@attr(tier=2)
class RoleCase54366(common.BaseTestCase):
    """ Try to create role with illegal characters. """
    __test__ = True

    @polarion("RHEVM3-7138")
    def test_role_creation(self):
        """ Try to create role name with invalid characters """
        for char in INVALID_CHARS:
            assert mla.addRole(False, name=char, permits='login')
            logger.info("Role with char '%s' can't be created.", char)


@attr(tier=2)
class RoleCase54540(common.BaseTestCase):
    """ Try to remove predefined roles """
    __test__ = True

    @polarion("RHEVM3-7147")
    def test_remove_predefined_roles(self):
        """ Test that pre-defined roles can not be removed. """
        msg = "Predefined role %s can't be removed."
        for role in mla.util.get(abs_link=False):
            assert mla.util.delete(role, False)
            logger.info(msg, role.get_name())


@attr(tier=2)
class RoleCase54411(common.BaseTestCase):
    """
    Check there are some predefined roles. Names could change in future, so
    test if engine returns still same roles.
    """
    __test__ = True

    @polarion("RHEVM3-7143")
    def test_predefined_roles(self):
        """ Check if rhevm return still same predefined roles """
        l = len(mla.util.get(abs_link=False))
        assert len(mla.util.get(abs_link=False)) == l
        logger.info("There are still same predefined roles.")


@attr(tier=2)
class RoleCase54403(common.BaseTestCase):
    """
    There is no support to copy role in REST.
    So testing copy role, as a get/add.
    """
    __test__ = True

    @polarion("RHEVM3-7144")
    def test_clone_role(self):
        """ Clone role """
        assert mla.addRole(True, name=config.USER_ROLE, permits='login')
        assert mla.removeRole(True, config.USER_ROLE)


@attr(tier=2)
class RolesCase54412(common.BaseTestCase):
    """
    Assigning a Role to a object, means that the role apply to all the
    objects that are contained within object hierarchy.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(RolesCase54412, cls).setup_class(request)

        def finalize():
            """ Recreate user """
            try:
                common.remove_user(True, config.USER_NAMES[0])
            except EntityNotFound:
                pass
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

    @polarion("RHEVM3-7142")
    def test_roles_hierarchy(self):
        """ Check if permissions are correctly inherited from objects """
        msg_f = "Object don't have inherited permissions."
        msg_t = "Object have inherited permissions."

        low_level = {
            config.CLUSTER_NAME[0]: vms.CLUSTER_API,
            config.DC_NAME[0]: vms.DC_API,
            config.MASTER_STORAGE: vms.STORAGE_DOMAIN_API,
        }
        high_level = {
            config.CLUSTER_NAME[0]:
                {
                    config.HOSTS[0]: vms.HOST_API,
                    config.VM_NAME: vms.VM_API,
                    config.VMPOOL_NAME: ll_vmpools.UTIL,
                    config.VM_NO_DISK: vms.VM_API
                },
            config.MASTER_STORAGE:
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

        error = False
        for ll_key in low_level.keys():
            logger.info("Testing propagated permissions from %s", ll_key)
            mla.addUserPermitsForObj(
                True,
                config.USER_NAMES[0],
                config.role.UserRole,
                low_level[ll_key].find(ll_key)
            )

            for hl_key, hl_val in high_level[ll_key].items():
                logger.info("Checking inherited permissions for '%s'", hl_key)
                nested_error = not common.check_if_object_has_role(
                    hl_val.find(hl_key),
                    config.role.UserRole
                )
                logger.error(msg_f) if nested_error else logger.info(msg_t)
                error = error or nested_error

            mla.removeUsersPermissionsFromObject(
                True,
                low_level[ll_key].find(ll_key),
                [config.USERS[0]]
            )

        assert not error
