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

__test__ = True

import logging
import config
import unittest2 as unittest

from common import DB
from nose.tools import istest
from functools import wraps

# rhevm api
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import templates

# raut quota
from raut.tests.webadmin.quota import QuotaTest

# rhevm_utils general exception
from utilities.errors import GeneralException

# BZ, TCMS plugins
try:
    from art.test_handler.tools import bz
except ImportError:
    def bz(*ids):
        def decorator(func):
            return func
        return decorator

try:
    from art.test_handler.tools import tcms
except ImportError:
    def tcms(*ids):
        def decorator(func):
            return func
        return decorator

LOGGER  = logging.getLogger(__name__)

# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
EXPORT_NAME = 'user_actions__export'  # EXPORT domain
VM_NAME = 'quota__vm'
TMP_VM_NAME = 'quota__tpm_vm'
DISK_NAME = 'quota_disk'
TEMPLATE_NAME = 'quota__template'
TMP_TEMPLATE_NAME = 'quota__template_tmp'
VM_SNAPSHOT = 'quota_vm__snapshot'
VM_POOL_NAME = 'quota__vm_pool'
CLUSTER_NAME = 'quota__cluster'
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

def setUpModule():
    # Setup db
    from utilities.rhevm_tools.base import Setup
    db.setup = Setup(config.OVIRT_ADDRESS, config.OVIRT_ROOT,
            config.OVIRT_ROOT_PASSWORD, conf=config.DB_NAME)

    # Create quota
    test.set_up()
    test.create_quota(config.MAIN_DC_NAME, QUOTA_NAME)
    test.tear_down()

    # Add Export domain
    storagedomains.addStorageDomain(True,
                type=vms.ENUMS['storage_dom_type_export'],
                storage_type=vms.ENUMS['storage_type_nfs'],
                host=config.MAIN_HOST_NAME,
                name=EXPORT_NAME,
                address=config.EXPORT_ADDRESS,
                path=config.EXPORT_PATH)
    storagedomains.attachStorageDomain(True, config.MAIN_DC_NAME,
            EXPORT_NAME)
    storagedomains.activateStorageDomain(True,
            config.MAIN_DC_NAME, EXPORT_NAME)

    # Add nfs data domain
    storagedomains.addStorageDomain(True,
            type=vms.ENUMS['storage_dom_type_data'],
            storage_type=vms.ENUMS['storage_type_nfs'],
            host=config.MAIN_HOST_NAME,
            name=config.ALT1_STORAGE_NAME,
            address=config.ALT1_STORAGE_ADDRESS,
            path=config.ALT1_STORAGE_PATH)
    storagedomains.attachStorageDomain(True, config.MAIN_DC_NAME,
            config.ALT1_STORAGE_NAME)
    storagedomains.activateStorageDomain(True,
            config.MAIN_DC_NAME, config.ALT1_STORAGE_NAME)

def tearDownModule():
    test.set_up()
    test.remove_quota(config.MAIN_DC_NAME, QUOTA_NAME)
    test.tear_down()

    # Delete export domain
    storagedomains.deactivateStorageDomain(True, config.MAIN_DC_NAME,
            EXPORT_NAME)
    storagedomains.detachStorageDomain(True, config.MAIN_DC_NAME,
            EXPORT_NAME)
    storagedomains.removeStorageDomain(True, EXPORT_NAME,
            config.MAIN_HOST_NAME, format='true')

    # delete nfs data domain
    storagedomains.deactivateStorageDomain(True, config.MAIN_DC_NAME,
            config.ALT1_STORAGE_NAME)
    storagedomains.detachStorageDomain(True, config.MAIN_DC_NAME,
            config.ALT1_STORAGE_NAME)
    storagedomains.removeStorageDomain(True, config.ALT1_STORAGE_NAME,
            config.MAIN_HOST_NAME, format='true')

