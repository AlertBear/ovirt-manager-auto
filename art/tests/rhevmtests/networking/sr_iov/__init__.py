#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV feature init
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Network/3_6_Network_SR_IOV
"""
import logging
import config as conf
from rhevmtests import networking
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("SR_IOV_Init")


def setup_package():
    """
    Prepare environment
    """
    networking.network_cleanup()
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    conf.HOST_O_SRIOV_NICS_OBJ = ll_sriov.SriovHostNics(conf.HOST_0_NAME)
    conf.HOST_0_PF_LIST = conf.HOST_O_SRIOV_NICS_OBJ.get_all_pf_nics_objects()
    conf.HOST_0_PF_NAMES = conf.HOST_O_SRIOV_NICS_OBJ.get_all_pf_nics_names()
    mgmt_nic_obj = hl_networks.get_management_network_host_nic(
        host=conf.HOST_0_NAME, cluster=conf.CL_0
    )

    # Remove the host NIC with management network from PF lists
    if mgmt_nic_obj.name in conf.HOST_0_PF_NAMES:
        conf.HOST_0_PF_NAMES.remove(mgmt_nic_obj.name)
        conf.HOST_0_PF_LIST = filter(
            lambda x: x.id != mgmt_nic_obj.id, conf.HOST_0_PF_LIST
        )
