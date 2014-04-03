#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Red Hat, Inc.
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

"""
Quota Test
Check different cases for quota limitations in None, Audit and Enforce mode
Include CRUD tests, different limitations of storage, memory and vcpu tests
"""
__test__ = True

import logging
import config

from common import DB
from nose.tools import istest

# rhevm api
from utilities.rhevm_tools.base import Setup
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.high_level.disks import delete_disks
from art.rhevm_api.tests_lib.low_level import templates
from art.unittest_lib import BaseTestCase as TestCase

# raut quota
from raut.tests.webadmin.quota import QuotaTest

# rhevm_utils general exception
from utilities.errors import GeneralException

# BZ, TCMS plugins
try:
    from art.test_handler.tools import bz
except ImportError:
    # noinspection PyUnusedLocal
    def bz(*ids):
        def decorator(func):
            return func
        return decorator

try:
    from art.test_handler.tools import tcms
except ImportError:
    # noinspection PyUnusedLocal
    def tcms(*ids):
        def decorator(func):
            return func
        return decorator

LOGGER = logging.getLogger(__name__)

# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
EXPORT_NAME = 'export_domain'  # EXPORT domain
VM_NAME = 'quota__vm'
TMP_VM_NAME = 'quota__tpm_vm'
DISK_NAME = 'quota_disk'
TEMPLATE_NAME = 'quota__template'
TMP_TEMPLATE_NAME = 'quota__template_tmp'
VM_SNAPSHOT = 'quota_vm__snapshot'
VM_POOL_NAME = 'quota__vm_pool'
CLUSTER_NAME = 'quota__cluster'
QUOTA_NONE = 0
QUOTA_AUDIT = 1
QUOTA_ENFORCED = 2
QUOTA_NAME = 'quota_1'
QUOTA_DESC = 'quota_1_desc'
QUOTA2_NAME = 'quota_2'
QUOTA2_DESC = 'quota_2_desc'
QUOTA3_NAME = 'quota_3'
QUOTA3_DESC = 'quota_3_desc'
TCMS_PLAN_ID = 8029
MB = 1024 * 1024
GB = 1024 * MB

test = QuotaTest()  # raut object to CRUD quota
db = DB(None)  # db instance to access db to check resources


def setup_module():
    # Setup db
    db.setup = Setup(config.OVIRT_ADDRESS, config.OVIRT_ROOT,
                     config.OVIRT_ROOT_PASSWORD, conf=config.DB_NAME)

    # Create quota
    test.set_up()
    test.create_quota(config.MAIN_DC_NAME, QUOTA_NAME)
    test.tear_down()


def teardown_module():
    test.set_up()
    test.remove_quota(config.MAIN_DC_NAME, QUOTA_NAME)
    test.tear_down()


class QuotaTestCRUD(TestCase):
    """
    This unittest class tests CRUD operation via selenium.
    """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        """ Create and setup resources for tests """
        test.set_up()

    @classmethod
    def tearDownClass(cls):
        """ Delete/release resources of test """
        test.edit_quota(config.MAIN_DC_NAME, QUOTA_NAME,
                        mem_limit=0, vcpu_limit=0, storage_limit=0)
        test.tear_down()

    @istest
    @tcms(TCMS_PLAN_ID, 231136)
    def a_create_quota(self):
        """ Create Quota with some limits """
        test.create_quota(config.MAIN_DC_NAME, QUOTA2_NAME,
                          description=QUOTA_DESC,
                          mem_limit=1024, vcpu_limit=1,
                          storage_limit=10)
        self.assertTrue(db.check_quota_exists(QUOTA2_NAME))

    @istest
    @tcms(TCMS_PLAN_ID, 231138)
    def b_edit_quota(self):
        """ Edit Quota """
        test.edit_quota(config.MAIN_DC_NAME, QUOTA2_NAME,
                        description=QUOTA_DESC,
                        mem_limit=2048, vcpu_limit=2, storage_limit=20)
        self.assertTrue(db.check_quota_limits(QUOTA2_NAME, mem_size_mb=2048,
                                              virtual_cpu=2,
                                              storage_size_gb=20))
        # TODO: check properties (thresholds, grace percentage, description)

    @istest
    @tcms(TCMS_PLAN_ID, 231141)
    def c_copy_quota(self):
        """ Copy Quota """
        test.copy_quota(config.MAIN_DC_NAME, QUOTA_NAME, name=QUOTA3_NAME,
                        description=QUOTA3_DESC)
        self.assertTrue(db.check_quota_exists(QUOTA3_NAME))

    @istest
    @tcms(TCMS_PLAN_ID, 231139)
    def d_delete_quota(self):
        """ Delete Quota """
        #TODO: Check if quota can be removed even when some object have
        test.remove_quota(config.MAIN_DC_NAME, QUOTA2_NAME)
        self.assertFalse(db.check_quota_exists(QUOTA2_NAME))
        test.remove_quota(config.MAIN_DC_NAME, QUOTA3_NAME)
        self.assertFalse(db.check_quota_exists(QUOTA3_NAME))


class QuotaTestMode(TestCase):
    """
    This unittest class tests quota enforced/audit mode.
    """
    __test__ = False
    positive = True

    @classmethod
    def setUpClass(cls):
        """ Create and setup resources for tests """
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        assert vms.createVm(True, VM_NAME, '',
                            cluster=config.MAIN_CLUSTER_NAME,
                            storageDomainName=config.MAIN_STORAGE_NAME,
                            size=10*GB, memory=512*MB, vm_quota=q_id,
                            disk_quota=q_id, nic=config.NIC,
                            network=config.cluster_network)

    @classmethod
    def tearDownClass(cls):
        """ Delete/release resources of test """
        assert vms.removeVm(True, VM_NAME)

    @istest
    @tcms('9428', '268989')
    def a_quota_memory_limit(self):
        """ Quota RAM limit """
        # Create VM with RAM 1024, quota level to 1024MB, try to run VM
        test.set_up()
        test.edit_quota(config.MAIN_DC_NAME, QUOTA_NAME,
                        mem_limit=1024, vcpu_limit=0, storage_limit=0)
        test.tear_down()
        self.assertTrue(vms.startVm(True, VM_NAME))
        self.assertTrue(vms.stopVm(True, VM_NAME))

    @istest
    @tcms('9428', '268990')
    def b_quota_memory_limit_in_grace(self):
        """ Quota RAM Limit in grace """
        # Create quota with 1024MB limit (Grace 120%)
        # Create vm with 1228 MB RAM, try to run it.
        self.assertTrue(vms.updateVm(True, VM_NAME, memory=1228*MB))
        self.assertTrue(vms.startVm(True, VM_NAME))
        self.assertTrue(vms.stopVm(True, VM_NAME))
        # TODO: check if warning event was generated

    @istest
    @tcms('9428', '268991')
    def c_quota_memory_limit_over_grace(self):
        """ Quota RAM Limit over grace """
        # Create quota with 1024MB limit (Grace 120%)
        # Create vm with 2048 MB RAM, try to run it.
        self.assertTrue(vms.updateVm(True, VM_NAME, memory=2*GB))
        self.assertTrue(vms.startVm(self.positive, VM_NAME))
        if self.positive:
            self.assertTrue(vms.stopVm(True, VM_NAME))
        self.assertTrue(vms.updateVm(True, VM_NAME, memory=GB))
        # TODO: check if warning event was generated

    @istest
    @tcms('9428', '268992')
    def d_quota_vcpu_limit(self):
        """ Quota vCPU limit """
        # Set vCPU to 1 from unlimited
        # set RAM to unlimited - same for RAM
        db.update_quota(QUOTA_NAME, grace_vds_group_percentage=100)
        test.set_up()
        test.edit_quota(config.MAIN_DC_NAME, QUOTA_NAME,
                        mem_limit=0, vcpu_limit=1, storage_limit=0)
        test.tear_down()
        self.assertTrue(vms.startVm(True, VM_NAME))
        self.assertTrue(vms.stopVm(True, VM_NAME))

    @istest
    @tcms('9428', '268993')
    def e_quota_vcpu_limit_in_grace(self):
        """ Quota vCPU limit in grace """
        self.assertTrue(vms.updateVm(True, VM_NAME, cpu_cores=2))
        self.assertTrue(vms.startVm(True, VM_NAME))
        self.assertTrue(vms.stopVm(True, VM_NAME))
        self.assertTrue(vms.updateVm(True, VM_NAME, cpu_cores=1))
        # TODO: check if warning event was generated

    @istest
    @tcms('9428', '268994')
    def f_quota_vcpu_limit_over_grace(self):
        """ Quota vCPU limit over grace """
        self.assertTrue(vms.updateVm(True, VM_NAME, cpu_cores=3))
        self.assertTrue(vms.startVm(self.positive, VM_NAME))
        if self.positive:
            self.assertTrue(vms.stopVm(True, VM_NAME))
        self.assertTrue(vms.updateVm(True, VM_NAME, cpu_cores=1))
        # TODO: check if warning event was generated

    @istest
    @tcms('9428', '268995')
    def g_quota_storage_limit(self):
        """ Quota storage limit """
        # Disable cluster quota
        db.update_quota(QUOTA_NAME, grace_vds_group_percentage=20)
        test.set_up()
        test.edit_quota(config.MAIN_DC_NAME, QUOTA_NAME,
                        mem_limit=0, vcpu_limit=0, storage_limit=20)
        test.tear_down()
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        self.assertTrue(disks.addDisk(True, alias=DISK_NAME,
                                      provisioned_size=10*GB,
                                      interface=config.DISK_INTERFACE,
                                      format=config.DISK_FORMAT,
                                      storagedomain=config.MAIN_STORAGE_NAME,
                                      quota=q_id))
        self.assertTrue(delete_disks([DISK_NAME]))

    @istest
    @tcms('9428', '268996')
    def h_quota_storage_limit_in_grace(self):
        """ Quota storage limit in grace """
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        self.assertTrue(disks.addDisk(True, alias=DISK_NAME,
                                      provisioned_size=14*GB,
                                      interface=config.DISK_INTERFACE,
                                      format=config.DISK_FORMAT,
                                      storagedomain=config.MAIN_STORAGE_NAME,
                                      quota=q_id))
        self.assertTrue(delete_disks([DISK_NAME]))
        # TODO: check if warning event was generated

    @istest
    @tcms('9428', '268997')
    def i_quota_storage_limit_over_grace(self):
        """ Quota storage limit over grace """
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        self.assertTrue(disks.addDisk(self.positive, alias=DISK_NAME,
                        provisioned_size=15*GB,
                        interface=config.DISK_INTERFACE,
                        format=config.DISK_FORMAT,
                        storagedomain=config.MAIN_STORAGE_NAME,
                        quota=q_id))
        if self.positive:
            self.assertTrue(delete_disks([DISK_NAME]))
        test.set_up()
        test.edit_quota(config.MAIN_DC_NAME, QUOTA_NAME,
                        mem_limit=0, vcpu_limit=0, storage_limit=0)
        test.tear_down()
        # TODO: check if warning event was generated

    @istest
    @tcms('9428', '268998')
    def j_delete_quota_in_use(self):
        """ Delete quota in use """
        test.set_up()
        self.assertRaises(GeneralException,
                          test.remove_quota, config.MAIN_DC_NAME, QUOTA_NAME)
        test.tear_down()


class QuotaTestEnforced(QuotaTestMode):
    """
    This unittest class tests quota Enforced mode.
    """
    __test__ = True

    positive = False

    # Create and setup resources for tests
    @classmethod
    def setUpClass(cls):
        db.set_dc_quota_mode(config.MAIN_DC_NAME, QUOTA_ENFORCED)
        super(QuotaTestEnforced, cls).setUpClass()


class QuotaTestAudit(QuotaTestMode):
    """
    This unittest class tests quota Audit mode.
    """
    __test__ = True

    positive = True

    # Create and setup resources for tests
    @classmethod
    def setUpClass(cls):
        db.set_dc_quota_mode(config.MAIN_DC_NAME, QUOTA_AUDIT)
        super(QuotaTestAudit, cls).setUpClass()


class QuotaTestObjectWithoutQuota(TestCase):
    """
    This class tests if object created in disabled mode can/can't
    be manipulated in audit/enforced mode(no quota assigned to objects)
    """
    __test__ = False

    positive = None
    mode = None

    @classmethod
    def setUpClass(cls):
        """ Create and setup resources for tests """
        db.set_dc_quota_mode(config.MAIN_DC_NAME, QUOTA_NONE)
        # Create vm with no quota
        assert vms.createVm(True, VM_NAME, '',
                            cluster=config.MAIN_CLUSTER_NAME,
                            storageDomainName=config.MAIN_STORAGE_NAME,
                            size=10*GB, memory=2*GB, nic=config.NIC,
                            network=config.cluster_network)
        # Create disk with no quota
        assert disks.addDisk(True, alias=DISK_NAME, provisioned_size=10*GB,
                             interface=config.DISK_INTERFACE,
                             format=config.DISK_FORMAT,
                             storagedomain=config.MAIN_STORAGE_NAME)
        assert disks.waitForDisksState(DISK_NAME)

        db.set_dc_quota_mode(config.MAIN_DC_NAME, cls.mode)

    @classmethod
    def tearDownClass(cls):
        """ Delete/release resources of test """
        assert vms.removeVm(True, VM_NAME)
        assert disks.deleteDisk(True, alias=DISK_NAME)
        assert disks.waitForDisksGone(True, DISK_NAME)

    @istest
    @tcms(TCMS_PLAN_ID, '236244')
    def update_vm(self):
        """ Update vm with quota enforce mode """
        LOGGER.info("Updating vm '%s' memory" % VM_NAME)
        self.assertTrue(vms.updateVm(self.positive, VM_NAME, memory=GB,
                                     memory_guaranteed=GB))
        if self.positive:
            self.assertTrue(vms.updateVm(self.positive, VM_NAME,
                                         memory=512*MB,
                                         memory_guaranteed=512*MB))

    @tcms(TCMS_PLAN_ID, '236240')
    @istest
    def run_vm(self):
        """ Run vm """
        # Add also case which tests, quota assigned only to vm not to disk
        LOGGER.info("Running vm '%s'" % VM_NAME)
        self.assertTrue(vms.startVm(self.positive, VM_NAME))
        if self.positive:
            self.assertTrue(vms.stopVm(True, VM_NAME))
            LOGGER.info("Stopping vm '%s'" % VM_NAME)

    @tcms(TCMS_PLAN_ID, '237011')
    @istest
    def create_snapshot(self):
        """ Create snapshot """
        # Add also case which tests, quota assigned only to disk not to vm
        LOGGER.info("Creating snapshot '%s'" % VM_SNAPSHOT)
        self.assertTrue(vms.addSnapshot(self.positive, VM_NAME, VM_SNAPSHOT))
        if self.positive:
            self.assertTrue(vms.removeSnapshot(True, VM_NAME, VM_SNAPSHOT))
            LOGGER.info("Removing snapshot '%s'" % VM_SNAPSHOT)

    @istest
    def create_template(self):
        """ Create template """
        # Template should be created in Enforced and in Audit
        # also when vm and vm disk has no quota assigned
        LOGGER.info("Creating template '%s'", TEMPLATE_NAME)
        self.assertTrue(
            templates.createTemplate(self.positive, vm=VM_NAME,
                                     name=TEMPLATE_NAME,
                                     cluster=config.MAIN_CLUSTER_NAME))
        if self.positive:
            self.assertTrue(templates.removeTemplate(True, TEMPLATE_NAME))

    # TODO: implement update_disk, move_disk and copy_disk, now no REST api
    # available


