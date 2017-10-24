#! /usr/bin/python
# -*- coding: utf-8 -*-

# Sanity Virt: RHEVM3/wiki/Compute/Virt_VM_Sanity
# Virt VMs: RHEVM3/wiki/Compute/Virt_VMs

"""
Import VM from external providers like VMWare, KVM, Zen
"""

import copy

import pytest

import config
from art.rhevm_api.tests_lib.low_level import (
    mac_pool as ll_mac_pool,
    vms as ll_vms,
    disks as ll_disks,
)
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, VirtTest
from art.unittest_lib import (
    tier2,
)
from fixtures import v2v_import_fixture
from rhevmtests.compute.virt import helper


@pytest.mark.usefixtures(v2v_import_fixture.__name__)
class TestV2V_RHEL(VirtTest):
    """
    Test RHEL VM import from external providers
    """
    vm_name = config.V2V_RHEL_7_2_NAME

    @tier2
    @pytest.mark.parametrize(
        "parameter",
        [
            'sockets',
            'cores',
            'threads',
            'memory',
            'disk_size',
            'nic_mac_address',
        ]
    )
    @polarion("RHEVM-21386")
    def test_import_rhel_vm(self, parameter):
        """
        Import VM from external provider and check its parameters
        Args:
            parameter (str): Name of the parameter to check
        """
        testflow.step(
            "Get imported vm {vm} {p}".format(vm=self.vm_name, p=parameter)
        )
        if parameter == 'disk_size':
            vm_disk = ll_disks.getObjDisks(self.vm_name, get_href=False)[0]
            actual_value = vm_disk.get_provisioned_size()
        else:
            actual_value = getattr(
                ll_vms, 'get_vm_{p}'.format(p=parameter)
            )(self.vm_name)

        expected_config = copy.copy(
            config.EXTERNAL_VM_CONFIGURATIONS['rhel72']
        )
        testflow.step("Get mac range for the environment")
        default_mac_range = ll_mac_pool.get_mac_range_values(
            ll_mac_pool.get_default_mac_pool()
        )[0]

        expected_config['nic_mac_address']['start'] = default_mac_range[0]
        expected_config['nic_mac_address']['end'] = default_mac_range[1]

        testflow.step(
            "Compare two values. Actual:{a} Expected:{e}".format(
                a=actual_value,
                e=expected_config[parameter]
            )
        )
        assert helper.compare_vm_parameters(
            param_name=parameter,
            param_value=actual_value,
            expected_config=expected_config
        ), "VM parameter {p}={v} is different from expected: {e}".format(
            p=parameter,
            v=actual_value,
            e=expected_config[parameter]
        )
