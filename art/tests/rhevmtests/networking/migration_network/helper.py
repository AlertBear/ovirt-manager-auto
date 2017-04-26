#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Migration Network helper
"""
import config as mig_conf
import copy
import logging

import rhevmtests.helpers as global_helper
import rhevmtests.networking.helper as network_helper
from art.rhevm_api.tests_lib.high_level import (
    networks as hl_networks,
    vms as hl_vms
)
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    vms as ll_vms
)
from art.rhevm_api.utils import test_utils
from rhevmtests.networking import config
from utilities import jobs

logger = logging.getLogger("Migration_Network_Helper")


def init_host_sn_dict(template_dict, networks, hosts, bond=None, ipv6=False):
    """
    Initialize a dictionary for host setup network

    Args:
        template_dict (dict): Template dict to be used in test case for host
            setup network
        networks (list): List of network names
        hosts (int): Number of hosts
        bond (str): Bond name
        ipv6 (bool): True to set IPv6 on host NIC

    Returns:
        dict: Host setup network dict
    """
    host_sn_dict = copy.deepcopy(template_dict)

    for host_index in range(hosts):
        net_dict = host_sn_dict[host_index]

        for net_name, test_network in zip(mig_conf.NETWORK_NAMES, networks):
            for key, val in net_dict.get(net_name, dict()).items():
                # Update network name
                if key == "network":
                    net_dict[net_name][key] = test_network
                # Update bond name
                if (
                    key == "nic" and bond and
                    net_name == mig_conf.NETWORK_NAMES[0]
                ):
                    net_dict[net_name][key] = bond
                # Use IPv6
                if ipv6:
                    ip_dict = net_dict[net_name]["ip"]["1"]
                    ip_dict["address"] = mig_conf.IPSV6[host_index]
                    ip_dict["version"] = "v6"
                    ip_dict["netmask"] = "24"

    return host_sn_dict


def get_hosts_ips(
    vm, src_host_rsc, dst_host_rsc, src_host_name, dst_host_name,
    nic_index, vlan=None, bond=None, ipv6=False
):
    """
    Get source and destination IP addresses from a given hosts

    Args:
        vm (str): VM name
        src_host_rsc (resources.VDS object): Source host resource
        dst_host_rsc (resources.VDS object): Destination host resource
        src_host_name (str): Source host name
        dst_host_name (str): Destination host name
        nic_index (int): NIC index to get IP from
        vlan (str): VLAN name to get IP from
        bond (str): BOND name to get IP from
        ipv6 (bool): True to get IPv6 IP

    Returns:
        tuple: Source and destination IPs, or None if error has occurred
    """
    if vlan:
        if bond:
            src_eth = dst_eth = ".".join([bond, vlan])
        else:
            src_eth = ".".join([src_host_rsc.nics[nic_index], vlan])
            dst_eth = ".".join([dst_host_rsc.nics[nic_index], vlan])
    elif bond:
        src_eth = dst_eth = bond
    else:
        src_eth = src_host_rsc.nics[nic_index]
        dst_eth = dst_host_rsc.nics[nic_index]

    src_ip = hl_networks.get_ip_on_host_nic(
        host=src_host_name, nic=src_eth, ipv6=ipv6
    )
    dst_ip = hl_networks.get_ip_on_host_nic(
        host=dst_host_name, nic=dst_eth, ipv6=ipv6
    )
    return src_ip, dst_ip if src_ip and dst_ip else None


def get_hoster_of_vms(vms):
    """
    Get hoster name and resource of VM's and make sure all VM's are running on
        the same host

    Args:
        vms (list): List of VM names

    Returns:
        tuple: Host name, host resource, or None if not all of them are
            running on the same host
    """
    hosters_set = set([ll_vms.get_vm_host(vm) for vm in vms])
    if len(hosters_set) > 1:
        logger.error("VM's: %s are not running on the same host", vms)
        return None
    host_name = hosters_set.pop()
    host_rsc = global_helper.get_host_resource_by_name(host_name=host_name)
    return host_rsc, host_name


def capture_traffic_while_migrating(
    vms, src_host_rsc, dst_host_rsc, src_host_name, dst_host_name, nic,
    src_ip, dst_ip, req_nic=None, maintenance=False
):
    """
    Capture migration traffic during network migration

    Args:
        vms (list): List of VM's to migrate
        src_host_rsc (resources.VDS object): Host object of source host
        dst_host_rsc (resources.VDS object): Host object of destination host
        src_host_name (str): Source host name
        dst_host_name (str): Destination host name
        nic (str): NIC where IP is configured for migration
        src_ip (str): Source IP from where the migration should be sent
        dst_ip (str): Destination IP where the migration should be sent
        req_nic (int): NIC with required network
        maintenance (bool): Set maintenance state on host

    Returns:
        bool: True is migration succeed, False otherwise
    """
    jobs_timeout = (
        config.TIMEOUT * mig_conf.REQUIRED_NIC_MIGRATION_TIMEOUT if not req_nic
        else config.TIMEOUT * mig_conf.DEFAULT_MIGRATION_TIMEOUT
    )
    tcpdump_cmd_timeout = str(config.TIMEOUT * mig_conf.TCPDUMP_TIMEOUT)
    tcpdump_kwargs = {
        "host_obj": dst_host_rsc,
        "nic": nic,
        "src": src_ip,
        "dst": dst_ip,
        "numPackets": mig_conf.TCPDUMP_PACKETS_COUNT,
        "timeout": tcpdump_cmd_timeout
    }
    migration_kwargs = {
        "vms_list": vms,
        "src_host": src_host_name,
        "vm_user": config.HOSTS_USER,
        "vm_password": config.VMS_LINUX_PW,
        "vm_os_type": "rhel"
    }

    if req_nic:
        migration_func = hl_vms.migrate_by_nic_down
        migration_kwargs["nic"] = src_host_rsc.nics[req_nic]
        migration_kwargs["password"] = config.HOSTS_PW
    elif maintenance:
        migration_func = hl_vms.migrate_by_maintenance
    else:
        migration_func = hl_vms.migrate_vms
        migration_kwargs["dst_host"] = dst_host_name

    tcpdump_job = jobs.Job(test_utils.run_tcp_dump, (), tcpdump_kwargs)
    migration_job = jobs.Job(migration_func, (), migration_kwargs)
    job_set = jobs.JobsSet()
    job_set.addJobs([tcpdump_job, migration_job])
    job_set.start()
    job_set.join(jobs_timeout)

    return tcpdump_job.result and migration_job.result


def check_migration_network(
    vms, nic_index=1, vlan=None, bond=None, req_nic=None, maintenance=False,
    non_vm=False, ipv6=False
):
    """
    Check migration network by shutting down host NIC or set host in
    maintenance and check for migration traffic via TCPDump.
    This function sets the source host as the running VM hoster.

    Args:
        vms (list): VMs to migrate
        nic_index (int): Index for the NIC where migration should occur
        vlan (str): Network VLAN
        bond (str): Network BOND
        req_nic (int): Index for NIC with required network
        maintenance (bool): Set host on maintenance
        non_vm (bool): Network is non-VM network
        ipv6 (bool): True to get IPv6 IP

    Returns:
        bool: True if migration succeeded and traffic captured, False
            otherwise
    """
    host_names = [config.HOSTS[i] for i in mig_conf.MIGRATION_HOSTS]
    host_vds = [config.VDS_HOSTS[i] for i in mig_conf.MIGRATION_HOSTS]
    test_vm = vms[0]

    # Get source host
    res = get_hoster_of_vms(vms=vms)
    if not res:
        return False
    src_host_rsc, src_host_name = res

    # Get destination host
    dst_host_name, dst_host_rsc = filter(
        lambda host, src_host_name=src_host_name:
        host[0] != src_host_name, zip(host_names, host_vds)
    )[0]

    logger.info(
        "Getting source IP and destination IP from hosts: %s",
        ", ".join(host_names)
    )
    if nic_index == 0:
        src_ip, dst_ip = src_host_rsc.ip, dst_host_rsc.ip
    else:
        res_get_hosts_ip = get_hosts_ips(
            vm=test_vm, src_host_rsc=src_host_rsc, dst_host_rsc=dst_host_rsc,
            src_host_name=src_host_name, dst_host_name=dst_host_name,
            nic_index=nic_index, vlan=vlan, bond=bond, ipv6=ipv6
        )
        if not res_get_hosts_ip:
            logger.error("Failed to get source and destination IP's for hosts")
            return False

        src_ip, dst_ip = res_get_hosts_ip

        # Verify if migration destination IP is reachable from source host
        # through the management network
        icmp_extra_args = "-6" if ipv6 else None
        if not network_helper.send_icmp_sampler(
            host_resource=src_host_rsc, dst=dst_ip,
            count=str(mig_conf.ICMP_DST_IP_COUNT), extra_args=icmp_extra_args
        ):
            return False
    logger.info(
        "Retrieved source IP: %s and destination IP: %s", src_ip, dst_ip
    )

    if bond:
        nic = bond
    elif vlan:
        nic = "{vnic}.{vlan}".format(
            vnic=dst_host_rsc.nics[nic_index], vlan=vlan
        )
    elif non_vm:
        nic = dst_host_rsc.nics[nic_index]
    else:
        # VM network
        nic = ll_networks.get_network_on_host_nic(
            dst_host_name, dst_host_rsc.nics[nic_index]
        )

    logger.info(
        "Starting migration from source: %s to destination: %s over NIC: "
        "%s NIC IP: %s", src_host_name, dst_host_name, nic, src_ip
    )
    return capture_traffic_while_migrating(
        vms=vms, src_host_rsc=src_host_rsc, dst_host_rsc=dst_host_rsc,
        src_host_name=src_host_name, dst_host_name=dst_host_name, nic=nic,
        src_ip=src_ip, dst_ip=dst_ip, req_nic=req_nic, maintenance=maintenance
    )
