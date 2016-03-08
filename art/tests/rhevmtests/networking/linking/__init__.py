#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Linking feature Init
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Network/3_2_Network_NetworkLinking
"""

import logging
import config as conf
import rhevmtests.networking as networking
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import rhevmtests.networking.helper as net_help

logger = logging.getLogger("Linking_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.HOST_0_NAME = conf.HOSTS[0]
    networking.network_cleanup()
    if not net_help.run_vm_once_specific_host(
        vm=conf.VM_0, host=conf.HOST_0_NAME, wait_for_up_status=True
    ):
        raise conf.NET_EXCEPTION()

    if not hl_networks.createAndAttachNetworkSN(
        data_center=conf.DC_0, cluster=conf.CL_0,
        host=conf.VDS_HOSTS[0], network_dict=conf.VLAN_NET_DICT,
        auto_nics=[0, 1]
    ):
        raise conf.NET_EXCEPTION()


def teardown_package():
    """
    Cleans the environment
    """
    ll_vms.stopVm(positive=True, vm=conf.VM_0)

    hl_networks.remove_net_from_setup(
        host=conf.HOST_0_NAME, data_center=conf.DC_0, all_net=True,
    )
