#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Virt test - RNG device
"""
import pytest
from art.unittest_lib import (
    tier2,
    testflow,
    common,
)
from art.test_handler.tools import polarion
from rhevmtests.compute.virt.fixtures import (
    create_vm_class, start_vms
)
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import rhevmtests.helpers as rhevm_helpers

import rhevmtests.compute.virt.config as config
import config as local_conf


@pytest.mark.usefixtures(
    create_vm_class.__name__,
    start_vms.__name__
)
class TestPCIERootPort(common.VirtTest):
    """
    Urandom RNG Device Class
    """
    vm_name = local_conf.Q35_VM_NAME
    vm_parameters = {
        "name": local_conf.Q35_VM_NAME,
        'template': config.TEMPLATE_NAME[0],
        'os_type': config.OS_TYPE,
        'cluster': config.CLUSTER_NAME[0],
        'custom_emulated_machine': local_conf.Q35_MACHINE_TYPE
    }
    wait_for_vms_ip = True

    @tier2
    @polarion("RHEVM-24566")
    def test_pcie_port_on_vm(self):
        """
        Verify if PCIe root ports are present in the VMs PCI devices list.
        """
        vm_ip = hl_vms.get_vm_ip(local_conf.Q35_VM_NAME)
        vm_resource = rhevm_helpers.get_host_resource(
            ip=vm_ip,
            password=config.HOSTS_PW
        )
        vm_resource.executor().wait_for_connectivity_state(positive=True)
        testflow.step(
            "Run command on VM and verify if PCIe root port is present."
        )
        rc, out, err = vm_resource.run_command(
            local_conf.PCIE_VERIFY_CMD_ON_VM
        )
        testflow.step(
            "Verify command executed successfully."
        )
        assert not rc, (
            "Failed to get the list of PCIe root ports on the VM side, with "
            "following error: {err}".format(
                out=out,
                err=err
            )
        )
        testflow.step(
            "Verify PCIe root port present in the pci devices list."
        )
        assert len(out.strip().split('\n')) > 0, (
            "PCIe root port was not found on the VM"
        )

    @tier2
    @polarion("RHEVM-24847")
    def test_pcie_port_on_host(self):
        """
        Verify if PCIe root ports are present in the virsh dump for specific VM
        """

        host_name = ll_vms.get_vm_host(local_conf.Q35_VM_NAME)

        host_ip = ll_hosts.get_host_ip(host_name)
        host_resource = rhevm_helpers.get_host_resource(
            ip=host_ip,
            password=config.HOSTS_PW
        )
        testflow.step(
            "Run command on host {host_name} and verify if PCIe root port is "
            "present.".format(host_name=host_name)
        )
        rc, out, err = host_resource.run_command(
            local_conf.PCIE_VERIFY_CMD_ON_HOST
        )
        testflow.step(
            "Verify command executed successfully."
        )
        assert not rc, (
            "Failed to get the list of PCIe root ports on the host side, with "
            "following error: {err}".format(
                out=out,
                err=err
            )
        )
        testflow.step(
            "Verify PCIe root port present in the host virsh dump of pci "
            "devices list."
        )
        assert len(out.strip().split('\n')) > 0, (
            "PCIe root port was not found in the virsh dump xml for the VM."
        )
