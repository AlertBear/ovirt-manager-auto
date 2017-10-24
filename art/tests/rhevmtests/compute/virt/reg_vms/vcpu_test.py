#! /usr/bin/python
# -*- coding: utf-8 -*-

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow, tier2
from fixtures import (
    change_cpu_limitations, default_cpu_settings,
    create_vm_for_vcpu
)
from rhevmtests.compute.virt.fixtures import create_dc


@pytest.mark.skipif(
    config.NO_HYPERCONVERGED_SUPPORT,
    reason=config.NO_HYPERCONVERGED_SUPPORT_SKIP_MSG
)
@pytest.mark.usefixtures(
    create_dc.__name__,
    create_vm_for_vcpu.__name__,


)
class TestVcpu(VirtTest):
    """
    VCPU cases
    """

    current_version = config.COMP_VERSION
    version_4_0 = "4.0"
    dc_version_to_create = version_4_0

    @tier2
    @polarion("RHEVM3-17327")
    @pytest.mark.parametrize(
        (
            "comp_version", "cpu_cores", "cpu_sockets", "cpu_threads",
            "positive", "change_limitation"
        ),
        [
            pytest.param(
                current_version, 16, 9, 2, True, False,
                marks=(polarion("RHEVM-17328"))
            ),
            pytest.param(
                current_version, 15, 10, 2, False, False,
                marks=(polarion("RHEVM-17328"))
            ),
            pytest.param(
                current_version, 5, 2, 1, True, True,
                marks=(polarion("RHEVM3-10623"))
            ),
            pytest.param(
                current_version, 3, 4, 1, False, True,
                marks=(polarion("RHEVM3-10623"))
            ),
            pytest.param(
                version_4_0, 16, 15, 1, True, False,
                marks=(polarion("RHEVM3-11267"))
            ),
            pytest.param(
                version_4_0, 10, 5, 5, False, False,
                marks=(polarion("RHEVM3-11267"))
            ),

        ]
    )
    @pytest.mark.usefixtures(
        default_cpu_settings.__name__, change_cpu_limitations.__name__,
    )
    def test_update_vm_cpu_to_max(
        self, comp_version, cpu_cores, cpu_sockets, cpu_threads,
        positive, change_limitation
    ):
        """
        Positive: Update VM cpu to maximum (288 cpu's)
        """
        vm_name = (
            config.VM_NAME[0] if comp_version == self.current_version
            else config.VCPU_4_0_VM
        )
        testflow.step(
            "Update VM %s cpu total to %s", vm_name,
            (cpu_cores*cpu_sockets*cpu_threads)
        )
        assert ll_vms.updateVm(
            positive=positive,
            vm=vm_name,
            cpu_cores=cpu_cores,
            cpu_socket=cpu_sockets,
            cpu_threads=cpu_threads
        )
