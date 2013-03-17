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

import unittest2 as unittest
import logging

from functools import wraps
from nose.tools import istest
from ovirtsdk.xml import params
from user_roles_tests import config
from user_roles_tests import common
from user_roles_tests import states
from user_roles_tests import roles
from ovirtsdk.infrastructure import errors

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

TCMS_PLAN_ID = 5767

# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
VM_NAME = 'user_disk_permissions__vm'
TMP_VM_NAME = 'user_disk_permissions__vm_tmp'
CLUSTER_NAME = 'user_disk_permissions__cluster'
DISK_NAME = 'user_disk_permissions__disk'
DISK_SHARED = 'user_disk_permissions__shared'
TMP_DISK_NAME = 'user_disk_permissions__disk_tmp'
TMP2_DISK_NAME = 'user_disk_permissions__disk_tmp2'

def loginAsUser(**kwargs):
    common.loginAsUser(**kwargs)
    global API
    API = common.API

def loginAsAdmin():
    common.loginAsAdmin()
    global API
    API = common.API

def setUpModule():
    ''' setUpModule '''
    common.addUser()
    common.createVm(VM_NAME)
    common.createDiskObject(DISK_NAME)

    common.createNfsStorage(storageName=config.ALT1_STORAGE_NAME,
                            address=config.ALT1_STORAGE_ADDRESS,
                            path=config.ALT1_STORAGE_PATH,
                            datacenter=config.MAIN_DC_NAME,
                            host=config.MAIN_HOST_NAME)
    common.attachActivateStorage(config.ALT1_STORAGE_NAME)

def tearDownModule():
    ''' tearDownModule '''
    loginAsAdmin()
    common.removeNonMasterStorage(storageName=config.ALT1_STORAGE_NAME,
                                  datacenter=config.MAIN_DC_NAME,
                                  host=config.MAIN_HOST_NAME)
    common.removeVm(VM_NAME)
    common.deleteDisk(None, DISK_NAME)
    common.removeUser()