class QuotaTestCRUD(unittest.TestCase):
    '''
    This unittest class tests CRUD operation via selenium.
    '''
    __test__ = True

    @classmethod
    def setUpClass(cls): # Create and setup resources for tests
        test.set_up()

    @classmethod
    def tearDownClass(cls): # Delete/release resources of test
        test.edit_quota(config.MAIN_DC_NAME, QUOTA_NAME,
                mem_limit=0, vcpu_limit=0, storage_limit=0)
        test.tear_down()

    @istest
    @tcms(TCMS_PLAN_ID, 231136)
    def a_createQuota(self):
        """ Create Quota """
        # Try to create quota with some limits.
        test.create_quota(config.MAIN_DC_NAME, QUOTA2_NAME,
                description=QUOTA_DESC, mem_limit=1024, vcpu_limit=1,
                storage_limit=10)
        assert db.checkQuotaExists(QUOTA2_NAME)

    @istest
    @tcms(TCMS_PLAN_ID, 231138)
    def b_editQuota(self):
        """ Edit Quota """
        # Try to edit creted quot
        test.edit_quota(config.MAIN_DC_NAME, QUOTA2_NAME, description=QUOTA_DESC,
                mem_limit=2048, vcpu_limit=2, storage_limit=20)
        db.checkQuotaLimits(QUOTA2_NAME, mem_size_mb=2048, virtual_cpu=2,
                storage_size_gb=20)
        # TODO: check properties (treshold,grace percentage, description)

    @istest
    @tcms(TCMS_PLAN_ID, 231141)
    def c_copyQuota(self):
        """ Copy Quota """
        # Try to copy Quota
        test.copy_quota(config.MAIN_DC_NAME, QUOTA_NAME, name=QUOTA3_NAME,
                description=QUOTA3_DESC)
        assert db.checkQuotaExists(QUOTA3_NAME)

    @istest
    @tcms(TCMS_PLAN_ID, 231139)
    def d_deleteQuota(self):
        """ Delete Quota """
        #TODO: Check if quota can be removed even when some object have
        # quota assigned, but DC is in Disabled mode
        test.remove_quota(config.MAIN_DC_NAME, QUOTA2_NAME)
        assert not db.checkQuotaExists(QUOTA2_NAME)
        test.remove_quota(config.MAIN_DC_NAME, QUOTA3_NAME)
        assert not db.checkQuotaExists(QUOTA3_NAME)

