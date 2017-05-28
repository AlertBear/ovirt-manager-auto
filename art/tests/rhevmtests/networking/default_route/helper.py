#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Helper for default route
"""
import netaddr

from art.unittest_lib import testflow


def is_dgw_from_ip_subnet(vds, ip):
    """
    Check if default gateway is from the same subnet as IP

    Args:
        vds (Host): Host resource
        ip (str): IP address

    Returns:
        bool: True if default gateway is from the IP subnet, False otherwise
    """
    dgw = vds.network.find_default_gw()
    testflow.step(
        "Check if default route (dgw) is from the same subnet of "
        "IP {ip}".format(dgw=dgw, ip=ip)
    )
    _, ip_and_netmask = vds.network.find_ips()
    if not dgw or ip_and_netmask:
        return False

    ips_and_mask = [i for i in ip_and_netmask if ip in i]
    if not ips_and_mask:
        return False

    ip_from_dgw = vds.network.find_ip_by_default_gw(
        default_gw=dgw, ips_and_mask=ips_and_mask
    )
    return ip == ip_from_dgw


def get_subnet_from_ip(ip_and_masks, ip):
    """
    Get subnet using host IP

    Args:
        ip_and_masks (list): List of IPs and masks [1.1.1.1/24]
        ip (str): Host IP

    Returns:
        str: IP subnet
    """
    local_ip_and_mask = [i for i in ip_and_masks if ip in i]
    assert local_ip_and_mask
    local_ip_and_mask = local_ip_and_mask[0]
    local_ip_network = netaddr.IPNetwork(local_ip_and_mask)
    return str(local_ip_network.network)
