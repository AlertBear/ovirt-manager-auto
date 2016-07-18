#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

import logging

import art.core_api.apis_exceptions as apis_exceptions
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as test_exceptions
import art.test_handler.settings as test_settings

ENUMS = test_settings.opts['elements_conf']['RHEVM Enums']

logger = logging.getLogger("art.hl_lib.networks")
CONNECTIVITY_TIMEOUT = 60
DISK_SIZE = 21474836480
LUN_PORT = 3260
INTERVAL = 2
ATTEMPTS = 600
TIMEOUT = 120
MAX_COUNTER = 60
DEFAULT_MTU = 1500
VDSM_CONF_FILE = "/etc/vdsm/vdsm.conf"
IFCFG_FILE_PATH = "/etc/sysconfig/network-scripts/"
HOST_NICS = ["eth0", "eth1", "eth2", "eth3", "eth4", "eth5"]
RHEL_IMAGE = "rhel6.5-agent3.5"
HYPERVISOR = "hypervisor"
RHEVH = "Red Hat Enterprise Virtualization Hypervisor"

# command variables
IP_CMD = "/sbin/ip"
MODPROBE_CMD = "/sbin/modprobe"


def remove_networks(positive, networks, data_center=None):
    """
    Remove networks

    Args:
        positive (bool): Expected state that the function should return
        networks (list): List of networks
        data_center (str): DC from where to remove network

    Returns:
        bool: True if remove networks succeeded, otherwise False
    """
    for net in networks:
        logger.info("Removing %s", net)
        if not ll_networks.remove_network(positive, net, data_center):
            logger.error("Failed to remove %s", net)
            return False
    return True


def createAndAttachNetworkSN(
    data_center=None, cluster=None, host=list(), auto_nics=list(),
    save_config=False, network_dict=None, vlan_auto_nics=None,
):
    """
    Function that creates and attach the network to the:
    a) DC, b) Cluster, c) Hosts with SetupNetworks

    __author__: 'gcheresh'

    Args:
        data_center (str): DC name.
        cluster (str): Cluster name.
        host (list): List of resources.VDS objects.
        auto_nics (list): A list of nics indexes to preserve.
        save_config (bool): Flag for saving configuration.
        network_dict (dict): Dictionary of dictionaries.
        vlan_auto_nics (dict): Dictionary for auto_nics with vlan.

    vlan_auto_nics example: {162: 0} where 162 is the vlan ID and
    0 is the host_nic index. (all int)

    network_dict parameters:
        Logical network name as the key for the following:
            nic (str): Interface to create the network on.
            usages (str): VM or ''  value (for VM or non-VM network).
            cluster_usages (str): Migration and/or display
                (can be set on one network).
            vlan_id (str): Network vlan id.
            mtu (int): Network mtu.
            required (bool): required/non-required network.
            bond (str): Bond name to create.
            slaves (list): Interfaces that the bond will be composed from.
            mode (int): The mode of the bond.
            bootproto (str): Boot protocol (none, dhcp, static).
            address (list): List of IP addresses of the network if bootproto
                is Static.
            netmask (list): List of netmasks of the  network if bootproto
                is Static.
            gateway (list): List of gateways of the network if bootproto
                is Static.
            profile_required (bool): Flag to create or not VNIC profile
                for the network.
            properties (str): Property of bridge_opts and/or ethtool_opts.
            description (str): New network description (if relevant).

    Returns:
        bool: True value if succeeded in creating and adding net list
            to DC/Cluster and Host with all the parameters.
    """
    # Makes sure host_list is always a list
    sn_dict = dict()
    host_list = [host] if not isinstance(host, list) else host

    for net, net_param in network_dict.items():
        if data_center and net:
            if not ll_networks.add_network(
                positive=True, name=net, data_center=data_center,
                usages=net_param.get("usages", "vm"),
                vlan_id=net_param.get("vlan_id"),
                mtu=net_param.get("mtu"),
                profile_required=net_param.get("profile_required"),
                qos_dict=net_param.get("qos"),
                description=net_param.get("description")
            ):
                return False

        if cluster and net:
            if not ll_networks.add_network_to_cluster(
                positive=True, network=net, cluster=cluster,
                required=net_param.get("required", "true"),
                usages=net_param.get("cluster_usages", None),
                data_center=data_center
            ):
                return False

    for host in host_list:
        host_name = ll_hosts.get_host_name_from_engine(host)
        logger.info("Found host name: %s", host_name)

        host_auto_nics = []
        for index in auto_nics:
            host_auto_nics.append(host.nics[index])

        if vlan_auto_nics:
            for key, val in vlan_auto_nics.iteritems():
                host_int = host.nics[val]
                host_vlan_int = ".".join([host_int, str(key)])
                host_auto_nics.append(host_vlan_int)

        idx = 0
        setup_network_dict = {"add": {}}
        for net, net_param in network_dict.items():
            param_nic = net_param.get("nic")
            if not param_nic:
                continue
            vlan_interface = None
            slaves = None
            param_slaves = net_param.get("slaves")
            param_vlan = net_param.get("vlan_id")
            idx += 1

            if param_slaves:
                slaves = [host.nics[s] for s in param_slaves]

            nic = (
                param_nic if "bond" in str(param_nic) else host.nics[param_nic]
            )

            if "vlan_id" in net_param:
                vlan_interface = "{0}.{1}".format(nic, param_vlan)

            nic = (
                vlan_interface if "vlan_id" in net_param else nic
            )
            sn_dict = convert_old_sn_dict_to_new_api_dict(
                new_dict=setup_network_dict, old_dict=net_param, idx=idx,
                nic=nic, network=net, slaves=slaves
            )

        if not network_dict:
            if not hl_host_network.clean_host_interfaces(
                host_name=host_name
            ):
                return False
        else:
            if not hl_host_network.setup_networks(
                host_name=host_name, **sn_dict
            ):
                return False
    return True


