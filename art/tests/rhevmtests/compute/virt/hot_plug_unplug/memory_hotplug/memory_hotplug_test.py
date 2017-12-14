#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Memory hotplug tests
"""

import pytest
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper
import rhevmtests.helpers as global_helper
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier1,
    tier2,
    tier3
)
from art.unittest_lib.common import VirtTest, testflow
from fixtures import reboot_vm
from rhevmtests import helpers as gen_helper
from rhevmtests.compute.virt import config


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class TestMemoryHotplug(VirtTest):
    """
    Hot-plug and Hot-unplug memory test cases
    """
    vm_ip = None
    vm_parameters = {
        'cluster': config.CLUSTER_NAME[0],
        'template': config.TEMPLATE_NAME[0],
        'os_type': config.VM_OS_TYPE,
        'display_type': config.VM_DISPLAY_TYPE,
        'max_memory': gen_helper.get_gb(16),
        'name': config.MEMORY_HOTPLUG_VM,
        'ballooning': False
    }
    vm_name = vm_parameters['name']

    @tier1
    @polarion("RHEVM3-22352")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_expand_reduce_memory_in_GB(self):
        """
        1. Expand VM memory using memory hot-plug: with 2x1GB,
        check memory updated
        2. Reduce VM memory using memory hot-unplug: with 1GB,
        check memory updated
        """
        testflow.step(
            "Expand VM memory using memory hot-plug: with 1GB,check memory "
            "updated"
        )
        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=config.GB,
            multiplier=2
        )
        testflow.step(
            "Reduce VM memory using memory hot-unplug: with 1GB,check memory "
            "updated"
        )
        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=-config.GB
        )

    @tier1
    @polarion("RHEVM3-22354")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_expand_reduce_memory_in_MB(self):
        """
        1. Expand VM memory using memory hot-plug: with 2x256MB,
        check memory updated
        2. Reduce VM memory using memory hot-unplug:
        with 256MB, check memory updated
        """
        testflow.step(
            "Expand VM memory using memory hot-plug: with 256MB,"
            "check memory updated"
        )

        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=config.MB_SIZE_256,
            multiplier=2
        )
        testflow.step(
            "Reduce VM memory using memory hot-unplug: with 256MB,"
            "check memory updated"
        )

        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=-config.MB_SIZE_256
        )

    @tier2
    @polarion("RHEVM3-22353")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_expand_memory_in_4GB(self):
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
        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=config.GB,
            multiplier=4
        )

    @tier1
    @polarion("RHEVM3-22351")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_expand_memory_in_multiple_of_256MB(self):
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
        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=config.MB_SIZE_256,
            multiplier=5
        )

    @tier2
    @polarion("RHEVM3-22155")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_memory_suspend_resume_vm(self):
        """
        1. Expand VM memory using memory hot-plug with 2x1GB,
        suspend and resume vm check that
        memory stay the same after suspend VM.
        2. Reduce VM memory using memory hot-unplug with 1GB,
        suspend and resume vm check that
        memory stay the same after suspend VM.
        """
        testflow.step(
            "Expand VM memory using memory hot-plug with 2*1GB, "
            "suspend and resume vm check the memory stay that same "
            "after suspend VM"
        )
        testflow.step("Record memory status on VM")
        hl_vms.get_memory_on_vm(
            global_helper.get_host_executor(
                ip=hl_vms.get_vm_ip(vm_name=self.vm_name),
                password=config.VMS_LINUX_PW
            )
        )
        _, _, new_memory = hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=config.GB,
            number_of_times=2
        )
        testflow.step("Suspend, resume VM")
        helper.suspend_resume_vm(vm_name=self.vm_name)
        testflow.step("Check VM memory on VM")
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name,
            expected_memory=new_memory,
            threshold=0.85
        ), "Memory check on VM failed"
        testflow.step(
            "Reduce VM memory using memory hot-unplug with 1GB, "
            "suspend and resume vm check the memory stay that same "
            "after suspend VM"
        )
        testflow.step("Record memory status on VM")
        hl_vms.get_memory_on_vm(
            global_helper.get_host_executor(
                ip=hl_vms.get_vm_ip(vm_name=self.vm_name),
                password=config.VMS_LINUX_PW
            )
        )
        _, _, new_memory = hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=-config.GB
        )
        testflow.step("Suspend, resume VM")
        helper.suspend_resume_vm(vm_name=self.vm_name)
        testflow.step("Check VM memory on VM")
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name,
            expected_memory=new_memory,
            threshold=0.85
        ), "Memory check on VM failed"

    @tier2
    @polarion("RHEVM3-22154")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_memory_reboot_vm_unplug(self):
        """
        Expand VM memory using memory hot-plug with 2*1GB,
        check memory update.
        Reduce VM memory using memory hot-unplug: with 1GB,
        check memory updated after reboot
        """
        testflow.step(
            "Expand VM memory using memory hot-plug with 2*1GB,"
            "check that memory stay the same after reboot VM"
        )
        testflow.step("Record memory status on VM")
        hl_vms.get_memory_on_vm(
            global_helper.get_host_executor(
                ip=hl_vms.get_vm_ip(self.vm_name),
                password=config.VMS_LINUX_PW
            )
        )
        _, _, new_memory = hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=config.GB,
            number_of_times=2
        )
        testflow.step("Check VM memory on VM")
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name,
            expected_memory=new_memory,
            threshold=0.85
        ), "Memory check on VM failed"
        testflow.step(
            "Reduce VM memory using memory hot-unplug: with 1GB,"
            "check memory updated"
        )
        testflow.step("Record memory status on VM")
        hl_vms.get_memory_on_vm(
            global_helper.get_host_executor(
                ip=hl_vms.get_vm_ip(self.vm_name),
                password=config.VMS_LINUX_PW
            )
        )
        _, _, new_memory = hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=-config.GB,
        )
        assert hl_vms.reboot_to_state(vm=self.vm_name)
        testflow.step("Check VM memory on VM")
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name,
            expected_memory=new_memory,
            threshold=0.85
        ), "Memory check on VM failed"

    @tier2
    @polarion("RHEVM3-22357")
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_vm_migration_after_memory_hotplug(self):
        """
        1. Expand VM memory using memory hot-plug: with 2GB,
        check memory updated
        2. Reduce VM memory using hot-unplug of 1GB,
        Migrate the VM and check the memory
        """
        testflow.step(
            "Expand VM memory using memory hot-plug: with 2GB,"
            "check memory updated"
        )
        testflow.step("Record memory status on VM")
        hl_vms.get_memory_on_vm(
            global_helper.get_host_executor(
                ip=hl_vms.get_vm_ip(self.vm_name),
                password=config.VMS_LINUX_PW
            )
        )
        _, _, new_memory = hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=config.GB,
            number_of_times=2
        )
        testflow.step("Migrate VM")
        assert ll_vms.migrateVm(
            positive=True,
            vm=self.vm_name
        ), "Failed to migrate VM: %s " % self.vm_name
        testflow.step("Check memory after migration")
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name,
            expected_memory=new_memory
        ), "Memory check on VM failed"

        testflow.step(
            "Reduce VM memory using memory hot-unplug: with 1GB,"
            "check memory updated"
        )
        _, _, new_memory = hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=-config.GB
        )
        testflow.step("Migrate VM")
        assert ll_vms.migrateVm(
            positive=True,
            vm=self.vm_name
        ), "Failed to migrate VM: %s " % self.vm_name
        testflow.step("Check memory after migration")
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name,
            expected_memory=new_memory
        ), "Memory check on VM failed"

    @tier2
    @pytest.mark.usefixtures(reboot_vm.__name__)
    @polarion("RHEVM3-22355")
    def test_neg_check_max_memory_device(self):
        """
        Negative case: Max memory device is 16. Try to add 17 memory devices
        """
        testflow.step(
            "Negative case: Max memory device is 16. "
            "Try to add 17 memory devices"
        )
        hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=config.MB_SIZE_256,
            number_of_times=16
        )
        memory_size = hl_vms.get_vm_memory(vm=self.vm_name)
        memory_size += config.MB_SIZE_256
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            memory=memory_size
        ), "succeed to add memory device over the limit of 16"

    @tier2
    @pytest.mark.usefixtures(reboot_vm.__name__)
    @polarion("RHEVM3-22350")
    def test_neg_wrong_memory_size(self):
        """
        Negative case: Expend VM memory with 400MB, wrong size should be in
        multiple of 256MB
        """
        testflow.step(
            "Negative case: Expend VM memory with 400MB, "
            "wrong size should be in multiple of 256MB"
        )
        memory_size = hl_vms.get_vm_memory(vm=self.vm_name)
        memory_size += config.MB_SIZE_400
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            memory=memory_size
        ), "succeed to add memory, wrong memory size."

    @tier3
    @polarion("RHEVM3-22157")
    @bz({'1496395': {}})
    @pytest.mark.usefixtures(reboot_vm.__name__)
    def test_snapshot_commit_uncommit_memory_hotunplug(self):
        """
        Expand VM memory using memory hot-plug: with 2*1GB,
        check memory updated.
        Create snapshot(with memory).
        Then reduce VM memory using hot-unplug of 1GB,
        1. Preview and undo preview of snapshot - check VM memory(2GB)
        2. Commit snapshot and check memory(3GB).
        """
        testflow.step(
            "Expand VM memory using memory hot-plug: with 2GB,"
            "check memory updated"
        )
        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=config.GB,
            multiplier=2
        )
        testflow.step("Creating snapshot with memory")
        new_memory = helper.create_snapshot_hot_unplug(vm_name=self.vm_name)
        testflow.step("Preview and undo preview of the snapshot")
        assert helper.prev_unprev_snapshot(vm_name=self.vm_name)
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name,
            expected_memory=new_memory
        ), "Memory check on VM failed"
        testflow.step("Commit Snapshot and start the VM")
        assert helper.commit_snapshot_start_vm(vm_name=self.vm_name)
        testflow.step("Check memory after snapshot commit")
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name,
            expected_memory=3*config.GB
        ), "Memory check on VM failed"

    @tier2
    @pytest.mark.usefixtures(reboot_vm.__name__)
    @polarion("RHEVM3-22159")
    def test_check_max_memory_device(self):
        """
        Max memory device is 16. Try to add 15 memory devices
        with memory hot-plug 256MB(total 3.75GB, 16devices),
        and remove them with memory hot-unplug
        """
        testflow.step(
            "Expand VM memory using memory hot-plug: with 256MB,"
            "15 times(total 3.75GB)"
        )
        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=config.MB_SIZE_256,
            multiplier=15
        )
        testflow.step(
            "Reduce VM memory using memory hot-unplug: with 256MB,"
            "16 times, check memory updated"
        )
        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=-config.MB_SIZE_256,
            multiplier=15
        )

    @tier2
    @pytest.mark.usefixtures(reboot_vm.__name__)
    @polarion("RHEVM3-22160")
    def test_diff_sizes_devices(self):
        """
        Add 6 memory devices with memory hot-plug
        two with 256MB, two with 512MB and two with 1GB.
        Remove one device from each size with memory hot-unplug
        """
        testflow.step(
            "Expand VM memory devices using memory hot-plug: "
            "with 2*256MB, 2*512MB and 2*GB"
            "check memory updated"
        )
        assert hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=config.MB_SIZE_256,
            number_of_times=2
        )
        assert hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=config.MB_SIZE_512,
            number_of_times=2
        )
        _, _, new_memory = hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=config.GB,
            number_of_times=2
        )
        testflow.step(
            "Remove VM memory devices using memory hot-unplug: "
            "with 1*256MB, 1*512MB and 1*GB"
            "check memory updated"
        )
        assert hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=-config.MB_SIZE_256
        )
        assert hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=-config.MB_SIZE_512
        )
        assert hl_vms.expand_vm_memory(
            vm_name=self.vm_name,
            mem_size_to_expand=-config.GB
        )
        expected_mem = new_memory - config.MEMORY_REMOVED
        assert global_helper.wait_for_vm_gets_to_full_memory(
            vm_name=self.vm_name,
            expected_memory=expected_mem,
        ), "Memory check on VM failed"

    @tier2
    @pytest.mark.usefixtures(reboot_vm.__name__)
    @polarion("RHEVM3-24892")
    def test_memory_unplug_memory_devices_at_once(self):
        """
        Max memory device is 16. Try to add 15 memory devices
        with memory hot-plug 256MB(total 3.75GB), and remove them
        with memory hot-unplug at once
        """
        testflow.step(
            "Expand VM memory using memory hot-plug: with 256MB,"
            "15 times(total 3.75GB)"
        )
        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=config.MB_SIZE_256,
            multiplier=15
        )
        testflow.step(
            "Reduce VM memory using memory hot-unplug: with 3.75GB,"
            "check memory updated"
        )
        assert helper.hotplug_memory_check(
            vm_name=self.vm_name,
            memory_to_expand=-config.MB_SIZE_3840
        )