class DiskPermissionsTests(unittest.TestCase):
    ''' DiskPermissionsTests '''
    __test__ = True

    def setUp(self):
        loginAsAdmin()

    @tcms(TCMS_PLAN_ID, 147121)
    def testDiskInheritedPermissions(self):
        """ DiskInheritedPermissions """
        # Check if disk inherit perms from SD
        sd = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        vm = API.vms.get(VM_NAME)

        disk = common.createDiskObject(TMP_DISK_NAME)
        common.givePermissionToObject(sd, roles.role.DiskOperator)
        self.assertTrue(common.hasUserPermissions(disk, roles.role.DiskOperator))
        LOGGER.info("Disk %s inherited permissions from sd." %(TMP_DISK_NAME))

        # Check if after disk is attach to vm it iherit VM perms
        common.givePermissionToObject(vm, roles.role.UserVmManager)
        vm.disks.add(disk)
        self.assertTrue(common.hasUserPermissions(disk, roles.role.UserVmManager))
        LOGGER.info("After attaching disk to vm, disk inherited permissons from VM.")

        # clean up
        disk.delete()
        common.waitForRemove(disk)
        common.removeAllPermissionFromObject(vm)
        common.removeAllPermissionFromObject(sd)

    @tcms(TCMS_PLAN_ID, 147122)
    def testCreateDisk(self):
        """ CreateDisk """
        sd = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        common.givePermissionToObject(sd, roles.role.StorageAdmin)

        # Check if user has StorageAdmin perms on SD he can create Disk
        loginAsUser(filter_=False)
        dd = common.createDiskObject(TMP_DISK_NAME, storage=config.MAIN_STORAGE_NAME)
        common.deleteDiskObject(dd)
        LOGGER.info("User with StorageAdmin perms on SD can create disk.")

        # remove permissions from SD
        loginAsAdmin()
        common.removeAllPermissionFromObject(sd)
        common.givePermissionToObject(sd, roles.role.UserRole)

        # Check if user has not StorageAdmin perms on SD he can't create Disk
        loginAsUser()
        self.assertRaises(errors.RequestError, common.createDiskObject,
                TMP_DISK_NAME)
        LOGGER.info("User without StorageAdmin perms on SD can't create disk.")
        common.removeAllPermissionFromObject(sd)

    @tcms(TCMS_PLAN_ID, 147123)
    def testAttachDiskToVM(self):
        """ AttachDiskToVM """
        # Attach disk need perm on disk and on VM.
        vm = API.vms.get(VM_NAME)
        disk = API.disks.get(alias=DISK_NAME)
        common.givePermissionToObject(disk, roles.role.DiskOperator)
        common.givePermissionToObject(vm, roles.role.UserVmManager)

        loginAsUser()
        vm = common.getObjectByName(API.vms, VM_NAME)
        disk = common.getObjectByName(API.disks, DISK_NAME)
        vm.disks.add(disk)  # Attach
        LOGGER.info("User with UserVmManager role on vm and DiskOperator role"+
                " on disk can attach disk.")

        # Clean up
        loginAsAdmin()
        vm = API.vms.get(VM_NAME)
        disk = API.disks.get(alias=DISK_NAME)
        vm.disks.get(id=disk.get_id()).delete(params.Action(detach=True))  # Detach
        common.removeAllPermissionFromObject(vm)
        common.removeAllPermissionFromObject(disk)

    @tcms(TCMS_PLAN_ID, 147124)
    def testDetachDisk(self):
        """ DetachDisk """
        # Detach disk need only perms on VM
        vm = API.vms.get(VM_NAME)
        disk = API.disks.get(alias=DISK_NAME)
        vm.disks.add(disk)  # Attach

        common.givePermissionToObject(vm, roles.role.UserVmManager)
        # Need to have also have some perms on disk, to view
        # this disk to test if we can attach it
        common.givePermissionToObject(disk, roles.role.UserTemplateBasedVm)

        loginAsUser() # Try detach disk
        vm = common.getObjectByName(API.vms, VM_NAME)
        disk_id = common.getObjectByName(API.disks, DISK_NAME).get_id()
        vm.disks.get(id=disk_id).delete(params.Action(detach=True))
        LOGGER.info("User who has UserVmManager perms on vm, can detach disk.")

        loginAsAdmin()  # clean up
        vm = API.vms.get(VM_NAME)
        disk = API.disks.get(alias=DISK_NAME)
        common.removeAllPermissionFromObject(vm)
        common.removeAllPermissionFromObject(disk)

    @tcms(TCMS_PLAN_ID, 147125)
    def testActivateDeactivateDisk(self):
        """ ActivateDeactivateDisk """
        # Activate/deactivate disk need to have perms only on VM
        vm = API.vms.get(VM_NAME)
        common.givePermissionToObject(vm, roles.role.UserVmManager)

        loginAsUser()  # Try detach disk
        vm = common.getObjectByName(API.vms, VM_NAME)
        vmdisk = vm.disks.list()[0]
        vmdisk.deactivate()
        vmdisk.activate()
        LOGGER.info("User with UserVmManager permissions can active/deactive vm disk.")

        # Clean up
        loginAsAdmin()
        vm = API.vms.get(VM_NAME)
        common.removeAllPermissionFromObject(vm)

    @tcms(TCMS_PLAN_ID, 147126)
    def testRemoveDisk(self):
        """ RemoveDisk """
        # To remove disk you need aproriate permissions on disk
        common.createDiskObject(TMP_DISK_NAME)

        loginAsAdmin()  # Give user DiskOperator permissions
        disk = API.disks.get(TMP_DISK_NAME)
        common.givePermissionToObject(disk, roles.role.DiskOperator)
        # This is need, because after we delete disk we lost all permissions,
        # so even login perms
        common.givePermissionToObject(API.vms.get(VM_NAME), roles.role.UserRole)

        loginAsUser(filter_=True)  # Try to remove dsk as DiskOperator
        disk = common.getObjectByName(API.disks, TMP_DISK_NAME)
        common.deleteDiskObject(disk)

        loginAsAdmin()
        common.removeAllPermissionFromObject(API.vms.get(VM_NAME))
        LOGGER.info("User with DiskOperator permissions can remove disk.")

    @tcms(TCMS_PLAN_ID, 147127)
    def testUpdateDisk(self):
        """ UpdateDisk """
        # Edit disks need appropriate perms on disk.
        # Currently only vm disk can be updated
        loginAsAdmin()
        common.givePermissionToObject(API.vms.get(VM_NAME), roles.role.DiskOperator)

        loginAsUser(filter_=True)
        common.editVmDiskProperties(VM_NAME)

        loginAsAdmin()
        common.removeAllPermissionFromObject(API.vms.get(VM_NAME))

    @tcms(TCMS_PLAN_ID, 147128)
    def testMoveDisk(self):
        """ testMoveDisk """
        # Move disk without pemrissions
        common.createVm(TMP_VM_NAME)
        vm = API.vms.get(TMP_VM_NAME)
        common.givePermissionToObject(vm, roles.role.StorageAdmin)

        loginAsUser(filter_=False)
        disk = common.getObjectByName(API.vms, TMP_VM_NAME).disks.list()[0]
        sd2 = common.getObjectByName(API.storagedomains, config.ALT1_STORAGE_NAME)
        self.assertRaises(errors.RequestError, disk.move,
                params.Action(storage_domain=sd2))
        LOGGER.info("User without perms on sds can't move disk.")

        # Move disk with permissions only on destination sd
        loginAsAdmin()
        sd = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        sd2 = API.storagedomains.get(config.ALT1_STORAGE_NAME)
        common.removeAllPermissionFromObject(vm)
        common.givePermissionToObject(sd, roles.role.StorageAdmin)

        loginAsUser(filter_=False)
        disk = common.getObjectByName(API.vms, TMP_VM_NAME).disks.list()[0]
        sd2 = common.getObjectByName(API.storagedomains, config.ALT1_STORAGE_NAME)
        self.assertRaises(errors.RequestError, disk.move,
                params.Action(storage_domain=sd2))
        LOGGER.info("User without perms on target sd can't move disk.")

        # Move disk with permissions on both sds
        loginAsAdmin()
        sd2 = API.storagedomains.get(config.ALT1_STORAGE_NAME)
        common.givePermissionToObject(sd2, roles.role.DiskCreator)

        loginAsUser(filter_=False)
        disk = common.getObjectByName(API.vms, TMP_VM_NAME).disks.list()[0]
        sd2 = common.getObjectByName(API.storagedomains, config.ALT1_STORAGE_NAME)
        disk.move(params.Action(storage_domain=sd2))
        common.waitForState(disk, states.disk.ok)
        LOGGER.info("User with perms on target sd and disk can move disk.")

        loginAsAdmin()
        sd2 = API.storagedomains.get(config.ALT1_STORAGE_NAME)
        sd = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        common.removeAllPermissionFromObject(sd)
        common.removeAllPermissionFromObject(sd2)
        common.removeVm(TMP_VM_NAME)

    @tcms(TCMS_PLAN_ID, 147129)
    def testAddDiskToVm(self):
        """ editAddDiskToVm """
        sd = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        common.givePermissionToObject(sd, roles.role.UserTemplateBasedVm)
        common.givePermissionToVm(VM_NAME, roles.role.UserVmManager)

        sd = params.StorageDomains(storage_domain=[sd])
        disk = params.Disk(storage_domains=sd, size=1024 * 1024,
                    status=None, interface='virtio', format='cow',
                    sparse=True)

        loginAsUser()
        vm = common.getObjectByName(API.vms, VM_NAME)
        self.assertRaises(errors.RequestError, vm.disks.add, disk)
        LOGGER.info("User wihout approriate perms can't add disk to vm.")

        loginAsAdmin()
        sd = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        common.givePermissionToObject(sd, roles.role.DiskCreator)

        loginAsUser()
        vm = common.getObjectByName(API.vms, VM_NAME)
        d = vm.disks.add(disk)
        common.waitForState(d, states.disk.ok)
        common.deleteDiskObject(d)
        LOGGER.info("User with permissions on SD can add disk to vm.")

        loginAsAdmin()
        sd = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        common.removeAllPermissionFromObject(sd)
        common.removeAllPermissionFromObject(API.vms.get(VM_NAME))

    @tcms(TCMS_PLAN_ID, 147130)
    def testRemoveVm(self):
        """ RemoveVm """
        loginAsAdmin()
        common.createVm(TMP_VM_NAME)
        common.givePermissionToVm(TMP_VM_NAME, roles.role.DiskOperator)

        loginAsUser()  # Try to remove vm as disk operator
        self.assertRaises(errors.RequestError, common.removeVm, TMP_VM_NAME)
        LOGGER.info("User can't remove vm as DiskOperator.")

        loginAsAdmin()
        common.givePermissionToVm(TMP_VM_NAME, roles.role.UserVmManager)

        loginAsUser()  # Try to remove vm as uservmmanager
        common.removeVm(TMP_VM_NAME)
        LOGGER.info("User can remove vm as UserVmManager.")

    @tcms(TCMS_PLAN_ID, 147137)
    def testSharedDisk(self):
        """ SharedDisk """
        sd = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        sd = params.StorageDomains(storage_domain=[sd])
        disk = params.Disk(storage_domains=sd, size=1024 * 1024,
                interface='virtio', format='raw',
                shareable=True, alias=DISK_SHARED)
        d = API.disks.add(disk)
        common.waitForState(d, states.disk.ok)
        common.givePermissionToVm(VM_NAME, roles.role.UserVmManager)
        common.givePermissionToObject(d, roles.role.DiskOperator)

        loginAsUser()
        vm = common.getObjectByName(API.vms, VM_NAME)
        d = common.getObjectByName(API.disks, DISK_SHARED)

        disk = vm.disks.add(d)  # Attach
        common.editVmDiskProperties(VM_NAME, diskId=disk.get_id())
        common.deleteDiskObject(d)
