#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for networking jobs
"""

import logging
import config as conf
from random import randint
from utilities import jobs
from rhevmtests import helpers
from art.core_api import apis_utils
from art.test_handler import settings
from art.test_handler import exceptions
from art.rhevm_api.utils import test_utils
import rhevmtests.helpers as global_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Global_Network_Helper")

ENUMS = settings.opts['elements_conf']['RHEVM Enums']
IFCFG_PATH = "/etc/sysconfig/network-scripts"


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


def run_vm_once_specific_host(vm, host, wait_for_ip=False):
    """
    Run VM once on specific host

    :param vm: VM name
    :type vm: str
    :param host: Host name
    :type host: str
    :param wait_for_ip: Wait for VM to get IP
    :type wait_for_ip: bool
    :return: True if action succeeded, False otherwise
    :rtype: bool
    """
    logger.info("Check if %s is UP", host)
    host_status = ll_hosts.getHostState(host)
    if not host_status == ENUMS["host_state_up"]:
        logger.error("%s status is %s, cannot run VM", host, host_status)
        return False

    logging.info("Run VM once on host %s", host)
    if not ll_vms.runVmOnce(positive=True, vm=vm, host=host):
        logging.error("Couldn't run VM on host %s", host)
        return False

    if wait_for_ip:
        logging.info("Wait to get IP address")
        if not ll_vms.waitForIP(vm)[0]:
            logging.error("VM didn't get IP address")
            return False

    logging.info("Check that VM was started on host %s", host)
    vm_host = ll_vms.getVmHost(vm)[1]["vmHoster"]
    if not host == vm_host:
        logging.error(
            "VM should start on %s instead of %s", host, vm_host)
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
    logging.info("Start VM: %s", vm)
    if not ll_vms.startVm(positive=True, vm=vm):
        logging.error("Failed to start %s.", vm)
        return False

    logging.info("Waiting for IP from %s", vm)
    rc, out = ll_vms.waitForIP(vm=vm, timeout=180, sleep=10)
    if not rc:
        logging.error("Failed to get %s IP", vm)
        return False

    ip = out["ip"]
    logging.info("Running setPersistentNetwork on %s", vm)
    if not test_utils.setPersistentNetwork(host=ip, password=root_password):
        logging.error("Failed to seal %s", vm)
        return False

    logging.info("Stopping %s", vm)
    if not ll_vms.stopVm(positive=True, vm=vm):
        logging.error("Failed to stop %s", vm)
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
    if not hl_networks.createAndAttachNetworkSN(
        data_center=dc, cluster=cluster, network_dict=networks_dict
    ):
        raise conf.NET_EXCEPTION(
            "Couldn't create %s on %s" % (networks_dict, log)
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
    :raise: conf.NET_EXCEPTION
    """
    network_sync_dict = {
        "sync": {
            "networks": networks
        }
    }
    logger.info("syncing %s", networks)
    if not hl_host_network.setup_networks(host_name=host, **network_sync_dict):
        raise conf.NET_EXCEPTION("Failed to sync %s" % networks)

    if not networks_sync_status(host=host, networks=networks):
        raise conf.NET_EXCEPTION(
            "At least one of the networks from %s is out of sync, should be "
            "synced" % networks
        )


def remove_qos_from_dc(qos_name, datacenter=conf.DC_NAME[0], teardown=True):
    """
    Removes host network QoS from DC

    :param qos_name: Name of the host network QoS
    :type qos_name: str
    :param datacenter: Datacenter to create QoS on
    :type datacenter: str
    :param teardown: If running on teardown
    :type teardown: bool
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
    :raises: Network exception
    """
    logger.info(
        "Create new network host QoS profile with parameters %s", qos_dict
    )
    result = ll_dc.add_qos_to_datacenter(
        datacenter=datacenter, qos_name=qos_name,
        qos_type=conf.HOST_NET_QOS_TYPE, **qos_dict
    )
    if not result and positive:
        raise conf.NET_EXCEPTION(
            "Couldn't create Host Network QOS under DC when should"
        )
    if result and not positive:
        raise conf.NET_EXCEPTION(
            "Could create Host Network QOS under DC when shouldn't"
        )


