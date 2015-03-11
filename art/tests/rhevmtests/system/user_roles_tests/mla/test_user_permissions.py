'''
Testing working with permissions.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Tests if permissions are correctly inherited/viewed/assigned/removed.
'''

__test__ = True

import logging
import time

from rhevmtests.system.user_roles_tests import config
from rhevmtests.system.user_roles_tests.roles import role
from nose.tools import istest
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.rhevm_api.tests_lib.high_level import storagedomains as h_sd
from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.low_level import (
    users, vms, disks, vmpools, templates, mla, clusters, datacenters, hosts,
    storagedomains
)

LOGGER = logging.getLogger(__name__)
TCMS_PLAN_ID = 2602
# Predefined role for creation of VM as non-admin user
VM_PREDEFINED = role.UserVmManager
# Predefined role for creation of Disk as non-admin user
DISK_PREDEFINED = role.DiskOperator
# Predefined role for creation of Template as non-admin user
TEMPLATE_PREDEFINED = role.TemplateOwner


def loginAsUser(user_name, filter=True):
    users.loginAsUser(
        user_name, config.USER_DOMAIN, config.USER_PASSWORD, filter=filter
    )


def loginAsAdmin():
    users.loginAsUser(
        config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
        config.VDC_PASSWORD, filter=False
    )


def setUpModule():
    users.addUser(True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)
    users.addUser(True, user_name=config.USER_NAME2, domain=config.USER_DOMAIN)
    users.addUser(True, user_name=config.USER_NAME3, domain=config.USER_DOMAIN)

    vms.createVm(
        True, config.VM_NAME, '', cluster=config.CLUSTER_NAME[0],
        storageDomainName=config.MASTER_STORAGE, size=config.GB,
        network=config.MGMT_BRIDGE
    )
    templates.createTemplate(
        True, vm=config.VM_NAME, name=config.TEMPLATE_NAME,
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
    users.removeUser(True, config.USER_NAME2)
    users.removeUser(True, config.USER_NAME3)
    vms.removeVm(True, config.VM_NAME)
    disks.deleteDisk(True, config.DISK_NAME)
    disks.waitForDisksGone(True, config.DISK_NAME)
    vmpools.detachVms(True, config.VMPOOL_NAME)
    vm_name = '%s-1' % config.VMPOOL_NAME
    vms.waitForVMState(vm_name, state='down')
    vms.removeVm(True, vm_name)
    vmpools.removeVmPool(True, config.VMPOOL_NAME)
    templates.removeTemplate(True, config.TEMPLATE_NAME)
    test_utils.wait_for_tasks(
        config.VDC_HOST, config.VDC_ROOT_PASSWORD, config.DC_NAME[0]
    )


@attr(tier=0)
class PermissionsCase54408(TestCase):
    """ objects and user permissions """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        # Test these object for adding/removing/viewving perms on it
        cls.OBJS = {
            config.VM_NAME: vms.VM_API,
            config.TEMPLATE_NAME: templates.TEMPLATE_API,
            config.DISK_NAME: disks.DISKS_API,
            config.VMPOOL_NAME: vmpools.util,
            config.CLUSTER_NAME[0]: clusters.util,
            config.DC_NAME[0]: datacenters.util,
            config.HOSTS[0]: hosts.HOST_API,
            config.MASTER_STORAGE: storagedomains.util
        }

    # Check that there are two types of Permissions sub-tabs in the system:
    # for objects on which you can define permissions and for users.
    @istest
    @tcms(TCMS_PLAN_ID, 54408)
    def objectsAndUserPermissions(self):
        """ objects and user permissions """
        msg = '%s has permissions subcollection.'

        for k in self.OBJS.keys():
            obj = self.OBJS[k].find(k)
            href = '%s/permissions' % obj.get_href()
            assert self.OBJS[k].get(href=href) is not None
            LOGGER.info(msg % obj.get_name())


@attr(tier=0)
class PermissionsCase54409(TestCase):
    """" permissions inheritence """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        users.addRoleToUser(True, config.USER_NAME, role.ClusterAdmin)

    @classmethod
    def tearDownClass(cls):
        loginAsAdmin()
        users.removeUser(True, config.USER_NAME)
        users.addUser(
            True, user_name=config.USER_NAME, domain=config.USER_DOMAIN
        )

    @istest
    @tcms(TCMS_PLAN_ID, 54409)
    def permissionsInheritence(self):
        """ permissions inheritence """
        loginAsUser(config.USER_NAME, filter=False)
        self.assertTrue(
            vms.createVm(
                True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
                network=config.MGMT_BRIDGE
            )
        )
        self.assertTrue(vms.removeVm(True, config.VM_NAME1))
        LOGGER.info("User can create/remove vm with vm permissions.")

        loginAsAdmin()
        users.removeUser(True, config.USER_NAME)
        users.addUser(
            True, user_name=config.USER_NAME, domain=config.USER_DOMAIN
        )
        # To be able login
        mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.CLUSTER_NAME[0], role.UserRole
        )

        loginAsUser(config.USER_NAME)
        self.assertTrue(
            vms.createVm(
                False, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
                network=config.MGMT_BRIDGE
            )
        )
        LOGGER.info("User can't create/remove vm without vm permissions.")


