#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
High level functions for host network API
http://www.ovirt.org/Features/HostNetworkingApi
http://www.ovirt.org/Features/NetworkingApi
"""

import logging
from art.core_api.apis_utils import data_st, TimeoutingSampler
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


@ll_general.generate_logs()
def remove_networks_from_host(host_name, networks, nic=None):
    """
    Remove network attachments from host

    Args:
        host_name (str): Host name
        networks (list): Networks to remove
        nic (str): NIC name

    Returns:
        bool: True if success, otherwise False
    """
    host_obj = ll_hosts.get_host_object(host_name=host_name)
    nic_obj = ll_hosts.get_host_nic(host=host_obj, nic=nic)
    attachments = ll_host_network.get_networks_attachments(
        networks=networks, nic=nic_obj, host=host_obj
    )
    if not attachments:
        return False

    for att in attachments:
        if not ll_host_network.NETWORK_ATTACHMENT_API.delete(att, True):
            return False
    return True


@ll_general.generate_logs()
def add_network_to_host(host_name, nic_name=None, **kwargs):
    """
    Attach network to host/host NIC

    Args:
        host_name (str): Host name
        nic_name (str): NIC name
        kwargs (dict): Network attachment kwargs

    Returns:
        bool: True if success, otherwise False
    """
    nic_name = nic_name if nic_name else kwargs.get("nic")
    host_obj = ll_hosts.get_host_object(host_name=host_name)
    nic_obj = ll_hosts.get_host_nic(host=host_obj, nic=nic_name)
    network_attachment_obj = ll_host_network.prepare_network_attachment_obj(
        host=host_obj, **kwargs
    )
    attachments_href = ll_host_network.get_attachment_href(nic=nic_obj)

    res = ll_host_network.NETWORK_ATTACHMENT_API.create(
        entity=network_attachment_obj,
        positive=True,
        collection=attachments_href,
        coll_elm_name=ll_host_network.NETWORK_ATTACHMENT
    )[1]
    return res


@ll_general.generate_logs()
def update_network_on_host(host_name, nic_name=None, **kwargs):
    """
    Update network on host/host NIC

    Args:
        host_name (str): Host name
        nic_name (str): NIC name
        kwargs (dict): Network attachment kwargs

    Returns:
        bool: True if success, otherwise False
    """
    host_obj = ll_hosts.get_host_object(host_name=host_name)
    nic_obj = ll_hosts.get_host_nic(host=host_obj, nic=nic_name)
    network_name = kwargs.get("network")
    orig_attachment_obj = ll_host_network.get_networks_attachments(
        networks=[network_name], nic=nic_obj, host=host_obj
    )
    if not orig_attachment_obj:
        return False

    network_attachment_obj = ll_host_network.prepare_network_attachment_obj(
        host=host_obj, **kwargs
    )
    return ll_host_network.NETWORK_ATTACHMENT_API.update(
        origEntity=orig_attachment_obj[0],
        newEntity=network_attachment_obj,
        positive=True
    )[1]


@ll_general.generate_logs(step=True)
def setup_networks(host_name, retry=False, **kwargs):
    """
    Sends setupNetwork action request to VDS host

    add > add1: Attach network net1 to host_nic dummy1 with IP (Can be more
        then one IP per attachment but only one primary)
    add > add2: Create BOND with two slaves without network attached
    add > add3: Create nicless network (Network without host_nic attached)
    add > add4: Create NIC with label
    add > add5: Add network with DNS
    remove: Remove net2 network (Can remove more then one network)
        Remove bond20 (Can remove more then one BOND)
    update > update1: Update existing  bond30 to 3 slaves
    update > update2: Attach existing attached network net3 to host_nic
        dummy10
    update > update3: Remove existing bond30 slave and add new bond30 slave
    update > update4: Remove slave from existing bond30
    update > update5: Add new slave to existing bond30
    update > update6: Update existing bond30 mode to 1
    update > update7: Update existing bond30 with DNS
    sync > sync net1 and net2

    Args:
        host_name (str): Host name
        retry (bool): True to retry Setup Network request until timeout is
            reached, False otherwise

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
                            },
                            "ip2": {
                                "address": "2001::1",
                                "netmask": "32",
                                "boot_protocol": "static",
                                "version": "v6"
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
                    "add5": {
                        "nic": dummy10,
                        "dns": ["8.8.8.8"]
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
                    "update7": {
                        "nic": "bond30",
                         "dns": ["8.8.8.8"]
                "sync": {
                    "networks": ["net1", "net2"]
                    },
                }
            }

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
    host = ll_hosts.get_host_object(host_name=host_name)

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
                host=host, dict_to_remove=remove
            )
        )
    if add:
        network_attachments, bonds, labels = (
            ll_host_network.prepare_add_for_setupnetworks(
                network_attachments=network_attachments,
                labels=labels,
                host=host,
                dict_to_add=add
            )
        )
    if update:
        network_attachments, bonds, labels = (
            ll_host_network.prepare_add_for_setupnetworks(
                network_attachments=network_attachments,
                labels=labels, host=host,
                dict_to_add=update,
                update=True
            )
        )
    if sync:
        networks = sync["networks"]
        nets_to_sync = (
            ll_host_network.get_networks_attachments(
                host=host, networks=networks
            )
        )
        synchronized_network_attachments.set_network_attachment(nets_to_sync)

    sn_params = {
        "entity": host,
        "action": SETUPNETWORKS,
        "positive": True,
        "modified_network_attachments": network_attachments,
        "removed_network_attachments": removed_network_attachments,
        "modified_bonds": bonds,
        "removed_bonds": removed_bonds,
        "modified_labels": labels,
        "removed_labels": removed_labels,
        "synchronized_network_attachments": synchronized_network_attachments,
        "connectivity_timeout": check_connectivity_timeout,
        "check_connectivity": check_connectivity
    }
    res = bool(ll_hosts.HOST_API.syncAction(**sn_params))
    if not res and retry:
        sample = TimeoutingSampler(
            timeout=15, sleep=1,
            func=lambda: bool(ll_hosts.HOST_API.syncAction(**sn_params))
        )
        res = sample.waitForFuncStatus(result=True)

    if persist and res:
        return ll_hosts.commit_network_config(host=host_name)
    return res


