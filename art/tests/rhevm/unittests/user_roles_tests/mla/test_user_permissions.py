'''
Testing working with permissions.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Tests if permissions are correctly inherited/viewed/assigned/removed.
'''

__test__ = True

from user_roles_tests import config
from user_roles_tests.roles import role
from nose.tools import istest
from art.test_handler.tools import bz, tcms
from unittest import TestCase
from art.rhevm_api.tests_lib.high_level import storagedomains as h_sd
from art.rhevm_api.tests_lib.low_level import \
    users, vms, disks, vmpools, templates, mla, clusters, datacenters, hosts,\
    storagedomains
import logging

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
        user_name, config.USER_DOMAIN, config.USER_PASSWORD, filter=filter)


def loginAsAdmin():
    users.loginAsUser(
        config.OVIRT_USERNAME, config.OVIRT_DOMAIN,
        config.OVIRT_PASSWORD, filter=False)


def setUpModule():
    users.addUser(True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)
    users.addUser(True, user_name=config.USER_NAME2, domain=config.USER_DOMAIN)
    users.addUser(True, user_name=config.USER_NAME3, domain=config.USER_DOMAIN)

    vms.createVm(
        True, config.VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
        storageDomainName=config.MAIN_STORAGE_NAME, size=config.GB)
    templates.createTemplate(
        True, vm=config.VM_NAME, name=config.TEMPLATE_NAME,
        cluster=config.MAIN_CLUSTER_NAME)
    vmpools.addVmPool(
        True, name=config.VMPOOL_NAME, size=1,
        cluster=config.MAIN_CLUSTER_NAME, template=config.TEMPLATE_NAME)
    vms.waitForVMState('%s-%s' % (config.VMPOOL_NAME, 1), state='down')
    disks.addDisk(
        True, alias=config.DISK_NAME, interface='virtio', format='cow',
        provisioned_size=config.GB, storagedomain=config.MAIN_STORAGE_NAME)
    disks.waitForDisksState(config.DISK_NAME)


def tearDownModule():
    loginAsAdmin()
    users.removeUser(True, config.USER_NAME)
    users.removeUser(True, config.USER_NAME2)
    users.removeUser(True, config.USER_NAME3)
    vms.removeVm(True, config.VM_NAME)
    disks.deleteDisk(True, config.DISK_NAME)
    disks.waitForDisksGone(True, config.DISK_NAME)
    vmpools.detachVms(True, config.VMPOOL_NAME)
    import time
    time.sleep(20)
    vms.removeVm(True, '%s-%s' % (config.VMPOOL_NAME, 1))
    vmpools.removeVmPool(True, config.VMPOOL_NAME)
    templates.removeTemplate(True, config.TEMPLATE_NAME)


class PermissionsCase54408(TestCase):
    """ objects and user permissions """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        # Test these object for adding/removing/viewving perms on it
        cls.OBJS = {config.VM_NAME: vms.VM_API,
                    config.TEMPLATE_NAME: templates.TEMPLATE_API,
                    config.DISK_NAME: disks.DISKS_API,
                    config.VMPOOL_NAME: vmpools.util,
                    config.MAIN_CLUSTER_NAME: clusters.util,
                    config.MAIN_DC_NAME: datacenters.util,
                    config.MAIN_HOST_NAME: hosts.HOST_API,
                    config.MAIN_STORAGE_NAME: storagedomains.util}

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
            True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)

    @istest
    @tcms(TCMS_PLAN_ID, 54409)
    def permissionsInheritence(self):
        """ permissions inheritence """
        loginAsUser(config.USER_NAME, filter=False)
        self.assertTrue(vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME))
        self.assertTrue(vms.removeVm(True, config.VM_NAME1))
        LOGGER.info("User can create/remove vm with vm permissions.")

        loginAsAdmin()
        users.removeUser(True, config.USER_NAME)
        users.addUser(
            True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)
        # To be able login
        mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.MAIN_CLUSTER_NAME, role.UserRole)

        loginAsUser(config.USER_NAME)
        self.assertTrue(vms.createVm(
            False, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME))
        LOGGER.info("User can't create/remove vm without vm permissions.")


