#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Low level functions for host network API
http://www.ovirt.org/Features/HostNetworkingApi
http://www.ovirt.org/Features/NetworkingApi
"""

from art.core_api.apis_utils import data_st
import art.core_api.apis_exceptions as exceptions
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
from art.rhevm_api.utils.test_utils import get_api
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.general as ll_general

NETWORK = "network"
BOND = "bond"
UPDATE = "update"
SLAVES = "slaves"
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

    :param host_name: Host name
    :type host_name: str
    :return: Host network attachments
    :rtype: list
    """
    host = ll_hosts.HOST_API.find(host_name)
    return ll_hosts.HOST_API.getElemFromLink(
        host, NETWORKATTACHMENTS, NETWORK_ATTACHMENT
    )


def get_host_nic_network_attachments(host_name, nic):
    """
    Get host NIC network attachments from:
    api/hosts/<host_id>/nics/<nic_id>/networkattachments

    :param host_name: Host name
    :type host_name: str
    :param nic: NIC name
    :type nic: str
    :return: Host NIC network attachments
    :rtype: list
    """
    host_nic = ll_hosts.getHostNic(host_name, nic)
    return ll_hosts.HOST_NICS_API.getElemFromLink(
        host_nic, NETWORKATTACHMENTS, NETWORK_ATTACHMENT
    )


def get_networks_attachments(host_name, networks, nic=None):
    """
    Get networks attachments by network names

    :param host_name: Host name
    :type host_name: str
    :param networks: Network names list
    :type networks: list
    :param nic: NIC name
    :type nic: str
    :return: Network attachments
    :rtype: list
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

    :param host_name: Host name
    :type host_name: str
    :return: Host unmanaged objects
    :rtype: list
    """
    host = ll_hosts.HOST_API.find(host_name)
    return ll_hosts.HOST_API.getElemFromLink(
        host, UNMANAGEDNETWORKS, UNMANAGED_NETWORK
    )


def get_attachment_sync_status(attachment):
    """
    Get attachment sync status

    :param attachment: Network attachment
    :type attachment: NetworkAttachment object
    :return: True if network is synced else False
    :rtype: bool
    """
    reported = attachment.get_reported_configurations()
    return reported.get_in_sync()


def get_attachment_reported_configurations(attachment):
    """
    Get attachment reported configurations
    :param attachment: network attachment
    :type attachment: NetworkAttachment object
    :return: network attachment reported configurations
    :rtype: list
    """
    reported_ = attachment.get_reported_configurations()
    return reported_.get_reported_configuration()


def get_attachment_href(host_name, nic=None):
    """
    Get host/NIC attachment href

    :param host_name: Host name
    :type host_name: str
    :param nic: NIC name
    :type nic: str
    :return: Host/NIC attachment href
    :rtype: str
    """
    api = ll_hosts.HOST_NICS_API if nic else ll_hosts.HOST_API
    if nic:
        entity = ll_hosts.getHostNic(host_name, nic)
    else:
        entity = ll_hosts.HOST_API.find(host_name)

    return api.getElemFromLink(
        entity, NETWORKATTACHMENTS, get_href=True
    )


def prepare_network_attachment_obj(host_name, **kwargs):
    """
    Prepare network attachment object

    :param host_name: Host name
    :type host_name: str
    :param kwargs: Network attachment kwargs
    :type kwargs: dict
    :return: Network attachment object
    :rtype: NetworkAttachment object
    """
    network = kwargs.get(NETWORK)
    ip = kwargs.get("ip")
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
            try:
                host_nic = ll_hosts.getHostNic(host_name, nic)
            except exceptions.EntityNotFound:
                host_nic = data_st.HostNIC()
                host_nic.set_name(nic)
        else:
            host_nic = ll_hosts.getHostNic(host_name, nic)

        network_attachment_obj.set_host_nic(host_nic)

    if ip:
        network_attachment_obj = prepare_ip_object(
            network_attachment_obj, ip
        )

    if network and not update:
        add_network = ll_networks.findNetwork(
            network=network, data_center=datacenter, cluster=cluster
        )
        network_attachment_obj.set_network(add_network)

    return network_attachment_obj


