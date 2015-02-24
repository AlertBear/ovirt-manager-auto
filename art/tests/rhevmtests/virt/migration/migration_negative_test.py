#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Negative Migration Test - Tests to check vm migration
"""

import logging

from art.test_handler.exceptions import VMException
from rhevmtests.virt import config
from art.unittest_lib import VirtTest as TestCase
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.high_level.hosts import (
    switch_host_to_cluster
)

ENUMS = opts['elements_conf']['RHEVM Enums']
logger = logging.getLogger(__name__)
TCMS_PLAN_ID = '10421'


@attr(tier=1)
class TestMigrateNoAvailableHostOnCluster(TestCase):
    """
    Negative: No available host on cluster
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Change second host cluster(to cluster [1])
        """
        switch_host_to_cluster(
            config.HOSTS[1],
            config.CLUSTER_NAME[1]
        )

    @classmethod
    def teardown_class(cls):
        """
        Back host cluster to init(cluster [0])
        """
        switch_host_to_cluster(
            config.HOSTS[1],
            config.CLUSTER_NAME[0]
        )

    @tcms(TCMS_PLAN_ID, '301654')
    def test_migrate_vm(self):
        """
        Negative: Check vm migration
        """
        self.assertFalse(
            ll_vms.migrateVm(
                True,
                config.VM_NAME[0]
            ), 'migration success although'
               'no available host on cluster'
        )


@attr(tier=1)
class TestMigrateVmOnOtherDataCenter(TestCase):
    """
    Negative: Migrate vm on another data center
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Change second host cluster (to ADDITIONAL CL)
        """
        switch_host_to_cluster(
            config.HOSTS[1],
            config.ADDITIONAL_CL_NAME
        )

    @classmethod
    def teardown_class(cls):
        """
        Back host cluster to init (cluster [0])
        """
        switch_host_to_cluster(
            config.HOSTS[1],
            config.CLUSTER_NAME[0]
        )

    @tcms(TCMS_PLAN_ID, '301655')
    def test_migrate_vm(self):
        """
        Negative: Check vm migration
        """
        self.assertFalse(
            ll_vms.migrateVm(
                True,
                config.VM_NAME[0],
                host=config.HOSTS[1]
            ), 'migration success although'
               'migration between data centers is not supported'
        )


@attr(tier=1)
class TestMigrateVmOnSameHost(TestCase):
    """
    Negative: Migrate vm on the same host
    """
    __test__ = True

    @tcms(TCMS_PLAN_ID, '301656')
    def test_migrate_vm(self):
        """
        Negative: Check vm migration
        """
        self.assertFalse(
            ll_vms.migrateVm(
                True,
                config.VM_NAME[0],
                host=config.HOSTS[0]
            ), 'migration success although'
               'migration to the same host is NOT supported'
        )


@attr(tier=1)
class TestMigrationOverloadHost(TestCase):
    """
    Negative test:
     Test details:
     In setup:
      1. store VM os type for later update in teardown
      2. update VM os type to RHEL7 64bit to support large memory
      3. store VM memory for later update in teardown
      4. updates 2 VMs to 85% of host memory
     In test case:
      1. Set the host with the large memory to maintenance
      2. Check host stay in 'preparing for maintenance' state.
     In teardown:
        1. update Vms back to configure memory and os type
        2. activate host with max memory
    """
    __test__ = True
    vm_default_mem = config.GB
    test_vms = [config.VM_NAME[1], config.VM_NAME[2]]
    hosts = [config.HOSTS[0], config.HOSTS[1]]
    host_index_max_mem = -1
    vm_default_os_type = None
    # RHEL7 64bit supports large memory
    os_type = ENUMS['rhel7x64']
    percentage = 85

    @classmethod
    def setup_class(cls):
        """
        Setup:
        1. update VM os type to RHEL7 64bit to support large memory
        2. updates 2 VMs to 85% of host memory
        """

        logger.info("store os type of vms")
        cls.vm_default_os_type = hl_vms.get_vms_os_type(
            test_vms=cls.test_vms
        )[0]
        logger.info(
            "set os type to %s for vms %s",
            cls.os_type,
            cls.test_vms
        )
        if not hl_vms.update_os_type(
            os_type=cls.os_type,
            test_vms=cls.test_vms
        ):
            raise VMException(
                "Failed to update os type for vms %s",
                cls.test_vms
            )
        logger.info("store vm memory, for later update(in teardown)")
        cls.vm_default_mem = hl_vms.get_vm_memory(
            vm=cls.test_vms[0]
        )
        status, cls.host_index_max_mem = (
            hl_vms.set_vms_with_host_memory_by_percentage(
                test_hosts=cls.hosts,
                test_vms=cls.test_vms,
                percentage=cls.percentage
            )
        )
        if not status and cls.host_index_max_mem != -1:
            raise VMException("Failed to update vm memory with hosts memory")
        logger.info("Start all vms")
        for vm in cls.test_vms:
            logger.info("starting vm %s", vm)
            if not ll_vms.startVm(True, vm):
                raise VMException("Failed to start vms %s" % cls.test_vms)

    @classmethod
    def teardown_class(cls):
        """
        tearDown:
        1. update 2 Vms back to configure memory
        2. activate host with max memory
        """

        logger.info("Stop all vms")
        ll_vms.stop_vms_safely(
            cls.test_vms,
            max_workers=config.MAX_WORKERS
        )
        logger.info(
            "restore vms %s os type %s",
            cls.test_vms, cls.vm_default_os_type
        )
        if not hl_vms.update_os_type(
            cls.vm_default_os_type,
            cls.test_vms
        ):
            raise VMException(
                "Failed to update os type for vms %s" %
                cls.test_vms
            )
        logger.info(
            "restore vms %s memory %s" %
            (cls.test_vms, cls.vm_default_mem)
        )
        if not hl_vms.update_vms_memory(
            cls.test_vms,
            cls.vm_default_mem
        ):
            raise errors.VMException(
                "Failed to update memory for vms %s" %
                cls.test_vms
            )
        logger.info(
            "Activate host %s",
            config.HOSTS[cls.host_index_max_mem]
        )
        if not ll_hosts.activateHost(
            True,
            cls.hosts[cls.host_index_max_mem]
        ):
            raise errors.HostException(
                "Failed to activate host %s" %
                cls.hosts[cls.host_index_max_mem]
            )

    @tcms(TCMS_PLAN_ID, '301659')
    def test_check_host_and_vm_status(self):
        """
        Negative case:
        Set the host with the large memory to maintenance
        Check host stay in 'preparing for maintenance' state.
        """
        expected_host_status = ENUMS['host_state_preparing_for_maintenance']
        logger.info("Deactivate host %s",
                    self.hosts[self.host_index_max_mem])
        self.assertTrue(
            ll_hosts.deactivateHost(
                True,
                self.hosts[self.host_index_max_mem],
                expected_status=expected_host_status),
            "Failed to deactivate host")
        logger.info("Check that all vms still in up state")
        self.assertTrue(
            ll_vms.waitForVmsStates(
                True,
                self.test_vms),
            "not all VMs are up"
        )