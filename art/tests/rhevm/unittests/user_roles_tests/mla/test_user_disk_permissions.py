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

from user_roles_tests import config
from user_roles_tests import common
from user_roles_tests import states
from user_roles_tests import roles
from nose.tools import istest
from functools import wraps
from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors

import time
import unittest2 as unittest
import logging

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
DISK = None
VM_NAME = 'user_disk_permissions__vm'
DISK_NAME = 'user_disk_permissions__disk'
CLUSTER_NAME = 'user_disk_permissions__cluster'

TMP_VM_NAME = 'user_disk_permissions__vm_tmp'
TMP_DISK_NAME = 'user_disk_permissions__disk_tmp'
TMP2_DISK_NAME = 'user_disk_permissions__disk_tmp2'

def setUpModule():
    global DISK
    common.addUser()
    common.createVm(VM_NAME)
    DISK = common.createDiskObject(DISK_NAME)

    common.createNfsStorage(storageName=config.ALT1_STORAGE_NAME,
                            address=config.ALT1_STORAGE_ADDRESS,
                            path=config.ALT1_STORAGE_PATH,
                            datacenter=config.MAIN_DC_NAME,
                            host=config.MAIN_HOST_NAME)
    common.attachActivateStorage(config.ALT1_STORAGE_NAME)

def tearDownModule():
    common.loginAsAdmin()
    common.removeNonMasterStorage(storageName=config.ALT1_STORAGE_NAME,
                                  datacenter=config.MAIN_DC_NAME,
                                  host=config.MAIN_HOST_NAME)
    common.removeVm(VM_NAME)
    common.deleteDiskObject(DISK)
    common.deleteDisk(None, DISK_NAME)
    common.removeUser()