def remove_net_from_setup(
    host, network=list(), data_center=None, all_net=False, mgmt_network=None
):
    """
    Function that removes networks from the host, Cluster and DC

    Args:
        host (list): list or str of hosts names
        network (list): list of networks to remove
        data_center (str): DC where the network is
        all_net (bool): True to remove all networks from setup
            (except MGMT net)
        mgmt_network (str): Management network

    Returns:
        bool: True value if succeeded in deleting networks from Hosts,
            Cluster, DC
    """
    hosts_list = [host] if not isinstance(host, list) else host
    try:
        for host_name in hosts_list:
            if not hl_host_network.clean_host_interfaces(host_name):
                return False

    except Exception as ex:
        logger.error("Clean hosts interfaces failed %s", ex, exc_info=True)
        return False

    if all_net:
        if not remove_all_networks(
                datacenter=data_center, mgmt_network=mgmt_network
        ):
            return False
    else:
        if not remove_networks(True, network, data_center):
            return False
    return True


def create_dummy_interfaces(host, num_dummy=1, ifcfg_params=None):
    """
    create (X) dummy network interfaces on host

    Args:
        host (VDS): VDS
        num_dummy (int): number of dummy interfaces to create
        ifcfg_params (dict): Ifcfg file content

    Returns:
        bool: True/False
    """
    dummy_int = "dummy_%s"
    if ifcfg_params is None:
        ifcfg_params = {}

    for i in range(num_dummy):
        cmd = ["ip", "link", "add", dummy_int % i, "type", "dummy"]
        rc = host.run_command(cmd)[0]
        if rc:
            return False

        nic_name = dummy_int % i
        host.network.create_ifcfg_file(nic=nic_name, params=ifcfg_params)

    return True


