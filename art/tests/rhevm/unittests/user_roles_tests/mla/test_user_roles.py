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

LOGGER  = common.logging.getLogger(__name__)
API     = common.API

# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
VM_NAME = 'user_roles__vm'
VM_NO_DISK = 'user_roles__vm_nodisk'
TEMPLATE_NAME = 'user_roles__template'
TEMPLATE_NO_DISK = 'user_roles__template_nodisk'
DISK_NAME = 'user_roles__disk'
VMPOOL_NAME = 'user_roles__vmpool'

ROLE_USER_NAME = 'user_roles__roleUserName'
ROLE_ADMIN_NAME = 'user_roles__roleAdminName'
INVALID_CHARS = '&^$%#*+/\\`~\"\':?!()[]}{=|><'

ROLE_USER_PERMITS = API.roles.get(roles.role.UserRole).permits.list()
ROLE_UTBVM_PERMITS = API.roles.get(roles.role.UserTemplateBasedVm).permits.list()
ROLE_ADMIN_PERMITS = API.roles.get(roles.role.TemplateAdmin).permits.list()

# Predefined role for creation of VM as non-admin user
VM_PREDEFINED = roles.role.UserVmManager
# Predefined role for creation of Disk as non-admin user
DISK_PREDEFINED = roles.role.DiskOperator
# Predefined role for creation of Template as non-admin user
TEMPLATE_PREDEFINED = roles.role.TemplateOwner

TCMS_PLAN_ID = 2597

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
    common.createVm(VM_NAME)
    common.createVm(VM_NO_DISK, createDisk=False)
    common.createTemplate(VM_NO_DISK, TEMPLATE_NO_DISK)
    common.createTemplate(VM_NAME, TEMPLATE_NAME)
    common.createVmPool(VMPOOL_NAME, TEMPLATE_NAME)
    common.createDiskObject(DISK_NAME)

def tearDownModule():
    loginAsAdmin()
    common.removeVm(VM_NAME)
    common.removeVm(VM_NO_DISK)
    common.deleteDisk(None, alias=DISK_NAME)
    vmpool = API.vmpools.get(VMPOOL_NAME)
    common.removeAllVmsInPool(VMPOOL_NAME)
    common.removeVmPool(vmpool)
    common.removeTemplate(TEMPLATE_NAME)
    common.removeTemplate(TEMPLATE_NO_DISK)
    common.removeAllUsers()