# Check that in the object Permissions sub tab you will see all permissions
# that were associated with the selected object in the main grid or one of
# its ancestors.
@attr(tier=0)
class PermissionsCase5441054414(TestCase):
    """" permissions subtab """
    __test__ = True

    @istest
    @tcms(TCMS_PLAN_ID, '54410,54414')
    def permissionsSubTab(self):
        """ permissions subtab """
        # Try to add UserRole and AdminRole to object, then
        # check if both role are vissbile via /api/objects/objectid/permissions
        msg = "There are vissible all permissions which were associated."

        u1 = users.util.find(config.USER_NAME)
        u2 = users.util.find(config.USER_NAME2)
        LOGGER.info("Testing object %s" % config.VM_NAME)
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NAME, role=role.UserRole
        )
        mla.addVMPermissionsToUser(
            True, config.USER_NAME2, config.VM_NAME, role=role.UserRole
        )
        vm = vms.VM_API.find(config.VM_NAME)
        rolePermits = mla.permisUtil.getElemFromLink(vm,  get_href=False)
        users_id = [perm.user.get_id() for perm in rolePermits if perm.user]
        assert u1.get_id() in users_id and u2.get_id() in users_id
        LOGGER.info(msg)
        mla.removeUserPermissionsFromVm(True, config.VM_NAME, config.USER1)
        mla.removeUserPermissionsFromVm(True, config.VM_NAME, config.USER2)


# Assuming that there is always Super-Admin user on RHEV-M.
# Try to remove last permission on certain object.
# This also tests 54410
# It should be impossile to remove last Super-admin user with permission on
# system object.
# Try to remove last super-admin user with permission on system object.
# Try to remoce super-admin + system permission from the user.
@attr(tier=1)
class PermissionsCase5441854419(TestCase):
    """ last permission on object and test removal of SuperUser """
    __test__ = True

    @istest
    @tcms(TCMS_PLAN_ID, 54418)
    def lastPermOnObject(self):
        """ last permission on object """
        loginAsAdmin()
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME)
        mla.removeUserPermissionsFromVm(True, config.VM_NAME, config.USER1)

    @istest
    @tcms(TCMS_PLAN_ID, 54419)
    def removalOfSuperUser(self):
        """ test removal of SuperUser """
        assert users.removeUser(False, 'admin@internal', 'internal')
        assert mla.removeUserRoleFromDataCenter(
            False, config.DC_NAME[0], 'admin@internal', role.SuperUser
        )
        LOGGER.info(
            'Unable to remove admin@internal or his SuperUser permissions.'
        )


