#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Negative Migration Test - Tests to check vm migration
"""

import logging

from art.test_handler.exceptions import VMException
from rhevmtests.virt import config
from art.unittest_lib import VirtTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.unittest_lib import attr
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
from art.rhevm_api.tests_lib.low_level import storagedomains
import art.unittest_lib.common as common
from rhevmtests.virt import virt_helper


ENUMS = opts['elements_conf']['RHEVM Enums']
logger = logging.getLogger(__name__)
TCMS_PLAN_ID = '10421'


@attr(tier=2)
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
        hl_hosts.move_host_to_another_cluster(
            config.HOSTS[1],
            config.CLUSTER_NAME[1]
        )

    @classmethod
    def teardown_class(cls):
        """
        Back host cluster to init(cluster [0])
        """
        hl_hosts.move_host_to_another_cluster(
            config.HOSTS[1],
            config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-5666")
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


@attr(tier=2)
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
        hl_hosts.move_host_to_another_cluster(
            config.HOSTS[1],
            config.ADDITIONAL_CL_NAME
        )

    @classmethod
    def teardown_class(cls):
        """
        Back host cluster to init (cluster [0])
        """
        hl_hosts.move_host_to_another_cluster(
            config.HOSTS[1],
            config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-5658")
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


@attr(tier=2)
class TestMigrateVmOnSameHost(TestCase):
    """
    Negative: Migrate vm on the same host
    """
    __test__ = True

    @polarion("RHEVM3-5657")
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


@attr(tier=2)
@common.skip_class_if(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
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
    hosts = None
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
        cls.hosts = [config.HOSTS[0], config.HOSTS[1]]
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
        ll_vms.stop_vms_safely(cls.test_vms)
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

    @polarion("RHEVM3-5656")
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


@attr(tier=2)
class TestVMMigrateOptionsCase1(TestCase):
    """
    Negative case: VM Migration options case 1
    Create new VM with migration options disable (pin to host)
    """
    __test__ = True

    affinity = config.VM_PINNED
    vm_name = 'DoNotAllowMigration'
    storage_domain = None

    @classmethod
    def setup_class(cls):
        logger.info(
            'Create VM %s with option "Do not allow migration"',
            cls.vm_name
        )
        cls.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DC_NAME[0], config.STORAGE_TYPE_NFS
        )[0]
        if not ll_vms.createVm(
            True,
            vmName=cls.vm_name,
            vmDescription='VM_pin_to_host',
            cluster=config.CLUSTER_NAME[0],
            placement_affinity=cls.affinity,
            nic=config.NIC_NAME[0],
            storageDomainName=cls.storage_domain,
            size=config.DISK_SIZE,
            network=config.MGMT_BRIDGE,
            display_type=config.VM_DISPLAY_TYPE
        ):
            raise errors.VMException(
                "Failed to add vm %s " %
                cls.vm_name
            )
        if not ll_vms.startVm(True, cls.vm_name):
            raise errors.VMException(
                'Failed to start vm %s' %
                cls.vm_name
            )

    @classmethod
    def teardown_class(cls):
        try:
            logger.info('Stop vm: %s', cls.vm_name)
            if not ll_vms.stopVm(True, cls.vm_name):
                logger.error(
                    "Failed to stop vm %s",
                    cls.vm_name
                )
            logger.info('Remove vm')
            if not ll_vms.removeVm(True, cls.vm_name):
                logger.error(
                    'Failed to remove test vm %s' %
                    cls.vm_name
                )
        except Exception, e:
            logger.error(
                'TestVMMigrateOptionsCase2 teardown failed'
            )
            logger.error(e)

    @polarion("RHEVM3-5625")
    def test_migration_new_vm(self):
        """
         Negative test:
         Migration new VM with option 'Do not allow migration'
        """
        self.assertFalse(
            ll_vms.migrateVm(
                True,
                self.vm_name,
                host=config.HOSTS[1]),
            'Migration succeed although vm set to "Do not allow migration"'
        )


@attr(tier=2)
class TestVMMigrateOptionsCase2(TestCase):
    """
     Negative cases: VM Migration options cases
     Update exist VM with migration options to disable
     migration (pin to host)
    """
    __test__ = True
    affinity_pinned_to_host = config.VM_PINNED
    affinity_migratable = config.VM_MIGRATABLE

    @classmethod
    def setup_class(cls):
        logger.info(
            'update vm %s with affinity: pin to host',
            config.VM_NAME[1]
        )
        if not ll_vms.updateVm(
            True,
            config.VM_NAME[1],
            placement_affinity=cls.affinity_pinned_to_host
        ):
            raise errors.VMException(
                "Failed to update vm %s" %
                config.VM_NAME[1]
            )
        logger.info(
            'Start VM %s',
            config.VM_NAME[1]
        )
        if not ll_vms.startVm(True, config.VM_NAME[1]):
            raise errors.VMException('Failed to start vm')

    @classmethod
    def teardown_class(cls):
        try:
            if not ll_vms.stopVm(
                True,
                config.VM_NAME[1]
            ):
                logger.error(
                    'Failed to stop vm %s' %
                    config.VM_NAME[1]
                )
            logger.info(
                'update vm %s back to: migratable ',
                config.VM_NAME[1]
            )
            if not ll_vms.updateVm(
                True,
                config.VM_NAME[1],
                placement_affinity=cls.affinity_migratable
            ):
                logger.error(
                    'Failed to update vm %s' %
                    config.VM_NAME[1]
                )
        except Exception, e:
            logger.error(
                'TestVMMigrateOptionsCase2 teardown failed'
            )
            logger.error(e)

    @polarion("RHEVM3-5665")
    def test_update_vm(self):
        """
        Negative test:
        Migration updated VM with option 'Do not allow migration'
        """
        self.assertFalse(
            ll_vms.migrateVm(
                True,
                config.VM_NAME[1],
                host=config.HOSTS[1]),
            'Migration succeed although vm set to "Do not allow migration"'
        )


@attr(tier=2)
class TestMigrateVMWithLoadOnMemory(TestCase):
    """
    Negative test:
    Migrate VM With load on VM memory to fail migration.
    The load memory script is copy to VM, and run on it.
    """
    __test__ = True

    @classmethod
    def setUp(cls):
        logger.info('Start vm %s', config.VM_NAME[1])
        if not ll_vms.startVm(
            True,
            config.VM_NAME[1],
            wait_for_ip=True
        ):
            raise errors.VMException(
                'Failed to start vm %s',
                config.VM_NAME[1]
            )

    @classmethod
    def tearDown(cls):
        try:
            logging.info("Update memory usage to 60%")
            virt_helper.MEMORY_USAGE = 60
            logger.info('Stop vm: %s', config.VM_NAME[1])
            if not ll_vms.stopVm(
                True,
                config.VM_NAME[1]
            ):
                logger.error(
                    'Failed to stop vm %s'
                    % config.VM_NAME[1]
                )
        except Exception, e:
            logger.error(
                'TestMigrateVMWithLoadOnMemory teardown failed'
            )
            logger.error(e)

    @polarion("RHEVM3-5633")
    def test_check_migration_with_load_on_memory(self):
        """
         Negative test: Migrate VM with load on memory
        """
        logging.info("Update memory usage to 75%")
        virt_helper.MEMORY_USAGE = 75
        if not virt_helper.load_vm_memory(
            config.VM_NAME[1],
            memory_size='0.75'
        ):
            raise VMException("Failed to load VM memory")
        logger.info(
            "Start migration for VM: %s , migration should failed",
            config.VM_NAME[1]
        )
        self.assertFalse(
            ll_vms.migrateVm(
                True,
                config.VM_NAME[1]),
            'Migration pass although vm memory is loaded.'
        )
