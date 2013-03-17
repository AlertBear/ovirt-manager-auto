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
TMP_DISK_NAME = 'user_permissions__disk_tmp'
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

def loginAsUser(**kwargs):
    common.loginAsUser(**kwargs)
    global API
    API = common.API

def loginAsAdmin():
    common.loginAsAdmin()
    global API
    API = common.API

def setUpModule():
    common.addUser()
    common.addUser(userName=config.USER_NAME2)
    common.addUser(userName=config.USER_NAME3)

    common.createVm(VM_NAME)
    common.createTemplate(VM_NAME, TEMPLATE_NAME)
    common.createVmPool(VM_POOL_NAME, TEMPLATE_NAME)
    common.createDiskObject(DISK_NAME, storage=config.MAIN_STORAGE_NAME)

def tearDownModule():
    loginAsAdmin()
    common.removeUser(userName=config.USER_NAME3)
    common.deleteDisk(None, alias=DISK_NAME)
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
        loginAsAdmin()

    def _checkPredefinedPermissions(self, obj, predefined, admin):
        """
        Check if on object obj was created predefined permissions predefined
        only if user is administrative role - admin

        obj        - object to check
        predefined - predefined permissions on object
        admin      - True if role administrative else False
        """
        b = False
        for perm in obj.permissions.list():
            role_name = API.roles.get(id=perm.get_role().get_id()).get_name()
            b = b or role_name == predefined
        return not (False if b and admin else b)

    # Check that there are two types of Permissions sub-tabs in the system:
    # for objects on which you can define permissions and for users.
    @tcms(TCMS_PLAN_ID, 54408)
    def testObjectsAndUserPermissions(self):
        """ testObjectsAndUserPermissions """
        msg = '%s has permissions subcollection.'
        msg_not = '%s has not permissions subcollection.'
        user = common.getUser()
        try:
            user.permissions.list()
            LOGGER.info(msg % 'User')
        except Exception as e:
            raise AssertionError(msg_not % 'User')

        for k in OBJS.keys():
            try:
                OBJS[k].get(k).permissions.list()
                LOGGER.info(msg % OBJS[k].get(k).name)
            except Exception as e:
                raise AssertionError(msg_not % type(OBJS[k].get(k)).__name__)

        try:
            API.disks.get(alias=DISK_NAME).permissions.list()
            LOGGER.info(msg % 'Disk')
        except Exception as e:
            raise AssertionError(msg_not % 'Disk')

    @tcms(TCMS_PLAN_ID, 54409)
    def testPermissionsInheritence(self):
        """ testPermissionsInheritence """
        common.addRoleToUser(roles.role.ClusterAdmin)
        # To be able login after clusteradmin pers will be removed
        common.givePermissionToCluster(config.MAIN_CLUSTER_NAME,
                roles.role.UserRole)

        loginAsUser(filter_=False)
        common.createVm(TMP_VM_NAME)
        common.removeVm(TMP_VM_NAME)
        LOGGER.info("User can create/remove vm with vm permissions.")
        loginAsAdmin()
        common.removeRoleFromUser(roles.role.ClusterAdmin)
        loginAsUser()
        self.assertRaises(errors.RequestError, common.createVm, TMP_VM_NAME,
                createDisk=False)
        LOGGER.info("User can't create/remove vm without vm permissions.")
        loginAsAdmin()
        common.removeAllPermissionFromCluster(config.MAIN_CLUSTER_NAME)

    # Check that in the object Permissions sub tab you will see all permissions
    # that were associated with the selected object in the main grid or one of
    # its ancestors.
    @tcms(TCMS_PLAN_ID, 54410)
    def testPermissionsSubTab(self):
        """ testPermissionsSubTab """
        # Try to add UserRole and AdminRole to object, then
        # check if both role are vissbile via /api/objects/objectid/permissions

        u1 = common.getUser()
        u2 = common.getUser(config.USER_NAME2)
        for name, obj in OBJS.items():
            LOGGER.info("Testing object %s" % name)
            o = obj.get(name)
            common.removeAllPermissionFromObject(o)
            common.givePermissionToObject(o, roles.role.UserRole, config.USER_NAME)
            common.givePermissionToObject(o, roles.role.VmPoolAdmin, config.USER_NAME2)

            users = [perm.user.get_id() for perm in o.permissions.list()]
            assert u1.get_id() in users and u2.get_id() in users
            LOGGER.info("There are vissible all permissions which were associated.")
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
    @bz(919686)
    def testDelegatePerms(self):
        """ testDelegatePerms """
        b = False
        common.createVm(TMP_VM_NAME)
        # Test SuperUser that he can add permissions
        for role in [r.get_name() for r in API.roles.list()]:
            LOGGER.info("Testing role - %s" % role)
            # Get roles perms, to check for manipulate_permissions
            perms = [p.get_name() for p in API.roles.get(role).get_permits().list()]
            if not 'login' in perms:
               LOGGER.info('User not tested, because dont have login perms.')
               continue

            common.addRoleToUser(role)  # Test Adding perms form system SuperUser
            common.givePermissionToVm(TMP_VM_NAME, role)

            # For know if login as User/Admin
            filt = not('Admin' in role or roles.role.SuperUser == role)
            # login as user with role
            loginAsUser(filter_=filt)
            vm = common.getObjectByName(API.vms, TMP_VM_NAME)
            # Test if user with role can/can't manipualte perms
            if 'manipulate_permissions' in perms:
                if filt or roles.role.SuperUser != role:
                    self.assertRaises(errors.RequestError, common.givePermissionToObject,
                            vm, roles.role.TemplateAdmin)
                    LOGGER.info("'%s' can't add admin permissions." % role)
                    common.givePermissionToObject(vm, roles.role.UserVmManager)
                    LOGGER.info("'%s' can add user permissions." % role)
                    try:
                        common.removeAllPermissionFromObject(vm)
                    except Exception as e:  # bz 919686
                        loginAsAdmin()
                        common.removeAllPermissionFromVm(TMP_VM_NAME)
                        b = True
                else:
                    common.givePermissionToObject(vm, roles.role.UserVmManager)
                    LOGGER.info("'%s' can add user permissions." % role)
                    common.givePermissionToObject(vm, roles.role.TemplateAdmin)
                    LOGGER.info("'%s' can add admin permissions." % role)
                    try:
                        common.removeAllPermissionFromObject(vm)
                    except Exception as e:  # bz 919686
                        loginAsAdmin()
                        common.removeAllPermissionFromVm(TMP_VM_NAME)
                        b = True
            else:
                self.assertRaises(errors.RequestError, common.givePermissionToObject,
                        vm, roles.role.UserRole)
                LOGGER.info("'%s' can't manipulate permisisons." % role)

            loginAsAdmin()
            common.removeRoleFromUser(role)
            common.removeAllPermissionFromVm(TMP_VM_NAME)

        loginAsAdmin()
        common.removeVm(TMP_VM_NAME)
        if b:
            raise AssertionError

    # in order ro add new object you will need the appropriate permission on the
    # ancestor (e.g. to create a new storage domain you'll need a "add storage
    # domain" permission on the "system" object,to create a new Host/VM you will
    # need appropriate permission on the relevant cluster.
    @tcms(TCMS_PLAN_ID, 54432)
    def testNewObjectCheckPerms(self):
        """ Adding new business entity/new object. """
        LOGGER.info('This functionality tests modules admin_tests and user_tests')

    # Check if user is under some Group if it has permissions of its group
    @tcms(TCMS_PLAN_ID, 54446)
    def testUsersPermissions(self):
        """ UsersPermissions """
        # test all possible things? or just one role?
        LOGGER.info("Adding new group with UserVmManager perms")
        grp = common.addGroup()
        common.addRoleToGroup(roles.role.UserVmManager, grp)

        LOGGER.info("Login as user from group")
        loginAsUser(userName=config.GROUP_USER, domain=config.USER_DOMAIN,
                password=config.USER_PASSWORD)
        common.createVm(TMP_VM_NAME)
        self.assertRaises(errors.RequestError,
                common.createTemplate, TMP_VM_NAME, TMP_TEMPLATE_NAME)
        common.removeVm(TMP_VM_NAME)

        loginAsAdmin()
        common.deleteGroup()
        common.removeUser(userName=config.GROUP_USER)

    # Creating object from user API and admin API should be differnt:
    # for example admin API - createVm - should not delegate perms on VM
    # user API - createVm - should add perms UserVmManager on VM
    @tcms(TCMS_PLAN_ID, 54420)
    #@bz(881145) - bz_plugin don't check verison
    @bz(921450)
    def testObjAdminUser(self):
        """ Object creating from User and Admin portal """
        # This is already implemented in test_user_roles
        b = False

        for r in [roles.role.VmCreator, roles.role.TemplateCreator,
                roles.role.SuperUser]:
            loginAsAdmin()
            role = API.roles.get(r)
            r_permits = [p.get_name() for p in role.permits.list()]

            common.addRoleToUser(role.get_name())
            common.givePermissionToVm(VM_NAME, roles.role.UserRole)
            loginAsUser(filter_=False if role.administrative else True)

            LOGGER.info("Testing role - " + role.get_name())
            # Create vm,template, disk and check permissions of it
            if 'create_vm' in r_permits:
                LOGGER.info("Testing create_vm.")
                common.createVm(TMP_VM_NAME, createDisk=False)
                vm = common.getObjectByName(API.vms, TMP_VM_NAME)
                b = b or self._checkPredefinedPermissions(vm,
                        VM_PREDEFINED, role.administrative)
                common.removeVm(TMP_VM_NAME)
            if 'create_template' in r_permits:
                LOGGER.info("Testing create_template.")
                common.createTemplate(VM_NAME, TMP_TEMPLATE_NAME)
                tmp = common.getObjectByName(API.templates, TMP_TEMPLATE_NAME)
                b = b or self._checkPredefinedPermissions(tmp,
                        TEMPLATE_PREDEFINED, role.administrative)
                common.removeTemplate(TMP_TEMPLATE_NAME)
            if 'create_disk' in r_permits:
                LOGGER.info("Testing create_disk.")
                common.createDiskObject(TMP_DISK_NAME,
                        storage=config.MAIN_STORAGE_NAME)
                disk = common.getObjectByName(API.disks, TMP_DISK_NAME)
                b = b or self._checkPredefinedPermissions(disk,
                        DISK_PREDEFINED, role.administrative)
                common.deleteDiskObject(disk)
            loginAsAdmin()
            common.removeRoleFromUser(r)
        vm = API.vms.get(VM_NAME)
        common.removeAllPermissionFromVm(VM_NAME)
        if b:
            raise AssertionError

    # add a group of users from AD to the system (give it some admin permission)
    # login as user from group, remove the user
    # Check that group still exist in the Configure-->System.
    # Check that group's permissions still exist
    @tcms(TCMS_PLAN_ID, 108233)
    def testRemoveUserFromGroup(self):
        """ Removing user that part of the group. """
        LOGGER.info("Adding new group with TemplateAdmin perms")
        grp = common.addGroup()
        common.addRoleToGroup(roles.role.TemplateAdmin, grp)

        LOGGER.info("Login as user from group")
        loginAsUser(userName=config.GROUP_USER, domain=config.USER_DOMAIN,
                password=config.USER_PASSWORD)

        loginAsAdmin()
        if common.getUser():
            LOGGER.info("User was added.")
        else:
            raise AssertionError("User was not added.")

        common.removeUser(userName=config.GROUP_USER)
        common.deleteGroup()

    # Check that data-center has a user with UserRole permission
    # Create new desktop pool
    # Check that permission was inherited from data-center
    # Go to User-portal and ensure that user can take a machine from created pool
    @tcms(TCMS_PLAN_ID, 109086)
    def testPermsInhForVmPools(self):
        """ Permission inheritance for desktop pools """
        loginAsAdmin()
        common.givePermissionToDc(config.MAIN_DC_NAME, roles.role.UserRole)

        loginAsUser()
        vmpool = common.getObjectByName(API.vmpools, VM_POOL_NAME)
        common.vmpoolBasicOperations(vmpool)

        loginAsAdmin()
        common.removeAllPermissionFromDc(config.MAIN_DC_NAME)

    # create a StorageDomain with templates and VMs
    # grant permissions for user X to some VMs & templates on that SD
    # destroy the SD take a look in the user under permission tab
    @tcms(TCMS_PLAN_ID, 111082)
    #@bz(892642) - bz_plugin don't check verison
    @bz(921450)
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
        common.createDiskObject(TMP_DISK_NAME, storage=config.ALT1_STORAGE_NAME)
        disk = API.disks.get(alias=TMP_DISK_NAME)

        common.givePermissionToVm(TMP_VM_NAME, roles.role.UserVmManager)
        common.givePermissionToTemplate(TMP_TEMPLATE_NAME, roles.role.TemplateOwner)
        common.givePermissionToObject(disk, roles.role.DiskOperator)
        common.removeNonMasterStorage(storageName=config.ALT1_STORAGE_NAME,
                                      datacenter=config.MAIN_DC_NAME,
                                      host=config.MAIN_HOST_NAME, destroy=True)

        common.removeVm(TMP_VM_NAME)
        # Template should be removed, Vm should stay, but should not have disk
        try:
            for p in common.getUser().permissions.list():
                role_name = API.roles.get(id=p.get_role().get_id()).get_name()
                assert not (role_name == roles.role.UserVmManager or
                        role_name == roles.role.TemplateOwner or
                        role_name == roles.role.DiskOperator)
        except Exception as e:
            # Because of bug 892642, need to remove all perms that stays
            common.removeUser()
            common.addUser()
            raise e

