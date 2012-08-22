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

__test__ = False

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
VM_NAME = 'user_permissions__vm'
TMP_VM_NAME = 'user_permissions__tpm_vm'
TEMPLATE_NAME = 'user_permissions__template'
TMP_TEMPLATE_NAME = 'user_permissions__template_tmp'
VM_POOL_NAME = 'user_permissions__vm_pool'
CLUSTER_NAME = 'user_permissions__cluster'

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
    common.createVm(VM_NAME)
    common.createTemplate(VM_NAME, TEMPLATE_NAME)

def tearDownModule():
    common.removeTemplate(TEMPLATE_NAME)
    common.removeVm(VM_NAME)
    common.removeUser()

class PermissionsTests(unittest.TestCase):
    """ Tests that will be run for each role in VM_ROLES """
    __test__ = True

    def setUp(self):
        common.loginAsAdmin()

    @istest
    @logger
    def testPermissionsInheritence(self):
        """ testPermissionsInheritence """
        common.loginAsAdmin()
        common.addRoleToUser('ClusterAdmin')
        common.loginAsUser(filter_=False)
        common.createVm(TMP_VM_NAME)
        common.removeVm(TMP_VM_NAME)
        common.loginAsAdmin()
        common.removeRoleFromUser('ClusterAdmin')
        common.loginAsUser(filter_=False)
        self.assertRaises(errors.RequestError, common.createVm, TMP_VM_NAME)

    @istest
    @logger
    def testPermissionsSubTab(self):
        """ testPermissionsSubTab """
        common.loginAsAdmin()
        common.givePermissionToVm(VM_NAME, 'ClusterAdmin')
        common.givePermissionToCluster(config.MAIN_CLUSTER_NAME, 'ClusterAdmin')
        common.loginAsUser()
        # TODO
        common.loginAsAdmin()
        common.removeAllPermissionFromVm(VM_NAME)
        common.removeAllPermissionFromCluster(config.MAIN_CLUSTER_NAME)

    @istest
    @logger
    def testPermissionsPerRoleType(self):
        """ testPermissionsPerRoleType """
        common.loginAsAdmin()
        common.givePermissionToVm(VM_NAME, 'ClusterAdmin')
        common.givePermissionToVm(VM_NAME, 'UserRole')
        # TODO: CHECK ALL VMS PERMISSIONS
        common.removeAllPermissionFromVm(VM_NAME)

    @istest
    @logger
    def testLastPermOnObject(self):
        """ testLastPermOnObject """
        common.removeAllPermissionFromVm(VM_NAME)
        common.givePermissionToVm(VM_NAME, 'UserRole')
        common.removeAllPermissionFromVm(VM_NAME)

    @istest
    @logger
    def testRemovalOfSuperUser(self):
        """ testRemovalOfSuperUser """
        self.assertRaises(errors.RequestError, common.removeUser,
                config.OVIRT_USERNAME)
        self.assertRaises(errors.RequestError, common.removeRoleFromUser,
                'SuperUser', userName=config.OVIRT_USERNAME,
                domainName=config.OVIRT_DOMAIN)

    @istest
    @logger
    def testDelegatePerms(self):
        """ testDelegatePerms """
        common.loginAsAdmin()
        common.addRoleToUser('DataCenterAdmin')
        common.loginAsUser()
        self.assertRaises(errors.RequestError, common.addRoleToUser,
                'StorageAdmin')
        common.addRoleToUser('UserRole')

    @istest
    @logger
    def testPermsInhForVmPools(self):
        """ testPermsInhForVmPools """
        LOGGER.info("")
        common.loginAsAdmin()
        common.givePermissionToDc(config.MAIN_DC_NAME, 'UserRole')
        common.createVmPool(VM_POOL_NAME, TEMPLATE_NAME)
        common.loginAsUser()
        for vm in common.getAllVmsInPool(VM_POOL_NAME):
            vm.start()
            common.waitForState(vm, states.vm.up)
            vm.stop()
            common.waitForState(vm, states.vm.down)

    @istest
    @logger
    def testPermsRemovedAfterObjectRemove(self):
        """ testPermsRemovedAfterObjectRemove """
        LOGGER.info("")

        common.createNfsStorage(storageName=config.ALT_STORAGE_NAME,
            storageType='data',
            address=config.ALT_STORAGE_ADDRESS,
            path=config.ALT_STORAGE_PATH,
            datacenter=config.MAIN_DC_NAME,
            host=config.MAIN_HOST_NAME)
        common.attachActivateStorage(config.ALT_STORAGE_NAME, isMaster=False)
        common.createVm(TMP_VM_NAME, storage=config.ALT_STORAGE_NAME)
        common.createTemplate(TMP_VM_NAME, TMP_TEMPLATE_NAME)
        common.givePermissionToVm(TMP_VM_NAME, 'UserVmManager')
        common.givePermissionToTemplate(TMP_TEMPLATE_NAME, 'TemplateOwner')
        common.removeNonMasterStorage(config.ALT_STORAGE_NAME)
        # TODO: Check permissoons if disspaered

    #TODO: 108233, 109086, 54446

