#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Helper functions for fixtures.py
"""

import re

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests.networking import helper


def setup_network_helper(hosts_nets_nic_dict, sriov_nics, persist):
    """
    setup_networks helper for setup_networks fixtures

    Args:
        hosts_nets_nic_dict (dict): Networks dict
        sriov_nics (bool): If NICs should be SR-IOV NICs
        persist (bool): Save network configuration across reboots
    """
    ethtool_opts_str = "ethtool_opts"
    sn_dict = {
        "add": {}
    }

    for key, val in hosts_nets_nic_dict.iteritems():
        host = conf.HOSTS[key]
        host_resource = conf.VDS_HOSTS[key]
        if sriov_nics:
            sriov_host_object = ll_sriov.SriovHostNics(host=host)
            host_nics_list = sriov_host_object.get_all_pf_nics_names()
        else:
            host_nics_list = host_resource.nics

        for net, value in val.iteritems():
            slaves_list = list()
            slaves = value.get("slaves")
            nic = value.get("nic")
            network = value.get("network")
            datacenter = value.get("datacenter")
            ip_dict = value.get("ip")
            mode = value.get("mode")
            labels = value.get("labels")
            qos = value.get("qos")
            properties = value.get("properties")
            if properties and ethtool_opts_str in properties.keys():
                val = properties.get(ethtool_opts_str)
                match = re.findall(r'\d', val)
                if match:
                    host_nic_idx = match[0]
                    properties[ethtool_opts_str] = val.replace(
                        host_nic_idx, host_nics_list[int(host_nic_idx)]
                    )
            if slaves:
                for nic_ in slaves:
                    slaves_list.append(host_nics_list[nic_])
            if isinstance(nic, int):
                nic = host_nics_list[nic]

            sn_dict["add"][net] = {
                "network": network,
                "nic": nic,
                "datacenter": datacenter,
                "slaves": slaves_list,
                "mode": mode,
                "labels": labels,
                "properties": properties
            }
            sn_dict["add"][net]["qos"] = qos
            if ip_dict:
                for k, v in ip_dict.iteritems():
                    ip_dict[k]["netmask"] = v.get("netmask", "24")
                    ip_dict[k]["boot_protocol"] = v.get(
                        "boot_protocol", "static"
                    )
                sn_dict["add"][net]["ip"] = ip_dict

        log_dict = helper.remove_none_from_dict(sn_dict)
        testflow.setup(
            "Create %s via setup_network on host %s", log_dict, host
        )
        assert hl_host_network.setup_networks(
            host_name=host, persist=persist, **sn_dict
        )
        sn_dict["add"] = dict()


def clean_host_interfaces_helper(hosts_nets_nic_dict):
    """
    Clean host interfaces helper for clean_host_interfaces_sclass fixtures

    Args:
        hosts_nets_nic_dict (dict): Networks dict

    Returns:
        bool: True if operation succeeded, False otherwise
    """
    res = list()
    for key in hosts_nets_nic_dict.iterkeys():
        host_name = conf.HOSTS[key]
        res.append(hl_host_network.clean_host_interfaces(host_name=host_name))
    return all(res)
