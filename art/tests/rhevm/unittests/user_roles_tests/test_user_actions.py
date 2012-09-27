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

import config
import common
import states
import sys
import re
import unittest2 as unittest
from unittest2 import SkipTest
from nose.tools import istest
from functools import wraps

from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors

import logging

LOGGER = logging.getLogger(__name__)
API = common.API
GB = common.GB


# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
VM_NAME = 'user_actions__vm'  # used for whole module
TMP_VM_NAME = 'user_actions__vm_tmp'  # used once per test
EXPORT_NAME = 'user_actions__export'
SNAPSHOT_NAME = 'user_actions__snapshot'
ISO_NAME = 'user_actions__iso'
TEMPLATE_NAME = 'user_actions__template'
VMPOOL_NAME = 'user_actions__vmpool'
DISK_NAME = 'user_actions__disk'
TMP_TEMPLATE_NAME = 'user_actions__template_tmp'
TMP_VMPOOL_NAME = 'user_actions__vmpool_tmp'
TMP_DISK_NAME = 'user_actions__disk_tmp'
CLUSTER_NAME = 'user_actions__cluster'
TMP_CLUSTER_NAME = 'user_actions__cluster_tmp'
CLUSTER_CPU_TYPE = 'AMD Opteron G2'

ROLE_NAME = 'user_actions__role'
USER_ROLE_PERMITS = params.Permits(permit=API.roles.get('UserRole').get_permits().list())

PERMISSIONS = common.getSuperUserPermissions()


def resolve_permissions(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        LOGGER.info("Running: %s - %s" % (self.role, func.__name__))
        m = re.match('^.._(?P<type>[A-Z]+)_(?P<perm>.*)$', func.func_name)
        msg = "Combination '%s, %s, %s' doesn't make sence"
        if m.group('type') == 'POSITIVE':
            if m.group('perm') not in self.perms:
                LOGGER.info(msg % (self.role, m.group('type'), m.group('perm')))
                raise SkipTest(msg % (self.role, m.group('type'), m.group('perm')))
        if m.group('type') == 'NEG':
            if m.group('perm') in self.perms:
                LOGGER.info(msg % (self.role, m.group('type'), m.group('perm')))
                raise SkipTest(msg % (self.role, m.group('type'), m.group('perm')))
        try:
            result = func(self, *args, **kwargs)
            LOGGER.info("Case '%s' successed" % func.__name__)
            return result
        except Exception as err:
            LOGGER.error("!ERROR! => " + str(err))
            raise err

    return wrapper

def setUpModule():
    """ Prepare testing setup """
    common.addUser()
    common.createNfsStorage(EXPORT_NAME, storageType='export',
            address=config.EXPORT_ADDRESS, path=config.EXPORT_PATH)
    common.attachActivateStorage(EXPORT_NAME)
    common.createNfsStorage(ISO_NAME, storageType='iso',
            address=config.ISO_ADDRESS, path=config.ISO_PATH)
    common.attachActivateStorage(ISO_NAME)

def tearDownModule():
    common.removeUser()
    common.removeNonMasterStorage(EXPORT_NAME)
    common.removeNonMasterStorage(ISO_NAME)


##################### BASE CLASS OF TESTS #####################################
class UserActionsTests(unittest.TestCase):

    __test__ = False

    def setUp(self):
        common.loginAsUser(filter_=self.filter_)

    def tearDown(self):
        """ Re-create VM if it got removed, stops it if it isn't in
        state down.
        """
        common.loginAsAdmin()
        disk = common.getDisksByName(DISK_NAME)
        if disk is None:
            common.createDisk(DISK_NAME)

        vm = API.vms.get(VM_NAME)
        if vm is None:
            common.createVm(VM_NAME)
        common.stopVm(VM_NAME)

        tmp = API.templates.get(TEMPLATE_NAME)
        if tmp is None:
            common.createTemplate(VM_NAME, TEMPLATE_NAME)

        vmpool = API.vmpools.get(VMPOOL_NAME)
        if vmpool is None:
            common.createVmPool(VMPOOL_NAME, TEMPLATE_NAME)
        common.removeVmPool(TMP_VM_NAME)
        #common.deleteDisk(TMP_DISK_NAME)


    @classmethod
    def setUpClass(cls):
        common.createCluster(CLUSTER_NAME, config.MAIN_DC_NAME)
        common.createVm(VM_NAME)
        common.createTemplate(VM_NAME, TEMPLATE_NAME)
        common.createDisk(DISK_NAME)
        common.createVmPool(VMPOOL_NAME, TEMPLATE_NAME)

        common.addRoleToUser(cls.role)
        #common.givePermissionToDc(config.MAIN_DC_NAME, cls.role)
        common.givePermissionToVm(VM_NAME, cls.role)
        common.loginAsUser(filter_=cls.filter_)

    @classmethod
    def tearDownClass(cls):
        common.loginAsAdmin()
        common.removeCluster(CLUSTER_NAME)
        common.removeRoleFromUser(cls.role)
        common.removeAllPermissionFromDc(config.MAIN_DC_NAME)
        common.removeAllPermissionFromVm(VM_NAME)

        common.checkHostStatus(config.MAIN_HOST_NAME)
        common.checkDataCenterStatus(config.MAIN_DC_NAME)
        #common.deleteDisk(DISK_NAME)
        common.removeVmPool(VMPOOL_NAME)
        #common.removeTemplate(TEMPLATE_NAME)
        # Some issus with deleting build 118
        # for some time disbale create/delete template test

        common.removeVm(TMP_VM_NAME)
        common.removeVmPool(TMP_VMPOOL_NAME)
        common.removeTemplate(TMP_TEMPLATE_NAME)
        #common.deleteDisk(TMP_DISK_NAME)
        common.removeVm(VM_NAME)
        common.removeNonMasterStorage(config.ALT_STORAGE_NAME)

    @istest
    @resolve_permissions
    def aa_POSITIVE_vm_basic_operations(self):
        """ POSITIVE_vm_basic_operations """
        vm = API.vms.get(VM_NAME)
        vm.start()
        LOGGER.info("VM '%s' starting" % (VM_NAME))
        common.waitForState(vm, states.vm.up)
        vm.stop()
        LOGGER.info("VM '%s' stoping" % (VM_NAME))
        common.waitForState(vm, states.vm.down)

    @istest
    @resolve_permissions
    def ab_NEG_vm_basic_operations(self):
        """ NEG_vm_basic_operations """
        vm = API.vms.get(VM_NAME)
        self.assertRaises(errors.RequestError, vm.start)

    @istest
    @resolve_permissions
    def ac_POSITIVE_create_vm(self):
        """ POSITIVE_create_vm """
        common.createVm(TMP_VM_NAME)

    @istest
    @resolve_permissions
    def ad_NEG_create_vm(self):
        """ NEG_create_vm """
        self.assertRaises(errors.RequestError, common.createVm, TMP_VM_NAME,
                          createDisk=False)

    @istest
    @resolve_permissions
    def ae_POSITIVE_delete_vm(self):
        """ POSITIVE_delete_vm """
        common.removeVm(VM_NAME)

    @istest
    @resolve_permissions
    def af_NEG_delete_vm(self):
        """ NEG_delete_vm """
        self.assertRaises(errors.RequestError, common.removeVm, VM_NAME)

    @istest
    @resolve_permissions
    def ag_NEG_edit_vm_properties(self):
        """ NEG_edit_vm_properties """
        vm = API.vms.get(VM_NAME)
        display = params.Display(type_="vnc")
        vm.set_display(display)
        self.assertRaises(errors.RequestError, vm.update)

    @istest
    @resolve_permissions
    def ah_POSITIVE_edit_vm_properties(self):
        """ POSITIVE_edit_vm_properties """
        vm = API.vms.get(VM_NAME)
        before = vm.get_display().type_
        if before == "vnc":
            after = "spice"
        else:
            after = "vnc"

        display = params.Display(type_=after)
        vm.set_display(display)
        vm.update()

        vm = API.vms.get(VM_NAME)
        now = vm.get_display().type_
        assert before != now, "Failed to update VM display properties"
        LOGGER.info("VM '%s' updated" % (VM_NAME))

    @istest
    @resolve_permissions
    def ai_POSITIVE_change_vm_cd(self):
        """ POSITIVE_change_vm_cd """
        common.changeVmCd(VM_NAME, ISO_NAME)

    @istest
    @resolve_permissions
    def aj_NEG_change_vm_cd(self):
        """ NEG_change_vm_cd """
        self.assertRaises(errors.RequestError, common.changeVmCd, VM_NAME, ISO_NAME)

    @istest
    @resolve_permissions
    def am_NEG_import_export_vm(self):
        """ NEG_import_export_vm """
        vm = API.vms.get(VM_NAME)
        storage = API.storagedomains.get(EXPORT_NAME)
        param = params.Action(storage_domain=storage, exclusive=False)
        self.assertRaises(errors.RequestError, vm.export, param)

    @istest
    @resolve_permissions
    def an_POSITIVE_import_export_vm(self):
        """ POSITIVE_import_export_vm """
        vm = API.vms.get(VM_NAME)
        storage = API.storagedomains.get(EXPORT_NAME)
        param = params.Action(storage_domain=storage, exclusive=True)
        vm.export(param)
        common.waitForState(vm, states.vm.down)

    @istest
    @resolve_permissions
    def ao_NEG_configure_vm_network(self):
        """ NEG_configure_vm_network """
        vm = API.vms.get(VM_NAME)
        param = params.NIC(name=config.HOST_NIC,
                           network=params.Network(name=config.NETWORK_NAME),
                           interface='virtio')
        self.assertRaises(errors.RequestError, vm.nics.add, param)

    @istest
    @resolve_permissions
    def ap_POSITIVE_configure_vm_network(self):
        """ POSITIVE_configure_vm_network """
        vm = API.vms.get(VM_NAME)
        param = params.NIC(name=config.HOST_NIC,
                           network=params.Network(name=config.NETWORK_NAME),
                           interface='virtio')
        vm.nics.add(param)
        LOGGER.info("VM '%s' network configure success" % (VM_NAME))

    @istest
    @resolve_permissions
    def aq_NEG_configure_vm_storage(self):
        """ NEG_configure_vm_storage """
        # FIXME just add disk, or something with storage domains?
        vm = API.vms.get(VM_NAME)
        storage = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        param1 = params.StorageDomains(
                    storage_domain=[storage])
        param2 = params.Disk(storage_domains=param1, size=1 * GB,
                #type_='data',
                status=None, interface='virtio', format='cow',
                sparse=True)
        self.assertRaises(errors.RequestError, vm.disks.add, param2)

    @istest
    @resolve_permissions
    def ar_POSITIVE_configure_vm_storage(self):
        """ POSITIVE_configure_vm_storage """
        vm = API.vms.get(VM_NAME)
        storage = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        param1 = params.StorageDomains(
                storage_domain=[storage])
        param2 = params.Disk(storage_domains=param1, size=1 * GB,
                #type_='data',
                status=None, interface='virtio', format='cow',
                sparse=True)
        disk = vm.disks.add(param2)
        common.waitForState(disk, states.disk.ok)
        LOGGER.info("VM '%s' storage configure success" % (VM_NAME))

    @istest
    @resolve_permissions
    def au_NEG_manipulate_vm_snapshots(self):
        """ NEG_manipulate_vm_snapshots """
        vm = API.vms.get(VM_NAME)
        param = params.Snapshot(vm=vm, description=SNAPSHOT_NAME)
        self.assertRaises(errors.RequestError, vm.snapshots.add, param)

    @istest
    @resolve_permissions
    def av_POSITIVE_manipulate_vm_snapshots(self):
        """ POSITIVE_manipulate_vm_snapshots """
        vm = API.vms.get(VM_NAME)
        param = params.Snapshot(vm=vm, description=SNAPSHOT_NAME)
        vm.snapshots.add(param)
        common.waitForState(vm, states.vm.down)
        snap = vm.snapshots.get(description=SNAPSHOT_NAME)
        self.assertTrue(snap is not None)
        LOGGER.info("VM '%s' manipulate snaps success" % (VM_NAME))

    #@istest
    @resolve_permissions
    def aw_NEG_create_template(self):
        """ NEG_create_template """
        self.assertRaises(errors.RequestError, common.createTemplate, VM_NAME,
                TMP_TEMPLATE_NAME)

    #@istest
    @resolve_permissions
    def ax_POSITIVE_create_template(self):
        """ POSITIVE_create_template """
        common.createTemplate(VM_NAME, TMP_TEMPLATE_NAME)

    @istest
    @resolve_permissions
    def ay_NEG_edit_template_properties(self):
        """ NEG_edit_template_properties """
        template = API.templates.get(TEMPLATE_NAME)
        display = params.Display(type_="vnc")
        template.set_display(display)
        self.assertRaises(errors.RequestError, template.update)

    @istest
    @resolve_permissions
    def az_POSITIVE_edit_template_properties(self):
        """ POSITIVE_edit_template_properties """
        template = API.templates.get(TEMPLATE_NAME)
        before = template.get_display().type_
        if before == "vnc":
            after = "spice"
        else:
            after = "vnc"

        display = params.Display(type_=after)
        template.set_display(display)
        template.update()

        template = API.templates.get(TEMPLATE_NAME)
        now = template.get_display().type_
        assert before != now, "Failed to update Template display properties"
        LOGGER.info("Temaplate '%s' editing success" % (TEMPLATE_NAME))

    @istest
    @resolve_permissions
    def be_NEG_configure_template_network(self):
        """ NEG_configure_template_network """
        template = API.templates.get(TEMPLATE_NAME)
        param = params.NIC(name=config.HOST_NIC,
                    network=params.Network(name=config.NETWORK_NAME),
                    interface='virtio')
        self.assertRaises(errors.RequestError, template.nics.add, param)

    @istest
    @resolve_permissions
    def bf_POSITIVE_configure_template_network(self):
        """ POSITIVE_configure_template_network """
        template = API.templates.get(TEMPLATE_NAME)
        param = params.NIC(name=config.HOST_NIC,
                    network=params.Network(name=config.NETWORK_NAME),
                    interface='virtio')
        template.nics.add(param)
        LOGGER.info("Temaplate '%s' network configure success" % (TEMPLATE_NAME))

    @istest
    @resolve_permissions
    def bg_NEG_create_vm_pool(self):
        """ NEG_create_vm_pool """
        self.assertRaises(errors.RequestError, common.createVmPool,
                        TMP_VMPOOL_NAME, TEMPLATE_NAME)

    @istest
    @resolve_permissions
    def bh_POSITIVE_create_vm_pool(self):
        """ POSITIVE_create_vm_pool """
        common.createVmPool(TMP_VMPOOL_NAME, TEMPLATE_NAME)

    @istest
    @resolve_permissions
    def bi_NEG_edit_vm_pool_configuration(self):
        """ NEG_edit_vm_pool_configuration """
        self.assertRaises(errors.RequestError, common.addVmToPool, VMPOOL_NAME)

    @istest
    @resolve_permissions
    def bj_POSITIVE_edit_vm_pool_configuration(self):
        """ POSITIVE_edit_vm_pool_configuration """
        common.addVmToPool(VMPOOL_NAME)

    @istest
    @resolve_permissions
    def bk_NEG_delete_vm_pool(self):
        """ NEG_delete_vm_pool """
        self.assertRaises(errors.RequestError, common.removeVmPool, VMPOOL_NAME)

    @istest
    @resolve_permissions
    def bl_POSITIVE_delete_vm_pool(self):
        """ POSITIVE_delete_vm_pool """
        common.removeVmPool(VMPOOL_NAME)

    @istest
    @resolve_permissions
    def bm_NEG_vm_pool_basic_operations(self):
        """ NEG_vm_pool_basic_operations """
        self.assertRaises(errors.RequestError, common.vmpoolBasicOperations, VMPOOL_NAME)

    @istest
    @resolve_permissions
    def bn_POSITIVE_vm_pool_basic_operations(self):
        """ POSITIVE_vm_pool_basic_operations """
        common.vmpoolBasicOperations(VMPOOL_NAME)

    #@istest
    @resolve_permissions
    def bo_NEG_delete_template(self):
        """ NEG_delete_template """
        self.assertRaises(errors.RequestError, common.removeTemplate,
                    TEMPLATE_NAME)

    #@istest
    @resolve_permissions
    def bp_POSITIVE_delete_template(self):
        """ POSITIVE_delete_template """
        common.removeTemplate(TEMPLATE_NAME)

    @istest
    @resolve_permissions
    def bq_NEG_manipulate_permissions(self):
        """ NEG_manipulate_permissions """
        self.assertRaises(errors.RequestError, common.addPermissionsToUser, 'UserRole')

    @istest
    @resolve_permissions
    def br_POSITIVE_manipulate_permissions(self):
        """ POSITIVE_manipulate_permissions """
        common.addPermissionsToUser('UserRole')

    # Only for while comment this, because of speed of tests
    #@istest
    @resolve_permissions
    def bs_NEG_create_host(self):
        """ NEG_create_host """
        self.assertRaises(errors.RequestError, common.createHost,
                config.MAIN_CLUSTER_NAME)

    #@istest
    @resolve_permissions
    def bt_POSITIVE_create_host(self):
        """ POSITIVE_create_host """
        common.createHost(config.MAIN_CLUSTER_NAME)

    @istest
    @resolve_permissions
    def bu_NEG_edit_host_configuration(self):
        """ NEG_edit_host_configuration """
        host = API.hosts.get(config.MAIN_HOST_NAME)
        before = host.get_name()
        newName = before + '_'
        host.set_name(newName)
        self.assertRaises(errors.RequestError, host.update)

    @istest
    @resolve_permissions
    def bv_POSITIVE_edit_host_configuration(self):
        """ POSITIVE_edit_host_configuration """
        host = API.hosts.get(config.MAIN_HOST_NAME)
        before = host.get_name()
        newName = before + '_'
        host.set_name(newName)
        host.update()

        host = API.hosts.get(newName)
        assert host is not None, "Failed to update Host name"
        now = host.get_name()
        assert before != now, "Failed to update Host name"
        LOGGER.info("Host '%s' configuration success" % (config.MAIN_HOST_NAME))
        config.MAIN_HOST_NAME = now

    # TODO
    def bw_POSITIVE_configure_host_network(self):
        """ POSITIVE_configure_host_network """
        pass

    # TODO
    def bx_NEG_configure_host_network(self):
        """ NEG_configure_host_network """
        pass

    @istest
    @resolve_permissions
    def by_NEG_maniputlate_host(self):
        """ NEG_maniputlate_host """
        self.assertRaises(errors.RequestError, common.activeDeactiveHost,
                config.MAIN_HOST_NAME)

    @istest
    @resolve_permissions
    def bz_POSITIVE_maniputlate_host(self):
        """ POSITIVE_maniputlate_host """
        common.activeDeactiveHost(config.MAIN_HOST_NAME)

    @istest
    @resolve_permissions
    def cc_NEG_create_disk(self):
        """ NEG_create_disk """
        self.assertRaises(errors.RequestError, common.createDisk, TMP_DISK_NAME)

    @istest
    @resolve_permissions
    def cd_POSITIVE_create_disk(self):
        """ POSITIVE_create_disk """
        common.createDisk(TMP_DISK_NAME)

    @istest
    @resolve_permissions
    def ce_POSITIVE_attach_disk(self):
        """ POSITIVE_attach_disk """
        common.attachDiskToVm(DISK_NAME, VM_NAME)

    @istest
    @resolve_permissions
    def cf_NEG_attach_disk(self):
        """ NEG_attach_disk """
        self.assertRaises(errors.RequestError, common.attachDiskToVm, DISK_NAME,
                VM_NAME)

    @istest
    @resolve_permissions
    def cg_POSITIVE_edit_disk_properties(self):
        """ POSITIVE_edit_disk_properties """
        common.editDiskProperties(DISK_NAME)

    @istest
    @resolve_permissions
    def ch_NEG_edit_disk_properties(self):
        """ NEG_edit_disk_properties """
        self.assertRaises(errors.RequestError, common.editDiskProperties, DISK_NAME)

    # Not supported by API
    #@istest
    #@resolve_permissions
    def ci_POSITIVE_configure_disk_storage(self):
        """ POSITIVE_configure_disk_storage """
        pass

    # Not supported by API
    #@istest
    #@resolve_permissions
    def cj_NEG_configure_disk_storage(self):
        """ NEG_configure_disk_storage """
        pass

    @resolve_permissions
    def ck_NEG_delete_disk(self):
        """ NEG_delete_disk """
        self.assertRaises(errors.RequestError, common.deleteDisk, DISK_NAME)

    @resolve_permissions
    def cl_POSITIVE_delete_disk(self):
        """ POSITIVE_delete_disk """
        common.deleteDisk(DISK_NAME)

    @istest
    @resolve_permissions
    def cm_NEG_create_cluster(self):
        """ NEG_create_cluster """
        self.assertRaises(errors.RequestError, common.createCluster,
                        TMP_CLUSTER_NAME, config.MAIN_DC_NAME)

    @istest
    @resolve_permissions
    def cn_POSITIVE_create_cluster(self):
        """ POSITIVE_create_cluster """
        common.createCluster(TMP_CLUSTER_NAME, config.MAIN_DC_NAME)

    @istest
    @resolve_permissions
    def co_POSITIVE_edit_cluster_configuration(self):
        """ POSITIVE_edit_cluster_configuration """
        cluster = API.clusters.get(CLUSTER_NAME)

        before = cluster.get_cpu().get_id()
        if before == config.HOST_CPU_TYPE:
            after = CLUSTER_CPU_TYPE
        else:
            after = config.HOST_CPU_TYPE

        cpu = params.CPU(id=after)
        cluster.set_cpu(cpu)
        cluster.update()

        cluster = API.clusters.get(CLUSTER_NAME)
        now = cluster.get_cpu().get_id()
        assert before != now, "Failed to update cluster configuration"
        LOGGER.info("Cluster '%s' editing success" % (CLUSTER_NAME))

    @istest
    @resolve_permissions
    def cp_NEG_edit_cluster_configuration(self):
        """ NEG_edit_cluster_configuration """
        cluster = API.clusters.get(CLUSTER_NAME)

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
    def cq_NEG_configure_cluster_network(self):
        """ NEG_configure_cluster_network """
        cluster = API.clusters.get(CLUSTER_NAME)

        net = params.Network(name=config.NETWORK_NAME)
        self.assertRaises(errors.RequestError, cluster.networks.add, net)

    # FIXME
    @istest
    @resolve_permissions
    def cr_POSITIVE_configure_cluster_network(self):
        """ POSITIVE_configure_cluster_network """
        cluster = API.clusters.get(CLUSTER_NAME)

        net = params.Network(name=config.NETWORK_NAME)
        nets = cluster.networks.add(net)

        net = cluster.networks.get(name=config.NETWORK_NAME)
        assert net is not None
        LOGGER.info("Configuring cluster '%s' success" % CLUSTER_NAME)

    @istest
    @resolve_permissions
    def cs_NEG_delete_cluster(self):
        """ NEG_delete_cluster """
        self.assertRaises(errors.RequestError, common.removeCluster,
                    CLUSTER_NAME)

    @istest
    @resolve_permissions
    def ct_POSITIVE_delete_cluster(self):
        """ POSITIVE_delete_cluster """
        common.removeCluster(CLUSTER_NAME)

    @istest
    @resolve_permissions
    def cu_NEG_manipulate_roles(self):
        """ NEG_manipulate_roles """
        self.assertRaises(errors.RequestError, common.addRole, ROLE_NAME,
                USER_ROLE_PERMITS)

    @istest
    @resolve_permissions
    def cv_POSITIVE_manipulate_roles(self):
        """ POSITIVE_manipulate_roles """
        common.addRole(ROLE_NAME, USER_ROLE_PERMITS)

    @istest
    @resolve_permissions
    def cw_NEG_manipulate_users(self):
        """ NEG_manipulate_users """
        self.assertRaises(errors.RequestError, common.addUser,
                        userName=config.USER_NAME2, domainName=config.USER_DOMAIN)

    @istest
    @resolve_permissions
    def cx_POSITIVE_manipulate_users(self):
        """ POSITIVE_manipulate_users """
        common.addUser(userName=config.USER_NAME2, domainName=config.USER_DOMAIN)

    @istest
    @resolve_permissions
    def cx_NEG_create_storage_domain(self):
        """ NEG_create_storage_domain """
        self.assertRaises(errors.RequestError, common.createNfsStorage,
                    config.ALT_STORAGE_NAME, storageType='data',
                    address=config.ALT_STORAGE_ADDRESS,
                    path=config.ALT_STORAGE_PATH)

    @istest
    @resolve_permissions
    def cy_POSITIVE_create_storage_domain(self):
        """ POSITIVE_create_storage_domain """
        common.createNfsStorage(
            config.ALT_STORAGE_NAME, storageType='data',
            address=config.ALT_STORAGE_ADDRESS,
            path=config.ALT_STORAGE_PATH)

    @istest
    @resolve_permissions
    def cz_NEG_edit_storage_domain_configuration(self):
        """ NEG_edit_storage_domain_configuration """
        storage = API.storagedomains.get(config.MAIN_STORAGE_NAME)

        before = storage.get_name()
        newName = before + '_'
        storage.set_name(newName)
        self.assertRaises(errors.RequestError, storage.update)

    @istest
    @resolve_permissions
    def da_POSITIVE_edit_storage_domain_configuration(self):
        """ POSITIVE_edit_storage_domain_configuration """
        storage = API.storagedomains.get(config.MAIN_STORAGE_NAME)

        before = storage.get_name()
        newName = before + '_'
        storage.set_name(newName)
        storage.update()

        storage = API.storagedomains.get(config.MAIN_STORAGE_NAME)
        now = storage.get_name()
        assert before != now, "Failed to update storage name"
        LOGGER.info("Storage name '%s' editing success" % (config.MAIN_STORAGE_NAME))
        config.MAIN_STORAGE_NAME = config.MAIN_STORAGE_NAME + '_'

    @istest
    @resolve_permissions
    def db_NEG_manipulate_storage_domain(self):
        """ NEG_manipulate_storage_domain """
        self.assertRaises(errors.RequestError, common.detachAttachSD)

    @istest
    @resolve_permissions
    def dc_POSITIVE_manipulate_storage_domain(self):
        """ POSITIVE_manipulate_storage_domain """
        common.detachAttachSD()

    # TODO
    def df_NEG_port_mirroring(self):
        """ NEG_port_mirroring """
        pass

    # TODO
    def dg_POSITIVE_port_mirroring(self):
        """ POSITIVE_port_mirroring """
        vm = API.vms.get(VM_NAME)
        param = params.NIC(name=config.HOST_NIC,
                           network=params.Network(name=config.NETWORK_NAME),
                           interface='virtio')
        vm.nics.add(param)

    @istest
    @resolve_permissions
    def dd_NEG_delete_storage_domain(self):
        """ NEG_delete_storage_domain """
        if 'create_storage_domain' in self.perms:
            self.assertRaises(errors.RequestError, common.removeNonMasterStorage,
                    config.ALT_STORAGE_NAME)
        else:
            self.assertRaises(errors.RequestError, common.removeNonMasterStorage,
                    config.MAIN_STORAGE_NAME)

    @istest
    @resolve_permissions
    def de_POSITIVE_delete_storage_domain(self):
        """ NEG_delete_storage_domain """
        if 'create_storage_domain' in self.perms:
            common.removeNonMasterStorage(config.ALT_STORAGE_NAME)
        else:
            common.removeNonMasterStorage(config.MAIN_STORAGE_NAME)


    @istest
    @resolve_permissions
    def zc_NEG_move_vm(self):
        """ NEG_move_vm """
        filterHeader = common.getFilterHeader()

        common.loginAsAdmin()
        common.createNfsStorage(
            storageName=config.ALT_STORAGE_NAME, storageType='data',
            address=config.ALT_STORAGE_ADDRESS,
            path=config.ALT_STORAGE_PATH,
            datacenter=config.MAIN_DC_NAME,
            host=config.MAIN_HOST_NAME)
        common.attachActivateStorage(config.ALT_STORAGE_NAME, isMaster=False)

        common.loginAsUser(filter_=filterHeader)

        self.assertRaises(errors.RequestError, common.moveVm, VM_NAME)

    @istest
    @resolve_permissions
    def zd_POSITIVE_move_vm(self):
        """ POSITIVE_move_vm """
        filterHeader = common.getFilterHeader()

        common.loginAsAdmin()
        common.createNfsStorage(
            storageName=config.ALT_STORAGE_NAME, storageType='data',
            address=config.ALT_STORAGE_ADDRESS,
            path=config.ALT_STORAGE_PATH,
            datacenter=config.MAIN_DC_NAME,
            host=config.MAIN_HOST_NAME)
        common.attachActivateStorage(config.ALT_STORAGE_NAME, isMaster=False)

        common.loginAsUser(filter_=filterHeader)

        common.moveVm(VM_NAME)

    # Remove after create_host OK
    #@istest
    @resolve_permissions
    def za_NEG_migrate_vm(self):
        """ NEG_migrate_vm """
        filterHeader = common.getFilterHeader()

        common.loginAsAdmin()
        common.createNfsStorage(
            storageName=config.ALT_STORAGE_NAME, storageType='data',
            address=config.ALT_STORAGE_ADDRESS,
            path=config.ALT_STORAGE_PATH,
            datacenter=config.MAIN_DC_NAME,
            host=config.MAIN_HOST_NAME)
        common.attachActivateStorage(config.ALT_STORAGE_NAME, isMaster=False)

        common.loginAsUser(filter_=filterHeader)

        self.assertRaises(errors.RequestError, common.migrateVm, VM_NAME)

    # Remove after create_host OK
    #@istest
    @resolve_permissions
    def zb_POSITIVE_migrate_vm(self):
        """ POSITIVE_migrate_vm """
        filterHeader = common.getFilterHeader()

        common.loginAsAdmin()
        common.createNfsStorage(
            storageName=config.ALT_STORAGE_NAME, storageType='data',
            address=config.ALT_STORAGE_ADDRESS,
            path=config.ALT_STORAGE_PATH,
            datacenter=config.MAIN_DC_NAME,
            host=config.MAIN_HOST_NAME)
        common.attachActivateStorage(config.ALT_STORAGE_NAME, isMaster=False)

        common.loginAsUser(filter_=filterHeader)

        common.migrateVm(VM_NAME)

    # Only for while comment this, because of speed of tests
    #@istest
    @resolve_permissions
    def zy_NEG_delete_host(self):
        """ NEG_delete_host """
        if 'create_host' in self.perms:
            self.assertRaises(errors.RequestError, common.removeHost,
                    hostName=config.ALT_HOST_ADDRESS)
        else:
            self.assertRaises(errors.RequestError, common.removeHost,
                    hostName=config.MAIN_HOST_NAME)

    #@istest
    @resolve_permissions
    def zz_POSITIVE_delete_host(self):
        """ POSITIVE_delete_host """
        if 'create_host' in self.perms:
            common.removeHost(hostName=config.ALT_HOST_ADDRESS)
        else:
            common.removeHost(hostName=config.MAIN_HOST_NAME)


    ## TODO:  Not able in api?'create_storage_pool', 'delete_storage_pool', 'edit_storage_pool_configuration',
    ## 'configure_storage_pool_network', 'configure_rhevm,
    ## Wait for better documentation
    ## 'configure_quota', 'consume_quota', 'create_gluster_volume', 'manipulate_gluster_volume',
    ## 'delete_gluster_volume', 'login', 'change_vm_custom_properties'


##################### ROLE TESTS ##############################################
class UserVmManagerActionsTests(UserActionsTests):
    __test__ = False

    @classmethod
    def setUpClass(self):
        self.role = 'UserVmManager'
        self.perms = hasPermissions(self.role)
        common.createVm(VM_NAME)
        common.addRoleToUser(self.role)
        #common.givePermissionToDc(config.MAIN_DC_NAME, self.role)
        common.givePermissionToVm(VM_NAME, self.role)

        common.createHost(CLUSTER_NAME)
        common.loginAsUser()

    @classmethod
    def tearDownClass(self):
        common.loginAsAdmin()
        common.removeVm(VM_NAME)

        common.removeMasterStorage(storageName=config.ALT_STORAGE_NAME,
                        datacenter=config.MAIN_DC_NAME,
                        host=config.ALT_HOST_ADDRESS)
        common.removeHost()
        common.removeAllPermissionFromDc(config.MAIN_DC_NAME)


class PowerUserRoleActionsTests(UserActionsTests):
    __test__ = False

    @classmethod
    def setUpClass(self):
        self.role = 'PowerUserRole'
        self.perms = hasPermissions(self.role)
        common.createVm(VM_NAME)
        common.addRoleToUser(self.role)
        #common.givePermissionToDc(config.MAIN_DC_NAME, self.role)

        common.createHost(CLUSTER_NAME)

        common.loginAsUser()

    @classmethod
    def tearDownClass(self):
        common.loginAsAdmin()
        common.removeVm(VM_NAME)

        common.removeMasterStorage(storageName=config.ALT_STORAGE_NAME,
                        datacenter=config.MAIN_DC_NAME,
                        host=config.ALT_HOST_ADDRESS)
        common.removeHost()
        common.removeAllPermissionFromDc(config.MAIN_DC_NAME)


class UserRoleActionsTests(UserActionsTests):
    __test__ = False

    @classmethod
    def setUpClass(self):
        self.role = 'UserRole'
        self.filter_ = True
        self.perms = hasPermissions(self.role)
        super(UserRoleActionsTests, self).setUpClass()


class VmCreatorActionsTests(UserActionsTests):
    __test__ = False

    @classmethod
    def setUpClass(self):
        self.role = 'VmCreator'
        self.filter_ = True
        self.perms = hasPermissions(self.role)
        super(VmCreatorActionsTests, self).setUpClass()


class TemplateCreatorActionsTests(UserActionsTests):
    __test__ = False

    @classmethod
    def setUpClass(self):
        self.role = 'TemplateCreator'
        self.filter_ = True
        self.perms = hasPermissions(self.role)
        super(TemplateCreatorActionsTests, self).setUpClass()


class SuperUserActionsTests(UserActionsTests):
    __test__ = False

    @classmethod
    def setUpClass(self):
        self.role = 'SuperUser'
        self.perms = hasPermissions(self.role)
        common.createVm(VM_NAME)
        common.loginAsAdmin()
        # no need to give him permissions to specific objects


class TemplateAdminActionsTests(UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = 'TemplateAdmin'
        self.filter_ = False
        self.perms = hasPermissions(self.role)
        super(TemplateAdminActionsTests, self).setUpClass()


class TemplateOwnerActionsTests(UserActionsTests):
    __test__ = False  # Wait for BZ 857018

    @classmethod
    def setUpClass(self):
        self.role = 'TemplateOwner'
        self.filter_ = True
        self.perms = hasPermissions(self.role)
        super(TemplateOwnerActionsTests, self).setUpClass()


class VmPoolAdminActionsTests(UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = 'VmPoolAdmin'
        self.filter_ = False
        self.perms = hasPermissions(self.role)
        super(VmPoolAdminActionsTests, self).setUpClass()


class HostAdminActionsTests(UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = 'HostAdmin'
        self.filter_ = False
        self.perms = hasPermissions(self.role)
        super(HostAdminActionsTests, self).setUpClass()


class StorageAdminActionsTests(UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = 'StorageAdmin'
        self.filter_ = False
        self.perms = hasPermissions(self.role)
        super(StorageAdminActionsTests, self).setUpClass()

class DataCenterAdminActionsTests(UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = 'DataCenterAdmin'
        self.filter_ = False
        self.perms = hasPermissions(self.role)
        super(DataCenterAdminActionsTests, self).setUpClass()


class ClusterAdminActionsTests(UserActionsTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = 'ClusterAdmin'
        self.filter_ = False
        self.perms = hasPermissions(self.role)

        super(ClusterAdminActionsTests, self).setUpClass()

###############################################################################
def hasPermissions(role):
    """ Get a list of permissions the user role has.

    :param role:    (string) oVirt user role
    :return:        (list of strings) permissions the role should have
    """
    if role == 'SuperUser':
        return PERMISSIONS
    else:
        return common.getRolePermissions(role)


def doesNotHavePermissions(role):
    """ Get a list of permissions the user role shouldn't have.

    :param role:    (string) oVirt user role
    :return:        (list of strings) permissions the role doesn't have. Should
                    be equal to the 'PERMISSIONS' constant with substracted
                    'permission(role)' list
    """
    permissions = hasPermissions(role)
    return [p for p in PERMISSIONS if p not in permissions]
