"""
Migration Test - Basic tests to check vm migration
"""

import logging

from nose.tools import istest

from rhevmtests.virt import config
from art.unittest_lib import VirtTest as TestCase
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.high_level.vms as high_vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
import art.rhevm_api.tests_lib.high_level.hosts as high_host_api
from art.rhevm_api.utils.test_utils import getStat
from art.unittest_lib import attr
import art.rhevm_api.tests_lib.low_level.storagedomains as sd_api


ENUMS = opts['elements_conf']['RHEVM Enums']
logger = logging.getLogger(__name__)
TCMS_PLAN_ID = '10421'
HOSTS_STR = "".join([config.HOSTS[0], ',', config.HOSTS[1]])


class NegativeVmMigration(TestCase):
    """
    Basis class for vm migration negative test cases
    """
    __test__ = False
    init_cluster = config.CLUSTER_NAME[0]
    cluster_name = None

    @classmethod
    def setup_class(cls):
        """
        Change second host cluster and start vm
        """
        if cls.cluster_name:
            high_host_api.switch_host_to_cluster(config.HOSTS[1],
                                                 cls.cluster_name)
        if not high_vm_api.start_vm_on_specific_host(config.VM_NAMES[0],
                                                     config.HOSTS[0]):
            raise errors.VMException("Failed to start vm")

    @classmethod
    def teardown_class(cls):
        """
        Back host cluster to init and stop vm
        """
        logger.info("Stop vm %s", config.VM_NAMES[0])
        if not vm_api.stopVm(True, config.VM_NAMES[0]):
            raise errors.VMException("Failed to stop vm")
        if cls.cluster_name:
            high_host_api.switch_host_to_cluster(config.HOSTS[1],
                                                 cls.init_cluster)


@attr(tier=0)
class MigrateVmOnOtherCluster(NegativeVmMigration):
    """
    Negative: Migrate vm to another cluster in the same datacenter
    """
    __test__ = True
    cluster_name = config.CLUSTER_NAME[1]

    @tcms(TCMS_PLAN_ID, '301654')
    @istest
    def migrate_vm(self):
        """
        Negative: Check vm migration
        """
        self.assertFalse(vm_api.migrateVm(True, config.VM_NAMES[0],
                                          host=config.HOSTS[1]))


@attr(tier=0)
class MigrateVmOnOtherDatacenter(NegativeVmMigration):
    """
    Negative: Migrate vm on another datacenter
    """
    __test__ = True
    cluster_name = config.ADDITIONAL_CL_NAME

    @tcms(TCMS_PLAN_ID, '301655')
    @istest
    def migrate_vm(self):
        """
        Negative: Check vm migration
        """
        self.assertFalse(vm_api.migrateVm(True, config.VM_NAMES[0],
                                          host=config.HOSTS[1]))


@attr(tier=0)
class MigrateVmOnSameHost(NegativeVmMigration):
    """
    Negative: Migrate vm on the same host
    """
    __test__ = True

    @tcms(TCMS_PLAN_ID, '301656')
    @istest
    def migrate_vm(self):
        """
        Negative: Check vm migration
        """
        self.assertFalse(vm_api.migrateVm(True, config.VM_NAMES[0],
                                          host=config.HOSTS[0]))


