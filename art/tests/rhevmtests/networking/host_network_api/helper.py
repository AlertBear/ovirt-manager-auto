#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for Host Network API
"""

import logging
import config as conf
from art.unittest_lib import attr
import art.unittest_lib as unit_lib
import rhevmtests.networking as networking
import art.core_api.apis_utils as api_utils
import art.rhevm_api.utils.test_utils as test_utils
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Host_Network_API_Helper")


def check_dummy_on_host(host, positive=True):
    """
    Check if dummy interfaces exist/not exist on the host

    :param host: Host name
    :type host: str
    :param positive: True to check if dummy exist and False to make sure
                     it's not
    :type positive: bool
    :raise: NET_EXCEPTION
    """
    for_log = "exists" if positive else "not exist"
    log = "Dummy interface %s on engine" % for_log
    logger.info("Refresh %s capabilities", host)
    host_obj = ll_hosts.HOST_API.find(host)
    refresh_href = "{0};force".format(host_obj.get_href())
    ll_hosts.HOST_API.get(href=refresh_href)

    logger.info("Check if dummy_0 %s on %s via engine", for_log, host)
    sample = api_utils.TimeoutingSampler(
        timeout=networking.config.SAMPLER_TIMEOUT, sleep=1,
        func=conf.network_lib.check_dummy_on_host_interfaces,
        host_name=host, dummy_name="dummy_0"
    )
    if not sample.waitForFuncStatus(result=positive):
        if positive:
            raise conf.NET_EXCEPTION(log)
        else:
            logger.error(log)


def attach_network_attachment(
    network_dict, network, nic=None, positive=True
):
    """
    Attach network attachment to host NIC via NIC or host href

    :param network_dict: Network dict
    :type network_dict: dict
    :param network: Network name
    :type network: str
    :param nic: NIC name
    :type nic: str
    :param positive: Expected status
    :type positive: bool
    :raise: NetworkException
    """
    nic_log = nic if nic else network_dict.get("nic")
    logger.info(
        "Attaching %s to %s on %s", network, nic_log, conf.HOST_4
    )
    network_to_attach = network_dict.pop("network")
    res = hl_host_network.add_network_to_host(
        host_name=conf.HOST_4, network=network_to_attach, nic_name=nic,
        **network_dict
    )
    if res != positive:
        raise conf.NET_EXCEPTION(
            "Failed to attach %s to %s on %s" % (network, nic_log, conf.HOST_4)
        )


def prepare_networks_on_dc(
    networks_dict, dc=conf.DC_NAME, cluster=conf.CLUSTER_2
):
    """
    Create and attach all networks that are needed for all cases

    :param networks_dict: Networks dict
    :type networks_dict: dict
    :param dc: Datacenter name
    :type dc: str
    :param cluster: Cluster name
    :type cluster: str
    :raise: NetworkException
    """
    logger.info("Add networks to %s/%s", dc, cluster)
    if not hl_networks.createAndAttachNetworkSN(
        data_center=dc, cluster=cluster, network_dict=networks_dict
    ):
        raise conf.NET_EXCEPTION(
            "Failed to add networks to %s/%s" % (dc, cluster)
        )


def networks_sync_status(networks):
    """
    Get networks sync status

    :param networks: List of networks
    :type networks: list
    :return: True if sync else False
    :type: bool
    """
    for net in networks:
        logger.info("Get %s attachment", net)
        try:
            attachment = ll_host_network.get_networks_attachments(
                conf.HOST_4, [net]
            )[0]
        except IndexError:
            raise conf.NET_EXCEPTION("%s not found" % net)

        logger.info("Check if %s is unsync", net)
        if not ll_host_network.get_attachment_sync_status(attachment):
            logger.info("%s is not sync" % net)
            return False
    return True


def networks_unsync_reasons(net_sync_reason):
    """
    Check the reason for unsync networks is correct

    :param net_sync_reason: List of tuples of (network_name, unsync_reason)
    :type net_sync_reason: dict
    :return: True if unsync reason is correct
    :rtype: bool
    """
    for net, val in net_sync_reason.iteritems():
        reas = val.keys()[0]
        dict_to_compare = net_sync_reason[net][reas]
        logger.info("Check if %s unsync reason is %s", net, reas)
        unsync_reason = hl_host_network.get_networks_unsync_reason(
            conf.HOST_4, [net]
        )
        if not unsync_reason[net][reas] == dict_to_compare:
            logger.error(
                "Expected reasons are %s, got %s instead",
                dict_to_compare, unsync_reason[net][reas]
            )
            return False
    return True


def get_networks_sync_status_and_unsync_reason(net_sync_reason):
    """
    Check if networks attachment is unsync and check the unsync reason

    :param net_sync_reason: List of tuple of (network_name, unsync_reason)
    :type net_sync_reason: dict
    :raise: conf.NET_EXCEPTION
    """
    networks = [i for i in net_sync_reason]
    if networks_sync_status(networks):
        raise conf.NET_EXCEPTION("%s are synced but shouldn't" % networks)
    if not networks_unsync_reasons(net_sync_reason):
        raise conf.NET_EXCEPTION("%s unsync reason is incorrect" % networks)


def sync_networks(networks):
    """
    Sync the networks

    :param networks: List of networks to sync
    :type networks: list
    :raise: conf.NET_EXCEPTION
    """
    network_sync_dict = {
        "sync": {
            "networks": networks
        }
    }
    logger.info("syncing %s", networks)
    if not hl_host_network.setup_networks(
        host_name=conf.HOST_4, **network_sync_dict
    ):
        raise conf.NET_EXCEPTION("Failed to sync %s" % networks)

    if not networks_sync_status(networks):
        raise conf.NET_EXCEPTION


@attr(tier=2)
class TestHostNetworkApiTestCaseBase(unit_lib.NetworkTest):
    """
    base class which provides teardown class method for each test case
    """
    @classmethod
    def teardown_class(cls):
        """
        Remove all networks from the host NICs.
        """
        logger.info("Removing all networks from %s", conf.HOST_4)
        if not hl_host_network.clean_host_interfaces(conf.HOST_4):
            logger.error(
                "Failed to remove all networks from %s", conf.HOST_4
            )


def remove_networks_from_setup():
    """
    Remove all networks from setup
    """
    logger.info("Remove networks from setup")
    if not hl_networks.remove_net_from_setup(
        host=conf.VDS_HOSTS_4, auto_nics=[0], data_center=conf.DC_NAME,
        all_net=True, mgmt_network=conf.MGMT_BRIDGE
    ):
        logger.error(
            "Failed to remove %s from %s and %s",
            conf.NIC_DICT, conf.DC_NAME, conf.HOST_4
        )


def set_temp_ip_and_refresh_capabilities(interface, ip=None, netmask="24"):
    """
    Set temporary IP on interface and refresh capabilities

    :param interface: Interface name
    :type interface: str
    :param ip: IP to set
    :type ip: str
    :param netmask: Netmask for the IP
    :type netmask: str
    :raise: NET_EXCEPTION
    """
    int_ip = conf.VDS_HOSTS_4.network.find_ip_by_int(interface)
    host_ips = conf.VDS_HOSTS_4.network.find_ips()
    try:
        old_ip = [i for i in host_ips[1] if int_ip in i][0]
    except IndexError:
        old_ip = None
    if old_ip:
        logger.info("Delete IP %s from %s", old_ip, interface)
        cmd = ["ip", "addr", "del", "%s" % old_ip, "dev", interface]
        rc, out, err = conf.VDS_HOSTS_4.executor().run_cmd(cmd)
        if rc:
            raise conf.NET_EXCEPTION(
                "Failed to delete %s from %s. ERR: %s. %s" % (
                    old_ip, interface, err, out
                )
            )
    ip = int_ip if not ip else ip
    logger.info("Setting %s/%s on %s", ip, netmask, interface)
    if not test_utils.configure_temp_static_ip(
        host=conf.VDS_HOSTS_4.executor(), ip=ip, nic=interface, netmask=netmask
    ):
        raise conf.NET_EXCEPTION(
            "Failed to set %s/%s on %s" % (ip, netmask, interface)
        )
    host_obj = ll_hosts.HOST_API.find(conf.HOST_4)
    refresh_href = "{0};force".format(host_obj.get_href())
    ll_hosts.HOST_API.get(href=refresh_href)
