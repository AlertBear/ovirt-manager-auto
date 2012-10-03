#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__test__ = True

from user_roles_tests import config, common
from user_roles_tests import states, roles
from nose.tools import istest
from functools import wraps
from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors

import logging
import unittest2 as unittest

try:
    from art.test_handler.tools import bz
except ImportError:
    from user_roles_tests.common import bz

try:
    from art.test_handler.tools import tcms
except ImportError:
    from user_roles_tests.common import tcms

LOGGER  = common.logging.getLogger(__name__)
API     = common.API

# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
VM_NAME = 'user_permissions__vm'
TMP_VM_NAME = 'user_permissions__tpm_vm'
TEMPLATE_NAME = 'user_permissions__template'
TMP_TEMPLATE_NAME = 'user_permissions__template_tmp'
VM_POOL_NAME = 'user_permissions__vm_pool'
CLUSTER_NAME = 'user_permissions__cluster'
DISK_NAME = 'user_permissions__disk'
DISK_ID = None
OBJECTS = [API.clusters, API.datacenters, API.disks, API.groups, API.hosts,
        API.storagedomains, API.templates, API.vms, API.vmpools]

# Test these object for adding/removing/viewving perms on it
OBJS = {VM_NAME: API.vms, TEMPLATE_NAME: API.templates, VM_POOL_NAME: API.vmpools,
        config.MAIN_CLUSTER_NAME: API.clusters, config.MAIN_DC_NAME: API.datacenters,
        config.MAIN_HOST_NAME: API.hosts, config.MAIN_STORAGE_NAME: API.storagedomains}
        # FIXME dont work for disks(need to use alias) DISK_NAME, API.disks,

TCMS_PLAN_ID = 2602

# Predefined role for creation of VM as non-admin user
VM_PREDEFINED = roles.role.UserVmManager
# Predefined role for creation of Disk as non-admin user
DISK_PREDEFINED = roles.role.DiskOperator
# Predefined role for creation of Template as non-admin user
TEMPLATE_PREDEFINED = roles.role.TemplateOwner

def setUpModule():
    global DISK_ID
    common.addUser()
    common.addUser(userName=config.USER_NAME2)
    common.addUser(userName=config.USER_NAME3)

    common.createVm(VM_NAME)
    common.createTemplate(VM_NAME, TEMPLATE_NAME)
    common.createVmPool(VM_POOL_NAME, TEMPLATE_NAME)
    common.loginAsAdmin()
    DISK_ID = common.createDiskObject(DISK_NAME,
            storage=config.MAIN_STORAGE_NAME).get_id()

def tearDownModule():
    common.loginAsAdmin()
    common.removeUser(userName=config.USER_NAME3)
    common.deleteDisk(DISK_ID)
    common.removeAllVmsInPool(VM_POOL_NAME)
    common.removeVmPool(API.vmpools.get(VM_POOL_NAME))
    common.removeTemplate(TEMPLATE_NAME)
    common.removeVm(VM_NAME)
    common.removeUser()
    common.removeUser(userName=config.USER_NAME2)