# Try to add a permission associated with an
# administrator Role (i.e. "Administrator Permission") to another user when
# you don't have "Super-Admin" permission on the "System" object". - FAILED
# When you're user/super user ,try to delegate permission to another
# user/super user. - SUCCESS
@attr(tier=1)
class PermissionsCase54425(TestCase):
    """ test delegate perms """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

    @classmethod
    def tearDownClass(cls):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        users.removeUser(True, config.USER_NAME)
        users.addUser(
            True, user_name=config.USER_NAME, domain=config.USER_DOMAIN
        )

    @istest
    @tcms(TCMS_PLAN_ID, 54425)
    def delegatePerms(self):
        """ delegate perms """
        # Test SuperUser that he can add permissions
        for role_obj in mla.util.get(absLink=False):
            r = role_obj.get_name()
            LOGGER.info("Testing role - %s" % r)
            # Get roles perms, to check for manipulate_permissions
            role_obj = mla.util.find(r)  # multi user switching hack
            rolePermits = mla.util.getElemFromLink(
                role_obj, link_name='permits', attr='permit', get_href=False
            )
            perms = [p.get_name() for p in rolePermits]
            if 'login' not in perms:
                LOGGER.info("User not tested, because don't have login perms.")
                continue

            users.addRoleToUser(True, config.USER_NAME, r)
            mla.addVMPermissionsToUser(
                True, config.USER_NAME, config.VM_NAME1, r
            )

            # For know if login as User/Admin
            filt = not role_obj.administrative
            # login as user with role
            loginAsUser(config.USER_NAME, filter=filt)
            # Test if user with role can/can't manipualte perms
            if 'manipulate_permissions' in perms:
                if filt or role.SuperUser != r:
                    try:
                        mla.addVMPermissionsToUser(
                            False, config.USER_NAME, config.VM_NAME1,
                            role.TemplateAdmin
                        )
                    except:  # Ignore, user should not add perms
                        pass
                    LOGGER.info("'%s' can't add admin permissions." % r)
                    self.assertTrue(
                        mla.addVMPermissionsToUser(
                            True, config.USER_NAME, config.VM_NAME1
                        )
                    )
                    LOGGER.info("'%s' can add user permissions." % r)
                else:
                    self.assertTrue(
                        mla.addVMPermissionsToUser(
                            True, config.USER_NAME, config.VM_NAME1,
                            role.UserRole
                        )
                    )
                    LOGGER.info("'%s' can add user permissions." % r)
                    self.assertTrue(
                        mla.addVMPermissionsToUser(
                            True, config.USER_NAME, config.VM_NAME1,
                            role.TemplateAdmin
                        )
                    )
                    LOGGER.info("'%s' can add admin permissions." % r)
            else:
                try:
                    mla.addVMPermissionsToUser(
                        False, config.USER_NAME, config.VM_NAME1, role.UserRole
                    )
                except:  # Ignore, user should not add perms
                    pass
                LOGGER.info("'%s' can't manipulate permisisons." % r)

            loginAsAdmin()
            users.removeUser(True, config.USER_NAME)
            users.addUser(
                True, user_name=config.USER_NAME, domain=config.USER_DOMAIN
            )

    # in order ro add new object you will need the appropriate permission on
    # the ancestor (e.g. to create a new storage domain you'll need a "add
    # storage domain" permission on the "system" object,to create a new Host/VM
    # you will need appropriate permission on the relevant cluster.
    @istest
    @tcms(TCMS_PLAN_ID, 54432)
    def newObjectCheckPerms(self):
        """ Adding new business entity/new object. """
        msg = "This functionality tests modules admin_tests and user_tests"
        LOGGER.info(msg)


# Check if user is under some Group if it has permissions of its group
@attr(tier=1)
class PermissionsCase54446(TestCase):
    """ Check if user is under some Group if has permissions of its group """
    __test__ = True

    @classmethod
    def setUpClass(self):
        users.addGroup(
            True,
            config.GROUP_NAME,
            config.USER_DOMAIN
        )
        mla.addClusterPermissionsToGroup(
            True, config.GROUP_NAME, config.CLUSTER_NAME[0], role.UserVmManager
        )

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        users.removeUser(True, config.GROUP_USER)
        users.deleteGroup(True, config.GROUP_NAME)

    @istest
    @tcms(TCMS_PLAN_ID, 54446)
    def usersPermissions(self):
        """ users permissions """
        loginAsUser(config.GROUP_USER)
        self.assertTrue(
            vms.createVm(
                True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
                network=config.MGMT_BRIDGE
            )
        )
        self.assertTrue(
            templates.createTemplate(
                False, vm=config.VM_NAME1, name=config.TEMPLATE_NAME2,
                cluster=config.CLUSTER_NAME[0]
            )
        )


