#! /usr/bin/python
# -*- coding: utf-8 -*-

# Virt VMs: RHEVM3/wiki/Compute/Virt_VMs


import logging

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
import config
import rhevmtests.helpers as helper
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import tier1
from fixtures import add_vm_fixture

logger = logging.getLogger("update_vm_cases")


class TestUpdateVm(VirtTest):
    """
    Update vms with different parameters test cases
    """
    new_mem = 1280 * config.MB
    half_GB = 512 * config.MB
    vm_name = 'update_vm'

    @tier1
    @pytest.mark.parametrize(
        ("update_dict", "positive"),
        [
            pytest.param(
                {"time_zone": config.WIN_TZ, "os_type": config.WIN_2008}, True,
                marks=(
                    polarion("RHEVM3-12563"),
                    pytest.mark.skipif(
                        config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE
                    )
                )
            ),
            pytest.param(
                {"time_zone": config.WIN_TZ, "os_type": config.WIN_7}, True,
                marks=(
                    polarion("RHEVM3-12561"),
                    pytest.mark.skipif(
                        config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE
                    )
                )
            ),
            pytest.param(
                {"time_zone": config.RHEL_TZ, "os_type": config.RHEL6_64},
                True, marks=(
                    polarion("RHEVM3-12564"),
                    pytest.mark.skipif(
                        config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE
                    )
                )
            ),
            pytest.param(
                {"os_type": config.WIN_7}, False,
                marks=(
                    polarion("RHEVM3-12562"),
                    pytest.mark.skipif(
                        config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE
                    )
                )
            ),

            pytest.param(
                {
                    "placement_affinity": config.VM_MIGRATABLE,
                    "placement_host": 0
                }, True,
                marks=(polarion("RHEVM3-12528"))
            ),
            pytest.param(
                {
                    "placement_affinity": config.VM_USER_MIGRATABLE,
                    "placement_host": 0
                }, True,
                marks=(polarion("RHEVM3-12531"))
            ),
            pytest.param(
                {
                    "placement_affinity": config.VM_PINNED,
                    "placement_host": 0
                }, True,
                marks=(polarion("RHEVM3-12529"))
            ),
            pytest.param(
                {
                    "placement_affinity": config.VM_USER_MIGRATABLE,
                    "placement_host": config.VM_ANY_HOST
                }, True,
                marks=(polarion("RHEVM3-12530"))
            ),
            pytest.param(
                {
                    "placement_affinity": config.VM_MIGRATABLE,
                    "placement_host": config.VM_ANY_HOST
                }, True,
                marks=(polarion("RHEVM3-12527"))
            ),
            pytest.param(
                {"description": 'TEST'}, True, marks=(polarion("RHEVM3-12533"))
            ),
            pytest.param(
                {"memory": config.TWO_GB}, True,
                marks=(polarion("RHEVM3-12556"))
            ),
            pytest.param(
                {"cpu_socket": 2}, True, marks=(polarion("RHEVM3-12559"))
            ),
            pytest.param(
                {"cpu_socket": 40}, False, marks=(polarion("RHEVM3-12566"))
            ),
            pytest.param(
                {"cpu_cores": 2}, True, marks=(polarion("RHEVM3-12558"))
            ),
            pytest.param(
                {"display_type": config.VNC}, True,
                marks=(
                    polarion("RHEVM3-12534"),
                    pytest.mark.skipif(config.PPC_ARCH,
                                       reason=config.PPC_SKIP_MESSAGE
                                       )
                )
            ),
            pytest.param(
                {"memory": half_GB}, False, marks=(polarion("RHEVM3-12565"))
            ),
            pytest.param(
                {"name": vm_name}, True, marks=(polarion("RHEVM3-12557"))
            )

        ]
    )
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_update_vm(self, update_dict, positive):
        """
        Update vms with different parameters test cases
        """

        host_id = update_dict.get(config.VM_PLACEMENT_HOST)
        if host_id and isinstance(host_id, int):
            update_dict[config.VM_PLACEMENT_HOST] = config.HOSTS[host_id]

        testflow.step(
            "Test is %s positive: Update vm with: %s", positive, update_dict
        )
        assert ll_vms.updateVm(
            positive=positive, vm=self.vm_name, **update_dict
        )

    @tier1
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

    @tier1
    @polarion("RHEVM3-12532")
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

    @tier1
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

    @tier1
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

    @tier1
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
