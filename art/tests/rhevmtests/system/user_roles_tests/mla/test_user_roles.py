'''
Testing rhevm roles.
1 Host, 1 SD, 1 DC, 1 cluster will be created for test.
This will cover scenario for create/remove/editin/using roles.
'''

import logging

from rhevmtests.system.user_roles_tests import config
from rhevmtests.system.user_roles_tests.roles import role as role_e
from nose.tools import istest
from art.core_api.apis_exceptions import EntityNotFound
from art.unittest_lib import attr, CoreSystemTest as TestCase

from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level import (
    users, vms, disks, vmpools, templates, mla
)

LOGGER = logging.getLogger(__name__)

INVALID_CHARS = '&^$%#*+/\\`~\"\':?!()[]}{=|><'
TCMS_PLAN_ID = 2597


def loginAsAdmin():
    users.loginAsUser(
        config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
        config.VDC_PASSWORD, filter=False
    )


def setUpModule():
    users.addUser(True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)
    vms.createVm(
        True, config.VM_NO_DISK, '', cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE
    )
    vms.createVm(
        True, config.VM_NAME, '', cluster=config.CLUSTER_NAME[0],
        storageDomainName=config.MASTER_STORAGE, size=config.GB,
        network=config.MGMT_BRIDGE
    )
    templates.createTemplate(
        True, vm=config.VM_NAME, name=config.TEMPLATE_NAME,
        cluster=config.CLUSTER_NAME[0]
    )
    templates.createTemplate(
        True, vm=config.VM_NO_DISK, name=config.TEMPLATE_NO_DISK,
        cluster=config.CLUSTER_NAME[0]
    )
    vmpools.addVmPool(
        True, name=config.VMPOOL_NAME, size=1,
        cluster=config.CLUSTER_NAME[0], template=config.TEMPLATE_NAME
    )
    vms.waitForVMState('%s-%s' % (config.VMPOOL_NAME, 1), state='down')
    disks.addDisk(
        True, alias=config.DISK_NAME, interface='virtio', format='cow',
        provisioned_size=config.GB, storagedomain=config.MASTER_STORAGE
    )
    disks.wait_for_disks_status(config.DISK_NAME)


def tearDownModule():
    loginAsAdmin()
    users.removeUser(True, config.USER_NAME)
    vms.removeVm(True, config.VM_NAME)
    vms.removeVm(True, config.VM_NO_DISK)
    disks.deleteDisk(True, config.DISK_NAME)
    disks.waitForDisksGone(True, config.DISK_NAME)
    vmpools.detachVms(True, config.VMPOOL_NAME)
    vms.removeVm(True, '%s-%s' % (config.VMPOOL_NAME, 1))
    vmpools.removeVmPool(True, config.VMPOOL_NAME)
    templates.removeTemplate(True, config.TEMPLATE_NAME)
    templates.removeTemplate(True, config.TEMPLATE_NO_DISK)


def _retrieve_current_role(curr_role):
    return [
        temp_role for temp_role in mla.util.get(
            absLink=False
        ) if temp_role.name == curr_role.name
    ][0]


def _get_role_permits(curr_role):
    return mla.util.getElemFromLink(
        curr_role, link_name='permits', attr='permit', get_href=False
    )


@attr(tier=1)
class RoleCase54413(TestCase):
    """
    Check that only users which are permitted to create role, can create role.
    """
    __test__ = True

    @tcms(TCMS_PLAN_ID, 54413)
    @istest
    def createRolePerms(self):
        """ Check if user can add/del role if he has permissions for it """
        cantLogin = "Role %s not tested, because don't have login permissions."
        roles = mla.util.get(absLink=False)
        size = len(roles)

        for index, curr_role in enumerate(roles, start=1):
            LOGGER.info(
                "Role named ({0}/{1}): {2}".format(
                    index, size, curr_role.get_name()
                )
            )
            loginAsAdmin()
            users.addUser(True, user_name=config.USER_NAME,
                          domain=config.USER_DOMAIN)
            # need to retrieve the roles again since inside the loop we logout
            # which means disconnect from the server and reconnect again
            curr_role = _retrieve_current_role(curr_role)
            role_permits = _get_role_permits(curr_role)
            permit_list = [temp_role.get_name() for temp_role in role_permits]
            if 'login' not in permit_list:
                LOGGER.info(cantLogin, curr_role.get_name())
                continue

            self.assertTrue(users.addRoleToUser(
                True, config.USER_NAME, curr_role.get_name())
            )
            LOGGER.info(
                "Testing if role %s can add new role.", curr_role.get_name()
            )
            users.loginAsUser(
                config.USER_NAME, config.USER_DOMAIN, config.USER_PASSWORD,
                filter=not curr_role.administrative
            )
            if 'manipulate_roles' in permit_list:
                self.assertTrue(
                    mla.addRole(
                        True, name=config.USER_ROLE, permits='login'
                    )
                )
                self.assertTrue(mla.removeRole(True, config.USER_ROLE))
                self.assertTrue(
                    mla.addRole(
                        True,
                        name=config.ADMIN_ROLE,
                        permits='login',
                        administrative='true'
                    )
                )
                self.assertTrue(mla.removeRole(True, config.ADMIN_ROLE))
                LOGGER.info(
                    "%s can manipulate with roles.", curr_role.get_name()
                )
            else:
                self.assertTrue(
                    mla.addRole(
                        False, name=config.USER_ROLE, permits='login'
                    )
                )
                self.assertTrue(
                    mla.addRole(
                        False, name=config.ADMIN_ROLE, permits='login'
                    )
                )
                LOGGER.info(
                    "%s can't manipulate with roles.", curr_role.get_name()
                )
            loginAsAdmin()
            users.removeUser(True, config.USER_NAME)

    @classmethod
    def teardown_class(cls):
        """ Recreate user """
        loginAsAdmin()
        users.removeUser(True, config.USER_NAME)
        users.addUser(
            True,
            user_name=config.USER_NAME,
            domain=config.USER_DOMAIN
        )


