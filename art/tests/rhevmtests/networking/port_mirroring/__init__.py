#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Port Mirroring init.
"""

import helper
import logging
from rhevmtests import networking
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Port_Mirroring_Init")


def setup_package():
    """
    Prepare environment
    """
    networking.network_cleanup()
    helper.create_networks_pm()
    helper.create_vnic_profiles_with_pm()

    logger.info(
        "Setting %s with profile %s on %s", conf.NIC_NAME[0],
        conf.MGMT_BRIDGE + "_PM", conf.VM_NAME[0]
    )
    helper.set_port_mirroring(
        conf.VM_NAME[0], conf.NIC_NAME[0], conf.MGMT_BRIDGE
    )

    vm_list = conf.VM_NAME[:conf.NUM_VMS]
    hl_vms.start_vms_on_specific_host(
        vm_list=vm_list, max_workers=len(vm_list), host=conf.HOSTS[0],
        wait_for_ip=False, wait_for_status=conf.ENUMS['vm_state_up']
    )

    helper.add_nics_to_vms()
    helper.configure_ip_all_vms()

    logger.info("Stop iptables service on hosts")
    for host in conf.VDS_HOSTS[:2]:
        if not host.service(conf.FIREWALL_SRV).stop():
            raise conf.NET_EXCEPTION("Cannot stop Firewall service")


def teardown_package():
    """
    Clean the environment
    """
    net_help.remove_ifcfg_files(conf.VM_NAME[:conf.NUM_VMS])
    logger.info("Stopping %s", conf.VM_NAME[:conf.NUM_VMS])
    if not ll_vms.stopVms(conf.VM_NAME):
        logger.error("Failed to stop VMs")

    for vm in conf.VM_NAME:
        vm_nics = ll_vms.get_vm_nics_obj(vm)
        for nic in vm_nics:
            if nic.name == conf.NIC_NAME[0]:
                logger.info(
                    "Setting %s profile on %s in %s",
                    conf.MGMT_BRIDGE, nic.name, vm
                )
                if not ll_vms.updateNic(
                        True, vm, conf.NIC_NAME[0],
                        network=conf.MGMT_BRIDGE,
                        vnic_profile=conf.MGMT_BRIDGE
                ):
                    logger.error(
                        "Failed to update %s in %s to profile "
                        "without port mirroring", conf.NIC_NAME[0], vm
                    )
            else:
                logger.info("Removing %s from %s", nic.name, vm)
                if not ll_vms.removeNic(True, vm, nic.name):
                    logger.error(
                        "Failed to remove %s from %s", nic, vm
                    )
    logger.info("Removing all networks from DC/Cluster and hosts")
    if not hl_networks.remove_net_from_setup(
        host=conf.HOSTS[0], data_center=conf.DC_NAME[0], all_net=True,
        mgmt_network=conf.MGMT_BRIDGE
    ):
        logger.error("Cannot remove network from setup")
