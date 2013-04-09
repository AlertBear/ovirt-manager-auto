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
import roles
import sys
import re
import unittest2 as unittest
from unittest2 import SkipTest
from nose.tools import istest
from functools import wraps
from time import sleep

from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors

import logging

try:
    from art.test_handler.tools import bz
except ImportError:
    from user_roles_tests.common import bz

try:
    from art.test_handler.tools import tcms
except ImportError:
    from user_roles_tests.common import tcms

LOGGER = logging.getLogger(__name__)
API = common.API
GB = common.GB


# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
VM_NAME = 'user_actions__vm'  # used for whole module
VM_NET_NAME = 'user_actions__vm_net'  # used once per test
TMP_VM_NAME = 'user_actions__vm_tmp'  # used once per test
EXPORT_NAME = 'user_actions__export'
SNAPSHOT_NAME = 'user_actions__snapshot'
ISO_NAME = 'shared_iso_domain'
TEMPLATE_NAME = 'user_actions__template'
TEMPLATE_VMPOOL = 'user_actions__template_vmp'
TEMPLATE_NET_NAME = 'user_actions__tmp_net_name'
VMPOOL_NAME = 'user_actions__vmpool'
DISK_NAME = 'user_actions__disk'
TMP_TEMPLATE_NAME = 'user_actions__template_tmp'
TMP_VMPOOL_NAME = 'user_actions__vmpool_tmp'
TMP_DISK_NAME = 'user_actions__disk_tmp'
TMP2_DISK_NAME = 'user_actions__disk_tmp2'
CLUSTER_NAME = 'user_actions__cluster'
TMP_CLUSTER_NAME = 'user_actions__cluster_tmp'
CLUSTER_CPU_TYPE = 'AMD Opteron G2'
DC_NETWORK_NAME = 'dc_net_name'
DC_NETWORK_NAME_TMP = 'dc_net_name_tmp'
DC_NAME_TMP = 'user_actions__dc_tmp'
DC_NAME_TMP2 = 'user_actions__dc_tm2p'
ROLE_NAME = 'user_actions__role'
USER_ROLE_PERMITS = permit=API.roles.get(roles.role.UserRole).get_permits().list()

PERMISSIONS = common.getSuperUserPermissions()

# Tcms Id's
# Change ID's if plan were regenerated
NEG_ID = 211210  # first negative test case id
POS_ID = 211847  # first positive test case id
POS_PLAN = 7468  # positive plan id
NEG_PLAN = 7450  # negative plan id

