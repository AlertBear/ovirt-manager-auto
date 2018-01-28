#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
External Network Provider helper functions
"""

import logging
import re
import shlex
import socket

from contextlib import closing

import config as ovn_conf
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as net_conf
import rhevmtests.networking.helper as net_helper
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.high_level import (
    vms as hl_vms,
    networks as hl_networks
)
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms, external_providers,
    general as ll_general
)
from art.test_handler import exceptions
from art.unittest_lib import testflow
from art.rhevm_api.utils import jobs

logger = logging.getLogger("external_network_provider_helper")


def run_vm_and_wait_for_ip(vm, host):
    """
    Run a VM on host, wait for MGMT IP and save its Host resource

    Args:
        vm (str): VM name
        host (str): Host name

    Returns:
        bool: True if VM started successfully, False otherwise

    """
    if hl_vms.run_vm_once_specific_host(
        vm=vm, host=host, wait_for_up_status=True
    ):
        try:
            ovn_conf.OVN_VMS_RESOURCES[vm] = global_helper.get_vm_resource(
                vm=vm, start_vm=False
            )
        except exceptions.VMException:
            return False
        return True
    return False


def set_ip_non_mgmt_nic(vm, address_type="static", ip_network=None):
    """
    Set IP network on the non-mgmt NIC of a VM that has two NIC's installed

    Args:
        vm (str): VM name
        address_type (str): IP address type, can be "static" for static IP, or
            "dynamic" for automatic IP
        ip_network (str): IP network to be set (in CIDR convention, e.g.
            192.168.100.0/24) to be used in conjunction with static address
            type

    Returns:
        str: IP address of the VM, or empty string if error has occurred

    """
    interface = net_helper.get_non_mgmt_nic_name(
        vm_resource=ovn_conf.OVN_VMS_RESOURCES[vm]
    )
    if not interface:
        return ""
    interface = interface[0]

    vm_resource = ovn_conf.OVN_VMS_RESOURCES[vm]

    if address_type == "static" and ip_network:
        ret = vm_resource.run_command(
            command=shlex.split(
                ovn_conf.OVN_CMD_SET_IP.format(net=ip_network, eth=interface)
            )
        )
        return ip_network if ret[0] == 0 else ""
    elif address_type == "dynamic":
        network = vm_resource.get_network()

        logger.info(
            "Requesting IP address from DHCP on VM: %s interface: %s",
            vm, interface
        )
        if vm_resource.run_command(
            command=shlex.split(
                ovn_conf.OVN_CMD_DHCLIENT.format(eth=interface)
            )
        )[0] != 0:
            return ""

        ip = network.find_ip_by_int(interface)
        if not ip:
            return ""

        logger.info("VM: %s acquired IP address: %s", vm, ip)
        return ip
    return ""


def create_ifcfg_on_vm(vm, action="create"):
    """
    Create interface configuration file which prevents OVN DHCP from changing
    the routing table of a VM

    Args:
        vm (str): VM name
        action (str): "create" to create file, or "delete" to delete file

    Returns:
        bool: True if file created or deleted successfully, False otherwise

    """
    interface = net_helper.get_non_mgmt_nic_name(
        vm_resource=ovn_conf.OVN_VMS_RESOURCES[vm]
    )
    if not interface:
        return False
    interface = interface[0]

    vm_resource = ovn_conf.OVN_VMS_RESOURCES[vm]
    network = vm_resource.get_network()
    filename = ovn_conf.OVN_CMD_NET_SCRIPT.format(eth=interface)

    logger.info(
        "Creating configuration file: %s to prevent default route"
        " changes on VM: %s", filename, vm
    )
    network.create_ifcfg_file(interface, {"DEFROUTE": "no"})
    return vm_resource.fs.exists(filename)


def check_ssh_file_copy(src_host, dst_host, dst_ip, size):
    """
    Check SSH file copy of given MB size from source host to destination host

    Args:
        src_host (Host): Source host
        dst_host (Host): Destination host
        dst_ip (str): Destination host IP
        size (int): File size in megabytes (MB)

    Returns:
        tuple: True and transfer rate (MB/s) if copy was successful, False and
            0.0 transfer rate otherwise
    """
    return_fail = False, 0.0

    if not global_helper.set_passwordless_ssh(
        src_host=src_host, dst_host=dst_host, dst_host_ips=[dst_ip]
    ):
        return return_fail

    logger.info(
        "Checking SSH file copy of {count} MB file from VM: {src} "
        "to VM: {dst}".format(count=size, src=src_host.fqdn, dst=dst_host.fqdn)
    )
    rc, out, err = src_host.run_command(
        shlex.split(
            ovn_conf.OVN_CMD_SSH_TRANSFER_FILE.format(count=size, dst=dst_ip)
        )
    )
    if rc:
        return return_fail
    if not out:
        out = err

    err_txt = "Something went wrong with dd command output: %s" % out
    # Extract last MB/s value from dd command output
    match = re.findall(ovn_conf.OVN_DD_MBS_REGEX, out)
    try:
        transfer_rate = float(match[0])
    except (ValueError, IndexError):
        logger.error(err_txt)
        return return_fail

    logger.info(
        "SSH file copy completed with %s MB/s transfer rate", transfer_rate
    )
    return True, transfer_rate


def check_ping(vm, dst_ip, max_loss=0, count=ovn_conf.OVN_PING_COUNT):
    """
    Send ICMP ping between VM and destination IP address, packets will be sent
    from the non-management interface

    Args:
        vm (str): VM name as source to send the ping
        dst_ip (str): Destination IP address
        max_loss (int): Maximum number of packets loss to tolerate in a
            successful ping
        count (int): Number of packets to send

    Returns:
        bool: True if ping was successful, False otherwise

    """
    interface = net_helper.get_non_mgmt_nic_name(
        vm_resource=ovn_conf.OVN_VMS_RESOURCES[vm]
    )
    if not interface:
        return False
    interface = interface[0]

    ret = ovn_conf.OVN_VMS_RESOURCES[vm].run_command(
        command=shlex.split(
            ovn_conf.OVN_CMD_PING.format(
                ip=dst_ip, count=count, size=ovn_conf.OVN_PING_SIZE,
                eth=interface
            )
        )
    )

    match = re.findall(ovn_conf.OVN_PING_PACKETS_RECEIVED_REGEX, ret[1])
    if max_loss > 0 and match:
        logger.info(
            "Ping migration test: packets sent: %s received: %s [max defined "
            "packet loss: %s]",
            count, int(match[0]), max_loss
        )
        return int(match[0]) >= max_loss
    return ret[0] == 0


def wait_for_port(host, port):
    """
    Wait for listening TCP port on host

    Args:
        host (Host): Host object
        port (int): TCP port number

    Returns:
        bool: True, if TCP port is open on host, False otherwise
    """

    def run_netstat():
        """
        Run netstat to check if remote host has a specific open open

        Returns:
            bool: True if open is open, False otherwise
        """
        cmd = "netstat -ltn | grep :{port}".format(port=port)
        rc = host.executor().run_cmd(shlex.split(cmd))[0]
        logger.debug("netstat command: '%s' return code: %s", cmd, rc)
        return rc == 0

    sampler = TimeoutingSampler(timeout=2, sleep=3, func=run_netstat)
    return sampler.waitForFuncStatus(result=True)


def check_dns_resolver(vm, ip_address):
    """
    Check if IP address is configured as a DNS resolver in a VM

    Args:
        vm (str): VM name
        ip_address (str): DNS IP address

    Returns:
        bool: True if given IP address is configured as resolver on VM,
            False if not, or error has occurred

    """
    logger.info("Looking for nameserver: %s in %s", ip_address, vm)
    fs = ovn_conf.OVN_VMS_RESOURCES[vm].fs
    resolv_content = ""
    if fs.exists(ovn_conf.OVN_CMD_RESOLV_CONFIG):
        resolv_content = fs.read_file(ovn_conf.OVN_CMD_RESOLV_CONFIG)
    else:
        logger.error("Unable to locate: %s", ovn_conf.OVN_CMD_RESOLV_CONFIG)
    return ip_address in resolv_content


def check_hot_unplug_and_plug(
    vm, vnic, network=None, vnic_profile=None, mac_address=None
):
    """
    Check hot-plug and hot-unplug vNIC on VM, and change network, vNIC
    profile or MAC address values

    Args:
        vm (str): VM name
        vnic (str): vNIC name (as represented in the OS)
        network (str): Network name
        vnic_profile (str): vNIC profile
        mac_address (str): MAC address

    Returns:
        bool: True if action was successful, False otherwise

    """
    for state, action in zip(
        ("False", "True"), ("Hot-unplugging", "Hot-plugging")
    ):
        update_nic_args = {
            "positive": True,
            "vm": vm,
            "nic": vnic,
            "plugged": state,
            "mac_address": mac_address
        }

        testflow.step("%s vNIC: %s on VM: %s", action, ovn_conf.OVN_VNIC, vm)
        msg = "Changing vNIC: {vnic} {prop} to: {val}"

        if network and state == "True":
            testflow.step(msg.format(vnic=vnic, prop="network", val=network))
            update_nic_args["network"] = network
        if vnic_profile and state == "True":
            testflow.step(
                msg.format(vnic=vnic, prop="vNIC profile", val=vnic_profile)
            )
            update_nic_args["vnic_profile"] = vnic_profile
        if mac_address and state == "True":
            testflow.step(
                msg.format(vnic=vnic, prop="MAC address", val=mac_address)
            )
        if not ll_vms.updateNic(**update_nic_args):
            return False
    return True


def check_ping_during_vm_migration(ping_kwargs, migration_kwargs):
    """
    Check VM migration while sending ping to the VM

    Args:
        ping_kwargs (dict): send_ping function kwargs
        migration_kwargs (dict): migrate_vms function kwargs

    Returns:
        bool: True if migration and ping tests were successful, False if one
            of them failed

    """
    ping_job = jobs.Job(target=check_ping, args=(), kwargs=ping_kwargs)
    migrate_job = jobs.Job(
        target=hl_vms.migrate_vms, args=(), kwargs=migration_kwargs
    )
    job_set = jobs.JobsSet()
    job_set.addJobs(jobs=[ping_job, migrate_job])
    job_set.start()
    job_set.join(timeout=ovn_conf.OVN_MIGRATION_TIMEOUT)

    logger.info(
        "Migration job result: %s ping job result: %s", migrate_job.result,
        ping_job.result
    )
    return migrate_job.result and ping_job.result


def set_vm_non_mgmt_interface_mtu(vm, mtu):
    """
    Set IP on the non-mangement interface of a VM

    Args:
        vm (Host): VM Host object
        mtu (int): MTU size

    Returns:
        bool: True if succeeded, False otherwise
    """
    eth = net_helper.get_non_mgmt_nic_name(vm_resource=vm)
    if not eth:
        return False
    else:
        eth = eth[0]

    return vm.network.set_mtu(nics=[eth], mtu=str(mtu))


def restart_service_and_wait(host, service, port):
    """
    Restart a system service and wait for service port to be opened

    Args:
        host (Host): Host object
        service (str): Service name
        port (int): TCP Port number

    Returns:
        bool: True if service is restarted and service port is opened,
            False otherwise
    """
    if not service_handler(host=host, service=service, action="restart"):
        return False

    return wait_for_port(host=host, port=port)


def service_handler(host, service, action="stop"):
    """
    System service handler

    Args:
        host (Host): Host object
        service (str): Service name
        action (str): Action to take on service, can be "stop", "start",
            "restart" or "active" to get running service state

    Returns:
        bool: True if action was successful or if service state is running,
            False otherwise

    """
    if action == "start":
        return host.service(name=service).start()
    elif action == "stop":
        try:
            return host.service(name=service).stop()
        except Exception:
            return True
    elif action == "restart":
        return host.service(name=service).restart()
    elif action == "active":
        return host.run_command(
            shlex.split(ovn_conf.OVN_CMD_SERVICE_STATUS.format(name=service))
        )[0] == 0
    else:
        return False


def get_provider_from_engine(provider_name, keystone_user, keystone_pass):
    """
    Get OVN provider from engine

    Args:
        provider_name (str): Provider name
        keystone_user (str): Keystone username
        keystone_pass (str): Keystone password

    Returns:
        bool: True if get was successful, False otherwise
    """
    ovn_conf.OVN_EXTERNAL_PROVIDER_PARAMS["name"] = provider_name
    ovn_conf.OVN_EXTERNAL_PROVIDER_PARAMS["keystone_username"] = keystone_user
    ovn_conf.OVN_EXTERNAL_PROVIDER_PARAMS["keystone_password"] = keystone_pass
    return external_providers.ExternalNetworkProvider(
        **ovn_conf.OVN_EXTERNAL_PROVIDER_PARAMS
    )


def get_float(str_float):
    """
    Convert a given string to float number

    Args:
        str_float (str): String to be converted to float

    Returns:
        tuple: True/False for conversion result, and converted float value
    """
    try:
        return True, float(str_float)
    except ValueError:
        return False, 0.0


def collect_performance_counters(hosts):
    """
    Collect host(s) CPU and memory performance counters

    Args:
        hosts (list): List of host resources to benchmark

    Returns:
        tuple: average rounded CPU usage value, average rounded memory usage
            value, or empty tuple if error occurred during collection
    """
    cpu_counters = []
    memory_counters = []
    cpu_counter = mem_counter = 0.0

    while any(ovn_conf.COLLECT_PERFORMANCE_FLAGS):
        for host in hosts:
            # CPU counter collection
            if ovn_conf.COLLECT_PERFORMANCE_FLAGS[0]:
                cpu_rc, cpu_out, _ = host.run_command(
                    ovn_conf.OVN_CMD_GET_CPU_USAGE.split(" ")
                )
                is_float, cpu_counter = get_float(str_float=cpu_out)
                if cpu_rc or not is_float:
                    logger.error(
                        "Unexpected CPU collection output: %s", cpu_out
                    )
                    return ()
            # Memory counter collection
            if ovn_conf.COLLECT_PERFORMANCE_FLAGS[1]:
                mem_rc, mem_out, _ = host.run_command(
                    ovn_conf.OVN_CMD_GET_MEM_USAGE.split(" ")
                )
                is_float, mem_counter = get_float(str_float=mem_out)
                if mem_rc or not is_float:
                    logger.error(
                        "Unexpected memory collection output: %s", mem_out
                    )
                    return ()
            # Save counters on list
            cpu_counters.append(cpu_counter)
            memory_counters.append(mem_counter)

    # Calculate average values and round them
    avg_cpu = round(sum(cpu_counters) / len(cpu_counters))
    avg_memory = round(sum(memory_counters) / len(memory_counters))

    logger.info("Collected CPU counters: %s", cpu_counters)
    logger.info("Collected memory counters: %s", memory_counters)
    return avg_cpu, avg_memory


def copy_file_benchmark(**kwargs):
    """
    Copy file from source host to destination host and collect performance
    counters from VDS hosts: HOST-0 and HOST-1

    Keyword Args:
        src_host (Host): Source host resource
        dst_host (Host): Destination host resource
        dst_ip (str): Destination IP address
        size (int): Size in megabytes (MB)

    Returns:
        tuple: Copy job result and performance job result
    """
    # Create jobs
    performance_job = jobs.Job(
        target=collect_performance_counters, args=(),
        kwargs={"hosts": [net_conf.VDS_0_HOST, net_conf.VDS_1_HOST]}
    )
    copy_job = jobs.Job(target=check_ssh_file_copy, args=(), kwargs=kwargs)

    job_set = jobs.JobsSet()
    job_set.addJobs(jobs=[copy_job, performance_job])
    job_set.start()
    job_set.waitUntilAnyDone(time=ovn_conf.OVN_COPY_TIMEOUT)

    # Stop and clear collection threads
    ovn_conf.COLLECT_PERFORMANCE_FLAGS = False, False

    # Join threads to wait for performance job be completed
    job_set.join(timeout=ovn_conf.OVN_COPY_TIMEOUT)

    logger.info(
        "Copy job result: %s performance job result: %s",
        copy_job.result, performance_job.result
    )
    return copy_job.result, performance_job.result


def is_tcp_port_open(host, port, timeout=5):
    """
    Check if TCP port is open on host

    Args:
        host (str): Host name
        port (int): Port number
        timeout (int): Timeout

    Returns:
        bool: True if port is open, False otherwise
    """
    sock = socket.socket()
    sock.settimeout(timeout)

    with closing(sock):
        try:
            sock.connect((host, port))
        except socket.error as err:
            logger.error(
                "failed to connect %s port %s: %s", host, port, err
            )
            return False
    logger.info("TCP port: %s is open on: %s", port, host)
    return True


def check_ldap_availability(server, ports):
    """
    Check if LDAP server is available by enumerating LDAP TCP ports

    Args:
        server (str): LDAP server name
        ports (list): List of LDAP ports to enumerate

    Returns:
        bool: True if LDAP server is available, False otherwise
    """
    for ldap_port in ports:
        logger.info("Checking if LDAP port: %s is available", ldap_port)
        if is_tcp_port_open(host=server, port=ldap_port, timeout=3):
            return True
    return False


@ll_general.generate_logs(step=True)
def wait_for_auto_sync(
    networks, removal=True, timeout=ovn_conf.AUTO_SYNC_WAIT
):
    """
    Wait for networks changes to be synced by auto-sync

    Args:
        networks (list): List of network names to expect
        removal (bool): True to wait for removal of networks, False for
            creation of networks
        timeout (int): Timeout in seconds for auto-sync

    Returns:
        bool: True if operation was successful, False otherwise
    """
    sample = TimeoutingSampler(
        timeout=timeout, sleep=1,
        func=lambda:
            all(
                n not in hl_networks.get_network_names()
                if removal else
                n in hl_networks.get_network_names()
                for n in networks
            )
    )
    return sample.waitForFuncStatus(result=True)
