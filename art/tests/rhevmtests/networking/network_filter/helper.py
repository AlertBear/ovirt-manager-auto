#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for network_filter
"""

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as nf_conf
import rhevmtests.networking.config as conf


def add_update_vnic_profile_and_check_filter(
    action, vnic_profile, network_filter=None, datacenter=conf.DC_0
):
    """
    Add/Update network filter and check network filter after

    Args:
        action (str): add or update action
        vnic_profile (str): vNIC profile name to add/update
        network_filter (str): Network filter to apply
        datacenter (str): Datacenter name for add/update vNIC profile

    Returns:
        bool: True if add/update succeed and filter applied, False otherwise
    """
    before_nf_res = None
    nf_attr_dict = None
    if action == "add":
        if not ll_networks.add_vnic_profile(
            positive=True, name=vnic_profile, network=conf.MGMT_BRIDGE,
            data_center=datacenter, network_filter=network_filter
        ):
            return False

    if action == "update":
        if not network_filter:
            nf_attr_dict = ll_networks.get_vnic_profile_attr(
                name=vnic_profile, network=conf.MGMT_BRIDGE,
                attr_list=[nf_conf.NETWORK_FILTER_STR], data_center=datacenter
            )

        before_nf_res = nf_attr_dict[nf_conf.NETWORK_FILTER_STR]
        if not ll_networks.update_vnic_profile(
            positive=True, name=vnic_profile, network=conf.MGMT_BRIDGE,
            data_center=datacenter, network_filter=network_filter
        ):
            return False

    nf_attr_dict = ll_networks.get_vnic_profile_attr(
        name=vnic_profile, network=conf.MGMT_BRIDGE,
        attr_list=[nf_conf.NETWORK_FILTER_STR], data_center=datacenter
    )
    nf_res = nf_attr_dict[nf_conf.NETWORK_FILTER_STR]
    if network_filter == "None":
        return nf_res is None

    elif not network_filter:
        if action == "update":
            return nf_res == before_nf_res
        else:
            return nf_res == conf.VDSM_NO_MAC_SPOOFING

    return nf_res == network_filter
