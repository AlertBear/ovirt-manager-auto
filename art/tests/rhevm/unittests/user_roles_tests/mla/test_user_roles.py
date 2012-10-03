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
from unittest2 import SkipTest
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

from art.test_handler.settings import opts
# rhevm_api
from art.rhevm_api.tests_lib.high_level import storagedomains as storagedomains_high
from art.rhevm_api.tests_lib.low_level import users
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import networks
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks

LOGGER  = common.logging.getLogger(__name__)
API     = common.API

# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
VM_NAME = 'user_roles__vm'
TMP_VM_NAME = 'user_roles__vm_tmp'
TEMPLATE_NAME = 'user_roles__template'
DISK_NAME = 'user_roles__disk'
TMP_DISK_NAME = 'user_roles__disk_tmp'
VMPOOL_NAME = 'user_roles__vmpool'

ROLE_USER_NAME = 'user_roles__roleUserName'
ROLE_ADMIN_NAME = 'user_roles__roleAdminName'
ROLE_USER_PERMITS = API.roles.get(roles.role.UserRole).get_permits().list()
ROLE_ADMIN_PERMITS = API.roles.get(roles.role.TemplateAdmin).get_permits().list()
INVALID_CHARS = '&^$%#*+/\\`~\"\':?!()[]}{=|><'

# Predefined role for creation of VM as non-admin user
VM_PREDEFINED = roles.role.UserVmManager
# Predefined role for creation of Disk as non-admin user
DISK_PREDEFINED = roles.role.DiskOperator
# Predefined role for creation of Template as non-admin user
TEMPLATE_PREDEFINED = roles.role.TemplateOwner

TCMS_PLAN_ID = 2597

def setUpModule():
    common.addUser()
    common.addUser(userName=config.USER_NAME2)
    #common.addUser(userName=config.USER_NAME3)

    common.createVm(VM_NAME, createDisk=False)

def tearDownModule():
    common.loginAsAdmin()
    common.deleteDisk(None, alias=DISK_NAME)
    common.deleteDisk(None, alias=TMP_DISK_NAME)
    common.removeVm(VM_NAME)
    common.removeAllUsers()