# There is used bz 881145 because of art dont check verison of verification of bug
class PermissionsTests(unittest.TestCase):
    """ Tests that will be run for each role in VM_ROLES """
    __test__ = True

    def setUp(self):
        common.loginAsAdmin()

    def _checkPredefinedPermissions(self, obj, predefined, admin):
        """
        Check if on object obj was created predefined permissions predefined
        only if user is administrative role - admin

        obj        - object to check
        predefined - predefined permissions on object
        admin      - True if role administrative else False
        """
        perms = obj.permissions.list()
        if admin:
            assert len(perms) == 0
        else:
            role_name = None
            if len(perms) == 1:
                role_name = API.roles.get(id=perms[0].get_role().get_id()).get_name()
            assert len(perms) == 1 and role_name == predefined

    # Check that there are two types of Permissions sub-tabs in the system:
    # for objects on which you can define permissions and for users.
    @tcms(TCMS_PLAN_ID, 54408)
    @bz(881145)
    def testObjectsAndUserPermissions(self):
        """ testObjectsAndUserPermissions """
        user = common.getUser()
        try:
            user.permissions.list()
        except Exception as e:
            raise AssertionError("User has no permissions: %s" % e)

        for k in OBJS.keys():
            try:
                OBJS[k].get(k).permissions.list()
            except Exception as e:
                raise AssertionError("Object has not permissions sub-tab: %s" % e)
        # Disks using 'alias' instead of 'name'
        try:
            API.disks.get(id=DISK_ID).permissions.list()
        except Exception as e:
            raise AssertionError("Object has not permissions sub-tab: %s" % e)

    @tcms(TCMS_PLAN_ID, 54409)
    def testPermissionsInheritence(self):
        """ testPermissionsInheritence """
        common.loginAsAdmin()
        common.addRoleToUser(roles.role.ClusterAdmin)
        common.loginAsUser(filter_=False)
        common.createVm(TMP_VM_NAME)
        common.removeVm(TMP_VM_NAME)
        LOGGER.info("User can create/remove vm")
        common.loginAsAdmin()
        common.removeRoleFromUser(roles.role.ClusterAdmin)
        common.loginAsUser(filter_=False)
        self.assertRaises(errors.RequestError, common.createVm, TMP_VM_NAME)

    # Check that in the object Permissions sub tab you will see all permissions
    # that were associated with the selected object in the main grid or one of
    # its ancestors.
    @tcms(TCMS_PLAN_ID, 54410)
    def testPermissionsSubTab(self):
        """ testPermissionsSubTab """
        # Try to add UserRole and AdminRole to object, then
        # check if both role are vissbile via /api/objects/objectid/permissions

        # FIXME dont work for disks(need to use alias)
        u1 = common.getUser()
        u2 = common.getUser(config.USER_NAME2)
        for name, obj in OBJS.items():
            LOGGER.info("Testing object %s" % name)
            o = obj.get(name)
            common.removeAllPermissionFromObject(o)
            common.givePermissionToObject(o, roles.role.UserRole, config.USER_NAME)
            common.givePermissionToObject(o, roles.role.VmPoolAdmin, config.USER_NAME2)

            users = [perm.user.get_id() for perm in o.permissions.list()]
            assert len(users) == 2
            assert u1.get_id() in users and u2.get_id() in users
            LOGGER.info("There are only vissible all permissions which were associated.")

            common.removeAllPermissionFromObject(o)


    # This test 54410 too
    # Define permissions by several Role types on the same object.
    # For example Admin role and User role on VM.
    # Check that you can see both - Admin/User.
    @tcms(TCMS_PLAN_ID, 54414)
    def testPermissionsPerRoleType(self):
        """ testPermissionsPerRoleType """
        self.testPermissionsSubTab()

    # Assuming that there is always Super-Admin user on RHEV-M.
    # Try to remove last permission on certain object.
    # This also tests 54410
    @tcms(TCMS_PLAN_ID, 54418)
    def testLastPermOnObject(self):
        """ testLastPermOnObject """
        common.removeAllPermissionFromVm(VM_NAME)
        common.givePermissionToVm(VM_NAME, roles.role.UserRole)
        common.removeAllPermissionFromVm(VM_NAME)

    # It should be impossile to remove last Super-admin user with permission on
    # system object.
    # Try to remove last super-admin user with permission on system object.
    # Try to remoce super-admin + system permission from the user.
    @tcms(TCMS_PLAN_ID, 54419)
    def testRemovalOfSuperUser(self):
        """ testRemovalOfSuperUser """
        self.assertRaises(errors.RequestError, common.removeUser,
                    config.OVIRT_USERNAME, config.OVIRT_DOMAIN)
        self.assertRaises(errors.RequestError, common.removeRoleFromUser,
                    roles.role.SuperUser, userName=config.OVIRT_USERNAME,
                    domainName=config.OVIRT_DOMAIN)
        LOGGER.info("Unable to remove admin@internal or his SuperUser permissions.")

    # Try to add a permission associated with an
    # administrator Role (i.e. "Administrator Permission") to another user when
    # you don't have "Super-Admin" permission on the "System" object". - FAILED
    # When you're user/super user ,try to delegate permission to another
    # user/super user. - SUCCESS
    @tcms(TCMS_PLAN_ID, 54425)
    @bz(881145)
    def testDelegatePerms(self):
        """ testDelegatePerms """
        common.createVm(TMP_VM_NAME)
        vm = API.vms.get(TMP_VM_NAME)
        user = common.getUser(config.USER_NAME, config.USER_DOMAIN)
        role = API.roles.get(roles.role.UserVmManager)
        # Test SuperUser that he can add permissions
        for role in [r.get_name() for r in API.roles.list()]:
            LOGGER.info("Testing role - %s" % role)
            common.addRoleToUser(role)  # Test Adding perms form system SuperUser

            # For know if login as User/Admin
            filt = "Admin" in role
            filt = filt or roles.role.SuperUser == role
            filt = not filt
            # Get roles perms, to check for manipulate_permissions
            perms = [p.get_name() for p in API.roles.get(role).get_permits().list()]
            # login as user with role
            common.loginAsUser(filter_=filt)
            # Test if user with role can/can't manipualte perms
            for role_ in [r.get_name() for r in API.roles.list()]:
                # If user cant manipulate perms try it, and also
                # check if user cant manipulate admin perms
                if 'manipulate_permissions' in perms:
                    if 'Admin' in role_ or role_ == roles.role.SuperUser:
                        self.assertRaises(errors.RequestError, common.givePermissionToObject,
                                    vm, roles.role.UserVmManager,
                                    user_object=user, role_object=role)
                        LOGGER.info("'%s' can't add admin permissions." % role)
                    else:
                        try:
                            common.givePermissionToObject(vm, roles.role.UserVmManager,
                                user_object=user, role_object=role)
                            common.removeAllPermissionFromObject(vm)
                        except AssertionError as e:
                            # Woraround for 869334
                            pass
                        LOGGER.info("'%s'can manipulate with user permissions." % role)
                else:
                    self.assertRaises(errors.RequestError, common.addRoleToUser,
                                role_, userName=config.USER_NAME2)
                    LOGGER.info("'%s' can't manipulate permisisons." % role)

            common.loginAsAdmin()
            common.removeRoleFromUser(role)

    # in order ro add new object you will need the appropriate permission on the
    # ancestor (e.g. to create a new storage domain you'll need a "add storage
    # domain" permission on the "system" object,to create a new Host/VM you will
    # need appropriate permission on the relevant cluster.
    @tcms(TCMS_PLAN_ID, 54432)
    def testNewObjectCheckPerms(self):
        """ Adding new business entity/new object. """
        # Everything tests user_tests and admin_tests
        LOGGER.info("This funcionality tests modules user_tests and admin_tests")

    # Check if user is under some Group if it has permissions of its group
    @tcms(TCMS_PLAN_ID, 54446)
    @bz(881145)
    def testUsersPermissions(self):
        """ UsersPermissions """
        CASE_VM_NAME = 'case_vm_name'
        CASE_TEMPLATE = 'case_template'
        # test all possible things? or just one role?
        LOGGER.info("Adding new group with UserVmManager perms")
        grp = common.addGroup()
        common.addRoleToGroup(roles.role.UserVmManager, grp)

        LOGGER.info("Login as user from group")
        common.loginAsUser(userName=config.USER_NAME3,
                domain=config.USER_DOMAIN,
                password=config.USER_PASSWORD,
                filter_=True)

        common.createVm(CASE_VM_NAME)
        self.assertRaises(errors.RequestError,
                common.createTemplate, CASE_VM_NAME, CASE_TEMPLATE)
        common.removeVm(CASE_VM_NAME)

        common.loginAsAdmin()
        LOGGER.info("Deleting group '%s'" % grp.get_name())
        common.deleteGroup(grp)

    # Creating object from user API and admin API should be differnt:
    # for example admin API - createVm - should not delegate perms on VM
    # user API - createVm - should add perms UserVmManager on VM
    @tcms(TCMS_PLAN_ID, 54420)
    @bz(881145)
    def testObjAdminUser(self):
        """ Object creating from User and Admin portal """
        # This is already implemented in test_user_roles
        try:
            for role in API.roles.list():
                r_permits = [p.get_name() for p in role.permits.list()]
                if not 'login' in r_permits:
                    LOGGER.info("Role %s not tested because can't login." %role.get_name())
                    continue

                common.loginAsAdmin()
                #common.removeAllRolesFromUser()
                common.removeAllPermissionFromObject(common.getUser())
                common.addRoleToUser(role.get_name())
                common.loginAsUser(filter_=False if role.administrative else True)
                LOGGER.info("Testing role - " + role.get_name())
                # Create vm,template, disk and check permissions of it
                if 'create_vm' in r_permits:
                    LOGGER.info("Testing create_vm.")
                    common.createVm(TMP_VM_NAME, createDisk=False)

                    common.loginAsAdmin()
                    self._checkPredefinedPermissions(API.vms.get(TMP_VM_NAME),
                            VM_PREDEFINED, role.administrative)
                    common.removeVm(TMP_VM_NAME)
                    common.loginAsUser(filter_=not role.administrative)
                if 'create_template' in r_permits:
                    LOGGER.info("Testing create_template.")
                    common.createTemplate(VM_NAME, TEMPLATE_NAME)

                    common.loginAsAdmin()
                    self._checkPredefinedPermissions(API.templates.get(TEMPLATE_NAME),
                            TEMPLATE_PREDEFINED, role.administrative)
                    common.removeTemplate(TEMPLATE_NAME)
                    common.loginAsUser(filter_=not role.administrative)
                if 'create_disk' in r_permits:
                    LOGGER.info("Testing create_disk.")
                    d = common.createDiskObject(DISK_NAME,
                            storage=config.MAIN_STORAGE_NAME)

                    common.loginAsAdmin()
                    self._checkPredefinedPermissions(API.disks.get(DISK_NAME),
                            DISK_PREDEFINED, role.administrative)
                    common.deleteDiskObject(d)
                    common.loginAsUser(filter_=not role.administrative)
        except Exception as e:
            try:
                common.loginAsAdmin()
                if API.vms.get(TMP_VM_NAME) is not None:
                    common.removeVm(TMP_VM_NAME)
                if API.vms.get(TEMPLATE_NAME) is not None:
                    common.removeTemplate(TEMPLATE_NAME)
                if API.disks.get(DISK_NAME) is not None:
                    common.deleteDiskObject(API.disks.get(DISK_NAME))
                #common.removeAllRolesFromUser()
                common.removeAllPermissionFromObject(common.getUser())
                #common.deleteDisk(None, alias=DISK_NAME) FIXME
            except Exception as ee:
                LOGGER.error(str(ee))
            LOGGER.error(str(e))
            raise e


    # add a group of users from AD to the system (give it some admin permission)
    # login as user from group, remove the user
    # Check that group still exist in the Configure-->System.
    # Check that group's permissions still exist
    @tcms(TCMS_PLAN_ID, 108233)
    @bz(881145)
    def testRemoveUserFromGroup(self):
        """ Removing user that part of the group. """
        LOGGER.info("Adding new group with TemplateAdmin perms")
        try:
            grp = common.addGroup()
        except: # Woraround to 882710
            common.addUser(userName=config.USER_NAME2)
            common.addRoleToUser(roles.role.SuperUser, userName=config.USER_NAME2)
            common.loginAsUser(userName=config.USER_NAME2, filter_=False)
            common.addGroup()
            common.loginAsAdmin()

        common.addRoleToGroup(roles.role.TemplateAdmin, grp)

        LOGGER.info("Login as user from group")
        common.loginAsUser(userName=config.USER_NAME3,
                domain=config.USER_DOMAIN,
                password=config.USER_PASSWORD,
                filter_=True)

        common.removeUser(userName=config.USER_NAME3)
        common.loginAsAdmin()
        grp = API.groups.get(config.GROUP_NAME)
        assert grp is not None
        assert grp.permissions.list() > 0
        common.deleteGroup(grp)

    # Check that data-center has a user with UserRole permission
    # Create new desktop pool
    # Check that permission was inherited from data-center
    # Go to User-portal and ensure that user can take a machine from created pool
    @tcms(TCMS_PLAN_ID, 109086)
    def testPermsInhForVmPools(self):
        """ Permission inheritance for desktop pools """
        common.loginAsAdmin()
        common.givePermissionToDc(config.MAIN_DC_NAME, roles.role.UserRole)
        #common.createVmPool(VM_POOL_NAME, TEMPLATE_NAME)
        # Should be below loginAsUser, after bz is ok.
        vmpool = API.vmpools.get(VM_POOL_NAME)

        common.loginAsUser()
        vm_id = common.vmpoolBasicOperations(vmpool)

    # create a StorageDomain with templates and VMs
    # grant permissions for user X to some VMs & templates on that SD
    # destroy the SD take a look in the user under permission tab
    @tcms(TCMS_PLAN_ID, 111082)
    def testPermsRemovedAfterObjectRemove(self):
        """ PermsRemovedAfterObjectRemove """
        common.createNfsStorage(storageName=config.ALT1_STORAGE_NAME,
                    storageType='data',
                    address=config.ALT1_STORAGE_ADDRESS,
                    path=config.ALT1_STORAGE_PATH,
                    datacenter=config.MAIN_DC_NAME,
                    host=config.MAIN_HOST_NAME)
        common.attachActivateStorage(config.ALT1_STORAGE_NAME, isMaster=False)

        common.createVm(TMP_VM_NAME, storage=config.ALT1_STORAGE_NAME)
        common.createTemplate(TMP_VM_NAME, TMP_TEMPLATE_NAME)
        #common.removeAllRolesFromUser()
        common.removeAllPermissionFromObject(common.getUser())

        common.givePermissionToVm(TMP_VM_NAME, roles.role.UserVmManager)
        common.givePermissionToTemplate(TMP_TEMPLATE_NAME, roles.role.TemplateOwner)
        common.removeNonMasterStorage(storageName=config.ALT1_STORAGE_NAME,
                                      datacenter=config.MAIN_DC_NAME,
                                      host=config.MAIN_HOST_NAME, destroy=True)

        common.removeVm(TMP_VM_NAME)
        # Template should be removed, Vm should stay, but should not have disk
        for p in common.getUser().permissions.list():
            role_name = API.roles.get(id=p.get_role().get_id()).get_name()
            assert not (role_name == roles.role.UserVmManager or role_name == roles.role.TemplateOwner)
