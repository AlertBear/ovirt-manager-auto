import logging
import shlex

from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    hosts as ll_hosts
)
import rhevmtests.helpers as global_helper

logger = logging.getLogger("Bad_Bond_Helper")


def check_mac_address(mac_address, positive):
    """
    Check if given MAC address is zero or not

    Args:
        mac_address (str): MAC address
        positive (bool): True to check for valid bond address (non-zero), False
            to check for invalid bond address (zero)

    Returns:
        bool: True if MAC address is not zero or zero, according to the no_zero
            argument, False otherwise

    """
    zero_mac = "00:00:00:00:00:00"
    return mac_address != zero_mac if positive else mac_address == zero_mac


def get_bond_ad_partner_mac_in_linux(host_name, bond_name):
    """
    Get LACP bond (mode-4) ad_partner_mac MAC value in Linux

    Args:
        host_name (str): Host name
        bond_name (str): Bond name

    Returns:
        bool: True if get was successful, False otherwise

    """
    logger.info(
        "Checking if ad_partner_mac value is reported in Linux on bond: %s",
        bond_name
    )
    cmd = "cat /sys/class/net/%s/bonding/ad_partner_mac" % bond_name
    host_rsc = global_helper.get_host_resource_by_name(host_name=host_name)
    rc, os_out, _ = host_rsc.run_command(shlex.split(cmd))
    if rc or not os_out:
        logger.error(
            "Linux not reported ad_partner_mac value on bond: %s", bond_name
        )
        return False

    logger.info("Linux reported ad_partner_mac value: %s", os_out.strip())
    return True


def check_bond_ad_partner_mac_in_vds_client(host_name, bond_name):
    """
    Check if LACP bond (mode-4) ad_partner_mac value is reported by VDS client

    Args:
        host_name (str): Host name
        bond_name (str): Bond name

    Returns:
        str: MAC address, or empty string if not reported, or error has
            occurred

    """
    logger.info(
        "Checking if ad_partner_mac value is reported in vdsClient on bond:"
        " %s", bond_name
    )
    host_rsc = global_helper.get_host_resource_by_name(host_name=host_name)
    cmd_out = host_rsc.vds_client(cmd="Host.getCapabilities")
    if not cmd_out:
        logger.error(
            "vdsClient getVdsCapabilities returned empty response on host: %s",
            host_name
        )
        return ""

    cmd_out = cmd_out.get("bondings", dict()).get(bond_name, dict()).get(
        "ad_partner_mac"
    )

    if not cmd_out:
        logger.error(
            "vdsClient not reported ad_partner_mac value on bond: %s",
            bond_name
        )
        return ""

    logger.info("vdsClient reported ad_partner_mac value: %s", cmd_out)
    return cmd_out


def check_bond_ad_partner_mac_in_rest(host_name, bond_name):
    """
    Check if LACP bond (mode-4) ad_partner_mac value is reported by REST

    Args:
        host_name (str): Host name
        bond_name (str): Bond name

    Returns:
        str: MAC address, or empty string if not reported, or error has
            occurred
    """
    host_obj = ll_hosts.get_host_object(host_name=host_name)
    mac = ll_networks.get_bond_bonding_property(
        host=host_obj, bond=bond_name, property_name="ad_partner_mac"
    )
    if not mac:
        logger.error(
            "REST not reported ad_partner_mac value on bond: %s",
            bond_name
        )
        return ""

    logger.info("REST reported ad_partner_mac value: %s", mac.address)
    return mac.address