class DiskPermissionsTests(unittest.TestCase):
    __test__ = True

    @tcms(TCMS_PLAN_ID, 147121)
    @bz(881145)
    def testDiskInheritedPermissions(self):
        """ DiskInheritedPermissions """
        # Check if disk inherit perms from SD
        # Check if after disk is attach to vm it iherit VM perms
        sd = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        vm = API.vms.get(VM_NAME)

        temp_disk = 'temp_disk12'
        DISK = common.createDiskObject(temp_disk)
        try:
            common.givePermissionToObject(DISK, roles.role.DiskOperator)
            self.assertTrue(common.hasUserPermissions(DISK, roles.role.DiskOperator))
            common.givePermissionToObject(vm, roles.role.UserVmManager)
            vm.disks.add(DISK)
            self.assertTrue(common.hasUserPermissions(DISK, roles.role.UserVmManager))
        except Exception as e:
            raise e
        finally:
            # cleanUP
            DISK.delete()
            common.waitForRemove(DISK)
            common.removeAllPermissionFromObject(DISK)
            common.removeAllPermissionFromObject(vm)

    @tcms(TCMS_PLAN_ID, 147122)
    def testCreateDisk(self):
        """ CreateDisk """
        # Check if user has DiskOperator perms on SD he can create Disk
        # Check if user has not DiskOperator perms on SD he can't create Disk
        sd = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        common.givePermissionToObject(sd, roles.role.DiskOperator)
        common.loginAsUser()
        tmp_disk = common.createDiskObjectNoCheck(TMP_DISK_NAME, storage=sd.get_name())
        # FIXME After filter is ok
        common.loginAsAdmin()
        # FIXME: after .. could be removed
        dd = API.disks.get(alias=TMP_DISK_NAME)
        common.waitForState(dd, 'ok')

        common.removeAllPermissionFromObject(sd)
        common.loginAsUser()
        self.assertRaises(Exception, common.createDiskObjectNoCheck, TMP_DISK_NAME + 'x')
        # Replace by this after BZ 869334 is OK
        #self.assertRaises(errors.RequestError, common.createDiskObjectNoCheck, TMP_DISK_NAME + 'x')

        # clean Up
        common.loginAsAdmin()
        common.deleteDisk(None, alias=TMP_DISK_NAME)

    @tcms(TCMS_PLAN_ID, 147123)
    @bz(881145)
    def testAttachDiskToVM(self):
        """ AttachDiskToVM """
        # Attach disk need perm on disk and on VM.
        vm = API.vms.get(VM_NAME)

        common.givePermissionToObject(DISK, roles.role.DiskOperator)
        common.givePermissionToObject(vm, roles.role.UserVmManager)

        common.loginAsUser()
        vm.disks.add(DISK)  # Attach

        # Clean up
        common.loginAsAdmin()
        vm.disks.get(id=DISK.get_id()).delete(params.Action(detach=True))  # Detach
        common.removeAllPermissionFromObject(DISK)
        common.removeAllPermissionFromObject(vm)

    @tcms(TCMS_PLAN_ID, 147124)
    def testDetachDisk(self):
        """ DetachDisk """
        # Detach disk need only perms on VM
        vm = API.vms.get(VM_NAME)

        common.givePermissionToObject(vm, roles.role.UserVmManager)
        disk = vm.disks.add(DISK)

        common.loginAsUser() # Try detach disk
        vm.disks.get(id=disk.get_id()).delete(params.Action(detach=True))

        # Clean up
        common.loginAsAdmin()
        common.removeAllPermissionFromObject(vm)

    @tcms(TCMS_PLAN_ID, 147125)
    def testActivateDeactivateDisk(self):
        """ ActivateDeactivateDisk """
        # Activate/deactivate disk need to have perms only on VM
        vm = API.vms.get(VM_NAME)

        common.givePermissionToObject(vm, roles.role.UserVmManager)

        common.loginAsUser()  # Try detach disk

        vmdisk = vm.disks.list()[0]
        vmdisk.deactivate()
        vmdisk.activate()

        # Clean up
        common.loginAsAdmin()
        common.removeAllPermissionFromObject(vm)

    @tcms(TCMS_PLAN_ID, 147126)
    @bz(881145)
    def testRemoveDisk(self):
        """ RemoveDisk """
        # To remove disk you need aproriate permissions on disk
        common.loginAsAdmin()
        tmp_disk = common.createDiskObject(TMP_DISK_NAME)
        common.removeAllPermissionFromObject(common.getUser())

        try:
            common.loginAsUser()
            self.assertRaises(errors.RequestError, common.deleteDiskObject, tmp_disk)

            common.loginAsAdmin()
            common.givePermissionToObject(tmp_disk, roles.role.DiskOperator)

            common.loginAsUser()
            common.deleteDiskObject(tmp_disk)
        except Exception as e:
            raise e
        finally:
            common.loginAsAdmin()
            common.deleteDiskObject(tmp_disk)

    @tcms(TCMS_PLAN_ID, 147127)
    @bz(881145)
    def testUpdateDisk(self):
        """ UpdateDisk """
        # Edit disks need appropriate perms on disk.
        # Currently only vm disk can be updated
        common.loginAsAdmin()
        if API.vms.get(TMP_VM_NAME) is not None:
            common.removeVm(TMP_VM_NAME)
        common.createVm(TMP_VM_NAME)
        vm = API.vms.get(TMP_VM_NAME)
        tmp_disk = vm.disks.list()[0]

        try:
            common.loginAsUser()
            assert common.getObjectByName(API.vms, TMP_VM_NAME) is None

            common.loginAsAdmin()
            common.givePermissionToObject(tmp_disk, roles.role.DiskOperator)
            #common.givePermissionToObject(vm, roles.role.UserVmManager)

            common.loginAsUser()
            common.editVmDiskProperties(TMP_VM_NAME)
        except Exception as e:
            raise e
        finally:
            common.loginAsAdmin()
            common.removeVm(TMP_VM_NAME)

    @tcms(TCMS_PLAN_ID, 147128)
    @bz(881145)
    def testMoveOrCopy(self):
        """ MoveOrCopy """
        try:
            common.loginAsAdmin()
            disk = common.createDiskObject(TMP2_DISK_NAME, storage=config.MAIN_STORAGE_NAME)
            sd = common.getObjectByName(API.storagedomains, config.ALT1_STORAGE_NAME)
            source = common.getObjectByName(API.storagedomains, config.MAIN_STORAGE_NAME)
            common.loginAsUser()

            # Move disk without pemrissions
            self.assertRaises(errors.RequestError, disk.move,
                    params.Action(storage_domain=sd))
            # Move disk with permissions only on source sd
            common.loginAsAdmin()
            common.givePermissionToObject(source, roles.role.StorageAdmin)
            common.loginAsUser(filter_=False)
            self.assertRaises(errors.RequestError, disk.move,
                    params.Action(storage_domain=sd))
            # Move disk with permissions on both sds
            common.loginAsAdmin()
            common.givePermissionToObject(sd, roles.role.StorageAdmin)
            common.loginAsUser(filter_=False)
            disk.move(params.Action(storage_domain=sd))
            common.waitForState(disk, 'ok')
        finally:
            common.loginAsAdmin()
            common.waitForState(disk, 'ok')
            common.removeObject(disk)

    @tcms(TCMS_PLAN_ID, 147129)
    def testAddDiskToVm(self):
        """ editAddDiskToVm """
        vm = API.vms.get(VM_NAME)
        storage = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        sd = params.StorageDomains(storage_domain=[storage])
        disk = params.Disk(storage_domains=sd, size=1 * 1024 * 1024,
                    status=None, interface='virtio', format='cow',
                    sparse=True)

        common.loginAsUser()
        self.assertRaises(errors.RequestError, vm.disks.add, disk)
        LOGGER.info("User with no permissions cant add vm disk.")

        common.loginAsAdmin()
        common.givePermissionToVm(VM_NAME, roles.role.UserVmManager)

        common.loginAsUser()
        self.assertRaises(errors.RequestError, vm.disks.add, disk)
        LOGGER.info("User with permissions VmManager on VM, cant add disk to VM.")

        common.loginAsAdmin()
        common.givePermissionToObject(storage, roles.role.UserVmManager)

        common.loginAsUser()
        disk2 = vm.disks.add(disk)
        common.waitForState(disk2, 'ok')
        LOGGER.info("User with permissions on SD can add disk to vm.")
        vm.disks.get(id=disk2.get_id()).delete(params.Action(detach=True))
        LOGGER.info("Attached/detached")

        common.loginAsAdmin()
        disk = API.disks.get(id=disk2.get_id())
        common.removeObject(disk)


    @tcms(TCMS_PLAN_ID, 147130)
    def testRemoveVm(self):
        """ RemoveVm """
        common.loginAsAdmin()
        common.createVm(TMP_VM_NAME)
        vm = API.vms.get(TMP_VM_NAME)

        common.loginAsUser()
        self.assertRaises(errors.RequestError, vm.delete)

        common.loginAsAdmin()
        common.givePermissionToVm(TMP_VM_NAME, roles.role.UserVmManager)

        common.loginAsUser()
        common.removeVmObject(vm)


    @tcms(TCMS_PLAN_ID, 147137)
    @bz(881145)
    def testSharedDisk(self):
        """ SharedDisk """
        common.loginAsAdmin()
        common.createVm(TMP_VM_NAME, createDisk=False,
                       storage=config.MAIN_STORAGE_NAME)

        storage = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        sd = params.StorageDomains(storage_domain=[storage])
        disk = params.Disk(storage_domains=sd, size=1 * 1024 * 1024,
                    status=None, interface='virtio', format='raw',
                    sparse=True, shareable=True)
        d = API.disks.add(disk)
        common.waitForState(d, 'ok')
        vm = API.vms.get(TMP_VM_NAME)
        try:
            common.givePermissionToObject(vm, roles.role.UserVmManager)
            common.givePermissionToObject(d, roles.role.DiskOperator)
            common.loginAsUser()
            disk = vm.disks.add(d)  # Attach
            common.editVmDiskProperties(TMP_VM_NAME)  # Edit
            d.delete()  # Delete
            common.waitForRemove(d)
        except Exception as e:
            raise e
        finally:
            # Should be changed after bz is OK.
            common.loginAsAdmin()
            common.removeVm(TMP_VM_NAME)
            common.removeObject(d)
