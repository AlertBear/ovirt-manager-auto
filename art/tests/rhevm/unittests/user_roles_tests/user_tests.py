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

from user_roles_tests import roles
from user_roles_tests import common
from user_roles_tests import test_admin_actions

def setUpModule():
    test_admin_actions.setUpModule()

def tearDownModule():
    test_admin_actions.tearDownModule()

class UserVmManagerActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.UserVmManager
        self.perms = common.hasPermissions(self.role)
        self.filter_ = True
        super(UserVmManagerActionsTests, self).setUpClass()


class DiskOperatorActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.DiskOperator
        self.filter_ = True
        self.perms = common.hasPermissions(self.role)
        super(DiskOperatorActionsTests, self).setUpClass()


class DiskCreatorActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.DiskCreator
        self.filter_ = True
        self.perms = common.hasPermissions(self.role)
        super(DiskCreatorActionsTests, self).setUpClass()


class PowerUserRoleActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.PowerUserRole
        self.filter_ = True
        self.perms = common.hasPermissions(self.role)
        super(PowerUserRoleActionsTests, self).setUpClass()

class UserRoleActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.UserRole
        self.filter_ = True
        self.perms = common.hasPermissions(self.role)
        super(UserRoleActionsTests, self).setUpClass()


class VmCreatorActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.VmCreator
        self.filter_ = True
        self.perms = common.hasPermissions(self.role)
        super(VmCreatorActionsTests, self).setUpClass()


class TemplateCreatorActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.TemplateCreator
        self.filter_ = True
        self.perms = common.hasPermissions(self.role)
        super(TemplateCreatorActionsTests, self).setUpClass()


class TemplateOwnerActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.TemplateOwner
        self.filter_ = True
        self.perms = common.hasPermissions(self.role)
        super(TemplateOwnerActionsTests, self).setUpClass()