# Creating object from user API and admin API should be different:
# for example admin API - createVm - should not delegate perms on VM
# user API - createVm - should add perms UserVmManager on VM
@attr(tier=1)
class PermissionsCase54420(TestCase):
    """ Object creating from User and Admin portal """
    __test__ = True

    @istest
    @bz(881145)
    @tcms(TCMS_PLAN_ID, 54420)
    def objAdminUser(self):
        """ Object creating from User and Admin portal """
        # This is already implemented in test_user_roles
        def checkIfObjectHasRole(obj, role, admin):
            objPermits = mla.permisUtil.getElemFromLink(obj, get_href=False)
            roleNAid = users.rlUtil.find(role).get_id()
            perms_ids = [perm.get_role().get_id() for perm in objPermits]
            isIn = roleNAid in perms_ids
            return (not admin) == isIn

        b = False

        for rr in [role.VmCreator, role.TemplateCreator, role.SuperUser]:
            loginAsAdmin()
            role_obj = users.rlUtil.find(rr)
            rolePermits = mla.util.getElemFromLink(
                role_obj, link_name='permits', attr='permit', get_href=False
            )
            r_permits = [p.get_name() for p in rolePermits]

            users.addRoleToUser(True, config.USER_NAME, rr)
            mla.addClusterPermissionsToUser(
                True, config.USER_NAME, config.CLUSTER_NAME[0], role.UserRole
            )
            loginAsUser(config.USER_NAME, filter=not role_obj.administrative)

            LOGGER.info("Testing role - " + role_obj.get_name())
            # Create vm,template, disk and check permissions of it
            if 'create_vm' in r_permits:
                LOGGER.info("Testing create_vm.")
                vms.createVm(
                    True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
                    network=config.MGMT_BRIDGE
                )
                b = b or checkIfObjectHasRole(
                    vms.VM_API.find(config.VM_NAME1),
                    VM_PREDEFINED,
                    role_obj.administrative
                )
                loginAsAdmin()
                vms.removeVm(True, config.VM_NAME1)
            if 'create_template' in r_permits:
                LOGGER.info("Testing create_template.")
                templates.createTemplate(
                    True, vm=config.VM_NAME, name=config.TEMPLATE_NAME2,
                    cluster=config.CLUSTER_NAME[0]
                )
                b = b or checkIfObjectHasRole(
                    templates.TEMPLATE_API.find(config.TEMPLATE_NAME2),
                    TEMPLATE_PREDEFINED, role_obj.administrative
                )
                loginAsAdmin()
                templates.removeTemplate(True, config.TEMPLATE_NAME2)
            if 'create_disk' in r_permits:
                LOGGER.info("Testing create_disk.")
                disks.addDisk(
                    True, alias=config.DISK_NAME1,
                    interface='virtio', format='cow',
                    provisioned_size=config.GB,
                    storagedomain=config.MASTER_STORAGE
                )
                disks.wait_for_disks_status(config.DISK_NAME1)
                b = b or checkIfObjectHasRole(
                    disks.DISKS_API.find(config.DISK_NAME1),
                    DISK_PREDEFINED, role_obj.administrative
                )

                loginAsAdmin()
                disks.deleteDisk(True, config.DISK_NAME1)
                disks.waitForDisksGone(True, config.DISK_NAME1)

            users.removeUser(True, config.USER_NAME)
            users.addUser(
                True, user_name=config.USER_NAME, domain=config.USER_DOMAIN
            )
        if b:
            raise AssertionError


# add a group of users from AD to the system (give it some admin permission)
# login as user from group, remove the user
# Check that group still exist in the Configure-->System.
# Check that group's permissions still exist
@attr(tier=1)
class PermissionsCase108233(TestCase):
    """ Removing user that part of the group. """
    __test__ = True

    @classmethod
    def setUpClass(self):
        users.addGroup(
            True,
            config.GROUP_NAME,
            config.USER_DOMAIN
        )
        mla.addClusterPermissionsToGroup(
            True, config.GROUP_NAME, config.CLUSTER_NAME[0], role.UserRole
        )

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        users.removeUser(True, config.GROUP_USER)
        users.deleteGroup(True, config.GROUP_NAME)

    @tcms(TCMS_PLAN_ID, 108233)
    def testRemoveUserFromGroup(self):
        """ Removing user that part of the group. """
        loginAsUser(config.GROUP_USER)
        vms.VM_API.find(config.VM_NAME)

        loginAsAdmin()
        users.util.find(config.GROUP_USER)
        LOGGER.info("User was added.")


