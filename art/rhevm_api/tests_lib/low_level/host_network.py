#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Low level functions for host network API
http://www.ovirt.org/Features/HostNetworkingApi
http://www.ovirt.org/Features/NetworkingApi
"""

import logging

import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
from art.core_api.apis_utils import data_st
from art.rhevm_api.utils.test_utils import get_api

logger = logging.getLogger("art.ll_lib.host_nets")

NETWORK = "network"
BOND = "bond"
UPDATE = "update"
SLAVES = "slaves"
LABELS = "labels"
NIC = "nic"
MODE = "mode"
MIIMON = "miimon"
NETWORKS = "networks"
BONDS = "bonds"
NETWORKATTACHMENTS = "networkattachments"
NETWORK_ATTACHMENT = "network_attachment"
UNMANAGEDNETWORKS = "unmanagednetworks"
UNMANAGED_NETWORK = "unmanaged_network"
NETWORK_ATTACHMENT_API = get_api(NETWORK_ATTACHMENT, NETWORKATTACHMENTS)
UNMANAGED_NETWORKS_API = get_api(UNMANAGED_NETWORK, UNMANAGEDNETWORKS)


def get_host_network_attachments(host_name):
    """
    Get all host network attachments from:
    api/hosts/<host_id>/networkattachments

    Args:
        host_name (str): Host name

    Returns:
        list: Host network attachments
    """
    logger.info("Get host %s network attachments", host_name)
    host = ll_hosts.HOST_API.find(host_name)
    res = ll_hosts.HOST_API.getElemFromLink(
        host, NETWORKATTACHMENTS, NETWORK_ATTACHMENT
    )
    if not res:
        logger.error("Failed to get host %s network attachments", host_name)
    return res


def get_host_nic_network_attachments(host_name, nic):
    """
    Get host NIC network attachments from:
    api/hosts/<host_id>/nics/<nic_id>/networkattachments

    Args:
        host_name (str): Host name

    Returns:
        list: Host NIC network attachments
    """
    logger.info("Get host %s NIC %s network attachments", host_name, nic)
    host_nic = ll_hosts.get_host_nic(host_name, nic)
    res = ll_hosts.HOST_NICS_API.getElemFromLink(
        host_nic, NETWORKATTACHMENTS, NETWORK_ATTACHMENT
    )
    if not res:
        logger.error(
            "Failed to get host %s NIC %s network attachments", host_name, nic
        )
    return res


def get_networks_attachments(host_name, networks, nic=None):
    """
    Get networks attachments by network names

    Args:
        host_name (str): Host name
        networks (list): Network names list
        nic (str): NIC name

    Returns:
        list: Network attachments
    """
    func = "get_host{0}network_attachments".format("_nic_" if nic else "_")
    args = (host_name, nic) if nic else (host_name,)
    attachments = eval(func)(*args)

    return [
        att for att in attachments if get_network_name_from_attachment(att)
        in networks
    ]


def get_host_unmanaged_objects(host_name):
    """
    Get host unmanaged objects

    Args:
        host_name (str): Host name

    Returns:
        list: Host unmanaged objects
    """
    host = ll_hosts.HOST_API.find(host_name)
    return ll_hosts.HOST_API.getElemFromLink(
        host, UNMANAGEDNETWORKS, UNMANAGED_NETWORK
    )


def get_attachment_sync_status(attachment):
    """
    Get attachment sync status

    Args:
        attachment (NetworkAttachment): Network attachment

    Returns:
        bool: True if network is synced else False
    """
    return attachment.in_sync


def get_attachment_reported_configurations(attachment):
    """
    Get attachment reported configurations

    Args:
        attachment (NetworkAttachment): Network attachment

    Returns:
        list: Network attachment reported configurations
    """
    reported_ = attachment.get_reported_configurations()
    return reported_.get_reported_configuration()


def get_attachment_href(host_name, nic=None):
    """
    Get host/NIC attachment href

    Args:
        host_name (str): Host name
        nic (str): NIC name

    Returns:
        str: Host/NIC attachment href
    """
    api = ll_hosts.HOST_NICS_API if nic else ll_hosts.HOST_API
    if nic:
        entity = ll_hosts.get_host_nic(host_name, nic)
    else:
        entity = ll_hosts.HOST_API.find(host_name)

    return api.getElemFromLink(
        entity, NETWORKATTACHMENTS, get_href=True
    )


def prepare_network_attachment_obj(host_name, **kwargs):
    """
    Prepare network attachment object

    Args:
        host_name (str): Host name

    Keyword Args:
        update (bool): True to update network attachment
        ip (dict): IP dict
        network (str): Network name
        nic (str): NIC name
        override_configuration (bool): True to override configuration
        properties (dict): Properties dict
        datacenter (str): Data center name
        cluster (str): Cluster name
        qos (dict): QoS dict
        dns (list): DNS servers list

    Returns:
        NetworkAttachment: Network attachment object
    """
    network = kwargs.get(NETWORK)
    ip_none = {
        "ip": {
            "boot_protocol": "none"
        }
    }
    ip = kwargs.get("ip") or ip_none
    update = kwargs.get(UPDATE)
    nic = kwargs.get(NIC)
    override_configuration = kwargs.get("override_configuration")
    properties = kwargs.get("properties")
    datacenter = kwargs.get("datacenter")
    cluster = kwargs.get("cluster")
    qos = kwargs.get("qos")

    if update:
        network_attachment_obj = get_networks_attachments(
            host_name, [network]
        )
        if not network_attachment_obj:
            return None
        network_attachment_obj = network_attachment_obj[0]
    else:
        network_attachment_obj = data_st.NetworkAttachment()

    if override_configuration:
        network_attachment_obj.set_override_configuration(
            override_configuration
        )

    if properties:
        properties_obj = ll_networks.create_properties(**properties)
        network_attachment_obj.set_properties(properties_obj)

    if qos:
        qos_obj = ll_datacenters.prepare_qos_obj(**qos)
        network_attachment_obj.set_qos(qos_obj)

    if nic:
        if BOND in nic:
            host_nic = ll_hosts.get_host_nic(host_name, nic)
            if not host_nic:
                host_nic = data_st.HostNic()
                host_nic.set_name(nic)
        else:
            host_nic = ll_hosts.get_host_nic(host_name, nic)

        network_attachment_obj.set_host_nic(host_nic)

    network_attachment_obj = prepare_ip_object(
        network_attachment_obj, ip
    )

    if network and not update:
        add_network = ll_networks.find_network(
            network=network, data_center=datacenter, cluster=cluster
        )
        network_attachment_obj.set_network(add_network)

    return network_attachment_obj


def prepare_bond_attachment_obj(host_name, **kwargs):
    """
    Prepares a BOND host_nic object

    Args:
        host_name (str): Engine hostname

    Keyword Args:
            slaves (list): List of strings that represents slaves names
            nic (str): NIC name
            update (bool): True for update mode
            mode (int): Specifies a BOND mode type (0=Round-Robin,
                1=Active-Backup, ...)
            miimon (int): Specifies, in milliseconds, how often MII link
                monitoring occurs

    Returns:
        HostNic: HostNic object
    """
    slave_list = kwargs.get(SLAVES)
    nic_name = kwargs.get(NIC)
    update = kwargs.get(UPDATE)
    mode = kwargs.get(MODE)
    mii_mon = kwargs.get(MIIMON)

    if update:
        host_nic_bond_obj = ll_hosts.get_host_nic(host=host_name, nic=nic_name)
        bond_obj = host_nic_bond_obj.get_bonding()
        slaves = bond_obj.get_slaves()
        options = bond_obj.get_options()
        if mode:
            option = [i for i in options.get_option() if i.name == MODE][0]
            option.set_value(mode)
        if mii_mon:
            option = [i for i in options.get_option() if i.name == MIIMON][0]
            option.set_value(mii_mon)
    else:
        host_nic_bond_obj = data_st.HostNic()
        bond_obj = data_st.Bonding()
        options = data_st.Options()
        slaves = data_st.HostNics()
        if mode is not None:  # BOND mode can be 0
            options.add_option(data_st.Option(name=MODE, value=str(mode)))
        if mii_mon:
            options.add_option(data_st.Option(name=MIIMON, value=mii_mon))

    if nic_name:
        host_nic_bond_obj.set_name(nic_name)

    if slave_list:
        host_slave_nics = slaves.get_host_nic()
        try:
            host_slave_dict = dict((i.id, i) for i in host_slave_nics)
        except TypeError:
            host_slave_dict = dict()

        for slave in slave_list:
            host_nic = ll_hosts.get_host_nic(host=host_name, nic=slave)
            if host_nic and host_slave_dict.get(host_nic.id):
                del host_slave_dict[host_nic.id]
            else:
                slave_object = data_st.HostNic(name=slave.strip())
                host_slave_dict[slave] = slave_object

        slaves.set_host_nic(host_slave_dict.values())
        bond_obj.set_slaves(slaves)

    bond_obj.set_options(options)
    host_nic_bond_obj.set_bonding(bond_obj)
    return host_nic_bond_obj


def prepare_remove_for_setupnetworks(host_name, dict_to_remove):
    """
    Prepare HostNics/NetworkAttachments objects of networks and BONDs
    for setup_networks function

    Args:
        host_name (str): Host name
        dict_to_remove (dict): Dict with networks/BONDs to remove

    Returns:
        tuple: HostNics/NetworkAttachments/labels objects
    """
    removed_bonds = data_st.HostNics()
    removed_network_attachments = data_st.NetworkAttachments()
    removed_labels = data_st.NetworkLabels()
    for k in dict_to_remove.keys():
        if k == NETWORKS:
            attach = get_networks_attachments(
                host_name, dict_to_remove.get(NETWORKS)
            )
            for att in attach:
                removed_network_attachments.add_network_attachment(att)

        if k == BONDS:
            for bond in dict_to_remove.get(BONDS):
                bond_to_remove = ll_hosts.get_host_nic(host_name, bond)
                removed_bonds.add_host_nic(bond_to_remove)

        if k == LABELS:
            labels_list = dict_to_remove.get(LABELS)
            host_nics = ll_hosts.get_host_nics_list(host=host_name)
            label_objs = ll_networks.get_host_nic_label_objs_by_id(
                host_nics=host_nics, labels_id=labels_list
            )
            for label_to_remove in label_objs:
                removed_labels.add_network_label(label_to_remove)

    return removed_bonds, removed_network_attachments, removed_labels


def prepare_add_for_setupnetworks(
    network_attachments, labels, host_name, dict_to_add, update=False
):
    """
    Prepare NetworkAttachment object for setup_networks function

    Args:
        network_attachments (NetworkAttachment): Network attachment
        labels (Labels): labels object
        host_name (str): Host name
        dict_to_add (dict): Dict with networks to dict_to_add
        update (bool): True for update networks/BONDs/Labels

    Returns:
        tuple: Network_attachments, bonds and labels objects
    """
    bonds = data_st.HostNics()
    for k, v in dict_to_add.iteritems():
        if update:
            v[UPDATE] = True

        if v.get(SLAVES) or v.get(MODE):
            bond_obj = prepare_bond_attachment_obj(
                host_name=host_name, **v
            )
            bonds.add_host_nic(bond_obj)

        if v.get(NETWORK):
            network_attachment = prepare_network_attachment_obj(
                host_name=host_name, **v
            )
            network_attachments.add_network_attachment(network_attachment)

        if v.get(LABELS):
            labels_list = v.get(LABELS)
            host_nic = v.get("nic")
            for label in labels_list:
                label_obj = create_host_nic_label_object(
                    host_name=host_name, nic=host_nic, label=label
                )
                labels.add_network_label(label_obj)

    return network_attachments, bonds, labels


def prepare_ip_object(network_attachment, ip_dict):
    """
    Prepare Ip object for NetworkAttachment

    Args:
        network_attachment (NetworkAttachment): NetworkAttachment object
        ip_dict (dict): Dict with Ip params

    Returns:
        NetworkAttachment: NetworkAttachment object
    """
    ip_address_assignments = data_st.IpAddressAssignments()
    for value in ip_dict.values():
        ip_address_assignment = data_st.IpAddressAssignment()
        ip = data_st.Ip()
        for k, v in value.iteritems():
            if k == "boot_protocol":
                ip_address_assignment.set_assignment_method(v)
            else:
                setattr(ip, k, v)

        ip_address_assignment.set_ip(ip)
        ip_address_assignments.add_ip_address_assignment(ip_address_assignment)
        network_attachment.set_ip_address_assignments(ip_address_assignments)
    return network_attachment


def get_host_unmanaged_networks(host_name, networks=list()):
    """
    Get unmanaged network object from host

    Args:
        host_name (str): Host name
        networks (list): Networks names

    Returns:
        list: Unmanaged networks
    """
    unmanaged_networks = get_host_unmanaged_objects(host_name)
    if not networks:
        return unmanaged_networks
    return filter(lambda x: x.name in networks, unmanaged_networks)


def remove_unmanaged_networks(host_name, networks=list()):
    """
    Remove unmanaged networks from host

    Args:
        host_name (str): Host name
        networks (list): Networks to remove

    Returns:
        bool: True if network is removed else False
    """
    unmanged_networks = get_host_unmanaged_networks(host_name, networks)
    for unmanaged_network in unmanged_networks:
        log_info, log_error = ll_general.get_log_msg(
            log_action="Remove", obj_type="un-managed network",
            obj_name=unmanaged_network.name
        )
        logger.info(log_info)
        if not UNMANAGED_NETWORKS_API.delete(unmanaged_network, True):
            logger.error(log_error)
            return False
    return True


def get_network_name_from_attachment(attachment):
    """
    Get network name from network attachment

    Args:
        attachment (NetworkAttachment): Network attachment object

    Returns:
        str: Network name
    """
    return ll_general.get_object_name_by_id(
        ll_networks.NET_API, attachment.get_network().get_id()
    )


def create_host_nic_label_object(host_name, nic, label):
    """
    Prepare label object with host NIC

    Args:
        host_name (str): Host name
        nic (str): Host NIC name
        label (str): Label name

    Returns:
        Label: Label object
    """
    label_obj = ll_networks.create_label(label=label)
    host_nic_obj = ll_hosts.get_host_nic(host=host_name, nic=nic)
    label_obj.set_host_nic(host_nic_obj)
    return label_obj