@ll_general.generate_logs(step=True)
def clean_host_interfaces(host_name, remove_gluster=False):
    """
    Remove all networks beside management network from host_name

    Args:
        host_name (str): Host name
        remove_gluster (bool): True to remove gluster network

    Returns:
        bool: True if success, otherwise False
    """
    networks = []
    bonds = []
    labels = []
    host = ll_hosts.get_host_object(host_name=host_name)
    attachments = ll_host_network.get_host_network_attachments(host=host)
    cl_obj = ll_clusters.get_cluster_object(
        cluster_name=ll_hosts.get_host_cluster(host=host.name),
        all_content=True
    )
    mgmt_net_name = ll_networks.NET_API.find(
            val=cl_obj.get_management_network().get_id(),
            attribute="id"
    ).get_name()
    host_nics = ll_hosts.get_host_nics_list(host=host)
    for att in attachments:
        att_network_name = ll_general.get_object_name_by_id(
            object_api=ll_networks.NET_API,
            object_id=att.get_network().get_id()
        )

        if not remove_gluster:
            if ll_networks.is_gluster_network(
                network=att_network_name, cluster=host.get_cluster()
            ):
                continue

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

    if not ll_host_network.remove_unmanaged_networks(host=host):
        return False

    if networks + bonds + labels:
        kwargs = {
            "remove": {
                NETWORKS: networks,
                BONDS: bonds,
                LABELS: labels
            }
        }
        res = setup_networks(host_name=host_name, persist=True, **kwargs)
        if not res:
            return False
    return True


@ll_general.generate_logs(warn=True)
def get_attached_networks_names_from_host_nic(host_name, nic):
    """
    Get attached networks names from host NIC

    Args:
        host_name (str): Host name
        nic (str): NIC name

    Returns:
        list: Networks names from host NIC
    """
    host_obj = ll_hosts.get_host_object(host_name=host_name)
    nic_obj = ll_hosts.get_host_nic(host=host_obj, nic=nic)
    attachments = ll_host_network.get_host_nic_network_attachments(
        nic=nic_obj
    )
    return [
        ll_general.get_object_name_by_id(
            object_api=ll_networks.NET_API,
            object_id=att.get_network().get_id()
        ) for att in attachments
    ]


@ll_general.generate_logs()
def get_host_unmanaged_networks_info(host_name):
    """
    Get un-managed host networks info (name and host_nic)

    Args:
        host_name (str): Host name

    Returns:
        dict: un-managed networks info
    """
    res = dict()
    host_obj = ll_hosts.get_host_object(host_name=host_name)
    unmanaged_networks = ll_host_network.get_host_unmanaged_objects(
        host=host_obj
    )
    for un in unmanaged_networks:
        name = un.get_name()
        host_nic = un.get_host_nic().get_name()
        res[name] = host_nic
    return res


@ll_general.generate_logs()
def get_unsync_network_attachments(host_name, networks=None):
    """
    Get un-synced network attachment

    Args:
        host_name (str): Host name
        networks (list): Networks names

    Returns:
        list: Un-synced attachments list
    """
    host_obj = ll_hosts.get_host_object(host_name=host_name)
    if networks:
        attachments = ll_host_network.get_networks_attachments(
            host=host_obj, networks=networks
        )
    else:
        attachments = ll_host_network.get_host_network_attachments(
            host=host_obj
        )
    return [att for att in attachments if not att.in_sync]


@ll_general.generate_logs()
def get_networks_unsync_reason(host_name, networks=None):
    """
    Get un-synced network reason

    Args:
        host_name (str): Host name
        networks (list): Networks names

    Returns:
        dict: Un-synced reasons for each network
    """
    res = dict()
    report_name_dict = dict()
    attachments = get_unsync_network_attachments(
        host_name=host_name, networks=networks
    )
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


@ll_general.generate_logs(warn=True)
def check_network_on_nic(network, host, nic):
    """
    Checks if network resides on Host NIC via NIC attachments

    Args:
        network (str): Network name to check
        host (str): Host name
        nic (str): NIC name on Host

    Returns:
        bool: True if network resides on Host NIC, otherwise False
    """
    networks = get_attached_networks_names_from_host_nic(
        host_name=host, nic=nic
    )
    return network in networks
