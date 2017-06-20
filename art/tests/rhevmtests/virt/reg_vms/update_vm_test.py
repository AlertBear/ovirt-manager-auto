#! /usr/bin/python
# -*- coding: utf-8 -*-

# Virt VMs: RHEVM3/wiki/Compute/Virt_VMs


import logging
import pytest
from art.test_handler.tools import polarion, bz
import rhevmtests.helpers as helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
from art.unittest_lib import (
    tier1,
    tier2,
)
from art.unittest_lib import VirtTest, testflow
from rhevmtests.virt.reg_vms.fixtures import add_vm_fixture
import config

logger = logging.getLogger("update_vm_cases")


@tier1
class UpdateVm(VirtTest):
    """
    Update vms with different parameters test cases
    """
    __test__ = True
    new_mem = 1280 * config.MB
    half_GB = 512 * config.MB
    vm_name = 'update_vm'
    add_disk = False

    @polarion("RHEVM3-12563")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_update_1_vm_os_type_from_rhel_to_windows_2008(self):
        """
        Positive: Update vm OS type from rhel to Windows 2008
        """
        testflow.step("Positive: Update vm OS type from rhel to Windows 2008")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            time_zone=config.WIN_TZ,
            os_type=config.WIN_2008
        )

    @polarion("RHEVM3-12561")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_update_2_vm_os_type_from_rhel_to_windows_7(self):
        """
        Positive: Update vm OS type from rhel to Windows 7
        """
        testflow.step("Positive: Update vm OS type from rhel to Windows 7")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            time_zone=config.WIN_TZ,
            os_type=config.WIN_7
        )

    @polarion("RHEVM3-12564")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_update_3_vm_os_type_from_win7_to_rhel(self):
        """
        Positive: Update vm OS type from Windows 7 to RHEL
        """
        testflow.step("Positive: Update vm OS type from Windows 7 to RHEL")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            time_zone=config.RHEL_TZ,
            os_type=config.RHEL6_64
        )

    @polarion("RHEVM3-12562")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_update_4_vm_os_type_from_rhel_to_windows_7_neg(self):
        """
        Negative: Update vm OS type from rhel to Windows 7, no timezone update
        """
        testflow.step(
            "Negative: "
            "Update vm OS type from rhel to Windows 7, no timezone update"
        )
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            os_type=config.WIN_7
        )

    @polarion("RHEVM3-12560")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_5_vm_linux_boot_options(self):
        """
        Positive: Update vm OS parameters
        """
        testflow.step("Positive: Update vm OS parameters")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            kernel='/kernel-new-path',
            initrd='/initrd-new-path',
            cmdline='rd_NO_LUKS'
        )

    @polarion("RHEVM3-10098")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_6_vm_name(self):
        """
        Positive: Update vm name
        """
        new_name = "update_vm_1"
        testflow.step("Update vm name to new name")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            name=new_name)

        assert ll_vms.updateVm(
            positive=True,
            vm=new_name,
            name=self.vm_name)

    @tier2
    @polarion("RHEVM3-12528")
    @bz({'1260732': {}})
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_7_vm_affinity_to_migratable_with_host(self):
        """
        Positive: Update vm affinity to migratable with host
        """

        affinity = config.ENUMS['vm_affinity_migratable']
        testflow.step("Update vm affinity to vm_affinity_migratable with host")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            placement_affinity=affinity,
            placement_host=config.HOSTS[0]
        )

    @tier2
    @polarion("RHEVM3-12531")
    @bz({'1260732': {}})
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_8_vm_affinity_to_user_migratable_with_host(self):
        """
        Positive: Update vm affinity to user migratable with host
        """
        affinity = config.ENUMS['vm_affinity_user_migratable']
        testflow.step("Update vm affinity to user migratable with host")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            placement_affinity=affinity,
            placement_host=config.HOSTS[0]
        )

    @tier2
    @polarion("RHEVM3-12529")
    @bz({'1260732': {}})
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_9_vm_affinity_to_pinned_with_host(self):
        """
        Positive: Update vm affinity to pinned with host
        """
        affinity = config.ENUMS['vm_affinity_pinned']
        testflow.step("Update vm affinity to pinned with host")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            placement_affinity=affinity,
            placement_host=config.HOSTS[0])

    @tier2
    @polarion("RHEVM3-12527")
    @bz({'1260732': {}})
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_10_vm_affinity_to_migratable_to_any_host(self):
        """
        Positive: Update vm affinity to migratable on any host
        """
        affinity = config.ENUMS['vm_affinity_migratable']
        testflow.step("Update vm affinity to migratable on any host")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            placement_host=config.VM_ANY_HOST,
            placement_affinity=affinity
        )

    @tier2
    @polarion("RHEVM3-12530")
    @bz({'1260732': {}})
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_vm_11_affinity_to_user_migratable_to_any_host(self):
        """
        Positive: Update vm affinity to user migratable on any host
        """
        affinity = config.ENUMS['vm_affinity_user_migratable']
        testflow.step("Update vm affinity to user migratable on any host")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            placement_host=config.VM_ANY_HOST,
            placement_affinity=affinity
        )

    @polarion("RHEVM3-12533")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_12_vm_description(self):
        """
        Positive: Update vm description
        """
        testflow.step("Update vm description")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            description="TEST"
        )

    @polarion("RHEVM3-12532")
    @bz({'1218528': {'engine': ['java', 'sdk', 'cli']}})
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_13_vm_cluster(self):
        """
        Update vm cluster
        """
        testflow.step("Update vm cluster, set vm migratable")
        logger.info("Turn VM %s back to being migratable", self.vm_name)
        affinity = config.ENUMS['vm_affinity_migratable']
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            placement_host=config.VM_ANY_HOST,
            placement_affinity=affinity
        )
        cluster = config.CLUSTER_NAME[1]
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cluster=cluster,
            cpu_profile=None
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cluster=config.CLUSTER_NAME[0],
            cpu_profile=None
        )
        logger.info("Update cluster to: %s", cluster)

    @polarion("RHEVM3-12556")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_14_vm_memory(self):
        """
        Update vm memory
        """
        testflow.step("Update vm memory")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            memory=config.TWO_GB
        )

    @polarion("RHEVM3-12555")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_15_vm_guranteed_memory(self):
        """
        Positive: Update vm guaranteed memory
        """
        current_mem = ll_vms.get_vm_memory(vm_name=self.vm_name)
        if current_mem < self.new_mem:
            logger.info(
                "Memory is less then guaranteed in this case, "
                "update vm memory to:%s ", 2 * self.new_mem
            )
            ll_vms.updateVm(
                positive=True,
                vm=self.vm_name,
                memory=2 * self.new_mem,
                max_memory=helper.get_gb(4),
                compare=False
            )
        testflow.step("Update vm guaranteed memory")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            memory_guaranteed=self.new_mem
        )

    @polarion("RHEVM3-12559")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_16_vm_number_of_cpu_sockets(self):
        """
        Positive: Update vm number of CPU sockets
        """
        testflow.step("Update vm number of CPU sockets")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cpu_socket=2
        )

    @polarion("RHEVM3-12558")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_17_vm_number_of_cpu_cores(self):
        """
        Positive: Update vm number of CPU cores
        """
        testflow.step("Update vm number of CPU cores")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cpu_cores=2
        )

    @polarion("RHEVM3-12534")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_update_18_vm_display_type_to_vnc(self):
        """
        Positive: Update vm display type to VNC
        """
        display_type = config.ENUMS['display_type_vnc']
        testflow.step("Update vm display type to VNC")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            display_type=display_type
        )

    @polarion("RHEVM3-12526")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_update_19_spice_vm_number_of_monitors(self):
        """
        Positive: Update spice display type vm number of monitors
        """
        display_type = config.ENUMS['display_type_spice']
        testflow.step("Update spice display type vm number of monitors")
        logger.info(
            "Update vm %s display type to %s",
            self.vm_name, display_type
        )
        if not ll_vms.updateVm(True, self.vm_name, display_type=display_type):
            raise errors.VMException("Failed to update vm")
        logger.info("Positive: Update vm number of monitors to 2")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            monitors=2
        )
        testflow.step("Positive: Update vm number of monitors to 1")
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            monitors=1
        )

    @polarion("RHEVM3-12567")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_update_20_vnc_vm_number_of_monitors(self):
        """
        Positive & Negative: Update vnc display type & num of monitors
        """
        display_type = config.ENUMS['display_type_vnc']
        testflow.step(
            "Update vm %s display type to %s",
            self.vm_name, display_type
        )
        if not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            display_type=display_type
        ):
            raise errors.VMException("Failed to update vm")
        testflow.step("Negative: Update vm number of monitors to 2")
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            monitors=2
        )

    @polarion("RHEVM3-12557")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_21_vm_name_to_existing_one(self):
        """
        Negative: Update vm name to existing one
        """
        vm_exist_name = 'exist_vm'
        testflow.step("Add new vm %s", vm_exist_name)
        if not ll_vms.addVm(
            True, name=vm_exist_name,
            cluster=config.CLUSTER_NAME[0],
            os_type=config.VM_OS_TYPE,
            type=config.VM_TYPE,
            display_type=config.VM_DISPLAY_TYPE
        ):
            raise errors.VMException("Failed to add vm")
        testflow.step("Update vm name to existing one")
        assert not ll_vms.updateVm(
            True, self.vm_name,
            name=vm_exist_name
        )
        assert ll_vms.safely_remove_vms(
            [vm_exist_name]
        ), "Failed to remove vm %s" % vm_exist_name

    @polarion("RHEVM3-12566")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_22_vm_with_too_many_sockets(self):
        """
        Negative: Update vm with too many CPU sockets
        """
        testflow.step("Negative: Update vm with too many CPU sockets")
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cpu_socket=40
        )

    @polarion("RHEVM3-12565")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_23_vm_with_guranteed_memory_less_than_memory(self):
        """
        Negative: Update vm memory, to be less than guaranteed memory,
        that equal to 1gb
        """
        testflow.step(
            "Negative: Update vm memory, "
            "to be less than guaranteed memory,"
            "that equal to 1 GB"
        )
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            memory=self.half_GB
        )
