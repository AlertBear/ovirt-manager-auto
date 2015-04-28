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
import logging
from rhevmtests.sla import config

from common import DB, ui_setup
from nose.tools import istest

# rhevm api
from utilities.rhevm_tools.base import Setup
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import events
from art.rhevm_api.tests_lib.high_level.disks import delete_disks
from art.rhevm_api.tests_lib.low_level import templates
from art.unittest_lib import attr
from art.unittest_lib import SlaTest as TestCase

# raut quota
from raut.tests.webadmin.quota import QuotaTest

# rhevm_utils general exception
from utilities.errors import GeneralException

# BZ, TCMS plugins
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611

LOGGER = logging.getLogger(__name__)

# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
EXPORT_NAME = 'export_domain'  # EXPORT domain
VM_NAME = 'quota__vm'
VM_DESC = 'quota'
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
AUDIT_MODE = 'AUDIT'
ENFORCED_MODE = 'ENFORCED'
GRACE_MODE = 'GRACE'
EXCEED_MODE = 'EXCEED'
QUOTA_NAME = 'quota_1'
QUOTA_DESC = 'quota_1_desc'
QUOTA2_NAME = 'quota_2'
QUOTA2_DESC = 'quota_2_desc'
QUOTA3_NAME = 'quota_3'
QUOTA3_DESC = 'quota_3_desc'
TCMS_PLAN_ID = 8029
MB = 1024 * 1024
GB = 1024 * MB
DISK_FORMAT = config.ENUMS['format_cow']
DISK_INTERFACE = config.ENUMS['interface_virtio']

# Bugs:
#
# Bug 1167081 - Possible to run vm under quota with exceeded number of vcpu

quota_ui = QuotaTest()  # raut object to CRUD quota
db = DB(None)  # db instance to access db to check resources
GRACE_MSG = "limit exceeded and entered the grace zone"
EXCEED_AUDIT = "limit exceeded, proceeding since in Permissive (Audit) mode"
EXCEED_ENFORCED = "limit exceeded and operation was blocked"
QUOTA_EVENTS = {
    AUDIT_MODE: {
        GRACE_MODE: GRACE_MSG,
        EXCEED_MODE: EXCEED_AUDIT
    },
    ENFORCED_MODE: {
        GRACE_MODE: GRACE_MSG,
        EXCEED_MODE: EXCEED_ENFORCED
    }
}
EVENT_TIMEOUT = 10


def setup_module():
    # Setup db
    dbname = config.RHEVM_UTILS_ENUMS['RHEVM_DB_NAME']
    db.setup = Setup(config.VDC_HOST, config.VDC_ROOT_USER,
                     config.VDC_ROOT_PASSWORD, dbname=dbname)
    # Clear all event before test
    sql = "DELETE FROM audit_log"
    db.setup.psql(sql)

    with ui_setup(quota_ui):
        quota_ui.create_quota(config.DC_NAME[0], QUOTA_NAME)


def teardown_module():
    db.set_dc_quota_mode(config.DC_NAME[0], QUOTA_NONE)
    with ui_setup(quota_ui):
        quota_ui.remove_quota(config.DC_NAME[0], QUOTA_NAME)