@attr(tier=1)
class RoleCase54401(TestCase):
    """
    Assign new role to users, check that role behave correctly after update.
    """
    __test__ = True

    @tcms(TCMS_PLAN_ID, 54401)
    @istest
    def editRole(self):
        """ Try to update role and check if role is updated correctly """
        mla.addRole(True, name=config.USER_ROLE, permits='login')
        users.addUser(
            True, user_name=config.USER_NAME2, domain=config.USER_DOMAIN
        )
        # 1. Edit created role.
        self.assertTrue(
            mla.updateRole(
                True, config.USER_ROLE, description=config.USER_ROLE
            )
        )
        # 2.Create several users and associate them with certain role.
        self.assertTrue(
            users.addRoleToUser(
                True, config.USER_NAME, config.USER_ROLE
            )
        )
        self.assertTrue(
            users.addRoleToUser(
                True, config.USER_NAME2, config.USER_ROLE
            )
        )
        # 3.Create a new user and associate it with the role.
        self.assertTrue(
            users.addUser(
                True, user_name=config.USER_NAME3, domain=config.USER_DOMAIN
            )
        )
        self.assertTrue(
            users.addRoleToUser(
                True, config.USER_NAME3, config.USER_ROLE
            )
        )
        # 4.Edit new user's role.
        users.loginAsUser(
            config.USER_NAME, config.USER_DOMAIN,
            config.USER_PASSWORD, filter=True
        )
        self.assertRaises(
            EntityNotFound,
            vms.startVm,
            False,
            config.VM_NAME
        )

        loginAsAdmin()
        self.assertTrue(mla.addRolePermissions(
            True, config.USER_ROLE, permit='vm_basic_operations')
        )

        # 5.Check that after editing(changing) a role effect will be immediate.
        # User should operate vm now
        users.loginAsUser(
            config.USER_NAME, config.USER_DOMAIN,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(vms.startVm(True, config.VM_NAME))
        self.assertTrue(vms.stopVm(True, config.VM_NAME))
        users.loginAsUser(
            config.USER_NAME3, config.USER_DOMAIN,
            config.USER_PASSWORD, filter=True
        )
        self.assertTrue(vms.startVm(True, config.VM_NAME))
        self.assertTrue(vms.stopVm(True, config.VM_NAME))

    @classmethod
    def teardown_class(cls):
        """ Recreate user """
        loginAsAdmin()
        users.removeUser(True, config.USER_NAME)
        users.addUser(
            True,
            user_name=config.USER_NAME,
            domain=config.USER_DOMAIN
        )
        users.removeUser(True, config.USER_NAME2)
        users.removeUser(True, config.USER_NAME3)
        mla.removeRole(True, config.USER_ROLE)


@attr(tier=1)
class RoleCase54415(TestCase):
    """ Try to get list of roles as user and non-admin user """
    __test__ = True

    @tcms(TCMS_PLAN_ID, 54415)
    @istest
    def listOfRoles(self):
        """ Check if user can see all roles in system """
        msg = "Role %s is not tested because can't login."
        roles = mla.util.get(absLink=False)
        size = len(roles)

        for index, curr_role in enumerate(roles, start=1):
            LOGGER.info(
                "Role named ({0}/{1}): {2}".format(
                    index, size, curr_role.get_name()
                )
            )
            loginAsAdmin()
            self.assertTrue(
                users.addUser(
                    True, user_name=config.USER_NAME, domain=config.USER_DOMAIN
                )
            )
            # need to retrieve the roles again since inside the loop we logout
            # which means disconnect from the server and reconnect again
            curr_role = _retrieve_current_role(curr_role)
            role_permits = _get_role_permits(curr_role)
            if 'login' not in [p.get_name() for p in role_permits]:
                LOGGER.info(msg, curr_role.get_name())
                continue

            self.assertTrue(
                users.addUser(
                    True, user_name=config.USER_NAME, domain=config.USER_DOMAIN
                )
            )
            self.assertTrue(
                users.addRoleToUser(
                    True, config.USER_NAME, curr_role.get_name()
                )
            )
            users.loginAsUser(
                config.USER_NAME, config.USER_DOMAIN, config.USER_PASSWORD,
                filter=not curr_role.administrative
            )
            self.assertEqual(len(mla.util.get(absLink=False)), size)
            LOGGER.info(
                "User with role %s can see all roles.", curr_role.get_name()
            )
            loginAsAdmin()
            self.assertTrue(users.removeUser(True, config.USER_NAME))


@attr(tier=1)
class RoleCase54402(TestCase):
    """
    Try to remove role which is assigned to user and that is not assigned
    """
    __test__ = True

    @tcms(TCMS_PLAN_ID, 54402)
    @istest
    def removeRole(self):
        """ Try to remove roles which are associted to objects """
        msg = "Role %s can't be removed. It is associated with user."
        self.assertTrue(
            mla.addRole(
                True,
                name=config.USER_ROLE,
                permits='login'
            )
        )
        self.assertTrue(
            mla.addRole(
                True, name=config.ADMIN_ROLE,
                permits='login', administrative='true'
            )
        )

        self.assertTrue(
            mla.addVMPermissionsToUser(
                True, config.USER_NAME, config.VM_NAME, config.USER_ROLE
            )
        )
        # Try to remove role that has no association with users.
        self.assertTrue(mla.removeRole(True, config.ADMIN_ROLE))
        # Try to remove role that is associated with user.
        self.assertTrue(mla.removeRole(False, config.USER_ROLE))
        LOGGER.info(msg, config.USER_ROLE)
        self.assertTrue(
            mla.removeUserPermissionsFromVm(
                True, config.VM_NAME, config.USER1
            )
        )
        self.assertTrue(mla.removeRole(True, config.USER_ROLE))

    @classmethod
    def teardown_class(cls):
        """ Recreate user """
        users.removeUser(True, config.USER_NAME)
        users.addUser(
            True,
            user_name=config.USER_NAME,
            domain=config.USER_DOMAIN
        )


@attr(tier=1)
class RoleCase54366(TestCase):
    """ Try to create role with illegal characters. """
    __test__ = True

    @tcms(TCMS_PLAN_ID, 54366)
    @istest
    def roleCreation(self):
        """ Try to create role name with invalid characters """
        for char in INVALID_CHARS:
            self.assertTrue(mla.addRole(False, name=char, permits='login'))
            LOGGER.info("Role with char '%s' can't be created.", char)


@attr(tier=1)
class RoleCase54540(TestCase):
    """ Try to remove predefined roles """
    __test__ = True

    @tcms(TCMS_PLAN_ID, 54540)
    @istest
    def removePreDefinedRoles(self):
        """ Test that pre-defined roles can not be removed. """
        for role in mla.util.get(absLink=False):
            self.assertTrue(mla.util.delete(role, False))
            LOGGER.info(
                "Predefined role %s can't be removed.",
                role.get_name()
            )


@attr(tier=1)
class RoleCase54411(TestCase):
    """
    Check there are some predefined roles. Names could change in future, so
    test if engine returns still same roles.
    """
    __test__ = True

    @tcms(TCMS_PLAN_ID, 54411)
    @istest
    def predefinedRoles(self):
        """ Check if rhevm return still same predefined roles """
        l = len(mla.util.get(absLink=False))
        self.assertEqual(len(mla.util.get(absLink=False)), l)
        LOGGER.info("There are still same predefined roles.")


@attr(tier=1)
class RoleCase54403(TestCase):
    """
    There is no support to copy role in REST.
    So testing copy role, as a get/add.
    """
    __test__ = True

    @tcms(TCMS_PLAN_ID, 54403)
    @istest
    def cloneRole(self):
        """ Clone role """
        self.assertTrue(
            mla.addRole(
                True,
                name=config.USER_ROLE,
                permits='login'
            )
        )
        self.assertTrue(mla.removeRole(True, config.USER_ROLE))


@attr(tier=1)
class RolesCase54412(TestCase):
    """
    Assigning a Role to a object, means that the role apply to all the
    objects that are contained within object hierarchy.
    """
    __test__ = True

    @tcms(TCMS_PLAN_ID, 54412)
    @bz({949950: {}, 977304: {}})
    @istest
    def rolesHiearchy(self):
        """ Check if permissions are correctly inherited from objects """

        def checkIfObjectHasRole(obj, role):
            objPermits = mla.permisUtil.getElemFromLink(obj, get_href=False)
            roleNAid = users.rlUtil.find(role).get_id()
            return roleNAid in [
                perm.get_role().get_id() for perm in objPermits
            ]

        msg_f = "Object don't have inherited perms."
        msg_t = "Object have inherited perms."
        l = {
            config.CLUSTER_NAME[0]: vms.CLUSTER_API,
            config.DC_NAME[0]: vms.DC_API,
            config.MASTER_STORAGE: vms.STORAGE_DOMAIN_API,
        }
        h = {
            config.CLUSTER_NAME[0]:
            {
                config.HOSTS[0]: vms.HOST_API,
                config.VM_NAME: vms.VM_API,
                config.VMPOOL_NAME: vmpools.util,
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
                config.VMPOOL_NAME: vmpools.util,
                config.TEMPLATE_NAME: vms.TEMPLATE_API,
                config.VM_NO_DISK: vms.VM_API,
                config.TEMPLATE_NO_DISK: vms.TEMPLATE_API
            }
        }

        b = False
        for k in l.keys():
            LOGGER.info("Testing propagated permissions from %s", k)
            mla.addUserPermitsForObj(
                True, config.USER_NAME, role_e.UserRole, l[k].find(k)
            )
            for key, val in h[k].items():
                LOGGER.info("Checking inherited permissions for '%s'" % key)
                a = not checkIfObjectHasRole(val.find(key), role_e.UserRole)
                LOGGER.error(msg_f) if a else LOGGER.info(msg_t)
                b = b or a

            mla.removeUsersPermissionsFromObject(
                True, l[k].find(k), [config.USER1]
            )

        self.assertFalse(b)

    @classmethod
    def teardown_class(cls):
        """ Recreate user """
        try:
            users.removeUser(True, config.USER_NAME)
        except EntityNotFound:
            pass
        users.addUser(
            True,
            user_name=config.USER_NAME,
            domain=config.USER_DOMAIN
        )