class RolesTests(unittest.TestCase):
    """ Tests that will be run for each role in VM_ROLES """
    __test__ = True

    # Try to clone role
    # Clone was deleted from API
    # So using get -> add
    @tcms(TCMS_PLAN_ID, 54403)
    def testCloneRole(self):
        """ Clone role """
        role = API.roles.get(roles.role.UserRole)
        name = "Copy_of_" + role.get_name()
        LOGGER.info("Trying to clone UserRole - new name '%s'" % name)

        perms = params.Permits(ROLE_USER_PERMITS)
        role = params.Role(name=name, permits=perms, administrative=False)
        try:
            API.roles.add(role)
        except Exception as er:
            print er

        LOGGER.info("Role was added.")

        role = API.roles.get(name)

        assert role is not None
        role.delete()
        LOGGER.info("Removing newly created role.")
        assert API.roles.get(name) is None

    # Check that only user that has permission to perform action "creatre role"
    # can create new role ,both Admin and User
    @tcms(TCMS_PLAN_ID, 54413)
    def testCreateRolePerms(self):
        """ CreateRolePermissions """
        for role in API.roles.list():
            if not 'login' in [p.get_name() for p in role.permits.list()]:
                LOGGER.info("Role %s not tested because can't login." %role.get_name())
                continue

            common.addRoleToUser(role.get_name())
            LOGGER.info("Testing if role %s can add new role." % role.get_name())
            l = [r.get_name() for r in role.get_permits().list()]
            common.loginAsUser(filter_=False if role.administrative else True)
            if 'manipulate_roles' in l:
                if API.roles.get(ROLE_USER_NAME) is not None:
                    common.deleteRole(ROLE_USER_NAME)
                common.addRole(ROLE_USER_NAME, ROLE_USER_PERMITS)
                common.deleteRole(ROLE_USER_NAME)
                common.addRole(ROLE_ADMIN_NAME, ROLE_ADMIN_PERMITS)
                common.deleteRole(ROLE_ADMIN_NAME)
            else:
                self.assertRaises(errors.RequestError, common.addRole, ROLE_USER_NAME, ROLE_USER_PERMITS)
                self.assertRaises(errors.RequestError, common.addRole, ROLE_ADMIN_NAME, ROLE_ADMIN_PERMITS)

            LOGGER.info("Success")
            common.loginAsAdmin()
            common.removeAllRolesFromUser()
            common.removeAllPermissionFromObject(common.getUser())

    @tcms(TCMS_PLAN_ID, 54401)
    def testEditRole(self):
        """ EditRole """
        common.addRole(ROLE_USER_NAME, ROLE_USER_PERMITS)
        LOGGER.info("User role %s created" % ROLE_USER_NAME)

        # 1. Edit created role.
        self.assertRaises(errors.RequestError, common.updateRole, roles.role.UserRole,
                    description="NewDescription")
        LOGGER.info("UserRole can't be editited")
        # 2.Create several users and associate them with certain role.
        common.addRoleToUser(ROLE_USER_NAME)
        LOGGER.info("Added role '%s' to user '%s'" % (ROLE_USER_NAME, config.USER_NAME))
        common.addRoleToUser(ROLE_USER_NAME, userName=config.USER_NAME2)
        LOGGER.info("Added role '%s' to user '%s'" % (ROLE_USER_NAME, config.USER_NAME2))
        # 3.Create a new user and associate it with the role.
        common.addUser(userName=config.USER_NAME3)
        common.addRoleToUser(ROLE_USER_NAME, userName=config.USER_NAME3)
        LOGGER.info("Added role '%s' to newly created user '%s'" % (ROLE_USER_NAME, config.USER_NAME3))
        # 4.Edit new user's role.
        common.updateRole(ROLE_USER_NAME, description="OldDescription**")
        LOGGER.info("User role %s updated" % ROLE_USER_NAME)

        # 5.Check that after editing(changing) a role effect will be immediate.
        u1 = common.getUser()
        u2 = common.getUser(userName=config.USER_NAME2)
        u3 = common.getUser(userName=config.USER_NAME3)
        for user in [u1, u2, u3]:
            assert API.roles.get(id=user.roles.get(ROLE_USER_NAME).get_id()).get_description() == "OldDescription**"
            for r in user.roles.list():
                r.delete()
        LOGGER.info("All users, which has '%s' role were updated" % ROLE_USER_NAME)

        # clean up
        common.deleteRole(ROLE_USER_NAME)
        u3.delete()
        LOGGER.info("Cleaned up")


    # For all user roles, there should be option to list all roles
    @tcms(TCMS_PLAN_ID, 54415)
    def testListOfRoles(self):
        """ testListOfRoles """
        size = len(API.roles.list())
        for role in API.roles.list():
            if not 'login' in [p.get_name() for p in role.permits.list()]:
                LOGGER.info("Role %s not tested because can't login." %role.get_name())
                continue
            common.addRoleToUser(role.get_name())
            LOGGER.info("Testing if role %s can see all roles." % role.get_name())
            common.loginAsUser(filter_=False if role.administrative else True)

            assert len(API.roles.list()) == size

            LOGGER.info("Success")
            common.loginAsAdmin()
            common.removeAllRolesFromUser()
            common.removeAllPermissionFromObject(common.getUser())

    # Check if rhevm return still same predefined perms
    @tcms(TCMS_PLAN_ID, 54411)
    def testPredefinedRoles(self):
        """ testPredefinedRoles """
        LOGGER.info("Test case - PredefinedRoles")
        l = len(API.roles.list())
        assert len(API.roles.list()) == l
        LOGGER.info("Success")

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


    # When creating a new object in RHEV-M ,a new permission is automativally
    # added on it. The permission consists of new object,
    # current user and predefined role.
    @tcms(TCMS_PLAN_ID, 54421)
    @bz(881145)
    def testPredefinedRolesPerObject(self):
        """ PredefinedRolesPerObject """
        try:
            for role in API.roles.list():
                r_permits = [p.get_name() for p in role.permits.list()]
                if not 'login' in r_permits:
                    LOGGER.info("Role %s not tested because can't login." %role.get_name())
                    continue

                common.loginAsAdmin()
                common.removeAllRolesFromUser()
                common.removeAllPermissionFromObject(common.getUser())
                common.addRoleToUser(role.get_name())
                common.loginAsUser(filter_=False if role.administrative else True)
                LOGGER.info("Testing role - " + role.get_name())
                # Create vm,template, disk and check permissions of it
                if 'create_vm' in r_permits:
                    common.createVm(TMP_VM_NAME, createDisk=False)

                    common.loginAsAdmin()
                    self._checkPredefinedPermissions(API.vms.get(TMP_VM_NAME),
                            VM_PREDEFINED, role.administrative)
                    common.removeVm(TMP_VM_NAME)
                    common.loginAsUser(filter_=not role.administrative)
                if 'create_template' in r_permits:
                    common.createTemplate(VM_NAME, TEMPLATE_NAME)

                    common.loginAsAdmin()
                    self._checkPredefinedPermissions(API.templates.get(TEMPLATE_NAME),
                            TEMPLATE_PREDEFINED, role.administrative)
                    common.removeTemplate(TEMPLATE_NAME)
                    common.loginAsUser(filter_=not role.administrative)
                if 'create_disk' in r_permits:
                    common.createDiskObjectNoCheck(TMP_DISK_NAME,
                            storage=config.MAIN_STORAGE_NAME)

                    common.loginAsAdmin()
                    d = API.disks.get(alias=TMP_DISK_NAME)
                    common.waitForState(d, 'ok')
                    self._checkPredefinedPermissions(d, DISK_PREDEFINED,
                            role.administrative)
                    common.deleteDiskObject(d)
                    common.loginAsUser(filter_=not role.administrative)
        except Exception as e:
            try:
                common.loginAsAdmin()
                common.deleteDisk(None, alias=TMP_DISK_NAME)
                common.removeAllRolesFromUser()
                common.removeAllPermissionFromObject(common.getUser())
            except Exception as ee:
                LOGGER.error(str(ee))
            LOGGER.error(str(e))
            raise e


    # Test that pre-defined roles can not be removed.
    @tcms(TCMS_PLAN_ID, 54540)
    def testRemovePreDefinedRoles(self):
        """ RemovePreDefinedRoles """
        for role in API.roles.list():
            LOGGER.info("Trying to delete '%s'" % role.get_name())
            self.assertRaises(errors.RequestError, role.delete)


    @tcms(TCMS_PLAN_ID, 54402)
    def testRemoveRole(self):
        """ RemoveRole """
        if API.roles.get(ROLE_USER_NAME) is not None:
            common.deleteRole(ROLE_USER_NAME)
        common.addRole(ROLE_USER_NAME, ROLE_USER_PERMITS)
        LOGGER.info("User role %s created" % ROLE_USER_NAME)
        common.addRole(ROLE_ADMIN_NAME, ROLE_ADMIN_PERMITS, administrative=True)
        LOGGER.info("Admin role %s created" % ROLE_ADMIN_NAME)


        common.givePermissionToVm(VM_NAME, ROLE_USER_NAME)
        # 2,Try to remove role that has no association with users.
        common.deleteRole(ROLE_ADMIN_NAME)
        LOGGER.info("Role %s removed successfully" % ROLE_ADMIN_NAME)
        # 1.Try to remove role that is associated with user ot users.
        self.assertRaises(errors.RequestError, common.deleteRole,
                ROLE_USER_NAME)


        LOGGER.info("Role %s can't be removed" % ROLE_USER_NAME)
        # clean Up
        common.removeAllPermissionFromVm(VM_NAME)
        common.deleteRole(ROLE_USER_NAME)
        LOGGER.info("Cleaned up")


    # Create user with user role, and user with admin role
    # Try to give the new role name that consist illegal
    # charachters like (&^&$%^$%#*_+)
    @tcms(TCMS_PLAN_ID, 54366)
    def testRoleCreation(self):
        """ RoleCreation """
        if API.roles.get(ROLE_USER_NAME) is not None:
            common.deleteRole(ROLE_USER_NAME)
        common.addRole(ROLE_USER_NAME, ROLE_USER_PERMITS)
        LOGGER.info("User role %s created" % ROLE_USER_NAME)
        common.addRole(ROLE_ADMIN_NAME, ROLE_ADMIN_PERMITS, administrative=True)
        LOGGER.info("Admin role %s created" % ROLE_ADMIN_NAME)

        for char in INVALID_CHARS:
            LOGGER.info("Tesing char '%s' in role name" % char)
            self.assertRaises(errors.RequestError, common.addRole, char, ROLE_USER_PERMITS)

        # clean up
        common.deleteRole(ROLE_USER_NAME)
        common.deleteRole(ROLE_ADMIN_NAME)
        LOGGER.info("Cleaned up")


    @tcms(TCMS_PLAN_ID, 54412)
    @bz(881145)
    def testRolesHiearchy(self):
        """ RolesHiearchy """
        # TODO
        # HIEARCHY:
        # System -> DC -> SD      -> TMP
        #              |
        #              -> CLUSTER -> HOST
        #              |          -> VM
        #              |          -> Pool
        #              -> USER
        #1.Create Cluster.
        #2.Put host in the cluster.
        #3.Create VM on this cluster.
        #4.Assign role to a cluster.
        #5.Assigning a Role to a Cluster, means that the role apply to all the
        #objects that are contained within Cluster hierarchy (Host,VMs).
        #6.The same manner test hierarchy with other objects as well
        #    Data Center
        #    Storage Pool/Storage Domains
        #    Users
        #    Hosts
        #    VMs
        common.loginAsAdmin()
        try:
            l = {config.MAIN_CLUSTER_NAME: API.clusters,
                    config.MAIN_HOST_NAME: API.hosts,
                    config.MAIN_DC_NAME: API.datacenters,
                    config.MAIN_STORAGE_NAME: API.storagedomains}
            h = { # Hierchy
                config.MAIN_CLUSTER_NAME:
                [{config.MAIN_HOST_NAME: API.hosts}, {VM_NAME: API.vms},
                    {VMPOOL_NAME: API.vmpools}],
                config.MAIN_STORAGE_NAME:
                [{TEMPLATE_NAME: API.templates}],
                config.MAIN_DC_NAME:
                [{config.MAIN_HOST_NAME: API.hosts}, {VM_NAME: API.vms},
                    {VMPOOL_NAME: API.vmpools}, {TEMPLATE_NAME: API.templates}]
                }

            for k in l.keys():
                LOGGER.info("Testing propagated permissions from %s" % k)
                common.removeAllPermissionFromObject(l[k].get(k))  # Just for sure
                common.givePermissionToObject(l[k].get(k), roles.role.UserRole)
                for obj in h[k]:
                    for kk in obj.keys():
                        LOGGER.info("Checking inherited permissions for '%s'" % (obj[kk].get(kk).get_name()))
                        self._checkPredefinedPermissions(obj[kk].get(kk), roles.role.UserRole, False)

                common.removeAllPermissionFromObject(l[k].get(k))
        except Exception as e:
            LOGGER.error(str(e))
            for k in l.keys():
                common.removeAllPermissionFromObject(l[k].get(k))
            raise e