# Check that data-center has a user with UserRole permission
# Create new desktop pool
# Check that permission was inherited from data-center
# Ensure that user can take a machine from created pool
@attr(tier=1)
class PermissionsCase109086(TestCase):
    """ Permission inheritance for desktop pool """
    __test__ = True

    @classmethod
    def setUpClass(self):
        mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0], role.UserRole
        )

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        mla.removeUserPermissionsFromDatacenter(
            True, config.DC_NAME[0], config.USER1
        )

    @istest
    @tcms(TCMS_PLAN_ID, 109086)
    def permsInhForVmPools(self):
        """ Permission inheritance for desktop pools """
        loginAsUser(config.USER_NAME)
        self.assertTrue(vmpools.allocateVmFromPool(True, config.VMPOOL_NAME))
        loginAsAdmin()
        vms.waitForVMState('%s-%s' % (config.VMPOOL_NAME, 1), state='up')
        loginAsUser(config.USER_NAME)
        self.assertTrue(vmpools.stopVmPool(True, config.VMPOOL_NAME))
        loginAsAdmin()
        vms.waitForVMState('%s-%s' % (config.VMPOOL_NAME, 1), state='down')
        time.sleep(10)  # Didn't find any reliable way how to wait.


# create a StorageDomain with templates and VMs
# grant permissions for user X to some VMs & templates on that SD
# destroy the SD take a look in the user under permission tab
@attr(tier=1, extra_reqs={'datacenters_count': 2})
class PermissionsCase111082(TestCase):
    """ Test if perms removed after object is removed """
    __test__ = True

    apis = set(['rest'])

    @classmethod
    def setUpClass(self):
        h_sd.addNFSDomain(
            config.HOSTS[0], config.STORAGE_NAME[1],
            config.DC_NAME[0], config.ADDRESS[1],
            config.PATH[1]
        )
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[1], size=config.GB,
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True, vm=config.VM_NAME1, name=config.TEMPLATE_NAME2,
            cluster=config.CLUSTER_NAME[0]
        )
        disks.addDisk(
            True, alias=config.DISK_NAME1, interface='virtio', format='cow',
            provisioned_size=config.GB, storagedomain=config.STORAGE_NAME[1]
        )
        disks.wait_for_disks_status(config.DISK_NAME1)
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME1)
        mla.addPermissionsForTemplate(
            True, config.USER_NAME, config.TEMPLATE_NAME2, role.TemplateOwner
        )
        mla.addPermissionsForDisk(True, config.USER_NAME, config.DISK_NAME1)

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        users.removeUser(True, config.USER_NAME)
        users.addUser(
            True, user_name=config.USER_NAME, domain=config.USER_DOMAIN
        )
        storagedomains.remove_storage_domain(
            config.STORAGE_NAME[1],
            config.DC_NAME[0],
            config.HOSTS[0]
        )

    @istest
    @tcms(TCMS_PLAN_ID, 111082)
    def permsRemovedAfterObjectRemove(self):
        """ perms removed after object is removed """
        def checkIfObjectHasRole(obj, role):
            objPermits = mla.permisUtil.getElemFromLink(obj, get_href=False)
            roleNAid = users.rlUtil.find(role).get_id()
            perm_ids = [perm.get_role().get_id() for perm in objPermits]
            return roleNAid in perm_ids

        storagedomains.deactivateStorageDomain(
            True, config.DC_NAME[0], config.STORAGE_NAME[1]
        )
        storagedomains.removeStorageDomain(
            True, config.STORAGE_NAME[1], config.HOSTS[0], destroy=True
        )
        # When destroying SD, then also vm is destroyed
        # vms.removeVm(True, config.VM_NAME1)

        userVmManagerId = users.rlUtil.find(role.UserVmManager).get_id()
        templateOwnerId = users.rlUtil.find(role.TemplateOwner).get_id()
        diskOperatorId = users.rlUtil.find(role.DiskOperator).get_id()

        obj = users.util.find(config.USER_NAME)
        permits = mla.permisUtil.getElemFromLink(obj, get_href=False)

        permits_id = [p.get_role().get_id() for p in permits]
        assert userVmManagerId not in permits_id
        assert templateOwnerId not in permits_id
        assert diskOperatorId not in permits_id