class QuotaTestMode(unittest.TestCase):
    '''
    This unittest class tests quota enforced/audit mode.
    '''
    __test__ = False

    @classmethod
    def setUpClass(cls): # Create and setup resources for tests
        q_id = db.getQuotaIdByName(QUOTA_NAME)
        assert vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                storageDomainName=config.MAIN_STORAGE_NAME, size=10*GB,
                memory=512*MB, vm_quota=q_id, disk_quota=q_id)
        test.set_up()

    @classmethod
    def tearDownClass(cls): # Delete/release resources of test
        assert vms.removeVm(True, VM_NAME)
        test.tear_down()

    @istest
    def a_quotaRAMLimit(self):
        """ Quota RAM limit """
        # Create VM with RAM 1024, quota level to 1024MB, try to run VM
        test.edit_quota(config.MAIN_DC_NAME, QUOTA_NAME,
                mem_limit=1024, vcpu_limit=0, storage_limit=0)
        assert vms.startVm(True, VM_NAME)
        assert vms.stopVm(True, VM_NAME)

    @istest
    def b_quotaRAMLimitInGrace(self):
        """ Quota RAM Limit in grace """
        # Create quota with 1024MB limit (Grace 120%)
        # Create vm with 1228 MB RAM, try to run it.
        assert vms.updateVm(True, VM_NAME, memory=1228*MB)
        assert vms.startVm(True, VM_NAME)
        assert vms.stopVm(True, VM_NAME)
        # TODO: check if warning event was generated

    @istest
    def c_quotaRAMLimitOverGrace(self):
        """ Quota RAM Limit over grace """
        # Create quota with 1024MB limit (Grace 120%)
        # Create vm with 2048 MB RAM, try to run it.
        assert vms.updateVm(True, VM_NAME, memory=2*GB)
        assert vms.startVm(self.possitive, VM_NAME)
        if self.possitive:
            assert vms.stopVm(True, VM_NAME)
        assert vms.updateVm(True, VM_NAME, memory=GB)
        # TODO: check if warning event was generated

    @istest
    def d_quotavCPULimit(self):
        """ Quota vCPU limit """
        # Set vCPU to 1 from unlimited
        # set RAM to unlimited - same for RAM
        test.edit_quota(config.MAIN_DC_NAME, QUOTA_NAME,
                mem_limit=0, vcpu_limit=1, storage_limit=0)
        db.updateQuota(QUOTA_NAME, grace_vds_group_percentage=100)
        assert vms.startVm(True, VM_NAME)
        assert vms.stopVm(True, VM_NAME)

    @istest
    def e_quotavCPULimitInGrace(self):
        """ Quota vCPU limit in grace """
        assert vms.updateVm(True, VM_NAME, cpu_cores=2)
        assert vms.startVm(True, VM_NAME)
        assert vms.stopVm(True, VM_NAME)
        assert vms.updateVm(True, VM_NAME, cpu_cores=1)
        # TODO: check if warning event was generated

    @istest
    def f_quotavCPULimitOverGrace(self):
        """ Quota vCPU limit over grace """
        assert vms.updateVm(True, VM_NAME, cpu_cores=3)
        assert vms.startVm(self.possitive, VM_NAME)
        if self.possitive:
            assert vms.stopVm(True, VM_NAME)
        assert vms.updateVm(True, VM_NAME, cpu_cores=1)
        db.updateQuota(QUOTA_NAME, grace_vds_group_percentage=20)
        # TODO: check if warning event was generated

    @istest
    def g_quotaStorageLimit(self):
        """ Quota storage limit """
        # Disable cluster quota
        test.edit_quota(config.MAIN_DC_NAME, QUOTA_NAME,
                mem_limit=0, vcpu_limit=0, storage_limit=20)
        q_id = db.getQuotaIdByName(QUOTA_NAME)
        assert disks.addDisk(True, alias=DISK_NAME, provisioned_size=10*GB,
                      interface='virtio', format='cow',
                      storagedomain=config.MAIN_STORAGE_NAME,
                      quota=q_id)
        disks.waitForDisksState(DISK_NAME)
        assert disks.deleteDisk(True, alias=DISK_NAME)
        disks.waitForDisksGone(True, DISK_NAME)

    @istest
    def h_quotaStorageLimitInGrace(self):
        """ Quota storage limit in grace """
        q_id = db.getQuotaIdByName(QUOTA_NAME)
        assert disks.addDisk(True, alias=DISK_NAME, provisioned_size=14*GB,
                      interface='virtio', format='cow',
                      storagedomain=config.MAIN_STORAGE_NAME,
                      quota=q_id)
        disks.waitForDisksState(DISK_NAME)
        assert disks.deleteDisk(True, alias=DISK_NAME)
        disks.waitForDisksGone(True, DISK_NAME)
        # TODO: check if warning event was generated

    @istest
    def i_quotaStorageLimitOverGrace(self):
        """ Quota storage limit over grace """
        q_id = db.getQuotaIdByName(QUOTA_NAME)
        assert disks.addDisk(self.possitive, alias=DISK_NAME, provisioned_size=15*GB,
                      interface='virtio', format='cow',
                      storagedomain=config.MAIN_STORAGE_NAME,
                      quota=q_id)
        if self.possitive:
            disks.waitForDisksState(DISK_NAME)
            assert disks.deleteDisk(True, alias=DISK_NAME)
            disks.waitForDisksGone(True, DISK_NAME)
        test.edit_quota(config.MAIN_DC_NAME, QUOTA_NAME,
                mem_limit=0, vcpu_limit=0, storage_limit=0)
        # TODO: check if warning event was generated

    @istest
    def j_deleteQuotaInUse(self):
        """ Delete quota in use """
        self.assertRaises(GeneralException,
                test.remove_quota, config.MAIN_DC_NAME, QUOTA_NAME)
        test.tear_down()
        test.set_up()

