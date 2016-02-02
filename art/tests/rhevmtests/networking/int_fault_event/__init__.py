#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Display of NIC Slave/Bond fault on RHEV-M Event Log feature test
"""

import logging
import config as conf
from rhevmtests import networking
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Int_Fault_Event_Init")


def setup_package():
    """
    Running cleanup
    """
    conf.HOST_0 = conf.HOSTS[0]
    conf.VDS_HOSTS_0 = conf.VDS_HOSTS[0]
    conf.HOST_0_IP = conf.HOSTS_IP[0]
    conf.HOST_NICS = conf.VDS_HOSTS_0.nics
    networking.network_cleanup()
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.NETS_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )


def teardown_package():
    """
    Remove all networks from setup
    """
    hl_networks.remove_net_from_setup(
        host=conf.HOST_0, data_center=conf.DC_0, all_net=True
    )
