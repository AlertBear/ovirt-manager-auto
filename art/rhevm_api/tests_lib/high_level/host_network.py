#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
High level functions for host network API
http://www.ovirt.org/Features/HostNetworkingApi
http://www.ovirt.org/Features/NetworkingApi
"""

import logging
from art.core_api.apis_utils import data_st
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network

logger = logging.getLogger("art.hl_lib.host_net")

CONNECTIVITY_TIMEOUT = 60
NETWORKS = "networks"
NETWORK = "network"
BONDS = "bonds"
BOND = "bond"
UPDATE = "update"
SLAVES = "slaves"
LABELS = "labels"
NIC = "nic"
MODE = "mode"
MIIMON = "miimon"
SETUPNETWORKS = "setupnetworks"


def get_network_attachment_reported_values(
    host_name, network, nic=None, values=list()
):
    """
    Get network attachment values

    :param host_name: Host name
    :type host_name: str
    :param network: Network name
    :type network: str
    :param nic: NIC name
    :type nic: str
    :param values: Values to get example: ["mtu", "vlan", "bridged"]
    :type values: list
    :return: Network attachment values
    :rtype: dict
    """
    res = dict()
    attachment = ll_host_network.get_networks_attachments(
        host_name, [network], nic
    )
    if not attachment:
        return res

    reported = ll_host_network.get_attachment_reported_configurations(
        attachment[0]
    )

    for report in reported:
        key = report.get_name()
        res[key] = report.get_value()

    if values:
        return dict((i, res[i]) for i in values)
    return res


def remove_networks_from_host(host_name, networks, nic=None):
    """
    Remove network attachments from host

    :param host_name: Host name
    :type host_name: str
    :param networks: Networks to remove
    :type networks: list
    :param nic: NIC name
    :type nic: str
    :return: True/False
    :rtype: bool
    """
    attachments = ll_host_network.get_networks_attachments(
        host_name, networks, nic
    )
    if not attachments:
        return False

    logger.info(
        "Remove networks %s attachments from host %s", networks, host_name
    )
    for att in attachments:
        if not ll_host_network.NETWORK_ATTACHMENT_API.delete(att, True):
            logger.error(
                "Failed to remove networks %s attachments from host %s",
                networks, host_name
            )
            return False
    return True


def add_network_to_host(host_name, nic_name=None, **kwargs):
    """
    Attach network to host/host NIC

    :param host_name: Host name
    :type host_name: str
    :param nic_name: NIC name
    :type nic_name: str
    :param kwargs: Network attachment kwargs
    :type kwargs: dict
    :return: True/False
    :rtype: bool
    """
    nic_log = "to host NIC %s" % nic_name if nic_name else ""
    network = kwargs.get("network")
    log_info, log_error = ll_general.get_log_msg(
        action="Attach", obj_type="network", obj_name=network,
        extra_txt=nic_log, **kwargs
    )
    network_attachment_obj = ll_host_network.prepare_network_attachment_obj(
        host_name, **kwargs
    )
    attachments_href = ll_host_network.get_attachment_href(host_name, nic_name)

    logger.info(log_info)
    res = ll_host_network.NETWORK_ATTACHMENT_API.create(
        entity=network_attachment_obj,
        positive=True,
        collection=attachments_href,
        coll_elm_name=ll_host_network.NETWORK_ATTACHMENT
    )[1]
    if not res:
        logger.error(log_error)
    return res


def update_network_on_host(host_name, nic_name=None, **kwargs):
    """
    Update network on host/host NIC

    :param host_name: Host name
    :type host_name: str
    :param nic_name: NIC name
    :type nic_name: str
    :param kwargs: Network attachment kwargs
    :type kwargs: dict
    :return: True/False
    :rtype: bool
    """
    network_name = kwargs.get("network")
    nic_log = "to host NIC %s" if nic_name else ""
    log_info, log_error = ll_general.get_log_msg(
        action="Update", obj_type="network", obj_name=network_name,
        extra_txt=nic_log, **kwargs
    )
    orig_attachment_obj = ll_host_network.get_networks_attachments(
        host_name, [network_name], nic_name
    )
    if not orig_attachment_obj:
        return False

    network_attachment_obj = ll_host_network.prepare_network_attachment_obj(
        host_name, **kwargs
    )
    logger.info(log_info)
    res = ll_host_network.NETWORK_ATTACHMENT_API.update(
        orig_attachment_obj[0], network_attachment_obj, True
    )[1]
    if not res:
        logger.error(log_error)
    return res


def setup_networks(host_name, **kwargs):
    """
    Sends setupNetwork action request to VDS host

    add > add1: Attach network net1 to host_nic dummy1 with IP (Can be more
        then one IP per attachment but only one primary)
    add > add2: Create BOND with two slaves without network attached
    add > add3: Create nicless network (Network without host_nic attached)
    remove: Remove net2 network (Can remove more then one network)
        Remove bond20 (Can remove more then one BOND)
    update > update1: Update existing  bond30 to 3 slaves
    update > update2: Attach existing attached network net3 to host_nic
        dummy10
    update > update3: Remove existing bond30 slave and add new bond30 slave
    update > update4: Remove slave from existing bond30
    update > update5: Add new slave to existing bond30
    update > update6: Update existing bond30 mode to 1
    sync > sync net1 and net2

    Args:
        host_name (str): Host name

    Keyword Args:
            persist (bool): Make network settings persistent on the host
            dict (dict): Networks settings to be used in setup

    Example:
        dict = {
                "add": {
                    "add1": {
                        "datacenter": "dc1" # in case of same network name
                        "network": "net1",
                        "nic": "dummy1",
                        "ip": {
                            "ip1": {
                                "address": "1.1.1.1",
                                "netmask": "255.255.255.0",
                                "boot_protocol": "static",
                                "primary": True
                            }
                        }
                    },
                    "add2": {
                        "nic": "bond10",
                        "slaves": ["dummy2", "dummy3"]
                        },
                    "add3": {
                        "network": "net4"
                        },
                    "add4": {
                        "nic": dummy10,
                        "labels": ["lb1"]
                    },
                    "remove": {
                        "networks": ["net2"],
                        "bonds": ["bond20"],
                        "labels": ["lb1", "lb2"]
                        },
                    "update": {
                        "update1": {
                        "nic": "bond30",
                        "slaves": ["dummy6", "dummy7", "dummy8"]
                        },
                    "update2": {
                        "nic": "dummy10",
                        "network": "net3"
                        },
                    "update3": {
                        "nic": "bond30",
                        "slaves": ["dummy7", "dummy9"]
                    },
                    "update4": {
                        "nic": "bond30",
                        "slaves": ["dummy9"]
                    },
                    "update5": {
                        "nic": "bond30",
                        "slaves": ["dummy10"]
                    },
                    "update6": {
                        "nic": "bond30",
                         "mode": 1
                },
                "sync": {
                    "networks": ["net1", "net2"]
                    },
                }
            }

        setup_networks(host_name=hostname, kwargs=dict)
        setup_networks(host_name=hostname, kwargs=dict, persist=True)

    Returns:
        bool: True if success, otherwise False
    """
    bonds = data_st.HostNics()
    removed_bonds = data_st.HostNics()
    network_attachments = data_st.NetworkAttachments()
    removed_network_attachments = data_st.NetworkAttachments()
    labels = data_st.NetworkLabels()
    removed_labels = data_st.NetworkLabels()
    synchronized_network_attachments = data_st.NetworkAttachments()
    host = ll_hosts.HOST_API.find(host_name)

    remove = kwargs.get("remove")
    add = kwargs.get("add")
    update = kwargs.get("update")
    sync = kwargs.get("sync")
    persist = kwargs.get("persist", False)
    check_connectivity = kwargs.get("check_connectivity", True)
    check_connectivity_timeout = kwargs.get(
        "check_connectivity_timeout", CONNECTIVITY_TIMEOUT
    )

    if remove:
        removed_bonds, removed_network_attachments, removed_labels = (
            ll_host_network.prepare_remove_for_setupnetworks(
                host_name, remove
            )
        )
    if add:
        network_attachments, bonds, labels = (
            ll_host_network.prepare_add_for_setupnetworks(
                network_attachments, labels, host_name, add
            )
        )
    if update:
        network_attachments, bonds, labels = (
            ll_host_network.prepare_add_for_setupnetworks(
                network_attachments, labels, host_name, update, True
            )
        )
    if sync:
        networks = sync["networks"]
        nets_to_sync = (
            ll_host_network.get_networks_attachments(host_name, networks)
        )
        synchronized_network_attachments.set_network_attachment(nets_to_sync)

    logger.info("Sending SetupNetworks to %s with %s", host_name, kwargs)
    res = bool(
        ll_hosts.HOST_API.syncAction(
            entity=host, action=SETUPNETWORKS, positive=True,
            modified_network_attachments=network_attachments,
            removed_network_attachments=removed_network_attachments,
            modified_bonds=bonds, removed_bonds=removed_bonds,
            modified_labels=labels, removed_labels=removed_labels,
            synchronized_network_attachments=synchronized_network_attachments,
            connectivity_timeout=check_connectivity_timeout,
            check_connectivity=check_connectivity
        )
    )

    if not res:
        logger.error("Failed to send SetupNetworks to %s", host_name)
    if persist and res:
            res = ll_hosts.commit_network_config(host=host_name)

    return res


def clean_host_interfaces(host_name):
    """
    Remove all networks beside management network from host

    :param host_name: Host name
    :type host_name: str
    :return: True/False
    :rtype: bool
    """
    logger.info("Clean %s interfaces", host_name)
    networks = []
    bonds = []
    labels = []
    host = ll_hosts.HOST_API.find(host_name)
    host_cl = ll_general.get_object_name_by_id(
        ll_clusters.CLUSTER_API, host.get_cluster().get_id()
    )
    attachments = ll_host_network.get_host_network_attachments(host_name)
    mgmt_net_name = ll_networks.NET_API.find(
        ll_clusters.get_cluster_management_network(host_cl).get_id(), "id"
    ).get_name()
    host_nics = ll_hosts.get_host_nics_list(host_name)
    for att in attachments:
        att_network_name = ll_general.get_object_name_by_id(
            ll_networks.NET_API, att.get_network().get_id()
        )
        if att_network_name != mgmt_net_name:
            networks.append(att_network_name)

    for nic in host_nics:
        nic_name = nic.get_name()
        if nic_name.startswith(BOND) and "." not in nic_name:
            nic_network = nic.get_network()
            if nic_network:
                if nic_network.get_name() != mgmt_net_name:
                    bonds.append(nic_name)
            else:
                bonds.append(nic_name)

        labels.extend(
            [i.get_id() for i in ll_networks.get_host_nic_labels(nic=nic)]
        )

    if not ll_host_network.remove_unmanaged_networks(host_name):
        return False

    if networks + bonds + labels:
        kwargs = {
            "remove": {
                NETWORKS: networks,
                BONDS: bonds,
                LABELS: labels
            }
        }
        res = setup_networks(host_name, **kwargs)
        if not res:
            logger.error("Failed to clean %s interfaces", host_name)
            return False
    return True


def get_attached_networks_names_from_host_nic(host_name, nic):
    """
    Get attached networks names from host NIC

    :param host_name: Host name
    :type host_name: str
    :param nic: NIC name
    :type nic: str
    :return: Networks names from host NIC
    :rtype: list
    """
    attachments = ll_host_network.get_host_nic_network_attachments(
        host_name, nic
    )
    return [
        ll_general.get_object_name_by_id(
            ll_networks.NET_API, att.get_network().get_id()
        ) for att in attachments
    ]


def get_host_nic_name_from_network_attachment(host_name, network):
    """
    Get host NIC name from network attachment

    :param host_name: Host name
    :type host_name: str
    :param network: Network name
    :type network: str
    :return: Host NIC name
    :rtype: str
    """
    attachment = ll_host_network.get_networks_attachments(
        host_name, [network]
    )
    if not attachment:
        return None

    host_nics = ll_hosts.get_host_nics_list(host_name)
    attachment_id = attachment[0].get_host_nic().get_id()
    names = [
        i.get_name() for i in host_nics if attachment_id == i.get_id()
    ]
    return names[0] if names else None


def get_host_unmanaged_networks_info(host_name):
    """
    Get unmanaged host networks info (name and host_nic)

    :param host_name: Host name
    :type host_name: str
    :return: unmanaged networks info
    :rtype: dict
    """
    res = dict()
    unmanaged_networks = ll_host_network.get_host_unmanaged_objects(host_name)
    for un in unmanaged_networks:
        name = un.get_name()
        host_nic = un.get_host_nic().get_name()
        res[name] = host_nic
    return res


def get_unsync_network_attachments(host_name, networks=None):
    """
    Get unsynced network attachment

    :param host_name: Host name
    :type host_name: str
    :param networks: Networks names
    :type networks: list
    :return: Unsynced attachments list
    :rtype: list
    """
    if networks:
        attachments = ll_host_network.get_networks_attachments(
            host_name, networks
        )
    else:
        attachments = ll_host_network.get_host_network_attachments(host_name)
    return [
        att for att in attachments if not
        ll_host_network.get_attachment_sync_status(att)
    ]


def get_networks_unsync_reason(host_name, networks=None):
    """
    Get unsynced network reason

    :param host_name: Host name
    :type host_name: str
    :param networks: Networks names
    :type networks: list
    :return: Unsynced reasons for each network
    :rtype: dict
    """
    res = dict()
    report_name_dict = dict()
    attachments = get_unsync_network_attachments(host_name, networks)
    for att in attachments:
        net_name = ll_host_network.get_network_name_from_attachment(att)
        reported = ll_host_network.get_attachment_reported_configurations(att)
        for report in reported:
            reported_dict = dict()
            report_name = report.get_name()
            reported_dict["expected"] = report.get_expected_value()
            reported_dict["actual"] = report.get_actual_value()
            report_name_dict[report_name] = reported_dict
        res[net_name] = report_name_dict
    return res
