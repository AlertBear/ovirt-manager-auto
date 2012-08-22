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

import config
import common
import states
import unittest2 as unittest
import sys
from nose.tools import istest
from functools import wraps

from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors

import logging

LOGGER  = common.logging.getLogger(__name__)
API     = common.API


# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
VM_NAME = 'user_roles__vm'
ROLE_USER_NAME = 'user_roles__roleUserName'
ROLE_ADMIN_NAME = 'user_roles__roleAdminName'
ROLE_USER_PERMITS = API.roles.get('UserRole').get_permits().list()
ROLE_ADMIN_PERMITS = API.roles.get('TemplateAdmin').get_permits().list()
INVALID_CHARS = '&^$%#*+/\\`~\"\':?!()[]}{=|><'

def logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        LOGGER.info("Running: %s" % (func.__name__))
        try:
            result = func(*args, **kwargs)
            LOGGER.info("Case '%s' successed" % func.__name__)
            return result
        except Exception as err:
            LOGGER.info("!ERROR! => " + str(err))
            raise err

def setUpModule():
    common.addUser()
    common.addUser(userName=config.USER_NAME2)
    common.addUser(userName=config.USER_NAME3)

    common.createVm(VM_NAME, createDisk=False)

def tearDownModule():
    common.removeVm(VM_NAME)
    common.removeUser()


class RolesTests(unittest.TestCase):
    """ Tests that will be run for each role in VM_ROLES """
    __test__ = True

    @istest
    @logger
    def testRoleCreation(self):
        """ testRoleCreation """
        common.addRole(ROLE_USER_NAME, ROLE_USER_PERMITS)
        common.addRole(ROLE_ADMIN_NAME, ROLE_ADMIN_PERMITS, administrative=True)

        for char in INVALID_CHARS:
            self.assertRaises(errors.RequestError, common.addRole, char, ROLE_USER_PERMITS)
        # TODO CHECK FOR ERROR MSG:q

    @istest
    @logger
    def testEditRole(self):
        """ testEditRole """
        #?? common.updateRole(ROLE_USER_NAME, description="NewDescription")
        common.addRoleToUser(ROLE_USER_NAME, userName=config.USER_NAME)
        common.addRoleToUser(ROLE_USER_NAME, userName=config.USER_NAME2)
        common.addRoleToUser(ROLE_USER_NAME, userName=config.USER_NAME3)
        common.updateRole(ROLE_USER_NAME, description="OldDescription")

        for userName in [config.USER_NAME, config.USER_NAME2, config.USER_NAME3]:
            user = API.users.get(userName)
            assert user.roles.get(ROLE_USER_NAME).get_description() == "OldDescription"

    @istest
    @logger
    def testRemoveRole(self):
        """ testRemoveRole """
        common.givePermissionToVm(VM_NAME, ROLE_USER_NAME)
        common.deleteRole(ROLE_ADMIN_NAME)
        self.assertRaises(errors.RequestError, common.deleteRole,
                ROLE_USER_NAME)

    @istest
    @logger
    def testRemovePreDefinedRoles(self):
        """ testRemovePreDefinedRoles """
        for role in API.roles.list():
            self.assertRaises(errors.RequestError, role.delete)

    @istest
    @logger
    def testRolesHiearchy(self):
        """ testRolesHiearchy """
        common.givePermissionToCluster(config.MAIN_CLUSTER_NAME, 'UserRole')
        # TODO:
