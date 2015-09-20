#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Network labels feature init
"""
import logging
import config as conf
import rhevmtests.networking as networking
import rhevmtests.networking.helper as networking_helper

logger = logging.getLogger("Network_Labels_Init")

# ################################################


def setup_package():
    """
   Running cleanup
   Obtain host NICs for the first Network Host
   Create dummy interfaces
   Create networks
    """
    networking.network_cleanup()
    conf.HOST0_NICS = conf.VDS_HOSTS[0].nics
    conf.HOST1_NICS = conf.VDS_HOSTS[1].nics
    for i in range(2):
        networking_helper.prepare_dummies(
            host_resource=conf.VDS_HOSTS[i], num_dummy=conf.NUM_DUMMYS
        )
    networking_helper.prepare_networks_on_setup(
        networks_dict=conf.NET_DICT, dc=conf.DC_NAME[0],
        cluster=conf.CLUSTER_NAME[0]
    )


def teardown_package():
    """
    Cleans the environment
    """
    networking_helper.remove_networks_from_setup(hosts=conf.HOSTS[:2])
    for i in range(2):
        networking_helper.delete_dummies(host_resource=conf.VDS_HOSTS[i])
