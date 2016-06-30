#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Memory hotplug tests
"""

import logging
import pytest

from art.unittest_lib.common import attr, VirtTest
from art.test_handler.tools import polarion, bz
import art.test_handler.exceptions as errors
import rhevmtests.helpers as global_helper
from art.rhevm_api.utils.test_utils import getStat
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.clusters as ll_cluster
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.rhevm_api.tests_lib.low_level import jobs
import config


logger = logging.getLogger("memory_hotplug_cases")


@attr(tier=1)
@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class TestMemoryHotplugBaseClass(VirtTest):
    """
    Memory hotplug base class
    """

    __test__ = False
    vm_name = config.VM_MEMORY_HOT_PLUG_NAME

    @classmethod
    def setup_class(cls):
        """
        Create VM from template and run it
        """
        logger.info("Create new vm %s from template", cls.vm_name)
        if not ll_vms.createVm(
            positive=True, vmName=cls.vm_name, vmDescription=cls.vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0], os_type=config.VM_OS_TYPE,
            display_type=config.VM_DISPLAY_TYPE,
            network=config.MGMT_BRIDGE
        ):
            raise errors.VMException("Failed to create vm %s" % cls.vm_name)
        logger.info('Start vm %s', cls.vm_name)
        if not ll_vms.startVm(
            positive=True,
            wait_for_status=config.VM_UP,
            vm=cls.vm_name,
            wait_for_ip=True
        ):
            raise errors.VMException('Failed to start vm %s' % cls.vm_name)
        # vm must be up in order to hot plug memory
        vm_ip = hl_vms.get_vm_ip(cls.vm_name)
        logger.info("VM is up and ip is: %s", vm_ip)

    @classmethod
    def teardown_class(cls):
        """
        Stop and remove vm after each test case
        """
        logger.info("Remove vm %s", cls.vm_name)
        if not ll_vms.remove_all_vms_from_cluster(
            cluster_name=config.CLUSTER_NAME[0], skip=config.VM_NAME
        ):
            logger.error("Failed to remove vms")
        logger.info("wait until vm removed and job cleaned")
        jobs.wait_for_jobs([config.ENUMS['job_remove_vm']])

    def get_vm_resource(self):
        """
        initialize vm resource with root user
        :return: vm resource
        :rtype: Host
        """
        vm_host = global_helper.get_host_resource(
            ip=hl_vms.get_vm_ip(self.vm_name, False),
            password=config.VDC_ROOT_PASSWORD
        )
        return vm_host

    def check_memory_hotplug(self, memory_to_expand, multiplier=1):
        """
        update vm memory and check vm memory from engine and vm

        :param memory_to_expand: memory size to expand
        :type memory_to_expand: int
        :param multiplier: number of time to expand memory_to_expand
        :type multiplier: int
        :return new memory size after expand memory
        :rtype: int
        """
        memory_size_before, memory_size_after, new_memory_size = (
            hl_vms.expand_vm_memory(self.vm_name, memory_to_expand, multiplier)
        )
        self.assertNotEqual(
            memory_size_after, -1,
            "Failed to update memory"
        )
        self.assertNotEqual(
            memory_size_before, memory_size_after,
            "Memory didn't updated"
        )
        logger.info("Check VM memory from VM")
        self.assertTrue(
            hl_vms.check_vm_memory(
                self.get_vm_resource(),
                new_memory_size
            ),
            "Memory check on VM failed"
        )
        return new_memory_size


class TestMemoryHotplugCase01(TestMemoryHotplugBaseClass):
    """
    Expand VM memory in different sizes using memory hot-plug
    """
    __test__ = True

    @polarion("RHEVM3-14601")
    def test_expand_memory_in_GB(self):
        """
        Expand VM memory using memory hot-plug: with 1GB,
        check memory updated
        """
        self.check_memory_hotplug(memory_to_expand=config.GB)

    @polarion("RHEVM3-14602")
    def test_hotplug_memory_in_MB(self):
        """
        Expand VM memory using memory hot-plug: with 256MB,
        check memory updated
        """
        self.check_memory_hotplug(memory_to_expand=config.MB_SIZE_256)


class TestMemoryHotplugCase02(TestMemoryHotplugBaseClass):
    """
    Expand VM memory in different multiple size using memory hot-plug
    """
    __test__ = True

    @polarion("RHEVM3-14603")
    def test_expand_memory_in_4GB(self):
        """
        Expand VM memory using memory hot-plug: in multiple of 1GB,
        check memory updated
        """
        self.check_memory_hotplug(memory_to_expand=config.GB, multiplier=4)

    @polarion("RHEVM3-14605")
    def test_expand_memory_in_multiple_of_256MB(self):
        """
        Expand VM memory using memory hot-plug: in multiple of 256MB,
        check memory updated
        """

        self.check_memory_hotplug(
            memory_to_expand=config.MB_SIZE_256,
            multiplier=5
        )

    @polarion("RHEVM3-14606")
    def test_suspend_resume_vm(self):
        """
        Expand VM memory using memory hot-plug with 1GB, suspend and resume vm
        check that memory stay that same after suspend VM
        """
        new_memory_size = self.check_memory_hotplug(memory_to_expand=config.GB)
        logger.info("Suspend vm %s", self.vm_name)
        self.assertTrue(ll_vms.suspendVm(True, self.vm_name))
        logger.info("Resume vm %s", self.vm_name)
        self.assertTrue(ll_vms.startVm(
            positive=True, vm=self.vm_name, wait_for_ip=True),
            "Failed to start VM"
        )
        logger.info("Check VM memory on VM")
        self.assertTrue(
            hl_vms.check_vm_memory(
                self.get_vm_resource(),
                new_memory_size
            ),
            "Memory check on VM failed"
        )

    @polarion("RHEVM3-14607")
    def test_reboot_vm(self):
        """
        Expand VM memory using memory hot-plug with 1GB, suspend and resume vm
        check that memory stay that same after reboot VM
        """
        new_memory_size = self.check_memory_hotplug(memory_to_expand=config.GB)
        logger.info("reboot vm %s", self.vm_name)
        self.assertTrue(ll_vms.reboot_vms([self.vm_name]))
        logger.info("Check VM memory on VM")
        self.assertTrue(
            hl_vms.check_vm_memory(
                self.get_vm_resource(),
                new_memory_size
            ),
            "Memory check on VM failed"
        )


class TestMemoryHotplugCase03(TestMemoryHotplugBaseClass):
    """
    Expand VM memory with memory hot plug and check VM migration
    """
    __test__ = True

    @polarion("RHEVM3-14608")
    def test_vm_migration_after_memory_hotplug(self):
        """
        Expand VM memory using memory hot-plug: with 1GB,
        check memory updated
        """
        new_memory_size = self.check_memory_hotplug(config.GB)
        logger.info("Migrate VM")
        self.assertTrue(
            ll_vms.migrateVm(
                positive=True,
                vm=self.vm_name
            ),
            "Failed to migrate VM: %s " % config.VM_NAME[0]
        )
        logger.info("Check memory after migration")
        self.assertTrue(
            hl_vms.check_vm_memory(
                self.get_vm_resource(),
                new_memory_size
            ),
            "VM Memory check after migration failed"
        )


class TestMemoryHotplugCase04(TestMemoryHotplugBaseClass):
    """
    Check cluster over commit
    """

    __test__ = True
    vm_default_os_type = None
    # RHEL7 64bit supports large memory
    os_type = config.ENUMS['rhel7x64']

    @classmethod
    def setup_class(cls):
        logger.info("update cluster to over commit 200%")
        if not ll_cluster.updateCluster(
            True, config.CLUSTER_NAME[0], mem_ovrcmt_prc=200
        ):
            logger.error(
                "Failed to update cluster %s to over commit to 200%",
                config.CLUSTER_NAME[0]
            )
        super(TestMemoryHotplugCase04, cls).setup_class()
        logger.info("Update VM OS type")
        cls.vm_default_os_type = hl_vms.get_vms_os_type(
            test_vms=[cls.vm_name]
        )[0]
        if not hl_vms.update_os_type(
            os_type=cls.os_type,
            test_vms=[cls.vm_name]
        ):
            raise errors.VMException(
                "Failed to update os type for vms %s",
                cls.vm_name
            )

    @classmethod
    def teardown_class(cls):
        logger.info("update cluster to over commit to None")
        if not ll_cluster.updateCluster(
            True, config.CLUSTER_NAME[0], mem_ovrcmt_prc=0
        ):
            logger.error(
                "Failed to update cluster %s to over commit t0 None",
                config.CLUSTER_NAME[0]
            )
        super(TestMemoryHotplugCase04, cls).teardown_class()

    @bz({"1337145": {}})
    @polarion("RHEVM3-14611")
    def test_expand_vm_memory_over_host_memory(self):
        """
        Expanding VM memory over host memory
        """
        host_memory = getStat(
            ll_vms.getVmHost(self.vm_name)[1]["vmHoster"],
            'host', 'hosts', 'memory.total'
        )
        logger.info("Host memory %s: ", host_memory)
        new_memory_size = host_memory['memory.total'] + config.GB
        if new_memory_size // config.MB_SIZE_256 != 1:
            logger.info("normalize to multiple of 256 MB")
            whole = new_memory_size / config.MB_SIZE_256
            new_memory_size = whole * config.MB_SIZE_256
        logger.info(
            "Update VM %s memory to %s ", self.vm_name, new_memory_size
        )
        self.assertTrue(
            ll_vms.updateVm(
                positive=True,
                vm=self.vm_name,
                memory=new_memory_size
            ),
            "Failed to update VM memory"
        )
        logger.info("Check memory on VM")
        self.assertTrue(
            hl_vms.check_vm_memory(
                self.get_vm_resource(),
                new_memory_size
            ),
            "Failed to expand VM memory over host memory"
        )


@attr(tier=2)
class TestMemoryHotplugCase05(TestMemoryHotplugBaseClass):
    """
    Negative cases:
    1. Max memory device
    2. Size not in multiple of 256MB
    """

    __test__ = True

    @polarion("RHEVM3-14614")
    def test_check_max_memory_device(self):
        """
        Negative case: Max memory device is 16. Try to add 17 memory devices
        """
        hl_vms.expand_vm_memory(self.vm_name, config.MB_SIZE_256, 16)
        memory_size = hl_vms.get_vm_memory(self.vm_name)
        memory_size += config.MB_SIZE_256
        self.assertFalse(
            ll_vms.updateVm(
                positive=True,
                vm=self.vm_name,
                memory=memory_size
            ),
            "succeed to add memory device over the limit of 16"
        )

    @polarion("RHEVM3-14615")
    def test_wrong_memory_size(self):
        """
        Negative case: Expend VM memory with 400MB, wrong size should be in
        multiple of 256MB
        """
        memory_size = hl_vms.get_vm_memory(self.vm_name)
        memory_size += config.MB_SIZE_400
        self.assertFalse(
            ll_vms.updateVm(
                positive=True,
                vm=self.vm_name,
                memory=memory_size
            ),
            "succeed to add memory, wrong memory size."
        )
