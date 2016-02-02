#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MultiHost Init
"""

import logging
import config as conf
from rhevmtests import networking
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("MultiHost_Init")


def setup_package():
    """
    Run network cleanup and start VM
    """
    conf.HOST_NAME_0 = conf.HOSTS[0]
    conf.VDS_HOST_0 = conf.VDS_HOSTS[0]
    conf.VDS_HOST_1 = conf.VDS_HOSTS[1]
    conf.HOST_0_NICS = conf.VDS_HOST_0.nics
    conf.HOST_1_NICS = conf.VDS_HOST_1.nics
    conf.HOSTS_LIST = conf.HOSTS[:2]
    conf.VDS_HOSTS_LIST = [conf.VDS_HOST_0, conf.VDS_HOST_1]
    networking.network_cleanup()
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.NETS_DICT, dc=conf.DC_NAME_0,
        cluster=conf.CLUSTER_NAME_0
    )
    if not network_helper.run_vm_once_specific_host(
        vm=conf.VM_NAME_0, host=conf.HOST_NAME_0, wait_for_up_status=True
    ):
        raise conf.NET_EXCEPTION()


def teardown_package():
    """
    Stop VM
    """
    if not ll_vms.stopVm(positive=True, vm=conf.VM_NAME_0):
        logger.error("Failed to stop VM: %s", conf.VM_NAME_0)

    hl_networks.remove_net_from_setup(
        host=conf.HOSTS_LIST, data_center=conf.DC_NAME_0, all_net=True
    )
