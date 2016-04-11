#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test migration feature mix cases.
"""
import time
import logging
import pytest
import art.rhevm_api.tests_lib.high_level.vms as hl_vm
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.vms as ll_vm
import rhevmtests.virt.helper as virt_helper
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import common
import rhevmtests.networking.helper as network_helper
from rhevmtests.virt import config

logger = logging.getLogger("virt_migration_mix_cases")
ENUMS = opts['elements_conf']['RHEVM Enums']


########################################################################
#                             Test Cases                               #
########################################################################

@common.attr(tier=2)
class TestMigrationMixCase1(common.VirtTest):
    """
    1. Start all VMs (3 VMs on host_1, 2 VMs on host_2)
    2. Bidirectional vms migration between two hosts (simultaneous)
    3. Stop VMs
    """
    __test__ = True

    def setUp(self):
        """
        Start all VM on both hosts
        """
        for vm_index in range(1, 3):
            if not hl_vm.start_vm_on_specific_host(
                vm=config.VM_NAME[vm_index],
                host=config.HOSTS[0],
                wait_for_ip=True
            ):
                raise exceptions.VMException(
                    "Failed to start VM:%s" %
                    config.VM_NAME[vm_index]
                )
        for vm_index in range(3, 5):
            if not hl_vm.start_vm_on_specific_host(
                vm=config.VM_NAME[vm_index],
                host=config.HOSTS[1],
                wait_for_ip=True
            ):
                raise exceptions.VMException(
                    "Failed to start VM:%s" %
                    config.VM_NAME[vm_index]
                )

    def tearDown(self):
        """
        Stop All VMs except of first VM
        """
        logger.info("tear down: stop VMs")
        if not ll_vm.stop_vms_safely(config.VM_NAME[1:]):
            logger.error("Failed to stop VMs")

    @polarion("RHEVM3-5646")
    def test_bidirectional_migration_between_two_hosts(self):
        """
        Test bidirectional vms migration between two hosts
        """
        logger.info(
            "Check bidirectional vms migration between two hosts"
        )
        self.assertTrue(
            virt_helper.migration_vms_to_diff_hosts(vms=config.VM_NAME[1:5]),
            "Failed to migration all VMs"
        )


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@common.attr(tier=2)
class TestMigrationMixCase2(common.VirtTest):
    """
    Migrate VM with large memory
    VM memory is 85% of host memory
    Note: VM will run load on memory as part of test to simulate
    real working station
    """
    __test__ = True
    vm_name = config.MIGRATION_VM
    vm_default_mem = config.GB * 2
    new_vm_memory = None
    percentage = 85
    load_of_2_gb = 2000
    time_to_run_load = 120

    def setUp(self):
        """
        1. Updates VM to 85% of host memory
        2. Start VM
        """
        logger.info("Stop vm: %s", self.vm_name)
        if not ll_vm.stop_vms_safely([self.vm_name]):
            logger.error("Failed to stop vm: %s", self.vm_name)
        self.hosts = [config.HOSTS[0], config.HOSTS[1]]
        status, self.host_index_max_mem = (
            hl_vm.set_vms_with_host_memory_by_percentage(
                test_hosts=self.hosts,
                test_vms=[self.vm_name],
                percentage=self.percentage
            )
        )
        if not status and self.host_index_max_mem != -1:
            raise exceptions.VMException(
                "Failed to update vm memory with hosts memory"
            )
        if not ll_vm.startVm(True, self.vm_name, wait_for_ip=True):
            raise exceptions.VMException(
                "Failed to start vm %s" % config.VM_NAME[1])

    def tearDown(self):
        """
        1. Stop VM
        2. Update VM back to configure memory
        3. Start VM
        """
        host_after_migration = ll_vm.get_vm_host(self.vm_name)
        logger.info("Host after migration: %s", host_after_migration)
        host_index = (
            [
                i for i, x in enumerate(config.HOSTS[:2])
                if x != host_after_migration
            ][0]
        )
        logger.info("Stop vm: %s", self.vm_name)
        if not ll_vm.stop_vms_safely([self.vm_name]):
            logger.error("Failed to stop vm: %s", self.vm_name)
        logger.info(
            "restore vm %s memory %s", self.vm_name, self.vm_default_mem
        )
        if not hl_vm.update_vms_memory([self.vm_name], self.vm_default_mem):
            logger.error(
                "Failed to update memory for vm %s", self.vm_name
            )
        logger.info("Rerun VM on host %s", config.HOSTS[host_index])
        # workaround for BZ:1303994
        # VM is already running on destination host
        # wait 2 intervals of monitor to finish
        logger.info("sleep 30 sec")
        time.sleep(30)
        if not network_helper.run_vm_once_specific_host(
            vm=self.vm_name, host=config.HOSTS[host_index],
            wait_for_up_status=True
        ):
            raise exceptions.VMException(
                "Failed to start vm %s" % self.vm_name
            )

    @polarion("RHEVM3-14033")
    def test_migrate_vm_with_large_memory(self):
        """
        Run load on VM, migrate VM.
        """
        virt_helper.load_vm_memory_with_load_tool(
            vm_name=self.vm_name, load=self.load_of_2_gb,
            time_to_run=self.time_to_run_load
        )
        self.assertTrue(
            ll_vm.migrateVm(
                positive=True, vm=self.vm_name),
            "Failed to migrate VM with large memory"
        )


@common.attr(tier=2)
class TestMigrationMixCase3(common.VirtTest):
    """
    Migrate VM with more then 1 disk.
    Add to VM 2 disks and migrate VM
    remove disks in the end
    """
    __test__ = True

    vm_name = "VM_with_2_disks"
    cow_disk = config.DISK_FORMAT_COW
    disk_interfaces = config.INTERFACE_VIRTIO

    def setUp(self):
        """
        1. Add 2 disk to VM
        2. Start VM
        """
        master_domain = (
            ll_sd.get_master_storage_domain_name(config.DC_NAME[0])
        )
        if not ll_vm.createVm(
            positive=True,
            vmName=self.vm_name,
            vmDescription=self.vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0],
        ):
            raise exceptions.VMException(
                "Cannot create vm %s from template" % self.vm_name
            )
        logger.info("Successfully created VM from template")
        ll_vm.updateVmDisk(
            positive=True,
            vm=self.vm_name,
            disk=config.TEMPLATE_NAME[0],
            bootable=True
        )
        if not ll_vm.startVm(positive=True, vm=self.vm_name, wait_for_ip=True):
            raise exceptions.VMException(
                "Failed to start vm %s" % self.vm_name
            )
        logger.info("Add 2 disks to VM %s", self.vm_name)
        for x in xrange(0, 2):
            if not ll_vm.addDisk(
                positive=True,
                vm=self.vm_name,
                size=config.GB,
                storagedomain=master_domain,
                interface=self.disk_interfaces,
                format=self.cow_disk
            ):
                raise exceptions.VMException("Failed to add disk")

    def tearDown(self):
        """
        remove vm
        """
        logger.info("remove vm")
        if not ll_vm.safely_remove_vms([self.vm_name]):
            logger.error("Failed to remove vm: %s", self.vm_name)

    @polarion("RHEVM3-5647")
    def test_migrate_vm_with_more_then_one_disk(self):
        """
        Migrate VM with more then one disk
        """
        self.assertTrue(ll_vm.migrateVm(
            positive=True,
            vm=self.vm_name,
            wait=True
        ), "Failed to migrate VM with more then 1 disk"
        )


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@common.attr(tier=2)
class TestMigrationMixCase4(common.VirtTest):
    """
    In migration the destination host saves memory and CPU for the new VM,
    This test checks that those resources released at host after
    Migration finished, in order to check the pending resources
    We run query on DB. We get the resource status before and after migration.
    If resources are released the after list should be equals to the before,
    which is empty.
    """
    __test__ = True
    sql = "select vds_name,pending_vmem_size,pending_vcpus_count from vds;"
    vm_name = config.MIGRATION_VM

    @polarion("RHEVM3-5619")
    def test_check_DB_resources(self):
        """
        1. Get resource status before migration
        2. Migration VM
        3. Get resource status after migration
        4. compare resource status
        """
        table_before = config.ENGINE.db.psql(sql=self.sql)
        logger.info("table before migration %s", table_before)
        logger.info("start vm migration")
        self.assertTrue(
            ll_vm.migrateVm(
                positive=True,
                vm=self.vm_name
            ),
            "Failed to migration VM: %s " % self.vm_name
        )
        table_after = config.ENGINE.db.psql(sql=self.sql)
        logger.info("table after migration %s", table_after)
        self.assertTrue(
            virt_helper.compare_resources_lists(table_before, table_after),
            "Found resource that are pended to hosts")