class QuotaTestEnforcedWithOutQuota(QuotaTestObjectWithoutQuota):
    """
    This unittest class tests quota Enforced mode.
    """
    __test__ = True

    mode = QUOTA_ENFORCED  # Enforced
    positive = False


class QuotaTestAuditWithOutQuota(QuotaTestObjectWithoutQuota):
    """
    This unittest class tests quota Audit mode.
    """
    __test__ = True

    mode = QUOTA_AUDIT
    positive = True


class QuotaConsumptionCalc(TestCase):
    """
    This class tests if quota consumption is calculated right,
    when user create/remove/run/stop/etc.. vms/disks/etc
    """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        """ Create and setup resources for tests """
        db.set_dc_quota_mode(config.MAIN_DC_NAME, QUOTA_ENFORCED)
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                     storageDomainName=config.MAIN_STORAGE_NAME, size=10*GB,
                     memory=GB, vm_quota=q_id, disk_quota=q_id,
                     nic=config.NIC, network=config.cluster_network)

    @classmethod
    def tearDownClass(cls):
        """ Delete/release resources of test """
        vms.removeVm(True, VM_NAME)

    @istest
    @tcms(TCMS_PLAN_ID, 236236)
    def remove_vm(self):
        """ Remove vm """
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        self.assertTrue(
            vms.createVm(True, TMP_VM_NAME, '',
                         cluster=config.MAIN_CLUSTER_NAME,
                         storageDomainName=config.MAIN_STORAGE_NAME,
                         size=10*GB, memory=2*GB, vm_quota=q_id,
                         disk_quota=q_id, nic=config.NIC,
                         network=config.cluster_network))
        self.assertTrue(db.check_global_consumption(QUOTA_NAME,
                                                    mem_size_mb_usage=0,
                                                    virtual_cpu_usage=0,
                                                    storage_size_gb_usage=20))
        self.assertTrue(vms.removeDisk(True, TMP_VM_NAME,
                                       TMP_VM_NAME + '_Disk1'))
        self.assertTrue(db.check_global_consumption(QUOTA_NAME,
                                                    mem_size_mb_usage=0,
                                                    virtual_cpu_usage=0,
                                                    storage_size_gb_usage=10))
        self.assertTrue(vms.removeVm(True, TMP_VM_NAME))

    @istest
    @tcms(TCMS_PLAN_ID, 236237)
    def remove_template(self):
        """ Remove template """
        self.assertTrue(templates.createTemplate(True, vm=VM_NAME,
                        name=TMP_TEMPLATE_NAME))
        self.assertTrue(db.check_global_consumption(QUOTA_NAME,
                                                    mem_size_mb_usage=0,
                                                    virtual_cpu_usage=0,
                                                    storage_size_gb_usage=20))
        self.assertTrue(templates.removeTemplate(True,
                                                 template=TMP_TEMPLATE_NAME))
        self.assertTrue(db.check_global_consumption(QUOTA_NAME,
                                                    mem_size_mb_usage=0,
                                                    virtual_cpu_usage=0,
                                                    storage_size_gb_usage=10))

    @istest
    @tcms(TCMS_PLAN_ID, 236238)
    def vm_basic_operations(self):
        """ Vm basic operations """
        db.check_global_consumption(QUOTA_NAME, mem_size_mb_usage=0,
                                    virtual_cpu_usage=0)
        self.assertTrue(vms.startVm(True, VM_NAME))
        self.assertTrue(db.check_global_consumption(QUOTA_NAME,
                                                    mem_size_mb_usage=1024,
                                                    virtual_cpu_usage=1))
        self.assertTrue(vms.waitForVmsStates(True, VM_NAME))
        self.assertTrue(db.check_global_consumption(QUOTA_NAME,
                                                    mem_size_mb_usage=1024,
                                                    virtual_cpu_usage=1))
        self.assertTrue(vms.suspendVm(True, VM_NAME))
        self.assertTrue(db.check_global_consumption(QUOTA_NAME,
                                                    mem_size_mb_usage=0,
                                                    virtual_cpu_usage=0))
        self.assertTrue(vms.startVm(True, VM_NAME, vms.ENUMS['vm_state_up']))
        self.assertTrue(db.check_global_consumption(QUOTA_NAME,
                                                    mem_size_mb_usage=1024,
                                                    virtual_cpu_usage=1))
        self.assertTrue(vms.stopVm(True, VM_NAME))
        self.assertTrue(db.check_global_consumption(QUOTA_NAME,
                                                    mem_size_mb_usage=0,
                                                    virtual_cpu_usage=0))

    @istest
    @tcms(TCMS_PLAN_ID, 236240)
    def run_vm_once(self):
        """ Run vm once """
        self.assertTrue(vms.runVmOnce(True, VM_NAME))
        self.assertTrue(db.check_global_consumption(QUOTA_NAME,
                                                    mem_size_mb_usage=1024,
                                                    virtual_cpu_usage=1))
        self.assertTrue(vms.stopVm(True, VM_NAME))

    # TODO: Assign quota to disks, check if disk is counted

# TODO: class ImportExport Negative positive
# TODO: MLA+Quota
