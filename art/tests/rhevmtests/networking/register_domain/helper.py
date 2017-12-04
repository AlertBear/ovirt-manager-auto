#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for register domain tests
"""

from utilities import utils

from art.rhevm_api.tests_lib.low_level import (
    mac_pool as ll_mac_pool,
    vms as ll_vms,
    templates as ll_templates
)
import config as register_domain_conf
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow


def get_vm_params(vm):
    """
    Get VM params from dict

    Args:
        vm (str): VM name

    Returns:
        tuple: VM MAC, network and nic
    """
    mac = register_domain_conf.VMS_DICT[vm]["mac"]
    network = register_domain_conf.VMS_DICT[vm]["network"]
    nic = register_domain_conf.VMS_DICT[vm]["nic"]
    return mac, network, nic


def get_template_params(template):
    """
    Get template params from dict

    Args:
        template (str): template name

    Returns:
        tuple: Network and NIC
    """
    network = register_domain_conf.TEMPLATES_DICT.get(
        template
    ).get("network")

    nic = register_domain_conf.TEMPLATES_DICT.get(
        template
    ).get("nic")
    return network, nic


def check_mac_in_mac_range(vm, nic):
    """
    Check if VM vNIC mac is in MAC range

    Args:
        vm (str): VM name
        nic (str): VM vNIC name

    Returns:
        bool: True if VM vNIC mac in MAC pool range else False
    """
    vnic_mac = ll_vms.get_vm_nic_mac_address(vm=vm, nic=nic)
    cluster_mac_pool = ll_mac_pool.get_mac_pool_from_cluster(
        cluster=conf.CL_0
    )
    start_range, end_range = ll_mac_pool.get_mac_range_values(
        mac_pool_obj=cluster_mac_pool
    )[0]
    mac_range = utils.MACRange(start_range, end_range)
    return vnic_mac in mac_range


def create_vms(vms_to_recreate=None):
    """
    Create VMs

    Args:
        vms_to_recreate (list): VMs name to create with renamed name

    Raises:
        AssertionError: If VM create fail
    """
    for vm, params in register_domain_conf.VMS_DICT.iteritems():
        if vms_to_recreate:
            if vm not in vms_to_recreate:
                continue
            vm = "{vm}_renamed".format(vm=vm)

        mac = params.get("mac")
        network = params.get("network")
        nic = params.get("nic")

        testflow.setup(
            "Create VM %s with: %s, %s", vm, network, mac or "MAC from pool"
        )
        assert ll_vms.createVm(
            positive=True, vmName=vm, cluster=conf.CL_0, network=network,
            vnic_profile=network, mac_address=mac, nic=nic
        )
        if not vms_to_recreate:
            if not mac:
                mac = ll_vms.get_vm_nic_mac_address(vm=vm, nic=nic)
                register_domain_conf.VMS_DICT[vm]["mac"] = mac


def create_templates():
    """
    Create template
    """
    for template, params in register_domain_conf.TEMPLATES_DICT.items():
        vm = params.get("vm")
        assert ll_templates.createTemplate(
            positive=True, vm=vm, name=template, cluster=conf.CL_0
        )