class QuotaTestEnforced(QuotaTestMode):
    '''
    This unittest class tests quota Enforced mode.
    '''
    __test__ = True

    possitive = False

    @classmethod
    def setUpClass(self): # Create and setup resources for tests
        db.setDCQuotaMode(config.MAIN_DC_NAME, 2)
        super(QuotaTestEnforced, self).setUpClass()

class QuotaTestAudit(QuotaTestMode):
    '''
    This unittest class tests quota Audit mode.
    '''
    __test__ = True
    possitive = True

    @classmethod
    def setUpClass(self): # Create and setup resources for tests
        db.setDCQuotaMode(config.MAIN_DC_NAME, 1)
        super(QuotaTestAudit, self).setUpClass()

class QuotaTestObjectWithoutQuota(unittest.TestCase):
    '''
    This class tests if object created in disabled mode can/can't
    be manipulated in audit/enforced mode(no quota assigned to objects)
    '''
    __test__ = False

    @classmethod
    def setUpClass(cls): # Create and setup resources for tests
        db.setDCQuotaMode(config.MAIN_DC_NAME, 0)  # Set dc to disabled
        q_id = db.getQuotaIdByName(QUOTA_NAME)

        # Create vm with no quota
        assert vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                storageDomainName=config.MAIN_STORAGE_NAME, size=10*GB,
                memory=2*GB)
        # Create disk with no quota
        assert disks.addDisk(True, alias=DISK_NAME, provisioned_size=10*GB,
                      interface='virtio', format='cow',
                      storagedomain=config.MAIN_STORAGE_NAME)
        assert disks.waitForDisksState(DISK_NAME)

        db.setDCQuotaMode(config.MAIN_DC_NAME, cls.mode)

    @classmethod
    def tearDownClass(cls): # Delete/release resources of test
        assert vms.removeVm(True, VM_NAME)
        assert disks.deleteDisk(True, alias=DISK_NAME)
        assert disks.waitForDisksGone(True, DISK_NAME)

    @istest
    @tcms(TCMS_PLAN_ID, 235939)
    def updateVm(self):
        """ Update vm with quota enforce mode """
        LOGGER.info("Updating vm '%s' memory" % VM_NAME)
        assert vms.updateVm(self.positive, VM_NAME, memory=GB)
        if self.positive:
            assert vms.updateVm(self.positive, VM_NAME, memory=512*MB)

    @istest
    def runVm(self):
        """ Run vm """
        # Add also case which tests, quota assigned only to vm not to disk
        LOGGER.info("Running vm '%s'" % VM_NAME)
        assert vms.startVm(self.positive, VM_NAME)
        if self.positive:
            assert vms.stopVm(True, VM_NAME)
            LOGGER.info("Stopping vm '%s'" % VM_NAME)

    @istest
    def createSnapshot(self):
        """ Create snapshot """
        # Add also case which tests, quota assigned only to disk not to vm
        LOGGER.info("Creating snapshot '%s'" % VM_SNAPSHOT)
        assert vms.addSnapshot(self.positive, VM_NAME, VM_SNAPSHOT)
        if self.positive:
            assert vms.removeSnapshot(True, VM_NAME, VM_SNAPSHOT)
            LOGGER.info("Removing snapshot '%s'" % VM_SNAPSHOT)

    @istest
    @bz(913551)
    def createTemplate(self):
        """ Create template """
        # Template should be created in Enforced and in Audit
        # also when vm and vm disk has no quota assigned
        LOGGER.info("Creating template '%s'" % TEMPLATE_NAME)
        assert templates.createTemplate(True, vm=VM_NAME,
                name=TEMPLATE_NAME, cluster=config.MAIN_CLUSTER_NAME)
        templates.removeTemplate(True, TEMPLATE_NAME)

    @istest
    @tcms(TCMS_PLAN_ID, 4) # TODO:
    def updateDisk(self):
        """ Update disk """
        # TODO: implement updateVmDisk in rhevm_api
        pass

    @istest
    @tcms(TCMS_PLAN_ID, 5) # TODO:
    def moveDisk(self):
        """ Move disk """
        # TODO: implement moveDisk in rhevm_api
        pass

    @istest
    @tcms(TCMS_PLAN_ID, 5) # TODO:
    def copyDisk(self):
        """ Copy disk """
        # TODO: implement copyDisk in rhevm_api
        pass