@attr(tier=0)
class QuotaTestCRUD(TestCase):
    """
    This unittest class tests CRUD operation via selenium.
    """
    __test__ = True

    def setUp(self):
        """ Start browser & login. """
        quota_ui.set_up()

    def tearDown(self):
        """ Close browser. """
        quota_ui.tear_down()

    @classmethod
    def tearDownClass(cls):
        """ Delete/release resources of test """
        with ui_setup(quota_ui):
            quota_ui.edit_quota(config.DC_NAME[0], QUOTA_NAME,
                                mem_limit=0, vcpu_limit=0, storage_limit=0)

    @istest
    @tcms(TCMS_PLAN_ID, 231136)
    def a_create_quota(self):
        """ Create Quota with some limits """
        quota_ui.create_quota(config.DC_NAME[0], QUOTA2_NAME,
                              description=QUOTA_DESC,
                              mem_limit=1024, vcpu_limit=1,
                              storage_limit=10)
        self.assertTrue(db.check_quota_exists(QUOTA2_NAME))

    @istest
    @tcms(TCMS_PLAN_ID, 231138)
    def b_edit_quota(self):
        """ Edit Quota """
        quota_ui.edit_quota(config.DC_NAME[0], QUOTA2_NAME,
                            description=QUOTA_DESC,
                            mem_limit=2048, vcpu_limit=2, storage_limit=20)
        self.assertTrue(db.check_quota_limits(QUOTA2_NAME, mem_size_mb=2048,
                                              virtual_cpu=2,
                                              storage_size_gb=20))
        self.assertTrue(
            db.check_quota_properties(
                QUOTA2_NAME, description=QUOTA_DESC,
                threshold_vds_group_percentage=80,
                threshold_storage_percentage=80,
                grace_vds_group_percentage=20,
                grace_storage_percentage=20
            )
        )

    @istest
    @tcms(TCMS_PLAN_ID, 231141)
    def c_copy_quota(self):
        """ Copy Quota """
        quota_ui.copy_quota(config.DC_NAME[0], QUOTA_NAME, name=QUOTA3_NAME,
                            description=QUOTA3_DESC)
        self.assertTrue(db.check_quota_exists(QUOTA3_NAME))

    @istest
    @tcms(TCMS_PLAN_ID, 231139)
    def d_delete_quota(self):
        """ Delete Quota """
        quota_ui.remove_quota(config.DC_NAME[0], QUOTA2_NAME)
        self.assertFalse(db.check_quota_exists(QUOTA2_NAME))
        quota_ui.remove_quota(config.DC_NAME[0], QUOTA3_NAME)
        self.assertFalse(db.check_quota_exists(QUOTA3_NAME))


