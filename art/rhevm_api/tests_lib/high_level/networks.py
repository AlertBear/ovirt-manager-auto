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
import art.rhevm_api.tests_lib.high_level.datacenters as hl_datacenters
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as test_exceptions
from art.test_handler.settings import ART_CONFIG
import art.rhevm_api.tests_lib.low_level.events as ll_events

ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']

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


@ll_general.generate_logs(step=True)
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
    results = list()
    for net in networks:
        results.append(
            ll_networks.remove_network(
                positive=positive, network=net, data_center=data_center
            )
        )
    return all(results)


@ll_general.generate_logs(step=True)
def create_and_attach_networks(
    networks, data_center=None, clusters=[]
):
    """
    Create networks on datacenter and attach the networks to a cluster

    Args:
        data_center (str): DC name.
        clusters (list): List of clusters name.
        networks(dict): Dictionary of dictionaries.

    network_dict parameters:
        Logical network name as the key for the following:
            nic (str): Interface to create the network on.
            usages (str): VM or ''  value (for VM or non-VM network).
            cluster_usages (str): Migration and/or display
                (can be set on one network).
            vlan_id (str): Network vlan id.
            mtu (int): Network mtu.
            required (bool): required/non-required network.
            profile_required (bool): Flag to create or not VNIC profile
                for the network.
            properties (str): Property of bridge_opts and/or ethtool_opts.
            description (str): New network description (if relevant).

    Returns:
        bool: True value if succeeded in creating and adding net list
            to DC/Cluster with all the parameters.
    """
    for net, net_param in networks.items():
        if data_center and not ll_networks.add_network(
            positive=True, name=net, data_center=data_center,
            usages=net_param.get("usages", "vm"),
            vlan_id=net_param.get("vlan_id"),
            mtu=net_param.get("mtu"),
            profile_required=net_param.get("profile_required"),
            qos_dict=net_param.get("qos"),
            description=net_param.get("description")
        ):
            return False

        for cluster in clusters:
            if not ll_networks.add_network_to_cluster(
                positive=True, network=net, cluster=cluster,
                required=net_param.get("required", "true"),
                usages=net_param.get("cluster_usages"),
                data_center=data_center
            ):
                return False
    return True


@ll_general.generate_logs(step=True)
def remove_net_from_setup(
    host=None, network=None, data_center=None, all_net=False
):
    """
    Removes networks from the host, cluster and data_center

    Args:
        host (list): list or str of hosts names
        network (list): list of networks to remove
        data_center (str): DC where the network is
        all_net (bool): True to remove all networks from setup
            (except MGMT net)

    Returns:
        bool: True value if succeeded in deleting networks from Hosts,
            Cluster, DC
    """
    if host:
        hosts_list = [host] if not isinstance(host, list) else host
        try:
            for host_name in hosts_list:
                if not hl_host_network.clean_host_interfaces(
                    host_name=host_name
                ):
                    return False

        except Exception:
            return False

    if all_net:
        if not remove_all_networks(datacenter=data_center):
            return False
    else:
        if not remove_networks(
            positive=True, networks=network, data_center=data_center
        ):
            return False
    return True


@ll_general.generate_logs()
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
    host_nics = host.network.all_interfaces()
    dummy_int = "dummy_%s"
    ifcfg_params = ifcfg_params if ifcfg_params else {}

    for i in range(num_dummy):
        nic_name = dummy_int % i
        if nic_name in host_nics:
            logger.warning(
                "Dummy %s already exists on host %s", nic_name, host
            )
            continue

        cmd = ["ip", "link", "add", nic_name, "type", "dummy"]
        rc = host.run_command(cmd)[0]
        if rc:
            logger.error("Failed to create %s on host %s", nic_name, host)
            return False

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
    host_name = ll_hosts.get_host_name_from_engine(vds_resource=host)
    all_interfaces = host.network.all_interfaces()
    dummy_list = [i for i in all_interfaces if 'dummy' in i]
    for dummy in dummy_list:
        logger.info("Delete dummy %s from host %s", dummy, host)
        host.network.delete_interface(interface=dummy)
        ifcfg_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % dummy
        if host.fs.isfile(ifcfg_file):
            host.network.delete_ifcfg_file(nic=dummy)
    last_event = ll_events.get_max_event_id()
    return ll_hosts.refresh_host_capabilities(
        host=host_name, start_event_id=last_event
    )