class QuotaTestEnforcedWithouQuota(QuotaTestObjectWithoutQuota):
    __test__ = True

    mode = 2  # Enforced
    positive = False

class QuotaTestAuditWithouQuota(QuotaTestObjectWithoutQuota):
    __test__ = True

    mode = 1  # Audit
    positive = True

class QuotaConsumptionCalc(unittest.TestCase):
    '''
    This class tests if quota consumtion is calculated right,
    when user create/remove/run/stop/etc.. vms/disks/etc
    '''
    __test__ = True

    @classmethod
    def setUpClass(cls):
        db.setDCQuotaMode(config.MAIN_DC_NAME, 2)  # Set dc to disabled
        q_id = db.getQuotaIdByName(QUOTA_NAME)
        vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                storageDomainName=config.MAIN_STORAGE_NAME, size=10*GB,
                memory=GB, vm_quota=q_id, disk_quota=q_id)

    @classmethod
    def tearDownClass(cls):
        vms.removeVm(True, VM_NAME)

    @istest
    @tcms(TCMS_PLAN_ID, 236236)
    def removeVm(self):
        """ Remove vm """
        q_id = db.getQuotaIdByName(QUOTA_NAME)
        vms.createVm(True, TMP_VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                storageDomainName=config.MAIN_STORAGE_NAME, size=10*GB,
                memory=2*GB, vm_quota=q_id, disk_quota=q_id)
        db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=0,
                virtual_cpu_usage=0, storage_size_gb_usage=20)
        assert vms.removeDisk(True, TMP_VM_NAME, TMP_VM_NAME + '_Disk1')
        db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=0,
                virtual_cpu_usage=0, storage_size_gb_usage=10)
        assert vms.removeVm(True, TMP_VM_NAME)

    @istest
    @tcms(TCMS_PLAN_ID, 236237)
    @bz(913551)
    def removeTemplate(self):
        """ Remove template """
        assert templates.createTemplate(True, vm=VM_NAME, name=TMP_TEMPLATE_NAME)
        try:
            db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=0,
                virtual_cpu_usage=0, storage_size_gb_usage=20)
        except Exception as e:
            raise e
        finally:
            assert templates.removeTemplate(True, template=TMP_TEMPLATE_NAME)
        db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=0,
                virtual_cpu_usage=0, storage_size_gb_usage=10)

    @istest
    @tcms(TCMS_PLAN_ID, 236238)
    def vmBasicOperations(self):
        """ Vm basic operations """
        db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=0,
                virtual_cpu_usage=0)
        assert vms.startVm(True, VM_NAME)
        db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=1024,
                virtual_cpu_usage=1)
        assert vms.waitForVmsStates(True, VM_NAME)
        db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=1024,
                virtual_cpu_usage=1)
        assert vms.suspendVm(True, VM_NAME)
        db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=0,
                virtual_cpu_usage=0)
        assert vms.startVm(True, VM_NAME, vms.ENUMS['vm_state_up'])
        db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=1024,
                virtual_cpu_usage=1)
        assert vms.stopVm(True, VM_NAME)
        db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=0,
                virtual_cpu_usage=0)

    @istest
    @tcms(TCMS_PLAN_ID, 236240)
    def runVmOnce(self):
        """ Run vm once """
        assert vms.runVmOnce(True, VM_NAME)
        db.checkGlobalConsumption(QUOTA_NAME, mem_size_mb_usage=1024,
                virtual_cpu_usage=1)
        assert vms.stopVm(True, VM_NAME)

    # TODO: Assign quota to disks, check if disk is counted
# TODO: class ImportExport Negative positive
# TODO: MLA+Quota
