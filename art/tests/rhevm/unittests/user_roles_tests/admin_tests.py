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


class SuperUserActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.SuperUser
        self.filter_ = False
        self.perms = common.hasPermissions(self.role)
        super(SuperUserActionsTests, self).setUpClass()


class TemplateAdminActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.TemplateAdmin
        self.filter_ = False
        self.perms = common.hasPermissions(self.role)
        super(TemplateAdminActionsTests, self).setUpClass()


class VmPoolAdminActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.VmPoolAdmin
        self.filter_ = False
        self.perms = common.hasPermissions(self.role)
        super(VmPoolAdminActionsTests, self).setUpClass()


class HostAdminActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.HostAdmin
        self.filter_ = False
        self.perms = common.hasPermissions(self.role)
        super(HostAdminActionsTests, self).setUpClass()


class StorageAdminActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.StorageAdmin
        self.filter_ = False
        self.perms = common.hasPermissions(self.role)
        super(StorageAdminActionsTests, self).setUpClass()

class DataCenterAdminActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.DataCenterAdmin
        self.filter_ = False
        self.perms = common.hasPermissions(self.role)
        super(DataCenterAdminActionsTests, self).setUpClass()


class ClusterAdminActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.ClusterAdmin
        self.filter_ = False
        self.perms = common.hasPermissions(self.role)

        super(ClusterAdminActionsTests, self).setUpClass()


class NetworkAdminActionsTests(test_admin_actions.UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.NetworkAdmin
        self.filter_ = False
        self.perms = common.hasPermissions(self.role)

        super(NetworkAdminActionsTests, self).setUpClass()