def prepare_bond_attachment_obj(host_name, **kwargs):
    """
    Prepare BOND host_nic object

    :param host_name: Host name
    :type host_name: str
    :param kwargs: BOND kwargs
    :type kwargs: dict
    :return: HostNIC
    :rtype: HostNIC object
    """
    slave_list = kwargs.get(SLAVES)
    nic_name = kwargs.get(NIC)
    update = kwargs.get(UPDATE)
    if update:
        host_nic_bond_obj = ll_hosts.getHostNic(host_name, kwargs.get(NIC))
        bond_obj = host_nic_bond_obj.get_bonding()
        slaves = bond_obj.get_slaves()
        options = bond_obj.get_options()

    else:
        host_nic_bond_obj = data_st.HostNIC()
        bond_obj = data_st.Bonding()
        options = data_st.Options()
        slaves = data_st.Slaves()

    if nic_name:
        host_nic_bond_obj.set_name(nic_name)

    if slave_list:
        slaves_nics_ids = [i.get_id() for i in slaves.get_host_nic()]
        for nic in slave_list:
            if update:
                nic_id = ll_hosts.getHostNic(host_name, nic).get_id()
                if nic_id in slaves_nics_ids:
                    continue
            slaves.add_host_nic(data_st.HostNIC(name=nic.strip()))
        bond_obj.set_slaves(slaves)

    if kwargs.get(MODE):
        options.add_option(data_st.Option(
            name=MODE, value=kwargs.get(MODE))
        )
        bond_obj.set_options(options)
    if kwargs.get(MIIMON):
        options.add_option(
            data_st.Option(name=MIIMON, value=kwargs.get(MIIMON)
                           )
        )
        bond_obj.set_options(options)

    host_nic_bond_obj.set_bonding(bond_obj)
    return host_nic_bond_obj


def prepare_remove_for_setupnetworks(host_name, dict_to_remove):
    """
    Prepare HostNics/NetworkAttachments objects of networks and BONDs
    for setup_networks function

    :param host_name: Host name
    :type host_name: str
    :param dict_to_remove: Dict with networks/BONDs to remove
    :type dict_to_remove: dict
    :return: tuple of HostNics/NetworkAttachments objects
    :rtype: tuple
    """
    removed_bonds = data_st.HostNics()
    removed_network_attachments = data_st.NetworkAttachments()
    for k in dict_to_remove.keys():
        if k == NETWORKS:
            attach = get_networks_attachments(
                host_name, dict_to_remove.get(NETWORKS)
            )
            for att in attach:
                removed_network_attachments.add_network_attachment(att)

        if k == BONDS:
            for bond in dict_to_remove.get(BONDS):
                bond_to_remove = ll_hosts.getHostNic(host_name, bond)
                removed_bonds.add_host_nic(bond_to_remove)
    return removed_bonds, removed_network_attachments


def prepare_add_for_setupnetworks(
    network_attachments, host_name, dict_to_add, update=False
):
    """
    Prepare NetworkAttachment object for setup_networks function

    :param network_attachments: NetworkAttachment object
    :type network_attachments: NetworkAttachment
    :param host_name: Host name
    :type host_name: str
    :param dict_to_add: Dict with networks to dict_to_add
    :type dict_to_add: dict
    :param update: True for update networks/BONDs
    :type update: bool
    :return: Network_attachments and bonds objects
    :rtype: tuple
    """
    bonds = data_st.HostNics()
    for k in dict_to_add.keys():
        if update:
            dict_to_add.get(k)[UPDATE] = True

        if dict_to_add.get(k).get(SLAVES):
            bond_obj = prepare_bond_attachment_obj(
                host_name, **dict_to_add.get(k)
            )
            bonds.add_host_nic(bond_obj)

        if dict_to_add.get(k).get(NETWORK):
            network_attachment = prepare_network_attachment_obj(
                host_name, **dict_to_add.get(k)
            )
            network_attachments.add_network_attachment(network_attachment)
    return network_attachments, bonds


def prepare_ip_object(network_attachment, ip_dict):
    """
    Prepare IP object for NetworkAttachment

    :param network_attachment: NetworkAttachment object
    :type network_attachment: NetworkAttachment
    :param ip_dict: Dict with IP params
    :type ip_dict: dict
    :return: NetworkAttachment object
    :rtype: NetworkAttachment
    """
    for value in ip_dict.values():
        ip_address_assignments = data_st.IpAddressAssignments()
        ip_address_assignment = data_st.IpAddressAssignment()
        ip = data_st.IP()
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

    :param host_name: Host name
    :type host_name: str
    :param networks: Networks names
    :type networks: list
    :return: Unmanaged networks
    :rtype: list
    """
    unmanaged_networks = get_host_unmanaged_objects(host_name)
    if not networks:
        return unmanaged_networks
    return filter(lambda x: x.name in networks, unmanaged_networks)


def remove_unmanaged_networks(host_name, networks=list()):
    """
    Remove unmanaged networks from host

    :param host_name: Host name
    :type host_name: str
    :param networks: Networks to remove
    :type networks: list
    :return: True/False
    :rtype: bool
    """
    unmanged_networks = get_host_unmanaged_networks(host_name, networks)
    for unmanaged_network in unmanged_networks:
        if not UNMANAGED_NETWORKS_API.delete(unmanaged_network, True):
            return False
    return True


def get_network_name_from_attachment(attachment):
    """
    Get network name from network attachment

    :param attachment: Network attachment object
    :type attachment: NetworkAttachment
    :return: Network name
    :rtype: str
    """
    return ll_general.get_object_name_by_id(
        ll_networks.NET_API, attachment.get_network().get_id()
    )