def delete_dummy_interfaces(host):
    """
    Delete dummy network interfaces on host

    Args:
        host (VDS): VDS

    Returns:
        bool: True/False
    """
    rhevh = RHEVH in host.os.distribution.distname
    all_interfaces = host.network.all_interfaces()
    dummy_list = [i for i in all_interfaces if 'dummy' in i]
    for dummy in dummy_list:
        logger.info("Delete dummy %s from host %s", dummy, host)
        host.network.delete_interface(interface=dummy)
        ifcfg_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % dummy
        if host.fs.isfile(ifcfg_file):
            if rhevh:
                rc = host.run_command(["unpersist", ifcfg_file])[0]
                if rc:
                    return False
            host.network.delete_ifcfg_file(nic=dummy)
    return True


def remove_all_networks(datacenter=None, cluster=None, mgmt_network=None):
    """
    Remove all networks from DC/CL or from entire setup

    If cluster is specified - remove all network from specified cluster
    Elif datacenter is specified - remove all networks from specified DC
    If no datacenter or cluster are specified remove all networks from all DCs
    In all cases we don't remove the management network

    Args:
        datacenter (str): name of the datacenter.
        cluster (str): name of the cluster.
        mgmt_netowrk (str): name of management network (to be excluded from
            removal)

    Returns:
        bool: True if removing networks succeeded, otherwise False
    """
    networks_to_remove = []
    cluster_obj = (
        ll_clusters.get_cluster_object(cluster_name=cluster) if cluster else
        None
    )
    mgmt_networks_ids = (
        get_clusters_managements_networks_ids(
            cluster=[cluster_obj] if cluster else None
        )
    )
    if cluster:
        networks_list = ll_networks.get_cluster_networks(
            cluster=cluster, href=False
        )

    elif datacenter:
        networks_list = ll_networks.get_networks_in_datacenter(
            datacenter=datacenter
        )

    else:
        logger.info("Get all networks")
        networks_list = ll_networks.NET_API.get(absLink=False)

    for net in networks_list:
        if net.id not in mgmt_networks_ids:
            networks_to_remove.append(net.name)

    if not networks_to_remove:
        logger.info("There are no networks to remove")
        return True

    log = (
        "from %s, %s" % (datacenter, cluster) if datacenter or cluster
        else "from engine"
    )
    logger.info("Removing all networks %s", log)

    status = remove_networks(True, networks_to_remove, datacenter)

    if not status:
        logger.info("Failed to remove all networks %s", log)

    return status


def get_ip_on_host_nic(host, nic):
    """
    Get IP on host NIC

    Args:
        host (str): IP or FDQN of the host
        nic (str): NIC to get IP from, execpted NICs:
                   eth(x) - Non VLAN nic
                   eth(x).(xxx) - VLAN NIC
                   bond(x) - BOND NIC
                   bond(x).(xxx) - VLAN BOND NIC

    Returns:
        Ip or None: IP if HosNic have IP else None
    """
    host_nic = ll_hosts.get_host_nic(host=host, nic=nic)
    return host_nic.get_ip().get_address()


def check_host_nic_params(host, nic, **kwargs):
    """
    Check MTU, VLAN interface and bridge (VM/Non-VM) host nic parameters.

    Args:
        host (str): Host name
        nic (str): Nic to get parameters from

    Keyword Args:
        vlan_id (str): expected VLAN id on the host
        mtu (str): expected mtu on the host
        bridge (bool): Expected VM, Non-VM network (True for VM, False for
            Non-VM)

    Returns:
        bool: True if action succeeded, otherwise False
    """
    res = True
    host_nic = ll_hosts.get_host_nic(host, nic)
    expected_bridge = kwargs.get("bridge")
    expected_vlan_id = kwargs.get("vlan_id")
    expected_mtu = kwargs.get("mtu")

    if expected_bridge is not None:
        bridged = host_nic.get_bridged()
        logger.info("Check that %s has bridge %s", nic, expected_bridge)
        if expected_bridge != bridged:
            logger.error(
                "%s interface has bridge %s, expected is %s", nic, bridged,
                expected_bridge
            )
            res = False

    if expected_vlan_id:
        vlan_nic = ".".join([nic, expected_vlan_id])
        logger.info("Check that %s has vlan tag %s", nic, expected_vlan_id)
        try:
            ll_hosts.get_host_nic(host, vlan_nic)
        except apis_exceptions.EntityNotFound:
            logger.error("Fail to get %s interface from %s", vlan_nic, host)
            res = False

    if expected_mtu:
        logger.info("Check that %s have MTU %s", nic, expected_mtu)
        mtu = host_nic.get_mtu()
        if int(expected_mtu) != mtu:
            logger.error(
                "MTU value on %s is %s, expected is %s", nic, mtu,
                expected_mtu
            )
            res = False

    return res


