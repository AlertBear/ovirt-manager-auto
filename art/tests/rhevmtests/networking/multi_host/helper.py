#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for MultiHost
"""

import logging

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as multi_host_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper

logger = logging.getLogger("MultiHost_Helper")


def update_network_and_check_changes(
    net, nic=1, hosts=None, matches=1, positive=True, **kwargs
):
    """
    Update network and check that the network parameters are updated on engine
    and host(s)

    Args:
        net (str): Network name
        nic (int or str): Host NIC index or host BOND name
        hosts (list): Hosts indexes list to check the changes on
        matches (int): Number of matches to find in events
        positive (bool): True for positive update, False for negative update
        kwargs (dict): Params for update network function

    Keyword Args:
        name (str): New network name
        vlan (str): VLAN id
        mtu (int): MTU value
        bridge (bool): Bridge value (True for VM network, False for non-VM)

    Returns:
        bool: If check for positive update, return True if update network
            succeeded and applied successfully on engine and host.
            If check for negative update, return True if update network failed,
            False otherwise
    """
    name = kwargs.get("name")
    vlan_id = kwargs.get("vlan_id")
    mtu = kwargs.get("mtu")
    bridge = kwargs.pop("bridge", None)
    if bridge is not None:
        kwargs["usages"] = "vm" if bridge else ""
    hosts = hosts or [0]

    if positive:
        # If network name will be changed, look for the new name in success
        # event. Otherwise, look for the existing network name in event
        content_to_search = name or net
        # Wait for event id 1146, which indicate success to apply host network
        # change
        network_helper.call_function_and_wait_for_sn(
            func=ll_networks.update_network, content=content_to_search,
            positive=positive, network=net, matches=matches, **kwargs
        )

        # Go over the affected hosts and check for relevant OS changes
        hosts_list = [conf.HOSTS[host_index] for host_index in hosts]
        vds_hosts_list = [conf.VDS_HOSTS[host_index] for host_index in hosts]

        for host, vds_host in zip(hosts_list, vds_hosts_list):
            # Needed when NIC is BOND and not host NIC
            nic_name = vds_host.nics[nic] if isinstance(nic, int) else nic

            if mtu:
                if not check_mtu(
                    net=net, mtu=mtu, nic=nic_name, host=host,
                    vds_host=vds_host
                ):
                    return False
            if vlan_id:
                if not check_vlan(
                    net=net, vlan=vlan_id, nic=nic_name, host=host,
                    vds_host=vds_host
                ):
                    return False
            if bridge:
                if not check_bridge(
                    net=net, bridge=bridge, nic=nic_name, host=host,
                    vds_host=vds_host
                ):
                    return False

        return True
    else:
        # In negative check, return the response from engine
        return ll_networks.update_network(
            positive=positive, network=net, **kwargs
        )


def check_mtu(net, mtu, nic, host, vds_host):
    """
    Check that the updated network MTU is reflected on engine and on the host

    Args:
        net (str): Network name
        mtu (int): MTU value
        nic (str): Host NIC name
        host (str): Host name to check the changes on
        vds_host (resources.VDS): VDS resource to check the changes on

    Returns:
        bool: True if network MTU updated on engine and host, False otherwise
    """
    logger.info(multi_host_conf.MSG_UPDATED_ENGINE.format(net=net, prop="MTU"))
    mtu_dict = {
        "mtu": mtu
    }
    if not hl_networks.check_host_nic_params(host=host, nic=nic, **mtu_dict):
        return False

    logger.info(
        multi_host_conf.MSG_UPDATED_HOST.format(net=net, prop="MTU", host=host)
    )
    if not network_helper.check_mtu(
        vds_resource=vds_host, mtu=mtu, physical_layer=False,
        network=net, nic=nic
    ):
        logger.error(
            multi_host_conf.MSG_NOT_UPDATED_HOST.format(
                net=net, prop="MTU (logical layer)", host=host
            )
        )
        return False

    if not network_helper.check_mtu(vds_resource=vds_host, mtu=mtu, nic=nic):
        logger.error(
            multi_host_conf.MSG_NOT_UPDATED_HOST.format(
                net=net, prop="MTU (physical layer)", host=host
            )
        )
        return False
    return True


def check_vlan(net, vlan, nic, host, vds_host):
    """
    Check that the updated network VLAN is reflected on engine and on the host

    Args:
        net (str): Network name
        vlan (str): VLAN value
        nic: Host NIC name
        host (str): Host name to check the changes on
        vds_host (resources.VDS): VDS resource to check the changes on

    Returns:
        bool: True if network VLAN updated on engine and host, False otherwise
    """
    logger.info(
        multi_host_conf.MSG_UPDATED_ENGINE.format(net=net, prop="VLAN_ID")
    )
    vlan_dict = {
        "vlan_id": vlan
    }
    if not hl_networks.check_host_nic_params(host=host, nic=nic, **vlan_dict):
        return False

    logger.info(
        multi_host_conf.MSG_UPDATED_HOST.format(
            net=net, prop="VLAN_ID", host=host
        )
    )
    return ll_networks.is_vlan_on_host_network(
        vds_resource=vds_host, interface=nic, vlan=vlan
    )


def check_bridge(net, bridge, nic, host, vds_host):
    """
    Check that the updated network bridge is reflected on engine and on the
    host

    Args:
        net (str): Network name
        bridge (bool): Bridge value
        nic (str): Host NIC name
        host (str): Host name to check the changes on
        vds_host (resources.VDS): VDS resource to check the changes on

    Returns:
        bool: True if network bridge updated on host and engine,
            False otherwise
    """
    logger.info(
        multi_host_conf.MSG_UPDATED_ENGINE.format(net=net, prop="bridge")
    )
    bridge_dict = {
        "bridge": bridge
    }
    if not hl_networks.check_host_nic_params(
        host=host, nic=nic, **bridge_dict
    ):
        return False

    logger.info(
        multi_host_conf.MSG_UPDATED_HOST.format(
            net=net, prop="bridge", host=host
        )
    )
    return ll_networks.is_host_network_is_vm(
        vds_resource=vds_host, net_name=net
    )
