#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test migration feature mix cases.
"""
import helper
import logging
from art.test_handler import exceptions
from art.unittest_lib import common
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.high_level.vms as hl_vm
import art.rhevm_api.tests_lib.low_level.vms as ll_vm
import art.rhevm_api.tests_lib.low_level.storagedomains as sd_api
from rhevmtests.virt import config

logger = logging.getLogger("virt_migration_mix_cases")
ENUMS = opts['elements_conf']['RHEVM Enums']


########################################################################
#                             Test Cases                               #
########################################################################


@common.attr(tier=2)
class TestBidirectionalVmMigrationBetweenTwoHosts(common.VirtTest):
    """
    1. Start all VMs (3 VMs on host_1, 2 VMs on host_2)
    2. Bidirectional vms migration between two hosts (simultaneous)
    3. Stop VMs
    """
    __test__ = True

    bz = {'1273965': {'engine': None, 'version': ['3.6']}}

    @classmethod
    def setup_class(cls):
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

    @classmethod
    def teardown_class(cls):
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
            helper.migration_vms_to_diff_hosts(vms=config.VM_NAME[:5]),
            "Failed to migration all VMs"
        )


@common.attr(tier=2)
class TestMigrateVmWithLargeMemory(common.VirtTest):
    """
    Migrate VM with large memory
    VM memory is 85% of host memory
    Note: VM will run load on memory as part of test to simulate
    real working station
    """
    __test__ = True
    vm_name = config.VM_NAME[1]
    vm_default_mem = None
    hosts = [config.HOSTS[0], config.HOSTS[1]]
    vm_default_os_type = None
    # RHEL7 64bit supports large memory
    os_type = ENUMS['rhel7x64']
    percentage = 85

    @classmethod
    def setup_class(cls):
        """
        Setup:
        1. update VM os type to RHEL7 64bit to support large memory
        2. updates VM to 85% of host memory
        3. start VM
        """
        logger.info("store os type vm")
        cls.vm_default_os_type = hl_vm.get_vms_os_type(
            test_vms=[cls.vm_name]
        )[0]
        logger.info(
            "set os type to %s vm %s", cls.os_type, cls.vm_name)
        if not hl_vm.update_os_type(
            os_type=cls.os_type,
            test_vms=[cls.vm_name]
        ):
            raise exceptions.VMException(
                "Failed to update os type for vm %s" %
                cls.vm_name
            )
        logger.info("store vm memory, for later update(in teardown)")
        cls.vm_default_mem = hl_vm.get_vm_memory(vm=cls.vm_name)
        logger.info(
            "update vm memory to %s percent of host memory", cls.percentage
        )
        status, cls.host_index_max_mem = (
            hl_vm.set_vms_with_host_memory_by_percentage(
                test_hosts=cls.hosts,
                test_vms=[cls.vm_name],
                percentage=cls.percentage
            )
        )
        if not status and cls.host_index_max_mem != -1:
            raise exceptions.VMException(
                "Failed to update vm memory with hosts memory"
            )
        logger.info("Start vm")
        if not ll_vm.startVm(True, cls.vm_name, wait_for_ip=True):
            raise exceptions.VMException(
                "Failed to start vm %s" % config.VM_NAME[1])

    @classmethod
    def teardown_class(cls):
        """
        tearDown:
        update Vm back to configure memory,os
        """
        logger.info("Stop vm: %s", cls.vm_name)
        if not ll_vm.stop_vms_safely([cls.vm_name]):
            logger.error("Failed to stop vm: %s", cls.vm_name)
        logger.info(
            "restore vm %s os type %s",
            cls.vm_name, cls.vm_default_os_type
        )
        if not hl_vm.update_os_type(cls.vm_default_os_type, [cls.vm_name]):
            logger.error(
                "Failed to update os type for vm %s", cls.vm_name
            )
        logger.info(
            "restore vm %s memory %s", cls.vm_name, cls.vm_default_mem
        )
        if not hl_vm.update_vms_memory([cls.vm_name], cls.vm_default_mem):
            logger.error(
                "Failed to update memory for vm %s", cls.vm_name
            )

    @polarion("RHEVM3-14033")
    def test_migrate_vm_with_large_memory(self):
        """
        Run load on VM with option of load false(not reuse memory)
        migrate VM.
        """
        if not helper.load_vm_memory(
            self.vm_name,
            memory_size='0.5',
            reuse_memory='False',
            memory_usage=5
        ):
            raise exceptions.VMException("Failed to load VM memory")
        self.assertTrue(
            ll_vm.migrateVm(
                positive=True, vm=self.vm_name),
            "Failed to migrate VM with large memory"
        )


@common.attr(tier=2)
class TestMigrateVmMoreThenOneDisk(common.VirtTest):
    """
    Migrate VM with more then 1 disk.
    Add to VM 2 disks and migrate VM
    remove disks in the end
    """
    __test__ = True

    vm_name = "VM_with_2_disks"
    cow_disk = config.DISK_FORMAT_COW
    disk_interfaces = config.INTERFACE_VIRTIO

    @classmethod
    def setup_class(cls):
        """
        1. Add 2 disk to VM
        2. Start VM
        """
        master_domain = (
            sd_api.get_master_storage_domain_name(config.DC_NAME[0])
        )
        if not ll_vm.createVm(
            positive=True,
            vmName=cls.vm_name,
            vmDescription=cls.vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0],
        ):
            raise exceptions.VMException(
                "Cannot create vm %s from template" % cls.vm_name
            )
        logger.info("Successfully created VM from template")
        logger.info("Start vm")
        if not ll_vm.startVm(positive=True, vm=cls.vm_name, wait_for_ip=True):
            raise exceptions.VMException("Failed to start vm %s" % cls.vm_name)
        logger.info("Add 2 disks to VM %s", cls.vm_name)
        for x in xrange(0, 2):
            if not ll_vm.addDisk(
                positive=True,
                vm=cls.vm_name,
                size=config.GB,
                storagedomain=master_domain,
                interface=cls.disk_interfaces,
                format=cls.cow_disk
            ):
                raise exceptions.VMException("Failed to add disk")

    @classmethod
    def teardown_class(cls):
        """
        tearDown:
        remove vm
        """
        logger.info("remove vm")
        if not ll_vm.safely_remove_vms([cls.vm_name]):
            logger.error("Failed to remove vm: %s", cls.vm_name)

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


@common.attr(tier=2)
class TestCheckHostResourcesDuringMigration(common.VirtTest):
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
    vm_name = config.VM_NAME[1]

    @classmethod
    def setup_class(cls):

        logger.info('Start vm %s', cls.vm_name)
        if not ll_vm.startVm(
            True,
            cls.vm_name,
            wait_for_ip=True
        ):
            raise exceptions.VMException('Failed to start vm %s' % cls.vm_name)

    @classmethod
    def teardown_class(cls):
        logger.info('Stop vm: %s', cls.vm_name)
        if not ll_vm.stopVm(
            True,
            cls.vm_name
        ):
            logger.error('Failed to stop vm %s', cls.vm_name)

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
            helper.compare_resources_lists(table_before, table_after),
            "Found resource that are pended to hosts")


@common.attr(tier=3)
class TestMigrationWithStorageMatrix(common.VirtTest):
    """
    Create VM from glance and test VM migration

    """
    __test__ = True
    vm_name = 'virt_vm_from_glance'

    @classmethod
    def setup_class(cls):
        """
        Create VM from glance
        Start VM
        """

        sd_name = sd_api.getStorageDomainNamesForType(
            datacenter_name=config.DC_NAME[0],
            storage_type=config.STORAGE_TYPE
        )[0]
        glance_name = config.EXTERNAL_PROVIDERS[config.GLANCE]
        if not hl_vm.create_vm_using_glance_image(
            vmName=cls.vm_name, vmDescription="linux vm",
            cluster=config.CLUSTER_NAME[0], nic=config.NIC_NAME[0],
            storageDomainName=sd_name, network=config.MGMT_BRIDGE,
            glance_storage_domain_name=glance_name,
            glance_image=config.GOLDEN_GLANCE_IMAGE

        ):
            raise exceptions.VMException(
                "Cannot create VM %s" % cls.vm_name
            )
        logger.info("Starting %s", cls.vm_name)
        if not ll_vm.startVm(True, cls.vm_name):
            raise exceptions.VMException(
                "Failed to start %s" % cls.vm_name
            )

    @classmethod
    def teardown_class(cls):
        """
        Stop and remove VM
        """
        if not ll_vm.safely_remove_vms([cls.vm_name]):
            logger.error("Failed to stop and remove vm: %s", cls.vm_name)

    @polarion("RHEVM3-14034")
    def test_migration_vm(self):
        self.assertTrue(ll_vm.migrateVm(
            positive=True,
            vm=self.vm_name,
            wait=True), "Failed to migrate VM"
        )
