#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for networking jobs
"""

import logging
import re
import shlex
import uuid
from random import randint

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.events as ll_events
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import rhevmtests.helpers as global_helper
from art.core_api import apis_utils
from art.rhevm_api.tests_lib.low_level import events
from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.test_handler import settings
from rhevmtests import helpers
from utilities import jobs

logger = logging.getLogger("Global_Network_Helper")

ENUMS = settings.opts['elements_conf']['RHEVM Enums']
IFCFG_PATH = "/etc/sysconfig/network-scripts"
EXCLUDE_NICS = ["ifcfg-eth0", "ifcfg-lo"]
APPLY_NETWORK_CHANGES_EVENT_CODE = 1146
VIRSH_USER = "virsh"
VIRSH_PASS = "qum5net"
PE_EXPECT = "pe.expect"
PE_SENDLINE = "pe.sendline"


def create_random_ips(num_of_ips=2, mask=16):
    """
    Create random IPs (only support masks 8/16/24)

    :param num_of_ips: Number of IPs to create
    :type num_of_ips: int
    :param mask: IP subnet to create the IPs for
    :type mask: int
    :return: IPs
    :rtype: list
    """
    ips = []
    ip_mask = mask // 8
    base_ip = ".".join("5" * ip_mask)
    for i in xrange(num_of_ips):
        rand_num = [randint(1, 250) for i in xrange(4 - ip_mask)]
        rand_oct = ".".join(str(i) for i in rand_num)
        ips.append(".".join([base_ip, rand_oct]))
    return ips


def run_vm_once_specific_host(vm, host, wait_for_up_status=False):
    """
    Run VM once on specific host

    :param vm: VM name
    :type vm: str
    :param host: Host name
    :type host: str
    :param wait_for_up_status: Wait for VM to be UP
    :type wait_for_up_status: bool
    :return: True if action succeeded, False otherwise
    :rtype: bool
    """
    logger.info("Check if %s is up", host)
    host_status = ll_hosts.get_host_status(host)
    if not host_status == ENUMS["host_state_up"]:
        logger.error("%s status is %s, cannot run VM", host, host_status)
        return False

    logger.info("Run %s once on host %s", vm, host)
    if not ll_vms.runVmOnce(positive=True, vm=vm, host=host):
        logger.error("Couldn't run %s on host %s", vm, host)
        return False

    if wait_for_up_status:
        logger.info("Wait %s to be up", vm)
        ll_vms.wait_for_vm_states(vm_name=vm)

    logger.info("Check that %s was started on host %s", vm, host)
    vm_host = ll_vms.getVmHost(vm)[1]["vmHoster"]
    if not host == vm_host:
        logger.error(
            "%s should run on %s instead of %s", vm, host, vm_host)
        return False
    return True


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
    logger.info("Start VM: %s", vm)
    if not ll_vms.startVm(positive=True, vm=vm):
        logger.error("Failed to start %s.", vm)
        return False

    logger.info("Waiting for IP from %s", vm)
    rc, out = ll_vms.waitForIP(vm=vm, timeout=180, sleep=10)
    if not rc:
        logger.error("Failed to get %s IP", vm)
        return False

    ip = out["ip"]
    logger.info("Running setPersistentNetwork on %s", vm)
    if not test_utils.setPersistentNetwork(host=ip, password=root_password):
        logger.error("Failed to seal %s", vm)
        return False

    logger.info("Stopping %s", vm)
    if not ll_vms.stopVm(positive=True, vm=vm):
        logger.error("Failed to stop %s", vm)
        return False
    return True


def prepare_networks_on_setup(networks_dict, dc, cluster=None):
    """
    Create and attach all networks that are needed for all cases

    :param networks_dict: Networks dict
    :type networks_dict: dict
    :param dc: DC name
    :type dc: str
    :param cluster: Cluster name
    :type cluster: str
    :raise: NetworkException
    """
    log = "%s/%s" % (dc, cluster) if cluster else "%s" % dc
    logger.info("Add %s to %s", networks_dict, log)
    assert hl_networks.createAndAttachNetworkSN(
        data_center=dc, cluster=cluster, network_dict=networks_dict
    )


def networks_sync_status(host, networks):
    """
    Get networks sync status

    :param host: Host name
    :type host: str
    :param networks: List of networks
    :type networks: list
    :return: True if sync else False
    :type: bool
    """
    for net in networks:
        logger.info("Get %s attachment", net)
        try:
            attachment = ll_host_network.get_networks_attachments(
                host_name=host, networks=[net]
            )[0]
        except IndexError:
            logger.error("%s not found" % net)
            return False

        logger.info("Check if %s is unsync", net)
        if not ll_host_network.get_attachment_sync_status(
            attachment=attachment
        ):
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


def remove_qos_from_dc(qos_name, datacenter=conf.DC_NAME[0], teardown=True):
    """
    Removes host network QoS from DC

    :param qos_name: Name of the host network QoS
    :type qos_name: str
    :param datacenter: Datacenter to create QoS on
    :type datacenter: str
    :param teardown: If running on teardown
    :type teardown: bool
    :raise: NetworkException
    """
    msg = "Couldn't delete the QoS %s from DC %s", qos_name, datacenter
    logger.info("Remove QoS %s from %s", qos_name, datacenter)
    res = ll_dc.delete_qos_from_datacenter(
        datacenter=datacenter, qos_name=qos_name
    )
    if not res:
        if teardown:
            logger.error(msg)
        else:
            raise conf.NET_EXCEPTION(msg)


def create_host_net_qos(
    qos_name, positive=True, datacenter=conf.DC_NAME[0], **qos_dict
):
    """
    Create a host network qos with provided parameters

    :param qos_name: Name of the host network QoS
    :type qos_name: str
    :param positive: Flag if the test is positive or not
    :type positive: bool
    :param datacenter: Datacenter to create QoS on
    :type datacenter: str
    :param qos_dict: Dict of host network qos values to create QoS with
    :type qos_dict: dict
    :return: True/False
    :rtype: bool
    """
    result = ll_dc.add_qos_to_datacenter(
        datacenter=datacenter, qos_name=qos_name,
        qos_type=conf.HOST_NET_QOS_TYPE, **qos_dict
    )
    if not result and positive:
        logger.error(
            "Couldn't create Host Network QOS under DC when should"
        )
        return False

    if result and not positive:
        logger.error(
            "Could create Host Network QOS under DC when shouldn't"
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


def set_libvirt_sasl_status(engine_resource, host_resource, sasl=False):
    """
    Set passwordless ssh from engine to host
    Set sasl on/off for libvirtd on host

    :param engine_resource: Engine resource
    :type engine_resource: resources.Engine
    :param host_resource: Host resource
    :type host_resource: resources.VDS
    :param sasl: Set sasl on/off (True/False)
    :type sasl: bool
    :return: True/False
    :rtype: bool
    """
    if not sasl:
        if not helpers.set_passwordless_ssh(
            src_host=engine_resource, dst_host=host_resource
        ):
            return False

        if not set_libvirtd_sasl(host_obj=host_resource, sasl=sasl):
            return False

    else:
        if not set_libvirtd_sasl(host_obj=host_resource, sasl=sasl):
            return False
    return True


def set_libvirtd_sasl(host_obj, sasl=True):
    """
    Set auth_unix_rw="none" in libvirtd.conf to enable passwordless
    connection to libvirt command line (virsh)

    :param host_obj: resources.VDS object
    :type host_obj: VDS
    :param sasl: True to enable sasl, False to disable
    :type sasl: bool
    :return: True/False
    :rtype: bool
    """
    logger.info("%s sasl in libvirt" % "Enable" if not sasl else "Disable")
    sasl_off = 'auth_unix_rw="{0}"'.format(conf.SASL_OFF)
    sasl_on = 'auth_unix_rw="{0}"'.format(conf.SASL_ON)
    sed_arg = "'s/{0}/{1}/g'".format(
        sasl_on if not sasl else sasl_off, sasl_off if not sasl else sasl_on
    )

    # following sed procedure is needed by RHEV-H and its read only file system
    # TODO: add persist after config.VDS_HOST.os is available see
    # https://projects.engineering.redhat.com/browse/RHEVM-2049
    sed_cmd = ["sed", sed_arg, conf.LIBVIRTD_CONF]
    logger_str = "Enable" if sasl else "Disable"
    logger.info("%s sasl in %s", logger_str, conf.LIBVIRTD_CONF)
    rc, sed_out, _ = host_obj.run_command(command=sed_cmd)
    if rc:
        return False

    cat_cmd = ["echo", "%s" % sed_out, ">", conf.LIBVIRTD_CONF]
    rc, _, _ = host_obj.run_command(command=cat_cmd)
    if rc:
        return False

    try:
        hl_hosts.restart_services_under_maintenance_state(
            [conf.LIBVIRTD_SERVICE, conf.VDSMD_SERVICE], host_obj, conf.TIMEOUT
        )
    except exceptions.HostException as e:
        logger.error(e)
        return False
    return True


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
    logger.info(
        "Creating %s dummy interfaces on %s", num_dummy, host_name
    )
    if not hl_networks.create_dummy_interfaces(
        host=host_resource, num_dummy=num_dummy
    ):
        raise conf.NET_EXCEPTION(
            "Failed to create dummy interfaces on %s" % host_name
        )
    last_event = events.get_max_event_id(query="")
    logger.info("Refresh capabilities for %s", host_name)
    if not ll_hosts.refresh_host_capabilities(
        host=host_name, start_event_id=last_event
    ):
        raise conf.NET_EXCEPTION()

    logger.info("Check if %s exist on host via engine", conf.DUMMY_0)
    sample = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1,
        func=check_dummy_on_host_interfaces, dummy_name=conf.DUMMY_0,
        host_name=host_name
    )
    if not sample.waitForFuncStatus(result=True):
        raise conf.NET_EXCEPTION(
            "Dummy interface does not exist on engine"
        )


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
    host_nics = ll_hosts.get_host_nics_list(host_name)
    for nic in host_nics:
        if dummy_name == nic.name:
            return True
    return False


def delete_dummies(host_resource):
    """
    Delete all dummies interfaces from host

    :param host_resource: Host resource object
    :type host_resource: resources.VDS
    """
    host_name = ll_hosts.get_host_name_from_engine(host_resource)
    logger.info("Delete all dummy interfaces")
    if not hl_networks.delete_dummy_interfaces(host=host_resource):
        logger.error("Failed to delete dummy interfaces")

    last_event = events.get_max_event_id(query="")
    logger.info("Refresh capabilities for %s", host_name)
    ll_hosts.refresh_host_capabilities(
        host=host_name, start_event_id=last_event
    )

    logger.info(
        "Check that %s does not exist on host via engine", conf.DUMMY_0
    )
    sample = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1,
        func=check_dummy_on_host_interfaces, dummy_name=conf.DUMMY_0,
        host_name=host_name
    )
    if not sample.waitForFuncStatus(result=False):
        logger.error("Dummy interface exists on engine")


def is_network_in_vds_caps(host_resource, network):
    """
    Check if network exists in vdsCaps output

    :param host_resource: Host resource object
    :type host_resource: resources.VDS
    :param network: Network name
    :type network: str
    :return: True/False
    :rtype: bool
    """
    logger.info("Get vdsCaps output")
    out = host_resource.vds_client("getVdsCapabilities")
    logger.info("Check if %s in vdsCaps output", network)
    if network not in out["info"]["networks"].keys():
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
    tcpdump_job = jobs.Job(test_utils.run_tcp_dump, (), tcpdump_kwargs)
    func_job = jobs.Job(func, (), func_kwargs)
    job_set = jobs.JobsSet()
    job_set.addJobs([tcpdump_job, func_job])
    job_set.start()
    job_set.join(int(tcpdump_kwargs.get("timeout", conf.DUMP_TIMEOUT)) + 5)
    return tcpdump_job.result and func_job.result


def remove_networks_from_setup(hosts=None, dc=conf.DC_NAME[0]):
    """
    Remove all networks from datacenter and hosts

    :param hosts: Host name
    :type hosts: list
    :param dc: DC name
    :type dc: str
    """
    hosts = hosts if hosts else [conf.HOSTS[0]]
    logger.info("Remove all networks from setup")
    if not hl_networks.remove_net_from_setup(
        host=hosts, all_net=True, mgmt_network=conf.MGMT_BRIDGE,
        data_center=dc
    ):
        logger.error("Cannot remove all networks from setup")


def remove_ifcfg_files(vms, exclude_nics=list()):
    """
    Remove all ifcfg files beside exclude_nics from vms

    Args:
        vms (list): List of VMs
        exclude_nics (list): NICs to exclude from remove

    Returns:
        bool: True if operation succeed, False otherwise
    """
    exclude_nics = exclude_nics if exclude_nics else EXCLUDE_NICS
    for vm in vms:
        vm_resource = global_helper.get_vm_resource(vm=vm)
        rc, out, _ = vm_resource.run_command(["ls", "%s/ifcfg-*" % IFCFG_PATH])
        if rc:
            return False

        ifcfg_files = filter(
            lambda x: x.rsplit("/")[-1] not in exclude_nics, out.splitlines()
        )
        for ifcfg in ifcfg_files:
            logger.info("Remove %s from %s", ifcfg, vm)
            if not vm_resource.fs.remove(path=ifcfg):
                logger.error("Fail to remove %s for %s", ifcfg, vm)
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


def remove_networks_from_host(hosts=None):
    """
    Remove all networks from hosts

    :param hosts: Host name
    :type hosts: list
    """
    hosts = [conf.HOSTS[0]] if not hosts else hosts
    logger.info("Removing all networks from %s", hosts)
    for host_name in hosts:
        if not hl_host_network.clean_host_interfaces(host_name=host_name):
            logger.error(
                "Failed to remove all networks from %s", host_name
            )


def send_icmp_sampler(
    host_resource, dst, count="5", size="1500", extra_args=None,
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
    if not ll_events.find_event(
        last_event=last_event, event_code=APPLY_NETWORK_CHANGES_EVENT_CODE,
        content=content, matches=matches
    ):
        raise conf.NET_EXCEPTION()


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
    last_event = ll_events.get_last_event(APPLY_NETWORK_CHANGES_EVENT_CODE)
    if not func(**func_kwargs):
        raise conf.NET_EXCEPTION(
            "Failed to call %s with %s" % (func.__name__, func_kwargs)
        )
    wait_for_sn(content=content, last_event=last_event, matches=matches)


def check_queues_from_qemu(vm, host_obj, num_queues):
    """
    Get numbers of queues from qemu process by VM name

    :param vm: VM name
    :type vm: str
    :param host_obj: resource.VDS host object
    :type host_obj: resources.VDS
    :param num_queues: Number of queues to check
    :type num_queues: int
    :return: True/False
    :rtype: bool
    """
    cmd = ["pgrep", "-a", "qemu-kvm"]
    rc, out, _ = host_obj.run_command(cmd)
    if rc:
        return False

    logger.info("Check if VM %s have number of queues == %s", vm, num_queues)
    running_vms = re.findall(r'\d+ .*qemu-kvm.*', out)
    for run_vm in running_vms:
        if re.findall(r'-name %s' % vm, run_vm):
            qemu_queues = re.findall(r'fds=[\d\d:]+', out)
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


def set_virsh_sasl_password(vds_resource):
    """
    Set Virsh sasl password

    Args:
        vds_resource (VDS): VDS resource

    Returns:
        bool: True if action succeed False otherwise
    """
    cmd = "echo %s | saslpasswd2 -p -a libvirt %s" % (VIRSH_PASS, VIRSH_USER)
    return not bool(vds_resource.run_command(shlex.split(cmd))[0])


def virsh_delete_network(vds_resource, network):
    """
    Delete network using Virsh

    Args:
        vds_resource (VDS): VDS resource
        network (str): Network name

    Returns:
        bool: True if action succeed False otherwise
    """
    file_name = "/tmp/virsh_delete_network_%s.py" % network
    with vds_resource.executor().session() as resource_session:
        with resource_session.open_file(file_name, 'w') as resource_file:
            resource_file.write("import pexpect\n")
            resource_file.write("output = ''\n")
            resource_file.write(
                "cmd_destroy = 'virsh net-destroy vdsm-%s'\n" % network
            )
            resource_file.write(
                "cmd_undefine = 'virsh net-undefine vdsm-%s'\n" % network
            )
            resource_file.write("for cmd in [cmd_undefine, cmd_destroy]:\n")
            resource_file.write("    sleep(5)\n")
            resource_file.write("    pe = pexpect.spawn(cmd)\n")
            resource_file.write("    %s('.*name:')\n" % PE_EXPECT)
            resource_file.write("    %s('%s')\n" % (PE_SENDLINE, VIRSH_USER))
            resource_file.write("    %s('.*password:')\n" % PE_EXPECT)
            resource_file.write("    %s('%s')\n" % (PE_SENDLINE, VIRSH_PASS))
            resource_file.write("    output += pe.read()\n")
            resource_file.write("print output\n")
    rc = vds_resource.run_command(["python", file_name])[0]
    vds_resource.fs.remove(file_name)
    return not bool(rc)


def virsh_add_network(vds_resource, network):
    """
    Add network using Virsh

    Args:
        vds_resource (VDS): VDS resource
        network (str): Network name

    Returns:
        bool: True if action succeed False otherwise
    """
    xml_file_name = virsh_create_xml_network_file(
        vds_resource=vds_resource, network=network
    )

    file_name = "/tmp/virsh_add_network_%s.py" % network
    with vds_resource.executor().session() as resource_session:
        with resource_session.open_file(file_name, 'w') as resource_file:
            resource_file.write("import pexpect\n")
            resource_file.write("from time import sleep\n")
            resource_file.write(
                "cmd = 'virsh net-create %s'\n" % xml_file_name
            )
            resource_file.write("pe = pexpect.spawn(cmd)\n")
            resource_file.write("%s('.*name:')\n" % PE_EXPECT)
            resource_file.write("%s('%s')\n" % (PE_SENDLINE, VIRSH_USER))
            resource_file.write("%s('.*password:')\n" % PE_EXPECT)
            resource_file.write("%s('%s')\n" % (PE_SENDLINE, VIRSH_PASS))
            resource_file.write("print pe.read()\n")
    rc = vds_resource.run_command(["python", file_name])[0]
    vds_resource.fs.remove(file_name)
    vds_resource.fs.remove(xml_file_name)
    return not bool(rc)


def virsh_create_xml_network_file(vds_resource, network):
    """
    Create network XML file for virsh

    Args:
        vds_resource (VDS): VDS resource
        network (str): Network name

    Returns:
        str: File path of created file
    """
    xml_file_name = "/tmp/virsh_create_xml_network_%s.xml" % network
    vdsm_bridge_name = "vdsm-{0}".format(network)
    vdsm_bridge_line = "<name>{0}</name>".format(vdsm_bridge_name)
    bridge_name_line = "<bridge name='{0}'/>".format(network)
    uuid_line = "<uuid>{0}</uuid>".format(str(uuid.uuid4()))
    xml_str = ("<network>{0}{1}<forward mode='bridge'/>{2}</network>".format(
        vdsm_bridge_line, uuid_line, bridge_name_line))

    with vds_resource.executor().session() as resource_session:
        with resource_session.open_file(xml_file_name, 'w') as resource_file:
            resource_file.write(xml_str)
    return xml_file_name


def virsh_is_network_exists(vds_resource, network):
    """
    Get network name from virsh

    Args:
        vds_resource (VDS): VDS resource
        network (str): Network name

    Returns:
        str: Network name
    """
    cmd = "virsh -r net-list"
    rc, out, _ = vds_resource.run_command(shlex.split(cmd))
    if rc:
        return False
    return network in out


if __name__ == "__main__":
    pass