# Check that in the object Permissions sub tab you will see all permissions
# that were associated with the selected object in the main grid or one of
# its ancestors.
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
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME,
                                   role=role.UserRole)
        mla.addVMPermissionsToUser(True, config.USER_NAME2, config.VM_NAME,
                                   role=role.UserRole)
        vm = vms.VM_API.find(config.VM_NAME)
        rolePermits = mla.permisUtil.getElemFromLink(vm,  get_href=False)
        users_id = [perm.user.get_id() for perm in rolePermits]
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
        msg = "Unable to remove admin@internal or his SuperUser permissions."
        admin = '%s@%s' % (config.OVIRT_USERNAME, config.OVIRT_DOMAIN)
        assert users.removeUser(
            False, config.OVIRT_USERNAME, config.OVIRT_DOMAIN)
        assert mla.removeUserRoleFromDataCenter(
            False, config.MAIN_DC_NAME, admin, role.SuperUser)
        LOGGER.info(msg)


# Try to add a permission associated with an
# administrator Role (i.e. "Administrator Permission") to another user when
# you don't have "Super-Admin" permission on the "System" object". - FAILED
# When you're user/super user ,try to delegate permission to another
# user/super user. - SUCCESS
class PermissionsCase54425(TestCase):
    """ test delegate perms """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME)

    @classmethod
    def tearDownClass(cls):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        users.removeUser(True, config.USER_NAME)
        users.addUser(
            True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)

    @istest
    @tcms(TCMS_PLAN_ID, 54425)
    def delegatePerms(self):
        """ delegate perms """
        # Test SuperUser that he can add permissions
        for role_obj in mla.util.get(absLink=False):
            r = role_obj.get_name()
            LOGGER.info("Testing role - %s" % r)
            # Get roles perms, to check for manipulate_permissions
            rolePermits = mla.util.getElemFromLink(
                role_obj, link_name='permits', attr='permit', get_href=False)
            perms = [p.get_name() for p in rolePermits]
            if not 'login' in perms:
                LOGGER.info("User not tested, because don't have login perms.")
                continue

            users.addRoleToUser(True, config.USER_NAME, r)
            mla.addVMPermissionsToUser(
                True, config.USER_NAME, config.VM_NAME1, r)

            # For know if login as User/Admin
            filt = not('Admin' in r or role.SuperUser == r)
            # login as user with role
            loginAsUser(config.USER_NAME, filter=filt)
            # Test if user with role can/can't manipualte perms
            if 'manipulate_permissions' in perms:
                if filt or role.SuperUser != r:
                    try:
                        mla.addVMPermissionsToUser(False, config.USER_NAME,
                                                   config.VM_NAME1,
                                                   role.TemplateAdmin)
                    except:  # Ignore, user should not add perms
                        pass
                    LOGGER.info("'%s' can't add admin permissions." % r)
                    self.assertTrue(mla.addVMPermissionsToUser(
                        True, config.USER_NAME, config.VM_NAME1))
                    LOGGER.info("'%s' can add user permissions." % r)
                else:
                    self.assertTrue(mla.addVMPermissionsToUser(
                        True, config.USER_NAME, config.VM_NAME1,
                        role.UserRole))
                    LOGGER.info("'%s' can add user permissions." % r)
                    self.assertTrue(mla.addVMPermissionsToUser(
                        True, config.USER_NAME, config.VM_NAME1,
                        role.TemplateAdmin))
                    LOGGER.info("'%s' can add admin permissions." % r)
            else:
                try:
                    mla.addVMPermissionsToUser(False, config.USER_NAME,
                                               config.VM_NAME1, role.UserRole)
                except:  # Ignore, user should not add perms
                    pass
                LOGGER.info("'%s' can't manipulate permisisons." % r)

            loginAsAdmin()
            users.removeUser(True, config.USER_NAME)
            users.addUser(
                True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)

    # in order ro add new object you will need the appropriate permission on
    # the ancestor (e.g. to create a new storage domain you'll need a "add
    # storage domain" permission on the "system" object,to create a new Host/VM
    #you will need appropriate permission on the relevant cluster.
    @istest
    @tcms(TCMS_PLAN_ID, 54432)
    def newObjectCheckPerms(self):
        """ Adding new business entity/new object. """
        msg = "This functionality tests modules admin_tests and user_tests"
        LOGGER.info(msg)


