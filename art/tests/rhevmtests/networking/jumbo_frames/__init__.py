#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Jumbo Frames init
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Network
/3_1_Network_JumboFrame
"""

import logging
import config as conf
from rhevmtests import networking
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Jumbo_frame_Init")


def setup_package():
    """
    Start two VMs on separated hosts
    Get VMs IPs
    """
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.HOST_1_NAME = conf.HOSTS[1]
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.VDS_1_HOST = conf.VDS_HOSTS[1]
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    conf.HOST_1_NICS = conf.VDS_1_HOST.nics
    vms_list = [conf.VM_0, conf.VM_1]
    hosts_list = [conf.HOST_0_NAME, conf.HOST_1_NAME]
    networking.network_cleanup()

    network_helper.prepare_networks_on_setup(
        networks_dict=conf.NETS_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )
    for vm, host in zip(vms_list, hosts_list):
        if not network_helper.run_vm_once_specific_host(
            vm=vm, host=host, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()


def teardown_package():
    """
    Set all hosts interfaces with MTU 1500
    Clean hosts interfaces
    Stop VMs
    Remove networks from engine
    """
    network_dict = {
        "1": {
            "network": "clear_net_1",
            "nic": None
        },
        "2": {
            "network": "clear_net_1",
            "nic": None
        },
        "3": {
            "network": "clear_net_1",
            "nic": None
        }
    }

    for host, nics in zip(
        [conf.HOST_0_NAME, conf.HOST_1_NAME],
        [conf.HOST_0_NICS, conf.HOST_1_NICS]
    ):
        network_dict["1"]["nic"] = nics[1]
        network_dict["2"]["nic"] = nics[2]
        network_dict["3"]["nic"] = nics[3]
        hl_host_network.setup_networks(host_name=host, **network_dict)
        hl_host_network.clean_host_interfaces(host_name=host)

    ll_vms.stopVms(vms=[conf.VM_0, conf.VM_1])
    hl_networks.remove_net_from_setup(
        host=conf.HOSTS[:2], data_center=conf.DC_0,
        mgmt_network=conf.MGMT_BRIDGE, all_net=True
    )