@attr(tier=1)
class MigrationOverloadHost(TestCase):
    """
    Negative: Have two hosts, put one host to maintenance will create overload
    on second host, so engine will not unable to migrate all vms
    """
    __test__ = True
    number_of_vms = 10

    @classmethod
    def _create_vm(cls, vm_name, memory):
        """
        Wrapper for createVm method, that allow to create vm with different
        amount of memory
        """
        master_domain = (
            sd_api.get_master_storage_domain_name(config.DC_NAME[0])
        )
        if not vm_api.createVm(True, vm_name, config.VM_DESCRIPTION,
                               cluster=config.CLUSTER_NAME[0], memory=memory,
                               storageDomainName=master_domain,
                               network=config.MGMT_BRIDGE,
                               size=config.DISK_SIZE, nic='nic1'):
            raise errors.VMException("Failed to create VM: " + vm_name)

    @classmethod
    def setup_class(cls):
        """
        Create additional vms to overload host, start them
        and put one of the hosts to maintenance
        """
        total_mem = 0
        for host in config.HOSTS[0], config.HOSTS[1]:
            stats = getStat(host, 'host', 'hosts', 'memory.total')
            total_mem += stats['memory.total']
        logger.info("Total memory of both hosts = %d", total_mem)
        # vm_memory is set (host1 memory + host2 memory)/number_of_vms
        # This way not all vms will run only on one host.
        # It is rounded to MB, because this is how it is set in the database.
        vm_memory = ((total_mem/cls.number_of_vms)/config.MB)*config.MB
        logger.info("Create additional vms, with %s memory each", vm_memory)
        for vm_name in config.VM_NAMES[5:]:
            cls._create_vm(vm_name, vm_memory)
        for vm_name in config.VM_NAMES[5:]:
            if not vm_api.updateVm(True, vm_name, memory_guaranteed=vm_memory):
                raise errors.VMException("Failed to update vm %s" % vm_name)
        logger.info("Start all vms")
        vm_api.start_vms(config.VM_NAMES[5:], config.MAX_WORKERS,
                         wait_for_status=ENUMS['vm_state_up'],
                         wait_for_ip=False)

    @tcms(TCMS_PLAN_ID, '301659')
    @istest
    def check_host_and_vm_status(self):
        """
        Check host stay in 'preparing for maintenance' state.
        """
        expected_host_status = ENUMS['host_state_preparing_for_maintenance']
        logger.info("Deactivate host %s", config.HOSTS[0])
        self.assertTrue(host_api.deactivateHost(True, config.HOSTS[0],
                        expected_status=expected_host_status))
        logger.info("Check that all vms still in up state")
        self.assertTrue(vm_api.waitForVmsStates(True, config.VM_NAMES[5:]))

    @classmethod
    def teardown_class(cls):
        """
        Stop all vms, remove vms and activate host
        """
        logger.info("Stop all vms")
        vm_api.stop_vms_safely(config.VM_NAMES[5:],
                               max_workers=cls.number_of_vms)
        logger.info("Remove additional vms")
        if not vm_api.removeVms(True, config.VM_NAMES[5:]):
            raise errors.VMException("Failed to remove some vm")
        logger.info("Activate host %s", config.HOSTS[0])
        if not host_api.activateHost(True, config.HOSTS[0]):
            raise errors.HostException("Failed to activate host")


@attr(tier=0)
class HostToMaintenanceMigration(TestCase):
    """
    Check if all vms migrated when host move to maintenance
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Run all vms
        """
        logger.info("Start all vms")
        # Start vms on a specific host, to verify that vms will be migrated,
        # when the host move to maintenance
        high_vm_api.start_vms_on_specific_host(
            vm_list=config.VM_NAMES[:5], max_workers=5,
            host=config.HOSTS[0],
            wait_for_status=ENUMS['vm_state_up'], wait_for_ip=False)

    @tcms(TCMS_PLAN_ID, '301661')
    @istest
    def maintenance_hosts(self):
        """
        Check if all vms migrated when host move to maintenance
        """
        for host in config.HOSTS[0], config.HOSTS[1]:
            logger.info("Deactivate host %s", host)
            if not host_api.deactivateHost(True, host):
                raise errors.HostException("Failed to deactivate host")
            logger.info("Activate host %s", host)
            if not host_api.activateHost(True, host):
                raise errors.HostException("Failed to activate host")
        logger.info("Check that all vms up")
        self.assertTrue(vm_api.waitForVmsStates(True, config.VM_NAMES[:5]))

    @classmethod
    def teardown_class(cls):
        """
        Stop all vms
        """
        logger.info("Stop all vms")
        vm_api.stop_vms_safely(config.VM_NAMES[:5], max_workers=5)


@attr(tier=1)
class MigrateVMsSimultausly(TestCase):
    """
    Migrate several VMs simultanuasly
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Run all vms
        """
        logger.info("Start all vms")
        # Start vms on a specific host, to verify that vms will be migrated,
        # when the host move to maintenance
        high_vm_api.start_vms_on_specific_host(
            vm_list=config.VM_NAMES[:5], max_workers=5,
            host=config.HOSTS[0],
            wait_for_status=ENUMS['vm_state_up'], wait_for_ip=False)

    @tcms(TCMS_PLAN_ID, '301664')
    @istest
    def migrate_vms(self):
        """
        Migrate VMs
        """
        logger.info("hosts=%s", HOSTS_STR)
        self.assertTrue(vm_api.migrateVmsSimultaneously(
            True, vm_name=config.VM_NAME_BASIC, range_low=0,
            range_high=4, hosts=HOSTS_STR, useAgent=False, seed=0))
        logger.info("Check that all vms up")
        self.assertTrue(vm_api.waitForVmsStates(True, config.VM_NAMES[:5]))

    @classmethod
    def teardown_class(cls):
        """
        Stop all vms
        """
        logger.info("Stop all vms")
        vm_api.stop_vms_safely(config.VM_NAMES[:5], max_workers=5)
