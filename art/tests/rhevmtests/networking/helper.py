#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for networking jobs
"""

import logging
import os
import random
import re
import shlex

from art.rhevm_api.utils import jobs
from rhevmtests.networking import config
from rhevmtests import helpers

from art.rhevm_api.tests_lib.high_level import (
    host_network as hl_host_network,
    networks as hl_networks,
)
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    events as ll_events,
    host_network as ll_host_network,
    hosts as ll_hosts,
    vms as ll_vms,
    general as ll_general,
    datacenters as ll_datacenters,
    mac_pool as ll_mac_pool,
    networks as ll_networks,
    templates as ll_templates,
    events
)
import config as conf
from art.core_api import apis_utils
from art.rhevm_api.utils import test_utils
from art.test_handler import settings

logger = logging.getLogger("Global_Network_Helper")

ENUMS = settings.ART_CONFIG['elements_conf']['RHEVM Enums']
IFCFG_PATH = "/etc/sysconfig/network-scripts"
EXCLUDE_NICS = ["ifcfg-eth0", "ifcfg-lo"]
APPLY_NETWORK_CHANGES_EVENT_CODE = 1146
VIRSH_USER = "virsh"
VIRSH_PASS = "qum5net"
PE_EXPECT = "pe.expect"
PE_SENDLINE = "pe.sendline"
SN_TIMEOUT = 300
IFCFG_NETWORK_SCRIPTS_DIR = '/etc/sysconfig/network-scripts'
TCDUMP_TIMEOUT = "60"
MTU_DEFAULT_VALUE = 1500
SYS_CLASS_NET_DIR = '/sys/class/net'
DEFAULT_DC_CL = "Default"
BLANK_TEMPLATE = "Blank"


def create_random_ips(num_of_ips=2, mask=16, ip_version=4, base_ip_prefix="5"):
    """
    Create random IPs (only support masks 8/16/24)

    Args:
        num_of_ips (int): Number of IPs to create
        mask (int): IP subnet to create the IPs for
        ip_version (int): IP version to generate IPs (6 or 4)
        base_ip_prefix (str): IP number to generate IP from. (5 will
            generate 5.5.5.x according to mask)

    Returns:
        list: List of IPs
    """
    ips = list()
    if ip_version == 4:
        ip_mask = mask // 8
        base_ip = ".".join(base_ip_prefix * ip_mask)
    elif ip_version == 6:
        ip_mask = 3
        base_ip = "2001::"
    else:
        logger.error("IP version %s is not supported", ip_version)
        return ips

    int_list = random.sample(xrange(1, 250), 200)
    for i in xrange(num_of_ips):
        if ip_version == 4:
            ip_str = ""
            for x in range(4 - ip_mask):
                ip_str += ".{ip_oct}".format(ip_oct=int_list.pop(x))
            ips.append("".join([base_ip, ip_str]))

        if ip_version == 6:
            ips.append("{0}{1}".format(base_ip, int_list.pop(i)))
    return ips


def seal_vm(vm, root_password):
    """
    Start VM, seal VM and stop VM

    :param vm: VM name
    :type vm: str
    :param root_password: VM root password
    :type root_password: str
    :return: True/False
    :rtype: bool
    """
    if not ll_vms.startVm(positive=True, vm=vm):
        return False

    rc, out = ll_vms.wait_for_vm_ip(vm=vm, timeout=300, sleep=10)
    if not rc:
        return False

    ip = out["ip"]
    if not test_utils.setPersistentNetwork(host=ip, password=root_password):
        return False

    if not ll_vms.stopVm(positive=True, vm=vm):
        return False
    return True


def networks_sync_status(host, networks):
    """
    Get networks sync status

    Args:
        host (str): Host name
        networks (list): List of networks

    Returns:
        bool: True if sync else False
    """
    host_obj = ll_hosts.get_host_object(host_name=host)
    for net in networks:
        logger.info("Get %s attachment", net)
        try:
            attachment = ll_host_network.get_networks_attachments(
                host=host_obj, networks=[net]
            )[0]
        except IndexError:
            logger.error("%s not found" % net)
            return False

        logger.info("Check if %s is unsync", net)
        if not attachment.in_sync:
            logger.info("%s is not sync" % net)
            return False
    return True


def sync_networks(host, networks):
    """
    Sync the networks

    :param host: Host name
    :type host: str
    :param networks: List of networks to sync
    :type networks: list
    :return: True/False
    :rtype: bool
    """
    network_sync_dict = {
        "sync": {
            "networks": networks
        }
    }
    logger.info("syncing %s", networks)
    if not hl_host_network.setup_networks(host_name=host, **network_sync_dict):
        logger.error("Failed to sync %s", networks)
        return False

    if not networks_sync_status(host=host, networks=networks):
        logger.error(
            "At least one of the networks from %s is out of sync, should be "
            "synced", networks
        )
        return False
    return True


def update_host_net_qos(qos_name, datacenter=conf.DC_NAME[0], **qos_dict):
    """
    Update host network qos parameters with given dict parameters

    :param qos_name: Name of the host network QoS
    :type qos_name: str
    :param datacenter: Datacenter to create QoS on
    :type datacenter: str
    :param qos_dict: dict of host network qos values to update
    :type qos_dict: dict
    :raises: NetworkException
    """
    logger.info("Update network host QoS values with %s ", qos_dict)
    if not ll_dc.update_qos_in_datacenter(
        datacenter=datacenter, qos_name=qos_name, **qos_dict
    ):
        raise conf.NET_EXCEPTION(
            "Couldn't update Network QOS under DC with provided parameters"
        )


def prepare_dummies(host_resource, num_dummy=2):
    """
    Prepare dummies interfaces on host

    :param host_resource: Host resource object
    :type host_resource: resources.VDS
    :param num_dummy: Number of dummies to create
    :type num_dummy: int
    :raise: NetworkException
    """
    host_name = ll_hosts.get_host_name_from_engine(host_resource)
    assert hl_networks.create_dummy_interfaces(
        host=host_resource, num_dummy=num_dummy
    )
    last_event = events.get_max_event_id()
    assert ll_hosts.refresh_host_capabilities(
        host=host_name, start_event_id=last_event
    )
    sample = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1,
        func=check_dummy_on_host_interfaces, dummy_name=conf.DUMMY_0,
        host_name=host_name
    )
    assert sample.waitForFuncStatus(result=True)


def check_dummy_on_host_interfaces(dummy_name, host_name):
    """
    Check if dummy interface if on host via engine

    :param dummy_name: Dummy name
    :type dummy_name: str
    :param host_name: Host name
    :type host_name: str
    :return: True/False
    :rtype: bool
    """
    host_obj = ll_hosts.get_host_object(host_name=host_name)
    host_nics = ll_hosts.get_host_nics_list(host=host_obj)
    logger.info(
        "Check if dummy %s exist on host %s via engine",
        dummy_name, host_name
    )
    for nic in host_nics:
        if dummy_name == nic.name:
            return True
    logger.warning("Dummy %s does not exist in host %s", dummy_name, host_name)
    return False


def delete_dummies(host_resource):
    """
    Delete all dummies interfaces from host

    :param host_resource: Host resource object
    :type host_resource: resources.VDS
    """
    host_name = ll_hosts.get_host_name_from_engine(host_resource)
    hl_networks.delete_dummy_interfaces(host=host_resource)
    last_event = events.get_max_event_id()
    ll_hosts.refresh_host_capabilities(
        host=host_name, start_event_id=last_event
    )
    sample = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1,
        func=check_dummy_on_host_interfaces, dummy_name=conf.DUMMY_0,
        host_name=host_name
    )
    sample.waitForFuncStatus(result=False)


def is_network_in_vds_caps(host_resource, network, type_="networks"):
    """
    Check if network exists in vdsCaps output

    Args:
        host_resource (VDS): Host resource object
        network (str): Network name
        type_ (str): Network type (vlans, bridges, networks)

    Returns:
        bool: True if network found, false otherwise
    """
    logger.info("Get vdsCaps output")
    out = host_resource.vds_client(cmd="getCapabilities")
    logger.info("Check if %s in vdsCaps output", network)
    if network not in out.get(type_, dict()).keys():
        logger.error("%s %s is missing in vdsCaps", type_, network)
        return False
    return True


def check_traffic_during_func_operation(
    func, func_kwargs, tcpdump_kwargs
):
    """
    Search for packets in tcpdump output during given func (func) action

    :param func: Function object to run with tcpdump command
    :type func: function
    :param func_kwargs: Parameters of the function
    :type func_kwargs: dict
    :param tcpdump_kwargs: Parameters of the tcpdump function
    :type tcpdump_kwargs: dict
    :return True/False
    :rtype: bool

    :Example:

    tcpdump_kwargs = {
        "host_obj": listen_vm_obj,
        "nic": nic,
        "src": src_ip,
        "dst": dst_ip,
        "numPackets": 5,
        "timeout": str(conf.TIMEOUT)
    }

    icmp_kwargs = {
        "dst": dst_ip,
        "count": "10",
    }

    net_help.check_traffic_during_func_operation(
        func=src_vm_resource.network.send_icmp, func_kwargs=icmp_kwargs,
        tcpdump_kwargs=tcpdump_kwargs
    )
    """
    tcpdump_job = jobs.Job(run_tcp_dump, (), tcpdump_kwargs)
    func_job = jobs.Job(func, (), func_kwargs)
    job_set = jobs.JobsSet()
    job_set.addJobs([tcpdump_job, func_job])
    job_set.start()
    job_set.join(int(tcpdump_kwargs.get("timeout", conf.DUMP_TIMEOUT)) + 5)
    return tcpdump_job.result and func_job.result


def remove_ifcfg_files(vms_resources, exclude_nics=list()):
    """
    Remove all ifcfg files beside exclude_nics from vms

    Args:
        vms_resources (list): List of VMs resources
        exclude_nics (list): NICs to exclude from remove

    Returns:
        bool: True if operation succeed, False otherwise
    """
    exclude_nics = exclude_nics if exclude_nics else EXCLUDE_NICS
    for vm_resource in vms_resources:
        rc, out, _ = vm_resource.run_command(["ls", "%s/ifcfg-*" % IFCFG_PATH])
        if rc:
            return False

        ifcfg_files = filter(
            lambda x: x.rsplit("/")[-1] not in exclude_nics, out.splitlines()
        )
        for ifcfg in ifcfg_files:
            logger.info("Remove %s from %s", ifcfg, vm_resource)
            if not vm_resource.fs.remove(path=ifcfg):
                logger.error("Fail to remove %s for %s", ifcfg, vm_resource)
        vm_resource.run_command(["sync"])
    return True


def get_vm_interfaces_list(vm_resource, exclude_nics=list()):
    """
    Get VM interface list beside exclude_nics

    :param vm_resource: VM resource
    :type vm_resource: Resource.VDS
    :param exclude_nics: NICs to exclude from the list
    :type exclude_nics: list
    :return: VM interfaces list
    :rtype: list
    """
    logger.info("Getting interfaces list from %s", vm_resource.ip)
    vm_nics = vm_resource.network.all_interfaces()
    res = filter(lambda x: x not in exclude_nics, vm_nics)
    if not res:
        logger.error("Failed to get VM %s interfaces list", vm_resource.ip)
    return res


def send_icmp_sampler(
    host_resource, dst, count="5", size="1470", extra_args=None,
    timeout=conf.SAMPLER_TIMEOUT, sleep=1
):
    """
    Send ICMP to destination IP/FQDN

    :param host_resource: Host resource
    :param dst: IP/FQDN to send ICMP to
    :type dst: str
    :param count: Number of ICMP packets to send
    :type count: str
    :param size: Size of the ICMP packet
    :type size: str
    :param extra_args: Extra args for ping command
    :type extra_args: str
    :param timeout: Time to try
    :type timeout: int
    :param sleep: Time to sleep between each try
    :type sleep: int
    :return: True/False
    :rtype: bool
    """
    logger.info("Check ICMP traffic from %s to %s", host_resource.ip, dst)
    sample = test_utils.TimeoutingSampler(
        timeout=timeout, sleep=sleep, func=host_resource.network.send_icmp,
        dst=dst, count=count, size=size, extra_args=extra_args
    )
    if not sample.waitForFuncStatus(result=True):
        logger.error("Couldn't ping %s ", dst)
        return False

    logger.info("Traffic from %s to %s succeed", host_resource.ip, dst)
    return True


def wait_for_sn(content, last_event, matches=1):
    """
    Wait for setupNetworks call to finish by checking events

    :param content: String to search in event description
    :type content: str
    :param last_event: The last event to check events from
    :type: Event
    :param matches: Number of matches to find in events
    :type matches: int
    :raise: NetworkException
    """
    assert ll_events.find_event(
        last_event=last_event, event_code=APPLY_NETWORK_CHANGES_EVENT_CODE,
        content=content, matches=matches, timeout=SN_TIMEOUT
    )


def call_function_and_wait_for_sn(func, content, matches=1, **func_kwargs):
    """
    Call related network function (update_network, add_label) and wait for
    setupNetworks to finish (By waiting for event)

    :param func: Function to call
    :type func: function
    :param content: Content to search in event description
    :type content: str
    :param matches: Number of matches to find in events
    :type matches: int
    :param func_kwargs: Function kwargs
    :type func_kwargs: dict
    :raise: NetworkException
    """
    err_log = "Failed to call %s with %s" % (func.__name__, func_kwargs)
    last_event = ll_events.get_last_event(APPLY_NETWORK_CHANGES_EVENT_CODE)
    assert func(**func_kwargs), err_log
    wait_for_sn(content=content, last_event=last_event, matches=matches)


def check_queues_from_qemu(vm, num_queues):
    """
    Get numbers of queues from qemu process by VM name

    Args:
        vm (str): VM name
        num_queues (int): Number of queues to check

    Returns:
        bool: True if num_queues match the VM queues, False otherwise
    """
    host = ll_vms.get_vm_host(vm_name=vm)
    host_obj = conf.VDS_HOSTS[conf.HOSTS.index(host)]
    cmd = ["pgrep", "-a", "qemu-kvm"]
    rc, out, _ = host_obj.run_command(cmd)
    if rc:
        return False

    logger.info("Check if VM %s have number of queues == %s", vm, num_queues)
    running_vms = re.findall(r'\d+ .*qemu-kvm.*', out)
    for run_vm in running_vms:
        if re.findall(r'-name.*%s' % vm, run_vm):
            qemu_queues = re.findall(r'fds=[\d+:]+', out)
            if not qemu_queues:
                if num_queues == 0:
                    return True

                logger.error("Queues not found in qemu")
                return False

            for queue in qemu_queues:
                striped_queue = queue.strip("fds=")
                queues_found = len(striped_queue.split(":"))
                if num_queues != queues_found:
                    logger.error(
                        "%s queues found in qemu, didn't match the expected "
                        "%s queues", queues_found, num_queues
                    )
                    return False
            return True
    logger.error("%s not found on host", vm)
    return False


def get_non_mgmt_nic_name(vm_resource):
    """
    Get VM interface list excluding management network.

    Args:
        vm_resource (Host): VM resource.

    Returns:
        list: VM interface list.
    """
    mgmt_interface = vm_resource.network.find_mgmt_interface()

    logger.info(
        "Get VM interface excluding mgmt interface %s", mgmt_interface
    )
    return get_vm_interfaces_list(
        vm_resource=vm_resource, exclude_nics=[mgmt_interface]
    )


@ll_general.generate_logs(step=True)
def network_manager_remove_all_connections(host):
    """
    Remove all NetworkManager connections from host.

    Args:
        host (Host): Host resource.

    Returns:
        bool: True if all connections deleted, False otherwise.
    """
    res = list()
    all_connections = "nmcli connection show"
    delete_cmd = "nmcli connection delete {uuid}"
    rc, out, _ = host.run_command(
        command=shlex.split(all_connections)
    )
    if rc:
        return False

    for match in re.findall(r'\w+-\w+-\w+-\w+-\w+', out):
        res.append(
            host.run_command(
                command=shlex.split(delete_cmd.format(uuid=match))
            )[0]
        )
    return not all(res)


@helpers.ignore_exception
def remove_unneeded_vms_nics():
    """
    Remove all NICs from VM besides nic1
    """
    logger.info("Removing all NICs from VMs besides %s", config.NIC_NAME[0])
    mgmt_profiles_ids = []
    logger.info("Getting all %s vNIC profiles ids", config.MGMT_BRIDGE)
    for vnic_obj in ll_networks.get_vnic_profile_objects():
        if vnic_obj.name == config.MGMT_BRIDGE:
            mgmt_profiles_ids.append(vnic_obj.id)

    for vm in config.VM_NAME:
        vm_nics = ll_vms.get_vm_nics_obj(vm)
        for nic in vm_nics:
            if nic.name == config.NIC_NAME[0]:
                if nic.vnic_profile.id in mgmt_profiles_ids:
                    continue

                logger.info(
                    "Updating %s to %s profile on %s",
                    nic.name, config.MGMT_BRIDGE, vm
                )
                if not ll_vms.updateNic(
                    positive=True, vm=vm, nic=nic.name,
                    network=config.MGMT_BRIDGE,
                    vnic_profile=config.MGMT_BRIDGE, interface="virtio"
                ):
                    logger.error(
                        "Failed to update %s to profile %s on %s",
                        nic.name, config.MGMT_BRIDGE, vm
                    )
                logger.info("Found %s on %s. Not removing", nic.name, vm)

            else:
                logger.info("Removing %s from %s", nic.name, vm)
                if not ll_vms.removeNic(True, vm, nic.name):
                    logger.error("Failed to remove %s from %s", nic, vm)


@helpers.ignore_exception
def remove_unneeded_vnic_profiles():
    """
    Remove all vNIC profiles besides MGMT_PROFILE
    """
    logger.info(
        "Removing all vNIC profiles besides %s profile", config.MGMT_BRIDGE
    )
    for vnic in ll_networks.get_vnic_profile_objects():
        if vnic.name != config.MGMT_BRIDGE:
            logger.info("Removing %s profile", vnic.name)
            if not ll_networks.VNIC_PROFILE_API.delete(vnic, True):
                logger.error("Failed to remove %s profile", vnic.name)


@helpers.ignore_exception
def remove_unneeded_vms():
    """
    Remove all unneeded VMs
    """
    logger.info("Get all VMs")
    conf_vms = config.VM_NAME + [config.HE_VM]
    vms_to_remove = [
        vm for vm in ll_vms.get_all_vms_names() if vm not in conf_vms
    ]
    if vms_to_remove:
        logger.warning("VMs to remove: %s", vms_to_remove)
        ll_vms.safely_remove_vms(vms=vms_to_remove)


@helpers.ignore_exception
def remove_unneeded_templates():
    """
    Remove all templates besides [config.TEMPLATE_NAME]
    """
    logger.info("Get all templates")
    all_templates = ll_templates.TEMPLATE_API.get(abs_link=False)
    for template in all_templates:
        if template.name == BLANK_TEMPLATE:
            continue

        if template.name not in config.TEMPLATE_NAME:
            if not ll_templates.remove_template(
                positive=True, template=template.name
            ):
                logger.info("Failed to remove %s", template.name)


@helpers.ignore_exception
def remove_qos_from_setup():
    """
    Remove all QoS from datacenters
    """
    for dc in config.DC_NAME:
        all_qos = ll_datacenters.get_qoss_from_datacenter(datacenter=dc)
        for qos in all_qos:
            qos_name = qos.get_name()
            if qos_name == config.DEFAULT_MGMT_QOS:
                continue
            ll_datacenters.delete_qos_from_datacenter(
                datacenter=dc, qos_name=qos_name
            )


@helpers.ignore_exception
def remove_unneeded_mac_pools():
    """
    Remove unneeded MAC pools from setup (non Default MAC pool)
    """
    all_macs = ll_mac_pool.get_all_mac_pools()
    for mac in filter(lambda x: x.name != "Default", all_macs):
        ll_mac_pool.remove_mac_pool(mac_pool_name=mac.name)


def configure_temp_static_ip(
    vds_resource, ip, nic="eth1", netmask="255.255.255.0"
):
    """
    Configure temporary static IP on specific interface

    Args:
        vds_resource (VDS): VDS resource
        ip (str): temporary IP to configure on NIC
        nic (str): specific NIC to configure ip/netmask on
        netmask (str): netmask to configure on NIC (full or CIDR)

    Returns:
        bool:  True if command executed successfully, False otherwise
    """
    cmd = ["ip", "address", "add", "%s/%s" % (ip, netmask), "dev", nic]
    return not vds_resource.run_command(cmd)[0]


def check_mtu(
    vds_resource, mtu, physical_layer=True, network=None, nic=None,
    vlan=None, bond=None, bond_nic1='eth3', bond_nic2='eth2', bridged=True
):
    """
    Check MTU for all files provided from build_list_files_mtu function
    Uses helper test_mtu_in_script_list function to do it

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param mtu: the value to test against
    :type mtu: int
    :param network: the network name to test the MTU value
    :type network: str
    :param physical_layer: flag to test MTU for physical or logical layer
    :type physical_layer: bool
    :param nic: interface name to test the MTU value for
    :type nic: str
    :param vlan: vlan number to test the MTU value for nic.vlan
    :type vlan: str
    :param bond: bond name to test the MTU value for
    :type bond: str
    :param bond_nic1: name of the first nic of the bond
    :type bond_nic1: str
    :param bond_nic2: name of the second nic of the bond
    :type bond_nic2: str
    :param bridged: flag, to differentiate bridged and non_bridged network
    :type bridged: bool
    :return: True value if MTU in script files is correct
    :rtype: bool
    """
    ifcfg_script_list, sys_class_net_list = build_list_files_mtu(
        physical_layer=physical_layer, network=network, nic=nic, vlan=vlan,
        bond=bond, bond_nic1=bond_nic1, bond_nic2=bond_nic2, bridged=bridged
    )
    if not ifcfg_script_list or not sys_class_net_list:
        if not physical_layer and not bridged and not vlan:
            return True
        else:
            logger.error("The file with MTU parameter is empty")
            return False
    return test_mtu_in_script_list(
        vds_resource=vds_resource, script_list=ifcfg_script_list, mtu=mtu,
        flag_for_ifcfg=1) and test_mtu_in_script_list(
        vds_resource=vds_resource, script_list=sys_class_net_list, mtu=mtu
    )


def test_mtu_in_script_list(vds_resource, script_list, mtu, flag_for_ifcfg=0):
    """
    Helper function for check_mtu to test specific list of files

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param script_list: list with names of files to test MTU in
    :type script_list: list
    :param mtu: the value to test against
    :type mtu: int
    :param flag_for_ifcfg: flag if this file is ifcfg or not
    :type flag_for_ifcfg: int
    :return: True value if MTU in script list is correct
    :type: bool
    """
    err_msg = '"MTU in {0} is {1} when the expected is {2}"'
    for script_name in script_list:
        logger.info("Check if MTU for %s is %s", script_name, mtu)
        rc, out, _ = vds_resource.run_command(['cat', script_name])
        if rc:
            return False
        if flag_for_ifcfg:
            match_obj = re.search('MTU=([0-9]+)', out)
            if match_obj:
                mtu_script = int(match_obj.group(1))
            else:
                mtu_script = MTU_DEFAULT_VALUE
            if mtu_script != mtu:
                logger.error(err_msg.format(script_name, mtu_script, mtu))
                return False
        else:
            if int(out) != mtu:
                logger.error(err_msg.format(script_name, out, mtu))
                return False
    return True


def configure_temp_mtu(vds_resource, mtu, nic="eth1"):
    """
    Configure MTU temporarily on specific host interface

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param mtu: MTU to be configured on the host interface
    :type mtu: string
    :param nic: specific interface to configure MTU on
    :type nic: string
    :return: True if command executed successfully, False otherwise
    :rtype: bool
    """
    cmd = ["ip", "link", "set", "dev", nic, "mtu", mtu]
    rc, _, _ = vds_resource.run_command(cmd)
    if rc:
        return False
    return True


def run_tcp_dump(host_obj, nic, **kwargs):
    """
    Runs tcpdump on the given machine and returns its output.

    :param host_obj: Host resource
    :type host_obj: resources.VDS object
    :param nic: interface on which traffic will be monitored
    :type nic: str
    :param kwargs: Extra kwargs
    :type kwargs: dict
        :param src: source IP by which to filter packets
        :type src: str
        :param dst: destination IP by which to filter packets
        :type dst: str
        :param srcPort: source port by which to filter packets, should be
                       numeric (e.g. 80 instead of 'HTTP')
        :type srcPort: str
        :param dstPort: destination port by which to filter packets, should
                       be numeric like 'srcPort'
        :type dstPort: str
        :param protocol: protocol by which traffic will be received
        :type protocol: str
        :param numPackets: number of packets to be received (10 by default)
        :type numPackets: str
    :return: Returns tcpdump's output and return code.
    :rtype: tuple
    """
    cmd = [
        "timeout", kwargs.pop("timeout", TCDUMP_TIMEOUT), "tcpdump", "-i",
        nic, "-c", str(kwargs.pop("numPackets", "10")), "-nn"
    ]
    if kwargs:
        for k, v in kwargs.iteritems():
            cmd.extend([k, str(v), "and"])
        cmd.pop()  # Removes unnecessary "and"

    logger.info("TcpDump command to be sent: %s", cmd)
    host_exec = host_obj.executor()
    rc, output, err = host_exec.run_cmd(cmd)
    logger.debug("TcpDump output:\n%s", output)
    if rc:
        logger.error(
            "Failed to run tcpdump command or no packets were captured by "
            "filter. Output: %s ERR: %s", output, err
        )
        return False
    return True


def check_configured_mtu(vds_resource, mtu, inter_or_net):
    """
    Checks if the configured MTU on an interface or network match
    provided MTU using ip command

    Args:
        vds_resource (VDS): VDS resource
        mtu (str): expected MTU for the network/interface
        inter_or_net (str): interface name or network name

    Returns:
        bool: True if MTU on host is equal to "mtu", False otherwise.
    """
    logger.info(
        "Checking if %s is configured correctly with MTU %s", inter_or_net, mtu
    )
    cmd = ["ip", "link", "list", inter_or_net, "|", "grep", mtu]
    rc, out, _ = vds_resource.run_command(cmd)
    if rc:
        return False

    if out.find(mtu) == -1:
        logger.error(
            "MTU is not configured correctly on %s: %s", inter_or_net, out
        )
        return False
    return True


def build_list_files_mtu(
    physical_layer=True, network=None, nic=None, vlan=None, bond=None,
    bond_nic1='eth3', bond_nic2='eth2', bridged=True
):
    """
    Builds a list of file names to check MTU value

    :param network: network name to build ifcfg-network name
    :type network: str
    :param physical_layer: flag to create file names for physical or logical
    layer
    :type physical_layer: bool
    :param nic: nic name to build ifcfg-nic name
    :type nic: str
    :param vlan: vlan name to build ifcfg-* files names for
    :type vlan: str
    :param bond: bond name to create ifcfg-* files names for
    :type bond: str
    :param bond_nic1: name of the first nic of the bond
    :type bond_nic1: str
    :param bond_nic2: name of the second nic of the bond
    :type bond_nic2: str
    :param bridged: flag, to differentiate bridged and non_bridged network
    :type bridged: bool
    :return: 2 lists of ifcfg files names
    :rtype: tuple
    """
    ifcfg_script_list = []
    sys_class_net_list = []
    temp_name_list = []
    if not physical_layer:
        if bridged:
            temp_name_list.append("%s" % network)
        if vlan and bond:
            temp_name_list.append("%s.%s" % (bond, vlan))
        if vlan and not bond:
            temp_name_list.append("%s.%s" % (nic, vlan))
    else:
        if bond:
            for if_name in [bond_nic1, bond_nic2, bond]:
                temp_name_list.append("%s" % if_name)

        elif vlan or nic:
            temp_name_list.append("%s" % nic)

    for script_name in temp_name_list:
        ifcfg_script_list.append(os.path.join(
            IFCFG_NETWORK_SCRIPTS_DIR, "ifcfg-%s" % script_name)
        )
        sys_class_net_list.append(os.path.join(
            SYS_CLASS_NET_DIR, script_name, "mtu")
        )
    return ifcfg_script_list, sys_class_net_list