# Check if user is under some Group if it has permissions of its group
class PermissionsCase54446(TestCase):
    """ Check if user is under some Group if has permissions of its group """
    __test__ = True

    @classmethod
    def setUpClass(self):
        users.addGroup(True, config.GROUP_NAME)
        mla.addClusterPermissionsToGroup(True, config.GROUP_NAME,
                                         config.MAIN_CLUSTER_NAME,
                                         role.UserVmManager)

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
        self.assertTrue(vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME))
        self.assertTrue(templates.createTemplate(
            False, vm=config.VM_NAME1, name=config.TEMPLATE_NAME2,
            cluster=config.MAIN_CLUSTER_NAME))


# Creating object from user API and admin API should be different:
# for example admin API - createVm - should not delegate perms on VM
# user API - createVm - should add perms UserVmManager on VM
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
                role_obj, link_name='permits', attr='permit', get_href=False)
            r_permits = [p.get_name() for p in rolePermits]

            users.addRoleToUser(True, config.USER_NAME, rr)
            mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                            config.MAIN_CLUSTER_NAME,
                                            role.UserRole)
            loginAsUser(config.USER_NAME,
                        filter=False if role_obj.administrative else True)

            LOGGER.info("Testing role - " + role_obj.get_name())
            # Create vm,template, disk and check permissions of it
            if 'create_vm' in r_permits:
                LOGGER.info("Testing create_vm.")
                vms.createVm(True, config.VM_NAME1, '',
                             cluster=config.MAIN_CLUSTER_NAME)
                b = b or checkIfObjectHasRole(vms.VM_API.find(config.VM_NAME1),
                                              VM_PREDEFINED,
                                              role_obj.administrative)
                loginAsAdmin()
                vms.removeVm(True, config.VM_NAME1)
            if 'create_template' in r_permits:
                LOGGER.info("Testing create_template.")
                templates.createTemplate(
                    True, vm=config.VM_NAME, name=config.TEMPLATE_NAME2,
                    cluster=config.MAIN_CLUSTER_NAME)
                b = b or checkIfObjectHasRole(
                    templates.TEMPLATE_API.find(config.TEMPLATE_NAME2),
                    TEMPLATE_PREDEFINED, role_obj.administrative)
                loginAsAdmin()
                templates.removeTemplate(True, config.TEMPLATE_NAME2)
            if 'create_disk' in r_permits:
                LOGGER.info("Testing create_disk.")
                disks.addDisk(True, alias=config.DISK_NAME1,
                              interface='virtio', format='cow',
                              provisioned_size=config.GB,
                              storagedomain=config.MAIN_STORAGE_NAME)
                disks.waitForDisksState(config.DISK_NAME1)
                b = b or checkIfObjectHasRole(
                    disks.DISKS_API.find(config.DISK_NAME1),
                    DISK_PREDEFINED, role_obj.administrative)

                loginAsAdmin()
                disks.deleteDisk(True, config.DISK_NAME1)
                disks.waitForDisksGone(True, config.DISK_NAME1)

            users.removeUser(True, config.USER_NAME)
            users.addUser(
                True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)
        if b:
            raise AssertionError