@attr(tier=1)
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
        assert vms.createVm(True, VM_NAME, VM_DESC,
                            cluster=config.CLUSTER_NAME[0],
                            storageDomainName=config.STORAGE_NAME[0],
                            size=10*GB, memory=512*MB, vm_quota=q_id,
                            disk_quota=q_id, nic=config.NIC_NAME[0],
                            network=config.MGMT_BRIDGE)

    @classmethod
    def tearDownClass(cls):
        """ Delete/release resources of test """
        vms.stop_vms_safely([VM_NAME])
        assert vms.removeVm(True, VM_NAME)

    def _check_quota_message(self, max_id, limit):
        mode = AUDIT_MODE if self.positive else ENFORCED_MODE
        message = QUOTA_EVENTS[mode][limit]
        LOGGER.info("Waiting for event with message %s, "
                    "after event with id %s", message, max_id)
        return events.wait_for_event(message, start_id=max_id)

    @istest
    @tcms('9428', '268989')
    def a_quota_memory_limit(self):
        """ Quota RAM limit.
        Create VM with RAM 1024, quota level to 1024MB, try to run VM.
        """
        with ui_setup(quota_ui):
            quota_ui.edit_quota(config.DC_NAME[0], QUOTA_NAME,
                                mem_limit=1024, vcpu_limit=0,
                                storage_limit=0)
        self.assertTrue(vms.startVm(True, VM_NAME))
        self.assertTrue(vms.stopVm(True, VM_NAME))

    @istest
    @tcms('9428', '268990')
    def b_quota_memory_limit_in_grace(self):
        """ Quota RAM Limit in grace.
        Create quota with 1024MB limit (Grace 120%)
        Create vm with 1228 MB RAM, try to run it.
        """
        max_id = events.get_max_event_id(None)
        self.assertTrue(vms.updateVm(True, VM_NAME, memory=1228*MB))
        self.assertTrue(vms.startVm(True, VM_NAME))
        self.assertTrue(vms.stopVm(True, VM_NAME))
        self.assertTrue(self._check_quota_message(max_id, GRACE_MODE))

    @istest
    @tcms('9428', '268991')
    def c_quota_memory_limit_over_grace(self):
        """ Quota RAM Limit over grace.
        Create quota with 1024MB limit (Grace 120%)
        Create vm with 2048 MB RAM, try to run it.
        """
        max_id = events.get_max_event_id(None)
        self.assertTrue(vms.updateVm(True, VM_NAME, memory=2*GB))
        self.assertTrue(vms.startVm(self.positive, VM_NAME))
        if self.positive:
            self.assertTrue(vms.stopVm(True, VM_NAME))
        self.assertTrue(vms.updateVm(True, VM_NAME, memory=GB))
        self.assertTrue(self._check_quota_message(max_id, EXCEED_MODE))

    @istest
    @tcms('9428', '268992')
    def d_quota_vcpu_limit(self):
        """ Quota vCPU limit.
        Set vCPU to 1 from unlimited
        set RAM to unlimited - same for RAM
        """
        db.update_quota(QUOTA_NAME, grace_vds_group_percentage=100)
        with ui_setup(quota_ui):
            quota_ui.edit_quota(config.DC_NAME[0], QUOTA_NAME,
                                mem_limit=0, vcpu_limit=1, storage_limit=0)
        self.assertTrue(vms.startVm(True, VM_NAME))
        self.assertTrue(vms.stopVm(True, VM_NAME))

    @istest
    @tcms('9428', '268993')
    def e_quota_vcpu_limit_in_grace(self):
        """ Quota vCPU limit in grace """
        max_id = events.get_max_event_id(None)
        self.assertTrue(vms.updateVm(True, VM_NAME, cpu_cores=2))
        self.assertTrue(vms.startVm(True, VM_NAME))
        self.assertTrue(vms.stopVm(True, VM_NAME))
        self.assertTrue(vms.updateVm(True, VM_NAME, cpu_cores=1))
        self.assertTrue(self._check_quota_message(max_id, GRACE_MODE))

    @istest
    @tcms('9428', '268994')
    def f_quota_vcpu_limit_over_grace(self):
        """ Quota vCPU limit over grace """
        max_id = events.get_max_event_id(None)
        self.assertTrue(vms.updateVm(True, VM_NAME, cpu_cores=3))
        self.assertTrue(vms.startVm(self.positive, VM_NAME))
        if self.positive:
            self.assertTrue(vms.stopVm(True, VM_NAME))
        self.assertTrue(vms.updateVm(True, VM_NAME, cpu_cores=1))
        self.assertTrue(self._check_quota_message(max_id, EXCEED_MODE))

    def _check_hotplug(self, vm_state, mode, sockets):
        max_id = events.get_max_event_id(None)
        self.assertTrue(
            vms.startVm(
                True, VM_NAME,  wait_for_status=vm_state
            )
        )
        compare = self.positive
        self.assertTrue(
            vms.updateVm(True, VM_NAME, cpu_socket=sockets, compare=compare)
        )
        self.assertTrue(self._check_quota_message(max_id, mode))
        self.assertTrue(vms.stopVm(True, VM_NAME))
        if self.positive and mode != GRACE_MODE:
            self.assertTrue(vms.updateVm(True, VM_NAME, cpu_socket=1))
        self.assertTrue(vms.updateVm(True, VM_NAME, cpu_socket=1))

    @istest
    def g_quota_vcpu_hotplug_in_grace_vm_up(self):
        """
        Hotplug additional vCPU, when vm up, to put quota vCPU limit in grace
        """
        self._check_hotplug(config.ENUMS['vm_state_up'], GRACE_MODE, 2)

    @istest
    def h_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm up, to put quota vCPU limit over grace
        """
        self._check_hotplug(config.ENUMS['vm_state_up'], EXCEED_MODE, 3)

    @bz({'1167081': {'engine': None, 'version': ['3.5']}})
    @istest
    def i_quota_vcpu_hotplug_in_grace_vm_powering_up(self):
        """
        Hotplug additional vCPU, when vm powering up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(
            config.ENUMS['vm_state_powering_up'], GRACE_MODE, 2)

    @bz({'1167081': {'engine': None, 'version': ['3.5']}})
    @istest
    def j_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm powering up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            config.ENUMS['vm_state_powering_up'], EXCEED_MODE, 3)

    @istest
    @tcms('9428', '268995')
    def k_quota_storage_limit(self):
        """ Quota storage limit.
        Disable cluster quota
        """
        db.update_quota(QUOTA_NAME, grace_vds_group_percentage=20)
        with ui_setup(quota_ui):
            quota_ui.edit_quota(
                config.DC_NAME[0], QUOTA_NAME,
                mem_limit=0, vcpu_limit=0, storage_limit=20
            )
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        self.assertTrue(
            disks.addDisk(
                True, alias=DISK_NAME, provisioned_size=10*GB,
                interface=DISK_INTERFACE, format=DISK_FORMAT,
                storagedomain=config.STORAGE_NAME[0], quota=q_id
            )
        )

    @istest
    @tcms('9428', '268996')
    def l_quota_storage_limit_in_grace(self):
        """ Quota storage limit in grace """
        max_id = events.get_max_event_id(None)
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        self.assertTrue(
            disks.addDisk(
                True, alias=DISK_NAME, provisioned_size=14*GB,
                interface=DISK_INTERFACE, format=DISK_FORMAT,
                storagedomain=config.STORAGE_NAME[0], quota=q_id
            )
        )
        self.assertTrue(self._check_quota_message(max_id, GRACE_MODE))

    @istest
    @tcms('9428', '268997')
    def m_quota_storage_limit_over_grace(self):
        """ Quota storage limit over grace """
        max_id = events.get_max_event_id(None)
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        self.assertTrue(
            disks.addDisk(
                self.positive, alias=DISK_NAME, provisioned_size=15*GB,
                interface=DISK_INTERFACE, format=DISK_FORMAT,
                storagedomain=config.STORAGE_NAME[0], quota=q_id
            )
        )
        self.assertTrue(self._check_quota_message(max_id, EXCEED_MODE))
        with ui_setup(quota_ui):
            quota_ui.edit_quota(
                config.DC_NAME[0], QUOTA_NAME,
                mem_limit=0, vcpu_limit=0, storage_limit=0
            )

    @istest
    @tcms('9428', '268998')
    def n_delete_quota_in_use(self):
        """ Delete quota in use """
        with ui_setup(quota_ui):
            self.assertRaises(GeneralException, quota_ui.remove_quota,
                              config.DC_NAME[0], QUOTA_NAME)

    def tearDown(self):
        """
        If quota disk exist remove it
        """
        if disks.checkDiskExists(True, DISK_NAME):
            if not delete_disks([DISK_NAME]):
                logging.error("Failed to remove disk %s", DISK_NAME)