class RolesTests(unittest.TestCase):
    """ Tests that will be run for each role in VM_ROLES """
    __test__ = True

    def setUp(self):
        loginAsAdmin()

    def _checkPredefinedPermissions(self, obj, predefined):
        """
        Check if on object obj was created predefined permissions predefined

        obj        - object to check
        predefined - predefined permissions on object
        """
        b = False
        for perm in obj.permissions.list():
            role_name = API.roles.get(id=perm.get_role().get_id()).get_name()
            b = b or role_name == predefined
        return not b

    # Try to clone role
    # Clone was deleted from API
    # So using get -> add
    @tcms(TCMS_PLAN_ID, 54403)
    def testCloneRole(self):
        """ Clone role """
        common.addRole(ROLE_USER_NAME, roles.role.UserRole)
        common.deleteRole(ROLE_USER_NAME)

    # Check that only user that has permission to perform action "creatre role"
    # can create new role ,both Admin and User
    @tcms(TCMS_PLAN_ID, 54413)
    def testCreateRolePerms(self):
        """ CreateRolePermissions """
        for role in API.roles.list():
            if not 'login' in [p.get_name() for p in role.permits.list()]:
                LOGGER.info("Role %s not tested because can't login." % role.get_name())
                continue

            common.addRoleToUser(role.get_name())
            LOGGER.info("Testing if role %s can add new role." % role.get_name())
            l = [r.get_name() for r in role.get_permits().list()]
            loginAsUser(filter_=False if role.administrative else True)
            if 'manipulate_roles' in l:
                common.addRole(ROLE_USER_NAME, roles.role.UserRole)
                common.deleteRole(ROLE_USER_NAME)
                common.addRole(ROLE_ADMIN_NAME, roles.role.TemplateAdmin,
                        administrative=True)
                common.deleteRole(ROLE_ADMIN_NAME)
                LOGGER.info("%s can manipulate with roles." % role.get_name())
            else:
                self.assertRaises(errors.RequestError,
                        common.addRole, ROLE_USER_NAME, roles.role.UserRole)
                self.assertRaises(errors.RequestError,
                        common.addRole, ROLE_ADMIN_NAME, roles.role.TemplateAdmin)
                LOGGER.info("%s can't manipulate with roles." % role.get_name())

            loginAsAdmin()
            common.removeAllRolesFromUser()

    @tcms(TCMS_PLAN_ID, 54401)
    def testEditRole(self):
        """ EditRole """
        common.addRole(ROLE_USER_NAME, roles.role.UserTemplateBasedVm)
        LOGGER.info("User role %s created" % ROLE_USER_NAME)

        # 1. Edit created role.
        common.updateRole(ROLE_USER_NAME, description=ROLE_USER_NAME)
        LOGGER.info("'%s' was succcessfully editited" % ROLE_USER_NAME)
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
        common.updateRole(ROLE_USER_NAME, permits=ROLE_USER_PERMITS)
        LOGGER.info("User role %s updated" % ROLE_USER_NAME)

        # 5.Check that after editing(changing) a role effect will be immediate.
        # User should operate vm now
        loginAsUser()
        common.startVm(VM_NAME)
        loginAsUser(userName=config.USER_NAME3)
        common.stopVm(VM_NAME)
        LOGGER.info("All users, which has '%s' role were updated" % ROLE_USER_NAME)

        # clean up
        loginAsAdmin()
        common.removeAllUsers()
        common.addUser()
        common.addUser(userName=config.USER_NAME2)
        common.deleteRole(ROLE_USER_NAME)

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

            loginAsUser(filter_=False if role.administrative else True)
            assert len(API.roles.list()) == size
            LOGGER.info("Role %s can see all roles." % role.get_name())

            loginAsAdmin()
            common.removeAllRolesFromUser()

    # Check if rhevm return still same predefined perms
    @tcms(TCMS_PLAN_ID, 54411)
    def testPredefinedRoles(self):
        """ testPredefinedRoles """
        l = len(API.roles.list())
        assert len(API.roles.list()) == l
        LOGGER.info("There are still same predefined roles")

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
        common.addRole(ROLE_USER_NAME, roles.role.UserRole)
        common.addRole(ROLE_ADMIN_NAME, roles.role.TemplateAdmin,
                administrative=True)

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

    @tcms(TCMS_PLAN_ID, 54366)
    def testRoleCreation(self):
        """ RoleCreation """
        # Create user with user role, and user with admin role
        # This aslso tests other cases, so it is not here anymore
        # tests only invalid chars
        for char in INVALID_CHARS:
            LOGGER.info("Tesing char '%s' in role name" % char)
            self.assertRaises(errors.RequestError,
                    common.addRole, char, roles.role.UserRole)

    @tcms(TCMS_PLAN_ID, 54412)
    @bz(921450)
    def testRolesHiearchy(self):
        """ RolesHiearchy """
        # HIEARCHY:
        # System -> DC -> Sd      -> Disk
        #              |
        #              -> Cluster -> Host
        #              |          -> Vm     -> VmDisk
        #              |          -> VmPool
        #              -> Template
        #              -> Network
        # Check if permissions are correctly inherited
        msg_f = "Object don't have inherited perms."
        msg_t = "Object have inherited perms."
        common.removeAllPermissionFromObject(common.getUser())
        l = { # objects
                config.MAIN_CLUSTER_NAME: API.clusters,
                config.MAIN_DC_NAME: API.datacenters,
                config.MAIN_STORAGE_NAME: API.storagedomains,
                VM_NAME : API.vms
            }
        h = { # Hierchy
                config.MAIN_CLUSTER_NAME:
                {config.MAIN_HOST_NAME: API.hosts, VM_NAME: API.vms,
                    VMPOOL_NAME: API.vmpools, VM_NO_DISK: API.vms},
                config.MAIN_STORAGE_NAME:
                {DISK_NAME: API.disks},
                config.MAIN_DC_NAME:
                {config.MAIN_HOST_NAME: API.hosts, VM_NAME: API.vms,
                    VMPOOL_NAME: API.vmpools, TEMPLATE_NAME: API.templates,
                    VM_NO_DISK: API.vms, TEMPLATE_NO_DISK: API.templates},
                VM_NAME:
                {VM_NAME + '_Disk1' : API.vms.get(VM_NAME).disks}
            }

        b = False
        for k in l.keys():
            LOGGER.info("Testing propagated permissions from %s" % k)
            common.removeAllPermissionFromObject(l[k].get(k))  # Just for sure
            common.givePermissionToObject(l[k].get(k), roles.role.UserRole)
            for key, val in h[k].items():
                LOGGER.info("Checking inherited permissions for '%s'"
                        % (val.get(key).get_name()))
                a = self._checkPredefinedPermissions(val.get(key),
                        roles.role.UserRole)
                LOGGER.error(msg_f) if a else LOGGER.info(msg_t)
                b = b or a

            common.removeAllPermissionFromObject(l[k].get(k))

        common.removeUser()
        common.addUser()
        assert not b