def update_host_net_qos(qos_name, datacenter=conf.DC_NAME[0], **qos_dict):
    """
    Update host network qos parameters with given dict parameters

    :param qos_name: Name of the host network QoS
    :type qos_name: str
    :param datacenter: Datacenter to create QoS on
    :type datacenter: str
    :param qos_dict: dict of host network qos values to update
    :type qos_dict: dict
    :raises: Network exception
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
    Set passwordless ssh from emgine to host
    Set sasl on/off for libvirtd on host

    :param engine_resource: Engine resource
    :type engine_resource: resources.Engine
    :param host_resource: Host resource
    :type host_resource: resources.VDS
    :param sasl: Set sasl on/off (True/False)
    :type sasl: bool
    :raise: conf.NET_EXCEPTION
    """
    if not sasl:
        logger.info(
            "Setting passwordless ssh from engine (%s) to host (%s)",
            engine_resource.ip, host_resource.ip
        )
        if not helpers.set_passwordless_ssh(
            engine_resource, host_resource
        ):
            raise conf.NET_EXCEPTION(
                "Failed to set passwordless SSH to %s" % host_resource.ip
            )

        logger.info("Disabling sasl in libvirt")
        if not set_libvirtd_sasl(
            host_obj=host_resource, sasl=sasl
        ):
            raise conf.NET_EXCEPTION(
                "Failed to disable sasl on %s" % host_resource.ip
            )
    else:
        logger.info("Enabling sasl in libvirt")
        if not set_libvirtd_sasl(host_obj=host_resource, sasl=sasl):
            logger.error("Failed to enable sasl on %s", host_resource.ip)


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
    sasl_off = 'auth_unix_rw="{0}"'.format(conf.SASL_OFF)
    sasl_on = 'auth_unix_rw="{0}"'.format(conf.SASL_ON)
    sed_arg = "'s/{0}/{1}/g'".format(
        sasl_on if not sasl else sasl_off, sasl_off if not sasl else sasl_on
    )

    # following sed procedure is needed by RHEV-H and its read only file system
    # TODO: add persist after config.VDS_HOST.os is available see
    # https://projects.engineering.redhat.com/browse/RHEVM-2049
    sed_cmd = ["sed", sed_arg, conf.LIBVIRTD_CONF]
    host_exec = host_obj.executor()
    logger_str = "Enable" if sasl else "Disable"
    logger.info("%s sasl in %s", logger_str, conf.LIBVIRTD_CONF)
    rc, sed_out, err = host_exec.run_cmd(sed_cmd)
    if rc:
        logger.error(
            "Failed to run sed %s %s err: %s. out: %s",
            sed_arg, conf.LIBVIRTD_CONF, logger_str, err, sed_out
        )
        return False

    cat_cmd = ["echo", "%s" % sed_out, ">", conf.LIBVIRTD_CONF]
    rc, cat_out, err = host_exec.run_cmd(cat_cmd)
    if rc:
        logger.error(
            "Failed to %s sasl in libvirt. err: %s. out: %s",
            logger_str, err, cat_out
        )
        return False

    logger.info(
        "Restarting %s and %s services",
        conf.LIBVIRTD_SERVICE, conf.VDSMD_SERVICE
    )
    try:
        hl_hosts.restart_services_under_maintenance_state(
            [conf.LIBVIRTD_SERVICE, conf.VDSMD_SERVICE], host_obj, conf.TIMEOUT
        )
    except exceptions.HostException:
        logger.error(
            "Failed to restart %s/%s services", conf.VDSMD_SERVICE,
            conf.LIBVIRTD_SERVICE
        )
        return False
    return True