class QuotaTestEnforced(QuotaTestMode):
    """
    This unittest class tests quota Enforced mode.
    """
    __test__ = True

    positive = False

    # Create and setup resources for tests
    @classmethod
    def setUpClass(cls):
        db.set_dc_quota_mode(config.DC_NAME[0], QUOTA_ENFORCED)
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
        db.set_dc_quota_mode(config.DC_NAME[0], QUOTA_AUDIT)
        super(QuotaTestAudit, cls).setUpClass()


@attr(tier=1)
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
        db.set_dc_quota_mode(config.DC_NAME[0], QUOTA_NONE)
        # Create vm with no quota
        assert vms.createVm(True, VM_NAME, VM_DESC,
                            cluster=config.CLUSTER_NAME[0],
                            storageDomainName=config.STORAGE_NAME[0],
                            size=10*GB, memory=2*GB, nic=config.NIC_NAME[0],
                            network=config.MGMT_BRIDGE)
        # Create disk with no quota
        assert disks.addDisk(True, alias=DISK_NAME, provisioned_size=10*GB,
                             interface=DISK_INTERFACE,
                             format=DISK_FORMAT,
                             storagedomain=config.STORAGE_NAME[0])
        assert disks.wait_for_disks_status(DISK_NAME)

        db.set_dc_quota_mode(config.DC_NAME[0], cls.mode)

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
                                     cluster=config.CLUSTER_NAME[0]))
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


@attr(tier=0)
class QuotaConsumptionCalc(TestCase):
    """
    This class tests if quota consumption is calculated right,
    when user create/remove/run/stop/etc.. vms/disks/etc
    """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        """ Create and setup resources for tests """
        db.set_dc_quota_mode(config.DC_NAME[0], QUOTA_ENFORCED)
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        vms.createVm(True, VM_NAME, VM_DESC, cluster=config.CLUSTER_NAME[0],
                     storageDomainName=config.STORAGE_NAME[0], size=10*GB,
                     memory=GB, vm_quota=q_id, disk_quota=q_id,
                     nic=config.NIC_NAME[0], network=config.MGMT_BRIDGE)

    @classmethod
    def tearDownClass(cls):
        """ Delete/release resources of test """
        vms.removeVm(True, VM_NAME)

    @istest
    @bz({'1159642': {'engine': None, 'version': ['3.5']}})
    @tcms(TCMS_PLAN_ID, 236236)
    def remove_vm(self):
        """ Remove vm """
        q_id = db.get_quota_id_by_name(QUOTA_NAME)
        self.assertTrue(
            vms.createVm(True, TMP_VM_NAME, VM_DESC,
                         cluster=config.CLUSTER_NAME[0],
                         storageDomainName=config.STORAGE_NAME[0],
                         size=10*GB, memory=2*GB, vm_quota=q_id,
                         disk_quota=q_id, nic=config.NIC_NAME[0],
                         network=config.MGMT_BRIDGE))
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
