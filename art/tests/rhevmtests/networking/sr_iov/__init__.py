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
from art.rhevm_api.utils import test_utils
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters

logger = logging.getLogger("SR_IOV_Init")


def setup_package():
    """
    Prepare environment
    Add QoS to data-center
    Configure Engine to support multiple queues
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

    if not ll_datacenters.add_qos_to_datacenter(
        datacenter=conf.DC_0, qos_name=conf.NETWORK_QOS,
        qos_type=conf.NET_QOS_TYPE, inbound_average=conf.BW_VALUE,
        inbound_peak=conf.BW_VALUE, inbound_burst=conf.BURST_VALUE,
        outbound_average=conf.BW_VALUE, outbound_peak=conf.BW_VALUE,
        outbound_burst=conf.BURST_VALUE
    ):
        raise conf.NET_EXCEPTION()

    logger.info(
        "Configuring engine to support queues for %s version",
        conf.COMP_VERSION
    )
    param = [
        "CustomDeviceProperties="
        "'{type=interface;prop={queues=[1-9][0-9]*}}'",
        "'--cver=%s'" % conf.COMP_VERSION
    ]
    if not test_utils.set_engine_properties(
        engine_obj=conf.ENGINE, param=param
    ):
        raise conf.NET_EXCEPTION("Failed to enable queue via engine-config")


def teardown_package():
    """
    Remove queue support from engine
    Remove QoS from date-center
    """
    logger.info(
        "Removing queues support from engine for %s version", conf.COMP_VERSION
    )
    param = ["CustomDeviceProperties=''", "'--cver=%s'" % conf.COMP_VERSION]
    if not test_utils.set_engine_properties(
        engine_obj=conf.ENGINE, param=param
    ):
        logger.error(
            "Failed to remove queues support via engine-config"
        )

    ll_datacenters.delete_qos_from_datacenter(
        datacenter=conf.DC_0, qos_name=conf.NETWORK_QOS
    )