def create_basic_setup(
    datacenter, version, cluster=None, cpu=None, host=None,
    host_password=None
):
    """
    Create basic setup with datacenter and optional cluster and hosts

    Args:
        datacenter (str): Datacenter name
        version (str): Version of the datacenter/cluster
        cluster (str): Cluster name
        cpu (str): CPU type for cluster
        host (str or list): Host name or a list of Host names
        host_password (str): Password for the host

    Returns:
        bool: True if setup creation succeeded, otherwise False
    """
    logger.info("Create dc %s", datacenter)
    if not ll_datacenters.addDataCenter(
        positive=True, name=datacenter, version=version
    ):
        logger.error("Failed to create DC %s", datacenter)
        return False

    if cluster:
        logger.info("Create cluster %s under DC %s", cluster, datacenter)
        if not ll_clusters.addCluster(
            positive=True, name=cluster, cpu=cpu, data_center=datacenter,
            version=version
        ):
            logger.error(
                "Failed to add Cluster %s under DC %s", cluster, datacenter
            )
            return False

        if host:
            host_list = [host] if isinstance(host, basestring) else host
            logger.info("Add host %s under cluster %s", host_list, cluster)
            try:
                hl_hosts.add_hosts(
                    hosts_list=host_list, cluster=cluster,
                    passwords=[host_password] * len(host_list)
                )
            except test_exceptions.HostException:
                logger.error(
                    "Failed to add host %s under cluster %s",
                    host_list, cluster
                )
                return False
    return True


def remove_basic_setup(datacenter, cluster=None, hosts=[]):
    """
    Remove basic setup with datacenter and optional cluster and hosts

    Args:
        datacenter (str): Datacenter name
        cluster (str): Cluster name
        hosts (list): List of host names

    Returns:
        bool: True if setup removal succeeded, otherwise False
    """
    logger.info("Remove basic setup")
    if cluster:
        for host in hosts:
            logger.info("Remove host %s for cluster %s", host, cluster)
            if not ll_hosts.removeHost(
                positive=True, host=host, deactivate=True
            ):
                logger.error("Failed to remove host %s ", host)
                return False

        logger.info("Remove cluster %s", cluster)
        if not ll_clusters.removeCluster(positive=True, cluster=cluster):
            logger.error("Failed to remove Cluster %s", cluster)
            return False

    logger.info("Remove DC %s", datacenter)
    if not ll_datacenters.remove_datacenter(
        positive=True, datacenter=datacenter
    ):
        logger.error("Failed to remove DC %s", datacenter)
        return False
    return True


def is_management_network(cluster_name, network):
    """
    Check if network is management network

    Args:
        cluster_name (str): Name of the Cluster
        network (str): Network to check

    Returns:
        bool: True if network is management network, otherwise False
    """
    logger.info(
        "Check if network %s is management network under cluster %s",
        network, cluster_name
    )
    mgmt_net_obj = ll_networks.get_management_network(cluster_name)
    cl_mgmt_net_obj = ll_clusters.get_cluster_management_network(cluster_name)
    if (
            mgmt_net_obj.get_name() == network and
            mgmt_net_obj.get_id() == cl_mgmt_net_obj.get_id()
    ):
        return True
    logger.error(
        "Network %s is not management network under cluster %s",
        network, cluster_name
    )
    return False