@ll_general.generate_logs(step=True)
def remove_all_networks(datacenter=None, cluster=None, remove_gluster=False):
    """
    Remove all networks from datacenter or cluster or from entire setup

    If cluster is specified - remove all network from specified cluster
    Elif datacenter is specified - remove all networks from specified DC
    If no datacenter or cluster are specified remove all networks from all DCs
    In all cases we don't remove the management network

    Args:
        datacenter (str): name of the datacenter.
        cluster (str): name of the cluster
        remove_gluster (bool): True to remove gluster network

    Returns:
        bool: True if removing networks succeeded, otherwise False
    """
    networks_to_remove = list()
    cl_obj = (
        ll_clusters.get_cluster_object(cluster_name=cluster) if cluster else
        cluster
    )
    mgmt_networks_ids = get_clusters_managements_networks_ids(cluster=cluster)
    if cluster:
        networks_list = ll_networks.get_cluster_networks(
            cluster=cluster, href=False
        )

    elif datacenter:
        networks_list = ll_networks.get_networks_in_datacenter(
            datacenter=datacenter
        )

    else:
        networks_list = ll_networks.get_all_networks()

    for net in networks_list:
        if not remove_gluster:
            if ll_networks.is_gluster_network(
                network=net.name,
                cluster=cl_obj or ll_networks.get_network_cluster(
                    network=net.name, datacenter=datacenter
                )
            ):
                continue

        if net.id not in mgmt_networks_ids:
            networks_to_remove.append(net.name)

    if not networks_to_remove:
        return True

    return remove_networks(
        positive=True, networks=networks_to_remove, data_center=datacenter
    )


@ll_general.generate_logs()
def get_ip_on_host_nic(host, nic, ipv6=False):
    """
    Get IP on host NIC

    Args:
        host (str): IP or FDQN of the host
        nic (str): NIC to get IP from, execpted NICs:
                   eth(x) - Non VLAN nic
                   eth(x).(xxx) - VLAN NIC
                   bond(x) - BOND NIC
                   bond(x).(xxx) - VLAN BOND NIC
        ipv6 (bool): True to get IPv6 IP.

    Returns:
        str: IP if HosNic have IP else empty str
    """
    host_obj = ll_hosts.get_host_object(host_name=host)
    host_nic = ll_hosts.get_host_nic(host=host_obj, nic=nic)
    if host_nic:
        return host_nic.ip.address if not ipv6 else host_nic.ipv6.address
    return ""


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
    host_obj = ll_hosts.get_host_object(host_name=host)
    host_nic = ll_hosts.get_host_nic(host=host_obj, nic=nic)
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
            ll_hosts.get_host_nic(host=host_obj, nic=vlan_nic)
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