# add a group of users from AD to the system (give it some admin permission)
# login as user from group, remove the user
# Check that group still exist in the Configure-->System.
# Check that group's permissions still exist
class PermissionsCase108233(TestCase):
    """ Removing user that part of the group. """
    __test__ = True

    @classmethod
    def setUpClass(self):
        users.addGroup(True, config.GROUP_NAME)
        mla.addClusterPermissionsToGroup(True, config.GROUP_NAME,
                                         config.MAIN_CLUSTER_NAME,
                                         role.UserRole)

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
class PermissionsCase109086(TestCase):
    """ Permission inheritance for desktop pool """
    __test__ = True

    @classmethod
    def setUpClass(self):
        mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.MAIN_DC_NAME, role.UserRole)

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        mla.removeUserPermissionsFromDatacenter(
            True, config.MAIN_DC_NAME, config.USER1)

    @istest
    @bz(990985)
    @tcms(TCMS_PLAN_ID, 109086)
    def permsInhForVmPools(self):
        """ Permission inheritance for desktop pools """
        loginAsUser(config.USER_NAME)
        self.assertTrue(vmpools.allocateVmFromPool(True, config.VMPOOL_NAME))
        loginAsAdmin()
        vms.waitForVMState('%s-%s' % (config.VMPOOL_NAME, 1), state='up')
        loginAsUser(config.USER_NAME)
        self.assertTrue(vmpools.stopVmPool(True, config.VMPOOL_NAME))


# create a StorageDomain with templates and VMs
# grant permissions for user X to some VMs & templates on that SD
# destroy the SD take a look in the user under permission tab
class PermissionsCase111082(TestCase):
    """ Test if perms removed after object is removed """
    __test__ = True

    @classmethod
    def setUpClass(self):
        h_sd.addNFSDomain(
            config.MAIN_HOST_NAME, config.ALT1_STORAGE_NAME,
            config.MAIN_DC_NAME, config.ALT1_STORAGE_ADDRESS,
            config.ALT1_STORAGE_PATH)
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME,
            storageDomainName=config.ALT1_STORAGE_NAME, size=config.GB)
        templates.createTemplate(
            True, vm=config.VM_NAME1, name=config.TEMPLATE_NAME2,
            cluster=config.MAIN_CLUSTER_NAME)
        disks.addDisk(
            True, alias=config.DISK_NAME1, interface='virtio', format='cow',
            provisioned_size=config.GB, storagedomain=config.ALT1_STORAGE_NAME)
        disks.waitForDisksState(config.DISK_NAME1)
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME1)
        mla.addPermissionsForTemplate(
            True, config.USER_NAME, config.TEMPLATE_NAME2, role.TemplateOwner)
        mla.addPermissionsForDisk(True, config.USER_NAME, config.DISK_NAME1)

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        users.removeUser(True, config.USER_NAME)
        users.addUser(
            True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)

    @istest
    @bz(892642)
    @tcms(TCMS_PLAN_ID, 111082)
    def permsRemovedAfterObjectRemove(self):
        """ perms removed after object is removed """
        def checkIfObjectHasRole(obj, role):
            objPermits = mla.permisUtil.getElemFromLink(obj, get_href=False)
            roleNAid = users.rlUtil.find(role).get_id()
            perm_ids = [perm.get_role().get_id() for perm in objPermits]
            return roleNAid in perm_ids

        storagedomains.deactivateStorageDomain(True, config.MAIN_DC_NAME,
                                               config.ALT1_STORAGE_NAME)
        storagedomains.removeStorageDomain(
            True, config.ALT1_STORAGE_NAME,
            config.MAIN_HOST_NAME, destroy=True)
        # When destroying SD, then also vm is destroyed
        #vms.removeVm(True, config.VM_NAME1)

        userVmManagerId = users.rlUtil.find(role.UserVmManager).get_id()
        templateOwnerId = users.rlUtil.find(role.TemplateOwner).get_id()
        diskOperatorId = users.rlUtil.find(role.DiskOperator).get_id()

        obj = users.util.find(config.USER_NAME)
        permits = mla.permisUtil.getElemFromLink(obj, get_href=False)

        permits_id = [p.get_role().get_id() for p in permits]
        assert userVmManagerId not in permits_id
        assert templateOwnerId not in permits_id
        assert diskOperatorId not in permits_id