def prepare_dummies(host_resource, num_dummy=2):
    """
    Prepare dummies interfaces on host

    :param host_resource: Host resource object
    :type host_resource: resources.VDS
    :param num_dummy: Number of dummies to create
    :type num_dummy: int
    :raise: conf.NET_EXCEPTION
    """
    host_name = ll_hosts.get_host_name_from_engine(host_resource.ip)
    logger.info(
        "Creating %s dummy interfaces on %s", num_dummy, host_name
    )
    if not hl_networks.create_dummy_interfaces(
        host=host_resource, num_dummy=num_dummy
    ):
        raise conf.NET_EXCEPTION(
            "Failed to create dummy interfaces on %s" % host_name
        )
    logger.info("Refresh host capabilities")
    host_obj = ll_hosts.HOST_API.find(host_name)
    refresh_href = "{0};force".format(host_obj.get_href())
    ll_hosts.HOST_API.get(href=refresh_href)

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
    host_nics = ll_hosts.getHostNicsList(host_name)
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
    host_name = ll_hosts.get_host_name_from_engine(host_resource.ip)
    logger.info("Delete all dummy interfaces")
    if not hl_networks.delete_dummy_interfaces(host=host_resource):
        logger.error("Failed to delete dummy interfaces")

    logger.info("Refresh host capabilities")
    host_obj = ll_hosts.HOST_API.find(host_name)
    refresh_href = "{0};force".format(host_obj.get_href())
    ll_hosts.HOST_API.get(href=refresh_href)

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
    :raise: conf.NET_EXCEPTION
    """
    logger.info("Get vdsCaps output")
    out = host_resource.vds_client("getVdsCapabilities")
    logger.info("Check if %s in vdsCaps output", network)
    if network not in out["info"]["networks"].keys():
        raise conf.NET_EXCEPTION("%s not in vdsCaps output" % network)


def check_traffic_during_func_operation(
    func_name, func_kwargs, tcpdump_kwargs
):
    """
    Search for packets in tcpdump output during given func (func_name) action

    :param func_name: Name of the function to run with tcpdump command
    :type func_name: str
    :param func_kwargs: Parameters of the function
    :type func_kwargs: dict
    :param tcpdump_kwargs: Parameters of the tcpdump function
    :type tcpdump_kwargs: dict
    :return True/False
    :rtype: bool

    :Example:

    func_name="sendICMP"

    icmp_kwargs = {
        "host": src_vm,
        "user": config.VMS_LINUX_USER,
        "password": config.VMS_LINUX_PW,
        "ip": dst_ip,
        "func_path": "art.rhevm_api.utils.test_utils"
    }

    tcpdump_kwargs = {
        "host_obj": listen_vm_obj,
        "nic": nic,
        "src": src_ip,
        "dst": dst_ip,
        "numPackets": 5,
        "timeout": str(config.TIMEOUT)
    }

    net_help.check_traffic_during_func_operation(
        func_name="sendICMP", func_kwargs=icmp_kwargs,
        tcpdump_kwargs=tcpdump_kwargs
    )
    """

    tcpdump_job = jobs.Job(test_utils.run_tcp_dump, (), tcpdump_kwargs)
    func_path = func_kwargs.pop("func_path")
    imp_module = __import__(
        func_path, globals(), locals(), [func_name], -1
    )
    func = getattr(imp_module, func_name)
    func_job = jobs.Job(func, (), func_kwargs)
    job_set = jobs.JobsSet()
    job_set.addJobs([tcpdump_job, func_job])
    job_set.start()
    job_set.join(int(tcpdump_kwargs.get("timeout", conf.DUMP_TIMEOUT)) + 5)
    return tcpdump_job.result and func_job.result


def get_vm_resource(vm):
    """
    Get VM executor

    :param vm: VM name
    :type vm: str
    :return: VM executor
    :rtype: resource_vds
    """
    logger.info("Get IP for: %s", vm)
    rc, ip = ll_vms.waitForIP(vm=vm, timeout=conf.TIMEOUT)
    if not rc:
        raise conf.NET_EXCEPTION("Failed to get IP for: %s" % vm)
    ip = ip["ip"]
    return global_helper.get_host_resource_with_root_user(
        ip, conf.VMS_LINUX_PW
    )


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


def remove_ifcfg_files(vms):
    """
    Remove all ifcfg files beside ifcfg-eth0 from vms

    :param vms: List of VMs
    :type vms: list
    """
    exclude_nics = ["ifcfg-eth0", "ifcfg-lo"]
    for vm in vms:
        try:
            vm_resource = get_vm_resource(vm=vm)
        except conf.NET_EXCEPTION:
            logger.error("Failed to get VM resource for %s", vm)
            continue
        interfaces = get_all_ifcfg_files(hl_vms.get_vm_ip(vm, start_vm=False))
        interfaces = filter(
            lambda x: x.rsplit("/")[-1] not in exclude_nics, interfaces
        )
        for interface in interfaces:
            logger.info("Remove %s from %s", interface, vm)
            if not vm_resource.fs.remove(path=interface):
                logger.error("Fail to remove %s for %s", interface, vm)


def get_vm_interfaces_list(vm_resource, exclude_nic):
    """
    Get VM interface list beside ifcfg-eth0

    :param vm_resource: VM resource
    :type vm_resource: Resource.VDS
    :param exclude_nic: NIC name to keep
    :type exclude_nic: str
    :return: VM interfaces list
    :rtype: list
    """
    logger.info("Getting interfaces list from %s", vm_resource.ip)
    vm_nics = vm_resource.network.all_interfaces()
    return filter(lambda x: x != exclude_nic, vm_nics)


def get_all_ifcfg_files(host_ip):
    """
    Get all ifcfg files from Host resource

    :param host_ip: Host IP
    :type host_ip: str
    :return: List of all ifcfg files
    :rtype: list
    """
    resource = helpers.get_host_resource_with_root_user(host_ip, conf.HOSTS_PW)
    rc, out, err = resource.run_command(["ls", "%s/ifcfg-*" % IFCFG_PATH])
    if rc:
        return []
    return out.splitlines()


if __name__ == "__main__":
    pass
