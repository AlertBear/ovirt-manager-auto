#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Memory hotplug tests
"""

import logging
import pytest
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import rhevmtests.helpers as global_helper
from art.test_handler.tools import polarion
from art.unittest_lib.common import attr, VirtTest, testflow
from fixtures import reboot_vm
from rhevmtests.virt import config
import helper

logger = logging.getLogger("memory_hotplug_cases")


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class TestMemoryHotplug(VirtTest):
    """
    Hotplug memory test case
    """
    __test__ = True
    vm_ip = None
    vm_name = config.MEMORY_HOTPLUG_VM

    @attr(tier=1)
    @polarion("RHEVM3-14601")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_a_expand_memory_in_GB(self):
        """
        Expand VM memory using memory hot-plug: with 1GB,
        check memory updated
        """
        testflow.step(
            "Expand VM memory using memory hot-plug: with 1GB,check memory "
            "updated"
        )
        helper.hotplug_memory_check(
            vm_name=self.vm_name, memory_to_expand=config.GB
        )

    @attr(tier=1)
    @polarion("RHEVM3-14602")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_b_expand_memory_in_MB(self):
        """
        Expand VM memory using memory hot-plug: with 256MB,
        check memory updated
        """
        testflow.step(
            "Expand VM memory using memory hot-plug: with 256MB,"
            "check memory updated"
        )

        helper.hotplug_memory_check(
            vm_name=self.vm_name, memory_to_expand=config.MB_SIZE_256
        )

    @attr(tier=1)
    @polarion("RHEVM3-14603")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_c_expand_memory_in_4GB(self):
        """
        Expand VM memory using memory hot-plug:
        Total of 4GB - 4 iterations of 1GB
        check memory updated
        """
        testflow.step(
            "Expand VM memory using memory hot-plug: "
            "Total of 4GB - 4 iterations of 1GB"
            "check memory updated"
        )
        helper.hotplug_memory_check(
            vm_name=self.vm_name, memory_to_expand=config.GB, multiplier=4
        )

    @attr(tier=1)
    @polarion("RHEVM3-14605")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_d_expand_memory_in_multiple_of_256MB(self):
        """
        Expand VM memory using memory hot-plug:
        Total of 1280 MB: 5 iterations of 256MB
        check memory updated
        """
        testflow.step(
            "Expand VM memory using memory hot-plug:"
            "Total of 1280 MB: 5 iterations of 256MB"
            "check memory updated"
        )
        helper.hotplug_memory_check(
            vm_name=self.vm_name, memory_to_expand=config.MB_SIZE_256,
            multiplier=5
        )

    @attr(tier=1)
    @polarion("RHEVM3-14606")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_e_suspend_resume_vm(self):
        """
        Expand VM memory using memory hot-plug with 1GB, suspend and resume vm
        check that memory stay the same after suspend VM
        """
        testflow.step(
            "Expand VM memory using memory hot-plug with 1GB, "
            "suspend and resume vm check the memory stay that same "
            "after suspend VM"
        )
        testflow.step("Record memory status on VM")
        hl_vms.get_memory_on_vm(global_helper.get_vm_resource(self.vm_name))
        _, _, new_memory = hl_vms.expand_vm_memory(
            self.vm_name, mem_size_to_expand=config.GB
        )
        testflow.step("Suspend vm %s", self.vm_name)
        assert ll_vms.suspendVm(True, self.vm_name)
        testflow.step("Resume vm %s", self.vm_name)
        assert ll_vms.startVm(
            positive=True, vm=self.vm_name, wait_for_ip=True
        ), "Failed to start VM"
        testflow.step("Check VM memory on VM")
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name, expected_memory=new_memory
        ), "Memory check on VM failed"

    @attr(tier=1)
    @polarion("RHEVM3-14607")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_f_reboot_vm(self):
        """
        Expand VM memory using memory hot-plug with 1GB,
        check that memory stay the same after reboot VM
        """
        testflow.step(
            "Expand VM memory using memory hot-plug with 1GB,"
            "check that memory stay the same after reboot VM"
        )
        testflow.step("Record memory status on VM")
        hl_vms.get_memory_on_vm(global_helper.get_vm_resource(self.vm_name))
        _, _, new_memory = hl_vms.expand_vm_memory(
            self.vm_name, mem_size_to_expand=config.GB
        )
        testflow.step("reboot vm %s", self.vm_name)
        assert ll_vms.reboot_vms([self.vm_name])
        testflow.step("Check VM memory on VM")
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name,
            expected_memory=new_memory,
            threshold=0.85
        ), "Memory check on VM failed"

    @attr(tier=1)
    @polarion("RHEVM3-14608")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_vm_migration_after_memory_hotplug(self):
        """
        Expand VM memory using memory hot-plug: with 1GB,
        check memory updated
        """
        testflow.step(
            "Expand VM memory using memory hot-plug: with 1GB,"
            "check memory updated"
        )
        testflow.step("Record memory status on VM")
        hl_vms.get_memory_on_vm(global_helper.get_vm_resource(self.vm_name))
        _, _, new_memory = hl_vms.expand_vm_memory(
            self.vm_name, mem_size_to_expand=config.GB
        )
        testflow.step("Migrate VM")
        assert ll_vms.migrateVm(
            positive=True,
            vm=self.vm_name
        ), "Failed to migrate VM: %s " % config.VM_NAME[0]
        testflow.step("Check memory after migration")
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name, expected_memory=new_memory
        ), "Memory check on VM failed"

    @attr(tier=2)
    @pytest.mark.usefixtures(reboot_vm.__name__)
    @polarion("RHEVM3-14614")
    def test_neg_a_check_max_memory_device(self):
        """
        Negative case: Max memory device is 16. Try to add 17 memory devices
        """
        testflow.step(
            "Negative case: Max memory device is 16. "
            "Try to add 17 memory devices"
        )
        hl_vms.expand_vm_memory(self.vm_name, config.MB_SIZE_256, 16)
        memory_size = hl_vms.get_vm_memory(self.vm_name)
        memory_size += config.MB_SIZE_256
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            memory=memory_size
        ), "succeed to add memory device over the limit of 16"

    @attr(tier=2)
    @pytest.mark.usefixtures(reboot_vm.__name__)
    @polarion("RHEVM3-14615")
    def test_neg_b_wrong_memory_size(self):
        """
        Negative case: Expend VM memory with 400MB, wrong size should be in
        multiple of 256MB
        """
        testflow.step(
            "Negative case: Expend VM memory with 400MB, "
            "wrong size should be in multiple of 256MB"
        )
        memory_size = hl_vms.get_vm_memory(self.vm_name)
        memory_size += config.MB_SIZE_400
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            memory=memory_size
        ), "succeed to add memory, wrong memory size."