def get_nic_statistics(nic, host=None, vm=None, keys=None):
    """
    Get Host NIC/VM NIC statistics value for given keys.
    Available keys are:
        data.current.rx
        data.current.tx
        errors.total.rx
        errors.total.tx
        data.total.rx
        data.total.tx

    Args:
        nic (str): NIC name
        host (str): Host name
        vm (str): VM name
        keys (list): Keys to get keys for

    Returns:
        dict: Dict with keys values
    """
    res = dict()
    stats = ll_hosts.get_host_nic_statistics(
        host, nic
    ) if host else ll_vms.get_vm_nic_statistics(
        vm, nic
    )
    for stat in stats:
        stat_name = stat.get_name()
        if stat_name in keys:
            res[stat_name] = stat.get_values().get_value()[0].get_datum()
    return res


def convert_old_sn_dict_to_new_api_dict(
    new_dict, old_dict, idx, nic, network, slaves=list()
):
    """
    Convert old CreateAndAttachSN call dict to new network API dict to use
    in setup_networks()

    Args:
        new_dict (dict): New SN dict
        old_dict (dict): Network dict
        idx (int): Index number for new API dict
        nic (str): NIC name
        network (str): Network name
        slaves (list): BOND slaves list

    Returns:
        dict: New dict for new API function (setup_networks())
    """
    ip_dict = None
    properties = old_dict.get("properties")
    address = old_dict.get("address")
    netmask = old_dict.get("netmask")
    gateway = old_dict.get("gateway")
    boot_protocol = old_dict.get("bootproto")
    if address and boot_protocol:
        ip_dict = {
            "ip_1": {
                "address": address[0],
                "netmask": netmask[0] if netmask else None,
                "gateway": gateway[0] if gateway else None,
                "boot_protocol": boot_protocol,
            }
        }

    new_dict["add"][str(idx)] = {
        "nic": nic.rsplit(".")[0],
        "slaves": slaves,
        "network": network,
        "properties": properties,
    }
    if ip_dict:
        new_dict["add"][str(idx)]["ip"] = ip_dict
    return new_dict


def get_clusters_managements_networks_ids(cluster=None):
    """
    Get clusters managements networks IDs for all clusters in the engine if
    not cluster else get only for the given cluster

    Args:
        cluster (str): Cluster name

    Returns:
        list: Managements networks ids
    """
    clusters = (
        ll_clusters.CLUSTER_API.get(absLink=False) if not cluster else cluster
    )
    logger.info(
        "Get management networks id from %s", [cl.name for cl in clusters]
    )
    return [
        ll_networks.get_management_network(cluster_name=cl.name).id
        for cl in clusters
        ]


def get_management_network_host_nic(host, cluster):
    """
    Get host NIC name that management network resides on

    Args:
        host (str): Host name
        cluster (str): Cluster name

    Returns:
        HostNic or None: Host NIC  if found else None

    """
    mgmt_net = ll_networks.get_management_network(cluster_name=cluster)
    host_nics_list = ll_hosts.get_host_nics_list(host=host)
    host_nics_with_network = filter(
        lambda nic: getattr(nic, "network"), host_nics_list
    )
    for nic in host_nics_with_network:
        if nic.network.id == mgmt_net.id:
            return nic
    return None


def create_and_attach_label(label, networks=list(), host_nic_dict=None):
    """
    Add network label to the network in the list provided or/and to
    the NIC on the host

    Args:
        label (str): Label name.
        networks (list): List of networks.
        host_nic_dict (dict): Dictionary with hosts as keys and a list of host
            interfaces as a value for that key

    Examples:
         create_and_attach_label(
             label='label_1', networks=['net_1'],
             host_nic_dict={
            'silver-vdsb.qa.lab.tlv.redhat.com': ['eth3']
            }
         )

    Returns:
        bool: True if label was added properly, False otherwise
    """
    if networks:
        if not ll_networks.add_label(label=label, networks=networks):
            return False

    if host_nic_dict:
        if not ll_networks.add_label(
            label=label, host_nic_dict=host_nic_dict

        ):
            return False

    return True
