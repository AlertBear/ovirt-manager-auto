"""
Helper foc mac_addr tests
"""

import shlex

import rhevmtests.networking.config as network_config
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
from art.rhevm_api.tests_lib.low_level import (
    events as ll_events,
    hosts as ll_hosts
)


def run_macaddr_test(network):
    """
    Check if MACADDR is set in IFCFG

    Args:
        network (str): Network name

    Returns:
        bool: True If MACADDR in bond1 ifcfg file, False otherwise
    """
    bond = "bond1"
    cat_cmd = "cat {ifcfg_path}ifcfg-{bond}".format(
        ifcfg_path=hl_networks.IFCFG_FILE_PATH, bond=bond
    )
    last_event = ll_events.get_max_event_id()
    if not ll_hosts.refresh_host_capabilities(
        host=network_config.HOST_0_NAME, start_event_id=last_event
    ):
        return False

    sn_dict = {
        "add": {
            "1": {
                "network": network,
                "nic": bond,
            }
        }
    }
    if not hl_host_network.setup_networks(
        host_name=network_config.HOST_0_NAME, **sn_dict
    ):
        return False

    ifcfg_out = network_config.VDS_0_HOST.run_command(
        command=shlex.split(cat_cmd)
    )[1]

    return "MACADDR" in ifcfg_out