# Decide if test make sense, if not skip the test.
def resolve_permissions(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Skip tests which doesnt make sence
        m = re.match('^(?P<type>[A-Z]+)_(?P<perm>.*)$', func.func_name)
        msg = "Combination '%s, %s, %s' doesn't make sence"
        if m.group('type') == 'POSITIVE':
            if m.group('perm') not in self.perms:
                LOGGER.info(msg % (self.role, m.group('type'), m.group('perm')))
                raise SkipTest(msg % (self.role, m.group('type'), m.group('perm')))
        if m.group('type') == 'NEG':
            if m.group('perm') in self.perms:
                LOGGER.info(msg % (self.role, m.group('type'), m.group('perm')))
                raise SkipTest(msg % (self.role, m.group('type'), m.group('perm')))

        # Switch counting of ID's
        # Set neg, because there is much more neg cases
        #tcms(plan, nn)(func)
        # For logging of errors
        try:
            return func(self, *args, **kwargs)
        except Exception as err:
            LOGGER.error(err)
            raise err

    return wrapper

# Prepares setup for only this test module
def setUpModule():
    """ Prepare testing setup """
    global ISO_NAME
    common.addUser()
    common.createNfsStorage(EXPORT_NAME, storageType='export',
            address=config.EXPORT_ADDRESS, path=config.EXPORT_PATH)
    common.attachActivateStorage(EXPORT_NAME)
    ISO_NAME = common.createNfsStorage(ISO_NAME, storageType='iso',
            address=config.ISO_ADDRESS, path=config.ISO_PATH)
    common.attachActivateStorage(ISO_NAME)
    common.addNetworkToDC(DC_NETWORK_NAME, config.MAIN_DC_NAME)

    common.createHost(config.MAIN_CLUSTER_NAME, hostName=config.ALT1_HOST_ADDRESS,
            hostAddress=config.ALT1_HOST_ADDRESS,
            hostPassword=config.ALT1_HOST_ROOT_PASSWORD)
    common.createNfsStorage(storageName=config.ALT1_STORAGE_NAME,
            address=config.ALT1_STORAGE_ADDRESS,
            path=config.ALT1_STORAGE_PATH,
            datacenter=config.MAIN_DC_NAME,
            host=config.MAIN_HOST_NAME)
    common.attachActivateStorage(config.ALT1_STORAGE_NAME)
    common.createDataCenter(DC_NAME_TMP2)

# Removes created objects from setup
def tearDownModule():
    common.removeUser()
    for d in API.disks.list():
        common.deleteDiskObject(d)

    common.removeAllFromSD(EXPORT_NAME)
    common.removeAllFromSD(config.ALT1_STORAGE_NAME)

    common.removeNonMasterStorage(EXPORT_NAME, datacenter=config.MAIN_DC_NAME,
            host=config.MAIN_HOST_NAME)
    common.removeNonMasterStorage(ISO_NAME, datacenter=config.MAIN_DC_NAME,
            host=config.MAIN_HOST_NAME)

    common.removeNonMasterStorage(storageName=config.ALT1_STORAGE_NAME,
                        datacenter=config.MAIN_DC_NAME,
                        host=config.MAIN_HOST_NAME)
    common.removeHost(hostName=config.ALT1_HOST_ADDRESS)
    common.removeDataCenter(DC_NAME_TMP2)

def loginAsUser(**kwargs):
    common.loginAsUser(**kwargs)
    global API
    API = common.API

def loginAsAdmin():
    common.loginAsAdmin()
    global API
    API = common.API

##################### BASE CLASS OF TESTS #####################################
class UserActionsTests(unittest.TestCase):

    __test__ = False

    def setUp(self):
        loginAsUser(filter_=self.filter_)

    @classmethod
    def setUpClass(cls):
        common.createDiskObject(DISK_NAME, storage=config.MAIN_STORAGE_NAME)
        common.createCluster(CLUSTER_NAME, config.MAIN_DC_NAME)
        common.createVm(VM_NAME, storage=config.MAIN_STORAGE_NAME)
        common.createTemplate(VM_NAME, TEMPLATE_NAME)
        common.createTemplate(VM_NAME, TEMPLATE_VMPOOL)
        common.createVmPool(VMPOOL_NAME, TEMPLATE_VMPOOL)
        common.givePermissionsToGroup(TEMPLATE_NAME)
        common.addRoleToUser(cls.role)
        common.givePermissionToVm(VM_NAME, cls.role)
        common.givePermissionToPool(VMPOOL_NAME, cls.role)
        common.givePermissionToTemplate(TEMPLATE_NAME, cls.role)
        common.givePermissionToTemplate(TEMPLATE_VMPOOL, cls.role)
        common.givePermissionToDisk(DISK_NAME, cls.role)
        common.givePermissionToObject(API.networks.get(DC_NETWORK_NAME),
                cls.role)
        common.givePermissionToNet(config.NETWORK_NAME, config.MAIN_DC_NAME,
                cls.role)

        loginAsUser(filter_=cls.filter_)

    @classmethod
    def tearDownClass(cls):
        loginAsAdmin()

        common.removeRoleFromUser(cls.role)
        common.removeAllPermissionFromDc(config.MAIN_DC_NAME)
        common.removeAllPermissionFromObject(API.networks.get(DC_NETWORK_NAME))

        common.removeCluster(CLUSTER_NAME)
        vmpool = API.vmpools.get(VMPOOL_NAME)
        common.removeAllVmsInPool(VMPOOL_NAME)
        common.removeVmPool(vmpool)
        common.removeAllVms()
        common.removeTemplate(TEMPLATE_NAME)
        common.removeTemplate(TEMPLATE_VMPOOL)
        common.removeVm(VM_NAME)
        common.deleteDisk(None, alias=DISK_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_vm_basic_operations(self):
        """ POSITIVE_vm_basic_operations """
        # Try to start/stop vm
        vm = common.getObjectByName(API.vms, VM_NAME)
        vm.start()
        LOGGER.info("VM '%s' starting" % (VM_NAME))
        common.waitForState(vm, states.vm.up)
        LOGGER.info("VM '%s' suspending" % (VM_NAME))
        vm.suspend()
        common.waitForState(vm, states.vm.suspended)
        LOGGER.info("VM '%s' shuting down" % (VM_NAME))
        vm.shutdown()
        common.waitForState(vm, states.vm.down)
        vm.start()
        LOGGER.info("VM '%s' starting" % (VM_NAME))
        common.waitForState(vm, states.vm.up)
        vm.stop()
        LOGGER.info("VM '%s' stoping" % (VM_NAME))
        common.waitForState(vm, states.vm.down)

    @istest
    @resolve_permissions
    def NEG_vm_basic_operations(self):
        """ NEG_vm_basic_operations """
        self.assertRaises(errors.RequestError, common.startVm, VM_NAME)

        loginAsAdmin()
        common.startVm(VM_NAME)

        loginAsUser(filter_=self.filter_)
        vm = common.getObjectByName(API.vms, VM_NAME)
        self.assertRaises(errors.RequestError, vm.stop)
        self.assertRaises(errors.RequestError, vm.suspend)
        self.assertRaises(errors.RequestError, vm.shutdown)

        loginAsAdmin()
        common.stopVm(VM_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_create_vm(self):
        """ POSITIVE_create_vm """
        # Try to create VM
        common.createVm(TMP_VM_NAME, createDisk=False,
                storage=config.MAIN_STORAGE_NAME)

        loginAsAdmin() # clean
        common.removeVm(TMP_VM_NAME)

    @istest
    @resolve_permissions
    def NEG_create_vm(self):
        """ NEG_create_vm """
        self.assertRaises(errors.RequestError, common.createVm, TMP_VM_NAME,
                          createDisk=False, storage=config.MAIN_STORAGE_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_delete_vm(self):
        """ POSITIVE_delete_vm """
        # Try delete vm
        loginAsAdmin()
        common.createVm(TMP_VM_NAME, createDisk=False,
                storage=config.MAIN_STORAGE_NAME)

        loginAsUser(filter_=self.filter_)
        common.removeVm(TMP_VM_NAME)

    @istest
    @resolve_permissions
    def NEG_delete_vm(self):
        """ NEG_delete_vm """
        self.assertRaises(errors.RequestError, common.removeVm, VM_NAME)

    @istest
    @resolve_permissions
    def NEG_edit_vm_properties(self):
        """ NEG_edit_vm_properties """
        vm = common.getObjectByName(API.vms, VM_NAME)
        display = params.Display(type_="vnc")
        vm.set_display(display)
        self.assertRaises(errors.RequestError, vm.update)

    @istest
    @resolve_permissions
    def POSITIVE_edit_vm_properties(self):
        """ POSITIVE_edit_vm_properties """
        # Try to edit vm display type
        vm = common.getObjectByName(API.vms, VM_NAME)
        before = vm.get_display().type_
        if before == "vnc":
            after = "spice"
        else:
            after = "vnc"

        display = params.Display(type_=after)
        vm.set_display(display)
        vm.update()

        vm = common.getObjectByName(API.vms, VM_NAME)
        now = vm.get_display().type_
        assert before != now, "Failed to update VM display properties"
        LOGGER.info("VM '%s' updated" % (VM_NAME))

    @istest
    @resolve_permissions
    def POSITIVE_change_vm_cd(self):
        """ POSITIVE_change_vm_cd """
        # Try to change vm cd
        common.startVm(VM_NAME)
        vm = common.getObjectByName(API.vms, VM_NAME)
        sDomain = common.getObjectByName(API.storagedomains, ISO_NAME)
        isofile = sDomain.files.get(id=config.ISO_FILE)
        cdrom = vm.cdroms.get(id="00000000-0000-0000-0000-000000000000")
        cdrom.set_file(isofile)
        cdrom.update(current=True)
        LOGGER.info("VM's '%s' CD changed" % vm.get_name())
        common.stopVm(VM_NAME)

    @istest
    @resolve_permissions
    def NEG_change_vm_cd(self):
        """ NEG_change_vm_cd """
        loginAsAdmin()
        common.startVm(VM_NAME)

        loginAsUser(filter_=self.filter_)
        vm = common.getObjectByName(API.vms, VM_NAME)
        sDomain = common.getObjectByName(API.storagedomains, ISO_NAME)
        isofile = sDomain.files.get(id=config.ISO_FILE)
        cdrom = vm.cdroms.get(id="00000000-0000-0000-0000-000000000000")
        cdrom.set_file(isofile)
        self.assertRaises(errors.RequestError, cdrom.update, current=True)
        LOGGER.info("VM's '%s' CD can't be changed" % vm.get_name())

        loginAsAdmin()
        common.stopVm(VM_NAME)

    @istest
    @resolve_permissions
    def NEG_import_export_vm(self):
        """ NEG_import_export_vm """
        # Try to import VM to export domain
        vm = common.getObjectByName(API.vms, VM_NAME)
        storage = common.getObjectByName(API.storagedomains, EXPORT_NAME)

        param = params.Action(storage_domain=storage, exclusive=False)
        self.assertRaises(errors.RequestError, vm.export, param)

    @istest
    @resolve_permissions
    def POSITIVE_import_export_vm(self):
        """ POSITIVE_import_export_vm """
        vm = common.getObjectByName(API.vms, VM_NAME)
        storage = common.getObjectByName(API.storagedomains, EXPORT_NAME)
        param = params.Action(storage_domain=storage, exclusive=False)
        vm.export(param)
        common.waitForState(vm, states.vm.down)

        loginAsAdmin()
        storage = common.getObjectByName(API.storagedomains, EXPORT_NAME)
        common.removeVmObject(storage.vms.get(VM_NAME))

    @istest
    @resolve_permissions
    def NEG_configure_vm_network(self):
        """ NEG_configure_vm_network """
        vm = common.getObjectByName(API.vms, VM_NAME)
        param = params.NIC(name=config.HOST_NIC,
                           network=params.Network(name=config.NETWORK_NAME),
                           interface='virtio')
        self.assertRaises(errors.RequestError, vm.nics.add, param)

    @istest
    @resolve_permissions
    def POSITIVE_configure_vm_network(self):
        """ POSITIVE_configure_vm_network """
        # Try to add new network interface to vm
        vm = common.getObjectByName(API.vms, VM_NAME)
        param = params.NIC(name=config.HOST_NIC,
                           network=params.Network(name=config.NETWORK_NAME),
                           interface='virtio')
        vm.nics.add(param)
        LOGGER.info("VM '%s' network configure success" % (VM_NAME))

    @istest
    @resolve_permissions
    def NEG_configure_vm_storage(self):
        """ NEG_configure_vm_storage """
        # Add disk to vm(not floationg disk)
        vm = common.getObjectByName(API.vms, VM_NAME)
        storage = common.getObjectByName(API.storagedomains, config.MAIN_STORAGE_NAME)
        param1 = params.StorageDomains(storage_domain=[storage])
        param2 = params.Disk(storage_domains=param1, size=GB,
                status=None, interface='virtio', format='cow',
                sparse=True)
        self.assertRaises(errors.RequestError, vm.disks.add, param2)

    @istest
    @resolve_permissions
    def POSITIVE_configure_vm_storage(self):
        """ POSITIVE_configure_vm_storage """
        if not 'create_disk' in self.perms:
            LOGGER.warning("Configure storage can't be tested..")
            return
        vm = common.getObjectByName(API.vms, VM_NAME)
        storage = common.getObjectByName(API.storagedomains, config.MAIN_STORAGE_NAME)
        param1 = params.StorageDomains(storage_domain=[storage])
        param2 = params.Disk(storage_domains=param1, size=GB,
                status=None, interface='virtio', format='cow',
                sparse=True)
        disk = vm.disks.add(param2)
        common.waitForState(disk, states.disk.ok)
        LOGGER.info("VM '%s' storage configure success" % (VM_NAME))

    @istest
    @resolve_permissions
    def NEG_manipulate_vm_snapshots(self):
        """ NEG_manipulate_vm_snapshots """
        vm = common.getObjectByName(API.vms, VM_NAME)
        param = params.Snapshot(vm=vm, description=SNAPSHOT_NAME)
        self.assertRaises(errors.RequestError, vm.snapshots.add, param)

    @istest
    @resolve_permissions
    def POSITIVE_manipulate_vm_snapshots(self):
        """ POSITIVE_manipulate_vm_snapshots """
        # Try to create vm snapshot
        vm = common.getObjectByName(API.vms, VM_NAME)
        param = params.Snapshot(vm=vm, description=SNAPSHOT_NAME)
        s = vm.snapshots.add(param)
        common.waitForState(s, states.disk.ok)
        snap = vm.snapshots.get(id=s.get_id())
        self.assertTrue(snap is not None)
        snap.delete()
        common.waitForRemove(snap)
        LOGGER.info("VM '%s' manipulate snaps success" % (VM_NAME))

    @istest
    @resolve_permissions
    def NEG_create_template(self):
        """ NEG_create_template """
        # Try create template from VM
        self.assertRaises(errors.RequestError, common.createTemplate, VM_NAME,
                TMP_TEMPLATE_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_create_template(self):
        """ POSITIVE_create_template """
        common.createTemplate(VM_NAME, TMP_TEMPLATE_NAME)

        loginAsAdmin()
        common.removeTemplate(TMP_TEMPLATE_NAME)

    @istest
    @resolve_permissions
    def NEG_edit_template_properties(self):
        """ NEG_edit_template_properties """
        # Change tempalte display type
        template = common.getObjectByName(API.templates, TEMPLATE_NAME)
        display = params.Display(type_="vnc")
        template.set_display(display)
        self.assertRaises(errors.RequestError, template.update)

    @istest
    @resolve_permissions
    def POSITIVE_edit_template_properties(self):
        """ POSITIVE_edit_template_properties """
        template = common.getObjectByName(API.templates, TEMPLATE_NAME)
        before = template.get_display().type_
        if before == "vnc":
            after = "spice"
        else:
            after = "vnc"

        display = params.Display(type_=after)
        template.set_display(display)
        template.update()

        template = common.getObjectByName(API.templates, TEMPLATE_NAME)
        now = template.get_display().type_
        assert before != now, "Failed to update Template display properties"
        LOGGER.info("Temaplate '%s' editing success" % (TEMPLATE_NAME))

    @istest
    @resolve_permissions
    def NEG_configure_template_network(self):
        """ NEG_configure_template_network """
        # Add new network to tempalte
        template = common.getObjectByName(API.templates, TEMPLATE_NAME)
        param = params.NIC(name=TEMPLATE_NET_NAME,
                    network=params.Network(name=config.NETWORK_NAME),
                    interface='virtio')
        self.assertRaises(errors.RequestError, template.nics.add, param)

    @istest
    @resolve_permissions
    def POSITIVE_configure_template_network(self):
        """ POSITIVE_configure_template_network """
        template = common.getObjectByName(API.templates, TEMPLATE_NAME)
        param = params.NIC(name=TEMPLATE_NET_NAME,
                    network=params.Network(name=config.NETWORK_NAME),
                    interface='virtio')
        n = template.nics.add(param)
        n.delete()
        LOGGER.info("Temaplate '%s' network configure success" % (TEMPLATE_NAME))

    @istest
    @resolve_permissions
    def NEG_create_vm_pool(self):
        """ NEG_create_vm_pool """
        self.assertRaises(errors.RequestError, common.createVmPool,
                        TMP_VMPOOL_NAME, TEMPLATE_VMPOOL)

    @istest
    @resolve_permissions
    def POSITIVE_create_vm_pool(self):
        """ POSITIVE_create_vm_pool """
        # creates vmpool
        common.createVmPool(TMP_VMPOOL_NAME, TEMPLATE_VMPOOL)

        loginAsAdmin()
        vmpool = API.vmpools.get(TMP_VMPOOL_NAME)
        common.removeAllVmsInPool(TMP_VMPOOL_NAME)
        common.removeVmPool(vmpool)

    @istest
    @resolve_permissions
    def NEG_edit_vm_pool_configuration(self):
        """ NEG_edit_vm_pool_configuration """
        vmpool = common.getObjectByName(API.vmpools, VMPOOL_NAME)
        self.assertRaises(errors.RequestError, common.addVmToPool, vmpool)

    @istest
    @resolve_permissions
    def POSITIVE_edit_vm_pool_configuration(self):
        """ POSITIVE_edit_vm_pool_configuration """
        vmpool = common.getObjectByName(API.vmpools, VMPOOL_NAME)
        common.addVmToPool(vmpool)

    @istest
    @resolve_permissions
    def NEG_vm_pool_basic_operations(self):
        """ NEG_vm_pool_basic_operations """
        # Check if vm has any vms to run, if not add one
        loginAsAdmin()
        pool = API.vmpools.get(VMPOOL_NAME)
        if pool.get_size() == 0:
            common.addVmToPool(pool)
        loginAsUser(filter_=self.filter_)
        pool = common.getObjectByName(API.vmpools, VMPOOL_NAME)
        self.assertRaises(errors.RequestError, common.vmpoolBasicOperations, pool)

    @istest
    @resolve_permissions
    @bz(955545)
    def POSITIVE_vm_pool_basic_operations(self):
        """ POSITIVE_vm_pool_basic_operations """
        # Check if vm has any vms to run, if not add one
        loginAsAdmin()
        pool = API.vmpools.get(VMPOOL_NAME)
        if pool.get_size() == 0:
            common.addVmToPool(pool)
        loginAsAdmin()
        for vm in common.getAllVmsInPool(VMPOOL_NAME):
            common.waitForState(vm, states.vm.down)

        loginAsUser(filter_=self.filter_)
        pool = common.getObjectByName(API.vmpools, VMPOOL_NAME)
        common.vmpoolBasicOperations(pool)

    @istest
    @resolve_permissions
    def NEG_delete_vm_pool(self):
        """ NEG_delete_vm_pool """
        # Create pool, that could be deleted
        loginAsAdmin()
        common.createVmPool(TMP_VMPOOL_NAME, TEMPLATE_VMPOOL)
        common.givePermissionToPool(TMP_VMPOOL_NAME, self.role)
        vmpool = API.vmpools.get(TMP_VMPOOL_NAME)
        vms = [vm.get_id() for vm in common.getAllVmsInPool(TMP_VMPOOL_NAME)]

        loginAsUser(filter_=self.filter_)
        # Try to detach vms from pool as user

        # Can't try to detach vm for this roles, because they
        # never can't see vmpools vms
        if not (self.role in ['DiskCreator', 'VmCreator', 'TemplateCreator',
                'PowerUserRole']):
            for vm in vms:
                self.assertRaises(errors.RequestError, API.vms.get(id=vm).detach)

        # Detach and remove all vms in pool
        loginAsAdmin()
        for i in vms:
            vm = API.vms.get(id=i)
            vm.detach()
            common.waitForState(vm, states.vm.down)
            vm.delete()
            common.waitForRemove(vm)

        # Try to remove vm pool
        loginAsUser(filter_=self.filter_)
        if self.filter_:
            # BUG, Entity not found: 735ad44c-e71f-4585-be79-7d68da22ebfc
            # If vmpools has no vms and access via Filter API
            self.assertRaises(errors.RequestError, common.getObjectByName,
                    API.vmpools, TMP_VMPOOL_NAME)
        else:
            vmpool = common.getObjectByName(API.vmpools, TMP_VMPOOL_NAME)
            self.assertRaises(errors.RequestError, vmpool.delete)

        # clean up
        loginAsAdmin()
        vmpool = API.vmpools.get(TMP_VMPOOL_NAME)
        common.removeVmPool(vmpool)

    @istest
    @resolve_permissions
    def POSITIVE_delete_vm_pool(self):
        """ POSITIVE_delete_vm_pool """
        # Create vmpool that will be deleted
        loginAsAdmin()
        common.createVmPool(TMP_VMPOOL_NAME, TEMPLATE_VMPOOL)

        loginAsUser(filter_=self.filter_)
        # Try to delete vmpool, detach vms, remove vms and remove vmpool
        vmpool = common.getObjectByName(API.vmpools, TMP_VMPOOL_NAME)
        vms = [vm.get_id() for vm in common.detachAllVmsInPool(TMP_VMPOOL_NAME)]
        common.removeVmPool(vmpool)

        # Remove vms, which were attached to vmpool
        loginAsAdmin()  # Cleanup
        for v in vms:
            vm = API.vms.get(id=v)
            vm.delete()
            common.waitForRemove(vm)

    @istest
    @resolve_permissions
    def NEG_delete_template(self):
        """ NEG_delete_template """
        # Because of RemoveTemplate need for run no dependency vms
        self.assertRaises(errors.RequestError, common.removeTemplate,
                    TEMPLATE_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_delete_template(self):
        """ POSITIVE_delete_template """
        # Because of RemoveTemplate need for run no dependency vms
        common.removeTemplate(TEMPLATE_NAME)

        loginAsAdmin()  # Recreate
        common.createTemplate(VM_NAME, TEMPLATE_NAME)

    @istest
    @resolve_permissions
    def NEG_manipulate_permissions(self):
        """ NEG_manipulate_permissions """
        loginAsAdmin()
        common.createVm(TMP_VM_NAME, storage=config.MAIN_STORAGE_NAME)
        common.givePermissionToVm(TMP_VM_NAME, self.role)

        loginAsUser(filter_=self.filter_)
        vm = common.getObjectByName(API.vms, TMP_VM_NAME)
        role = common.getObjectByName(API.roles, roles.role.UserRole)
        user = common.getObjectByName(API.users, config.USER_NAME)
        self.assertRaises(errors.RequestError, common.givePermissionToObject, vm,
                roles.role.UserRole, user_object=user, role_object=role)

        # Then remove
        loginAsAdmin()
        common.removeVm(TMP_VM_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_manipulate_permissions(self):
        """ POSITIVE_manipulate_permissions """
        # Add 'UserRole' permissions to user
        loginAsAdmin()
        common.createVm(TMP_VM_NAME, storage=config.MAIN_STORAGE_NAME)

        loginAsUser(filter_=self.filter_)
        vm = common.getObjectByName(API.vms, TMP_VM_NAME)
        role = common.getObjectByName(API.roles, roles.role.UserRole)
        user = common.getObjectByName(API.users, config.USER_NAME)
        userID = user.get_id()
        roleID = role.get_id()

        common.givePermissionToObject(vm, roles.role.UserRole,
                user_object=user, role_object=role)

        # Then remove and check if permissions was really added
        loginAsAdmin()
        ok = False
        for p in vm.permissions.list():
            if p.get_role().get_id() == roleID and p.get_user().get_id() == userID:
                ok = True
        assert ok
        common.removeVm(TMP_VM_NAME)

    @istest
    @resolve_permissions
    def NEG_create_host(self):
        """ NEG_create_host """
        self.assertRaises(errors.RequestError, common.createHost,
                config.MAIN_CLUSTER_NAME, config.ALT2_HOST_ADDRESS,
                config.ALT2_HOST_ADDRESS, config.ALT2_HOST_ROOT_PASSWORD)

    @istest
    @resolve_permissions
    def POSITIVE_create_host(self):
        """ POSITIVE_create_host """
        # creates host
        common.createHost(config.MAIN_CLUSTER_NAME, config.ALT2_HOST_ADDRESS,
                config.ALT2_HOST_ADDRESS, config.ALT2_HOST_ROOT_PASSWORD)
        # After install switch to maintenece
        host = API.hosts.get(config.ALT2_HOST_ADDRESS)
        common.waitForTasks(host)
        common.waitForState(host, states.host.maintenance)

    @istest
    @resolve_permissions
    def NEG_edit_host_configuration(self):
        """ NEG_edit_host_configuration """
        # If role is user role, try user can't access /hosts url
        if self.filter_:
            self.assertRaises(errors.RequestError, API.hosts.get,
                    config.MAIN_HOST_NAME)
            return
        host = API.hosts.get(config.MAIN_HOST_NAME)
        # Try to change host name
        before = host.get_name()
        newName = before + '_'
        host.set_name(newName)
        LOGGER.info("Tring to set new name for host '%s'" % (before))
        self.assertRaises(errors.RequestError, host.update)

    @istest
    @resolve_permissions
    def POSITIVE_edit_host_configuration(self):
        """ POSITIVE_edit_host_configuration """
        # Edit host name, append '_'
        host = API.hosts.get(config.MAIN_HOST_NAME)
        before = host.get_name()
        newName = before + '_'
        host.set_name(newName)
        host.update()

        host = API.hosts.get(newName)
        assert host is not None, "Failed to update Host name"
        LOGGER.info("Host '%s' configuration success" % (config.MAIN_HOST_NAME))
        config.MAIN_HOST_NAME = newName

    @istest
    @resolve_permissions
    def POSITIVE_configure_host_network(self):
        """ POSITIVE_configure_host_network """
        loginAsAdmin()  # switch to maintence
        host = API.hosts.get(config.MAIN_HOST_NAME)
        common.waitForTasks(host)
        common.waitForState(host, states.host.maintenance)

        loginAsUser(filter_=self.filter_)
        try:
            common.configureHostNetwork(config.MAIN_HOST_NAME)
        finally:
            try:
                loginAsAdmin()  # switch host up
                host = API.hosts.get(config.MAIN_HOST_NAME)
                host.activate()
                common.waitForHostUpState(host)
                dc = API.datacenters.get(config.MAIN_DC_NAME)
                common.waitForState(dc, states.host.up)
            except Exception as e:
                LOGGER.warning("Error ocured while activating host: '%s'" % e)

    @istest
    @resolve_permissions
    def NEG_configure_host_network(self):
        """ NEG_configure_host_network """
        loginAsAdmin()  # switch to maintence
        host = API.hosts.get(config.MAIN_HOST_NAME)
        common.waitForTasks(host)
        common.waitForState(host, states.host.maintenance)

        loginAsUser(filter_=self.filter_)
        self.assertRaises(errors.RequestError, common.configureHostNetwork,
                    config.MAIN_HOST_NAME)

        loginAsAdmin()  # switch host up
        host = API.hosts.get(config.MAIN_HOST_NAME)
        host.activate()
        common.waitForHostUpState(host)
        dc = API.datacenters.get(config.MAIN_DC_NAME)
        common.waitForState(dc, states.host.up)

    @istest
    @resolve_permissions
    def NEG_maniputlate_host(self):
        """ NEG_maniputlate_host """
        # Get host as admin, cause user can't access /hosts url
        if self.filter_:
            self.assertRaises(errors.RequestError, API.hosts.list)
        else:
            host = API.hosts.get(config.MAIN_HOST_NAME)
            self.assertRaises(errors.RequestError, host.deactivate)

    @istest
    @resolve_permissions
    def POSITIVE_maniputlate_host(self):
        """ POSITIVE_maniputlate_host """
        # Active/Deactive host
        common.activeDeactiveHost(config.MAIN_HOST_NAME)

    @istest
    @resolve_permissions
    def NEG_create_disk(self):
        """ NEG_create_disk """
        self.assertRaises(errors.RequestError, common.createDiskObject,
                TMP_DISK_NAME, storage=config.MAIN_STORAGE_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_create_disk(self):
        """ POSITIVE_create_disk """
        # create disk - using no check because of bz 869334
        disk = common.createDiskObject(TMP_DISK_NAME,
                storage=config.MAIN_STORAGE_NAME)
        common.waitForState(disk, states.disk.ok)
        common.deleteDiskObject(disk)

    # If you want to attach disk, you also have to have 'configure_vm_storage'
    # permissions on vm.
    @istest
    @resolve_permissions
    def POSITIVE_attach_disk(self):
        """ POSITIVE_attach_disk """
        # Create a disk, to attach
        loginAsAdmin()
        disk = common.createDiskObject(TMP_DISK_NAME, storage=config.MAIN_STORAGE_NAME)
        loginAsUser(filter_=self.filter_)

        if 'configure_vm_storage' in self.perms:
            common.attachDiskToVm(disk, VM_NAME)
        else:
            LOGGER.info("Attach disk can't be tested because for attach floating disk\
                you need configure_vm_storage permissions on vm.")

        loginAsAdmin()  # Cleanup
        common.deleteDiskObject(disk)

    @istest
    @resolve_permissions
    def NEG_attach_disk(self):
        """ NEG_attach_disk """
        # Create disk to be attached
        loginAsAdmin()
        diskId = common.createDiskObject(TMP_DISK_NAME, storage=config.MAIN_STORAGE_NAME).get_id()
        common.givePermissionToObject(API.disks.get(id=diskId), self.role)

        loginAsUser(filter_=self.filter_)
        disk = API.disks.get(id=diskId)
        if 'configure_vm_storage' in self.perms:
            self.assertRaises(errors.RequestError, common.attachDiskToVm,
                    disk, VM_NAME)
        else:
            LOGGER.info("Attach disk can't be tested because for attach floating disk\
                    you need configure_vm_storage permissions on vm.")

        loginAsAdmin()
        common.deleteDiskObject(API.disks.get(id=diskId))

    @istest
    @resolve_permissions
    def POSITIVE_edit_disk_properties(self):
        """ POSITIVE_edit_disk_properties """
        # Update works only for VM disk
        common.editVmDiskProperties(VM_NAME)

    @istest
    @resolve_permissions
    def NEG_edit_disk_properties(self):
        """ NEG_edit_disk_properties """
        # Update works only for VM disk
        self.assertRaises(errors.RequestError, common.editVmDiskProperties, VM_NAME)

    @istest
    @resolve_permissions
    def NEG_delete_disk(self):
        """ NEG_delete_disk """
        # Creates a disk that shoul be removed, as admin
        loginAsUser(filter_=self.filter_)
        disk = common.getObjectByName(API.disks, None, alias=DISK_NAME)
        self.assertRaises(errors.RequestError, disk.delete)

    @istest
    @resolve_permissions
    def POSITIVE_delete_disk(self):
        """ POSITIVE_delete_disk """
        loginAsAdmin()
        disk = common.createDiskObject(TMP_DISK_NAME,
                storage=config.MAIN_STORAGE_NAME).get_id()
        common.givePermissionToObject(API.disks.get(id=disk), self.role)

        loginAsUser(filter_=self.filter_)
        common.deleteDisk(disk)

    @istest
    @resolve_permissions
    def NEG_create_cluster(self):
        """ NEG_create_cluster """
        self.assertRaises(errors.RequestError, common.createCluster,
                        TMP_CLUSTER_NAME, config.MAIN_DC_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_create_cluster(self):
        """ POSITIVE_create_cluster """
        # creates cluster
        common.createCluster(TMP_CLUSTER_NAME, config.MAIN_DC_NAME)

        # clean
        loginAsAdmin()
        common.removeCluster(TMP_CLUSTER_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_edit_cluster_configuration(self):
        """ POSITIVE_edit_cluster_configuration """
        # Chamge cpu type of cluster
        cluster = common.getObjectByName(API.clusters, CLUSTER_NAME)

        before = cluster.get_cpu().get_id()
        if before == config.HOST_CPU_TYPE:
            after = CLUSTER_CPU_TYPE
        else:
            after = config.HOST_CPU_TYPE

        cpu = params.CPU(id=after)
        cluster.set_cpu(cpu)
        cluster.update()

        cluster = common.getObjectByName(API.clusters, CLUSTER_NAME)
        now = cluster.get_cpu().get_id()
        assert before != now, "Failed to update cluster configuration"
        LOGGER.info("Cluster '%s' editing success" % (CLUSTER_NAME))

    @istest
    @resolve_permissions
    def NEG_edit_cluster_configuration(self):
        """ NEG_edit_cluster_configuration """
        cluster = common.getObjectByName(API.clusters, CLUSTER_NAME)

        before = cluster.get_cpu().get_id()
        if before == config.HOST_CPU_TYPE:
            after = CLUSTER_CPU_TYPE
        else:
            after = config.HOST_CPU_TYPE

        cpu = params.CPU(id=after)
        cluster.set_cpu(cpu)
        self.assertRaises(errors.RequestError, cluster.update)

    @istest
    @resolve_permissions
    def NEG_assign_cluster_network(self):
        """ NEG_assign_cluster_network """
        cluster = common.getObjectByName(API.clusters, CLUSTER_NAME)
        net = common.getObjectByName(API.networks, DC_NETWORK_NAME)

        self.assertRaises(errors.RequestError, cluster.networks.add, net)

    @istest
    @resolve_permissions
    def POSITIVE_assign_cluster_network(self):
        """ POSITIVE_assign_cluster_network """
        # Assign new network to cluster, then delete it
        cluster = common.getObjectByName(API.clusters, CLUSTER_NAME)
        net = common.getObjectByName(API.networks, DC_NETWORK_NAME)
        nets = cluster.networks.add(net)

        net = common.getObjectByName(cluster.networks, DC_NETWORK_NAME)
        assert net is not None
        LOGGER.info("Network '%s' assigned" % DC_NETWORK_NAME)

        loginAsAdmin()
        cluster = API.clusters.get(CLUSTER_NAME)
        net = cluster.networks.get(DC_NETWORK_NAME)
        net.delete()

    @istest
    @resolve_permissions
    def NEG_delete_cluster(self):
        """ NEG_delete_cluster """
        self.assertRaises(errors.RequestError, common.removeCluster,
                    CLUSTER_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_delete_cluster(self):
        """ POSITIVE_delete_cluster """
        # removes cluster
        common.removeCluster(CLUSTER_NAME)

        loginAsAdmin()
        common.createCluster(CLUSTER_NAME, config.MAIN_DC_NAME)

    @istest
    @resolve_permissions
    def NEG_manipulate_roles(self):
        """ NEG_manipulate_roles """
        self.assertRaises(errors.RequestError, common.addRole, ROLE_NAME,
                roles.role.UserRole)

    @istest
    @resolve_permissions
    def POSITIVE_manipulate_roles(self):
        """ POSITIVE_manipulate_roles """
        # Create new role
        common.addRole(ROLE_NAME, roles.role.UserRole)
        common.deleteRole(ROLE_NAME)

    @istest
    @resolve_permissions
    def NEG_manipulate_users(self):
        """ NEG_manipulate_users """
        self.assertRaises(errors.RequestError, common.addUser,
                        userName=config.USER_NAME2, domainName=config.USER_DOMAIN)

    @istest
    @resolve_permissions
    def POSITIVE_manipulate_users(self):
        """ POSITIVE_manipulate_users """
        # Import new user from domain and delete it
        common.addUser(userName=config.USER_NAME2, domainName=config.USER_DOMAIN)
        common.removeUser(userName=config.USER_NAME2, domainName=config.USER_DOMAIN)

    @istest
    @resolve_permissions
    def NEG_create_storage_domain(self):
        """ NEG_create_storage_domain """
        self.assertRaises(errors.RequestError, common.createNfsStorage,
                    config.ALT2_STORAGE_NAME, storageType='data',
                    address=config.ALT2_STORAGE_ADDRESS,
                    path=config.ALT2_STORAGE_PATH,
                    datacenter=config.MAIN_DC_NAME,
                    host=config.MAIN_HOST_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_create_storage_domain(self):
        """ POSITIVE_create_storage_domain """
        # create new storage domain
        common.createNfsStorage(
            config.ALT2_STORAGE_NAME, storageType='data',
            address=config.ALT2_STORAGE_ADDRESS,
            path=config.ALT2_STORAGE_PATH,
            datacenter=config.MAIN_DC_NAME,
            host=config.MAIN_HOST_NAME)

    @istest
    @resolve_permissions
    def NEG_edit_storage_domain_configuration(self):
        """ NEG_edit_storage_domain_configuration """
        newName = config.MAIN_STORAGE_NAME + '_'
        self.assertRaises(errors.RequestError, common.editObject,
                API.storagedomains, config.MAIN_STORAGE_NAME, newName=newName)

    @istest
    @resolve_permissions
    def POSITIVE_edit_storage_domain_configuration(self):
        """ POSITIVE_edit_storage_domain_configuration """
        common.editObject(API.storagedomains, config.MAIN_STORAGE_NAME, description='_', append=True)

    @istest
    @resolve_permissions
    def NEG_manipulate_storage_domain(self):
        """ NEG_manipulate_storage_domain """
        dc = common.getObjectByName(API.datacenters, config.MAIN_DC_NAME)
        storage = common.getObjectByName(API.storagedomains, EXPORT_NAME)
        storageInDc = common.getObjectByName(dc.storagedomains, EXPORT_NAME)

        self.assertRaises(errors.RequestError, common.deactivateActivateByStateObject,
                storage=storage, storageInDc=storageInDc, state=states.storage.maintenance, jmp=True,
                datacenter=config.MAIN_DC_NAME)
    @istest
    @resolve_permissions
    def POSITIVE_manipulate_storage_domain(self):
        """ POSITIVE_manipulate_storage_domain """
        # Try to activate deactivate SD
        dc = common.getObjectByName(API.datacenters, config.MAIN_DC_NAME)
        storage = common.getObjectByName(API.storagedomains, EXPORT_NAME)
        storageInDc = common.getObjectByName(dc.storagedomains, EXPORT_NAME)

        common.deactivateActivateByStateObject(storage=storage, storageInDc=storageInDc,
                state=states.storage.maintenance, jmp=True,
                datacenter=config.MAIN_DC_NAME)

    @istest
    @resolve_permissions
    def NEG_port_mirroring(self):
        """ NEG_port_mirroring """
        network = common.getObjectByName(API.networks, config.NETWORK_NAME)
        n = params.Networks(network=[network])
        pm = params.PortMirroring(networks=n)
        vm = common.getObjectByName(API.vms, VM_NAME)
        param = params.NIC(name=VM_NET_NAME,
                    network=network,
                    interface='virtio',
                    port_mirroring=pm)
        self.assertRaises(errors.RequestError, vm.nics.add, param)

    @istest
    @resolve_permissions
    def POSITIVE_port_mirroring(self):
        """ POSITIVE_port_mirroring """
        network = common.getObjectByName(API.networks, config.NETWORK_NAME)
        n = params.Networks(network=[network])
        pm = params.PortMirroring(networks=n)
        vm = common.getObjectByName(API.vms, VM_NAME)
        param = params.NIC(name=VM_NET_NAME,
                    network=network,
                    interface='virtio',
                    port_mirroring=pm)
        vm.nics.add(param)

    @istest
    @resolve_permissions
    def NEG_delete_storage_domain(self):
        """ NEG_delete_storage_domain """
        # removes sd
        if 'create_storage_domain' in self.perms:
            self.assertRaises(errors.RequestError, common.removeNonMasterStorage,
                    config.ALT2_STORAGE_NAME, config.MAIN_DC_NAME,
                    config.MAIN_HOST_NAME)
        else:
            self.assertRaises(errors.RequestError, common.removeNonMasterStorage,
                    config.MAIN_STORAGE_NAME, config.MAIN_DC_NAME,
                    config.MAIN_HOST_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_delete_storage_domain(self):
        """ NEG_delete_storage_domain """
        if 'create_storage_domain' in self.perms:
            common.removeNonMasterStorage(config.ALT2_STORAGE_NAME,
                    datacenter=config.MAIN_DC_NAME,
                    host=config.MAIN_HOST_NAME)
        else:
            common.removeNonMasterStorage(config.MAIN_STORAGE_NAME,
                    datacenter=config.MAIN_DC_NAME,
                    host=config.MAIN_HOST_NAME)

    # For MoveOrCopyDiskCommand there is required
    # configure_disk_storage so check it before
    # run move/copy disk
    @istest
    @resolve_permissions
    def NEG_move_vm(self):
        """ NEG_move_vm """
        loginAsAdmin()
        if common.getObjectByName(API.vms, TMP_VM_NAME) is not None:
            common.removeVm(TMP_VM_NAME)
        common.createVm(TMP_VM_NAME, storage=config.MAIN_STORAGE_NAME)
        common.givePermissionToVm(TMP_VM_NAME, self.role)

        loginAsUser(filter_=self.filter_)
        self.assertRaises(errors.RequestError, common.moveVm,
                TMP_VM_NAME, config.ALT1_STORAGE_NAME)

        loginAsAdmin() # clean
        common.removeVm(TMP_VM_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_move_vm(self):
        """ POSITIVE_move_vm """
        # Move vm from one SD to another
        # Create temporary vm, and then remove it as Admin
        # Dont suppose that user can create/remove vm/disk
        loginAsAdmin()
        if common.getObjectByName(API.vms, TMP_VM_NAME) is not None:
            common.removeVm(TMP_VM_NAME)
        common.createVm(TMP_VM_NAME, storage=config.MAIN_STORAGE_NAME)
        common.givePermissionToVm(TMP_VM_NAME, self.role)

        loginAsUser(filter_=self.filter_)
        common.moveVm(TMP_VM_NAME, config.ALT1_STORAGE_NAME)

        loginAsAdmin() # clean
        common.removeVm(TMP_VM_NAME)

    @istest
    @resolve_permissions
    def NEG_migrate_vm(self):
        """ NEG_migrate_vm """
        if self.filter_:
            self.assertRaises(errors.RequestError, API.hosts.list)
            return

        loginAsAdmin()
        common.startVm(VM_NAME)
        vm = common.getObjectByName(API.vms, VM_NAME)
        hostName = API.hosts.get(id=vm.get_host().get_id()).get_name()

        loginAsUser(filter_=self.filter_)
        host1 = API.hosts.get(config.MAIN_HOST_NAME)
        host2 = API.hosts.get(config.ALT1_HOST_ADDRESS)
        vm = common.getObjectByName(API.vms, VM_NAME)

        if hostName == config.ALT1_HOST_ADDRESS:
            self.assertRaises(errors.RequestError, common.migrateVm, vm, host1)
        else:
            self.assertRaises(errors.RequestError, common.migrateVm, vm, host2)

        loginAsAdmin()
        common.stopVm(VM_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_migrate_vm(self):
        """ POSITIVE_migrate_vm """
        # Migrate vm to another host, suppose that user
        # also can run/stop vm if he can migrate_vm

        # Have to be used, because UserVmManager cant access /hosts url
        loginAsAdmin()
        common.startVm(VM_NAME)
        vm = API.vms.get(VM_NAME)
        hostName = API.hosts.get(id=vm.get_host().get_id()).get_name()
        common.checkHostStatus(config.MAIN_HOST_NAME)
        common.checkHostStatus(config.ALT1_HOST_ADDRESS)

        loginAsUser(filter_=self.filter_)
        host1 = API.hosts.get(config.MAIN_HOST_NAME)
        host2 = API.hosts.get(config.ALT1_HOST_ADDRESS)
        vm = common.getObjectByName(API.vms, VM_NAME)

        if hostName == config.ALT1_HOST_ADDRESS:
            common.migrateVm(vm, host1)
        else:
            common.migrateVm(vm, host2)

        loginAsAdmin()
        common.stopVm(VM_NAME)

    @istest
    @resolve_permissions
    def NEG_delete_host(self):
        """ NEG_delete_host """
        self.assertRaises(errors.RequestError, common.removeHost,
                    hostName=config.ALT1_HOST_ADDRESS)

    @istest
    @resolve_permissions
    def POSITIVE_delete_host(self):
        """ POSITIVE_delete_host """
        if 'create_host' in self.perms:
            host = API.hosts.get(config.ALT2_HOST_ADDRESS)
            host.delete()
            assert common.updateObject(host) is None, "Failed to remove host"
        else:
            common.removeHost(hostName=config.ALT1_HOST_ADDRESS)

    @istest
    @resolve_permissions
    def POSITIVE_change_vm_custom_properties(self):
        """ POSITIVE_change_vm_custom_properties """
        common.changeVmCustomProperty(VM_NAME, regexp=None, name='sap_agent', value='true')

    @istest
    @resolve_permissions
    def NEG_change_vm_custom_properties(self):
        """ POSITIVE_change_vm_custom_properties """
        self.assertRaises(errors.RequestError, common.changeVmCustomProperty,
                VM_NAME, regexp=None, name='sap_agent', value='true')

    @istest
    @resolve_permissions
    def NEG_copy_template(self):
        """ NEG_copy_template """
        if 'configure_disk_storage' in self.perms:
            LOGGER.warning('Copy_template is deprecated, so user can copy template \
                    when he has configure_disk_storage permissions.')
            common.copyTemplate(templateName=TEMPLATE_NAME,
                    storageName=config.ALT1_STORAGE_NAME)
            loginAsAdmin()
            common.removeTemplate(TEMPLATE_NAME)
            common.createTemplate(VM_NAME, TEMPLATE_NAME)
        else:
            LOGGER.warning('Copy_template is deprecated, so user cant copy template \
                    when he has not configure_disk_storage permissions.')
            self.assertRaises(errors.RequestError, common.copyTemplate,
                    templateName=TEMPLATE_NAME,
                    storageName=config.ALT1_STORAGE_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_copy_template(self):
        """ POSITIVE_copy_template """
        if 'configure_disk_storage' in self.perms:
            LOGGER.warning('Copy_template is deprecated, so user can copy template \
                    when he has configure_disk_storage permissions.')
            common.copyTemplate(templateName=TEMPLATE_NAME,
                    storageName=config.ALT1_STORAGE_NAME)
            loginAsAdmin()
            common.removeTemplate(TEMPLATE_NAME)
            common.createTemplate(VM_NAME, TEMPLATE_NAME)
        else:
            LOGGER.warning('Copy_template is deprecated, so user cant copy template \
                    when he has not configure_disk_storage permissions.')
            self.assertRaises(errors.RequestError, common.copyTemplate,
                    templateName=TEMPLATE_NAME,
                    storageName=config.ALT1_STORAGE_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_create_storage_pool(self):
        """ POSITIVE_create_storage_pool """
        # Try to create DC
        common.createDataCenter(DC_NAME_TMP,
                storageType=config.MAIN_STORAGE_TYPE)

        # If success, remove it as admin
        loginAsAdmin()
        common.removeDataCenter(DC_NAME_TMP)

    @istest
    @resolve_permissions
    def NEG_create_storage_pool(self):
        """ NEG_create_storage_pool """
        self.assertRaises(errors.RequestError, common.createDataCenter, DC_NAME_TMP)

    @istest
    @resolve_permissions
    def POSITIVE_delete_storage_pool(self):
        """ POSITIVE_delete_storage_pool """
        # Try to remove datacenter
        # First of all create one as admin.
        loginAsAdmin()
        common.createDataCenter(DC_NAME_TMP,
                storageType=config.MAIN_STORAGE_TYPE)

        loginAsUser(filter_=self.filter_)
        common.removeDataCenter(DC_NAME_TMP)

    @istest
    @resolve_permissions
    def NEG_delete_storage_pool(self):
        """ NEG_delete_storage_pool """
        # First of all create one as admin.
        loginAsAdmin()
        common.createDataCenter(DC_NAME_TMP,
                storageType=config.MAIN_STORAGE_TYPE)

        loginAsUser(filter_=self.filter_)
        self.assertRaises(errors.RequestError, common.removeDataCenter,
                DC_NAME_TMP)

        # Unsuccessfull? Delete it.
        loginAsAdmin()
        common.removeDataCenter(DC_NAME_TMP)

    @istest
    @resolve_permissions
    def POSITIVE_edit_storage_pool_configuration(self):
        """ POSITIVE_edit_storage_pool_configuration """
        # Try to change DC name.
        common.editObject(API.datacenters, DC_NAME_TMP2, description='_', append=True)

    @istest
    @resolve_permissions
    def NEG_edit_storage_pool_configuration(self):
        """ NEG_edit_storage_pool_configuration """
        self.assertRaises(errors.RequestError, common.editObject,
                API.datacenters, DC_NAME_TMP2, newName=VM_NAME)

    @istest
    @resolve_permissions
    def POSITIVE_configure_storage_pool_network(self):
        """ POSITIVE_configure_storage_pool_network """
        # Try to add new network to DC.
        common.addNetworkToDC(DC_NETWORK_NAME_TMP, DC_NAME_TMP2)
        common.deleteNetwork(DC_NETWORK_NAME_TMP, DC_NAME_TMP2)

    @istest
    @resolve_permissions
    def NEG_configure_storage_pool_network(self):
        """ NEG_configure_storage_pool_network """
        self.assertRaises(errors.RequestError,
                common.addNetworkToDC, DC_NETWORK_NAME_TMP, DC_NAME_TMP2)

    @istest
    @resolve_permissions
    def POSITIVE_connect_to_vm(self):
        """ POSITIVE_connect_to_vm """
        common.generateTicket(VM_NAME)

    @istest
    @resolve_permissions
    def NEG_connect_to_vm(self):
        """ NEG_connect_to_vm """
        # Have to run vm, as admin, because I can't suppose that
        # user can run VM. Then try to generate ticket for VM.
        loginAsAdmin()
        common.startVm(VM_NAME)

        loginAsUser(filter_=self.filter_)
        vm = common.getObjectByName(API.vms, VM_NAME)
        self.assertRaises(errors.RequestError, vm.ticket)
        LOGGER.info("Vm '%s' ticket can't be generated." % VM_NAME)

        loginAsAdmin()
        common.stopVm(VM_NAME)