def remove_basic_setup(datacenter, cluster=None, hosts=list()):
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
            if not ll_hosts.remove_host(
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


@ll_general.generate_logs(step=True)
def is_management_network(cluster_name, network):
    """
    Check if network is management network

    Args:
        cluster_name (str): Name of the Cluster
        network (str): Network to check

    Returns:
        bool: True if network is management network, otherwise False
    """
    mgmt_net_obj = ll_networks.get_management_network(cluster_name)
    cl_obj = ll_clusters.get_cluster_object(
        cluster_name=cluster_name, all_content=True
    )
    cl_mgmt_net_obj = ll_clusters.get_cluster_management_network(
        cluster=cl_obj
    )
    return (
        mgmt_net_obj.get_name() == network and
        mgmt_net_obj.get_id() == cl_mgmt_net_obj.get_id()
    )


@ll_general.generate_logs()
def get_nic_statistics(nic, host=None, vm=None, keys=None):
    """
    Get Host NIC/VM NIC statistics value for given keys.

    Args:
        nic (str): NIC name
        host (str): Host name
        vm (str): VM name
        keys (list): Keys to get keys for

    Returns:
        dict: Dict with keys values

    Examples:
        get_nic_statistics(
            nic=rx_tx_stats.host_0_nics[1], host=rx_tx_stats.host_0_name,
            keys=[
                data.current.rx, data.current.tx, errors.total.rx
                errors.total.tx, data.total.rx, data.total.tx
                ]
            )
    """
    res = dict()
    if host:
        host_object = ll_hosts.get_host_object(host_name=host)
        stats = ll_hosts.get_host_nic_statistics(
            host=host_object, nic=nic
        )
    else:
        stats = ll_vms.get_vm_nic_statistics(vm=vm, nic=nic)
    for stat in stats:
        stat_name = stat.get_name()
        if stat_name in keys:
            stat_list = stat.get_values().get_value()
            if not stat_list:
                res[stat_name] = 0
            else:
                res[stat_name] = stat_list[0].get_datum()
    return res


def get_clusters_managements_networks_ids(cluster=None):
    """
    Get clusters managements networks IDs for all clusters in the engine if
    not cluster else get only for the given cluster

    Args:
        cluster (str): Cluster name

    Returns:
        list: Managements networks ids
    """
    mgmt_ids = list()
    all_clusters = ll_clusters.get_cluster_names_list()
    clusters = filter(
        lambda x: x == cluster if cluster else x, all_clusters
    )
    logger.info(
        "Get management networks id from %s", ", ".join(
            [cl for cl in clusters]
        )
    )
    for cl in clusters:
        mgmt_net = ll_networks.get_management_network(cluster_name=cl)
        if mgmt_net:
            mgmt_ids.append(mgmt_net.id)

    return mgmt_ids


@ll_general.generate_logs()
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
    host_obj = ll_hosts.get_host_object(host_name=host)
    host_nics_list = ll_hosts.get_host_nics_list(host=host_obj)
    host_nics_with_network = filter(
        lambda nic: getattr(nic, "network"), host_nics_list
    )
    for nic in host_nics_with_network:
        if nic.network.id == mgmt_net.id:
            return nic
    return None


def remove_unneeded_vnic_profiles(dc_name):
    """
    Remove vNIC profiles which aren't attached to the management network.

    Args:
        dc_name (str): Remove profiles from a specified Data-Center name.

    Returns:
        True if remove was successful, False if one or more profiles removal(s)
        failed.
    """
    dc_id = ll_datacenters.get_data_center(datacenter=dc_name).get_id()
    clusters = hl_datacenters.get_clusters_connected_to_datacenter(
        dc_id=dc_id
    )

    # Filter to safely remove vNIC profiles from non-management networks
    nets_ids_to_remove_from = list()

    for cluster in clusters:
        cluster_nets = ll_networks.get_cluster_networks(
            cluster=cluster.name, href=False
        )
        mngmnt_net = ll_clusters.get_cluster_management_network(
            cluster=cluster
        )
        non_mngmnt_nets_ids = [
            net.get_id() for net in cluster_nets
            if not mngmnt_net or net.get_id() != mngmnt_net.get_id()
        ]
        nets_ids_to_remove_from.extend(non_mngmnt_nets_ids)

    success = True
    for profile in ll_networks.get_vnic_profile_objects():
        if profile.get_network().get_id() in nets_ids_to_remove_from:
            logger.info("Removing vNIC profile: %s", profile.name)
            if not ll_networks.VNIC_PROFILE_API.delete(profile, True):
                logger.error("Failed removing vNIC profile: %s", profile.name)
                success = False
    return success


@ll_general.generate_logs()
def get_vm_interface_by_vnic(vm, vm_resource, vnic):
    """
    Get VM interface (eth0, eth1..) by VM vNIC (nic1, nic2...)

    Args:
        vm (str): VM name
        vm_resource (Host): VM Host resource
        vnic (str): VM vNIC name

    Returns:
        str: VM interface name
    """
    vm_interfaces = vm_resource.network.all_interfaces()
    vm_mac = ll_vms.get_vm_nic_mac_address(vm=vm, nic=vnic)
    vm_macs_interfaces = dict(
        [
            (
                vm_resource.network.find_mac_by_int(interfaces=[inter])[0],
                inter
            ) for inter in vm_interfaces
        ]
    )
    return vm_macs_interfaces.get(vm_mac, "")
