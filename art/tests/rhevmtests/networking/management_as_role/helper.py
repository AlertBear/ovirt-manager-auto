#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by MGMT network role feature
"""

import logging
import config as conf
import art.core_api.apis_utils as utils
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("MGMT_Net_Role_Helper")


def install_host_new_mgmt(
    host_resource=None, network=conf.MGMT_BRIDGE, dc=conf.EXT_DC_0,
    cl=conf.EXTRA_CLUSTER_0, dest_cl=conf.EXTRA_CLUSTER_0, new_setup=True,
    remove_setup=False, maintenance=True
):
    """
    Install host with MGMT network different from the previous one

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :param network: Network name for the MGMT
    :type network: str
    :param dc: DC for newly created setup
    :type dc: str
    :param cl: Cluster for newly created setup
    :type cl: str
    :param dest_cl: Cluster where host should be installed
    :type dest_cl: str
    :param new_setup: Flag indicating if there is a need to install a new setup
    :param remove_setup: Flag indicating if there is a need to remove setup
    :type remove_setup: bool
    :type new_setup:bool
    :param maintenance: Set host to maintenance before move
    :type maintenance: bool
    :raises: Network exception
    """
    if host_resource is None:
        host_resource = conf.VDS_1_HOST

    host_name = ll_hosts.get_host_name_from_engine(host_resource.ip)
    prepare_host_for_installation(
        host_resource=host_resource, network=network,
        dc=dc, cl=cl, new_setup=new_setup, host_name=host_name,
        maintenance=maintenance
    )

    add_host_new_mgmt(
        host_resource=host_resource, network=network, dc=dc, cl=cl,
        new_setup=new_setup, dest_cl=dest_cl, host_name=host_name,
        remove_setup=remove_setup
    )


def prepare_host_for_installation(
    host_resource, network, dc, cl, new_setup, host_name, maintenance=True
):
    """
    Prepares host for installation with new MGMT network

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :param network: Network name for the MGMT
    :type network: str
    :param dc: DC for newly created setup
    :type dc: str
    :param cl: Cluster for newly created setup
    :type cl: str
    :param new_setup: Flag indicating if there is a need to install a new setup
    :type new_setup:bool
    :param host_name: Name of the Host
    :type host_name: str
    :param maintenance: Set host to maintenance before move
    :type maintenance: bool
    :raises: Network exception
    """
    if maintenance:
        if not ll_hosts.deactivateHost(positive=True, host=host_name):
            raise conf.NET_EXCEPTION()

    if new_setup:
        create_setup(dc=dc, cl=cl)
        move_host_new_cl(host=host_name, cl=cl)

    update_host_mgmt_bridge(
        host_resource=host_resource, network=network, dc=dc,
        nic=host_resource.nics[0]
    )

    virsh_remove_network(vds_resource=conf.VDS_1_HOST, network=network)

    if not ll_hosts.removeHost(positive=True, host=host_name):
        raise conf.NET_EXCEPTION()

    remove_persistance_nets(host_resource=host_resource)


def add_host_new_mgmt(
    host_resource, network, dc, cl, new_setup, dest_cl, host_name, remove_setup
):
    """
    Add Host with new MGMT bridge

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :param network: Network name for the MGMT
    :type network: str
    :param dc: DC for newly created setup
    :type dc: str
    :param cl: Cluster for newly created setup
    :type cl: str
    :param new_setup: Flag indicating if there is a need to install a new setup
    :type new_setup:bool
    :param dest_cl: Cluster where host should be installed
    :type dest_cl: str
    :param host_name: Name of the Host
    :type host_name: str
    :param remove_setup: Remove the setup
    :type remove_setup: bool
    :raises: Network exception
    """
    if new_setup:
        if not hl_networks.createAndAttachNetworkSN(
            data_center=dc,  cluster=cl, network_dict=conf.NET_DICT
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_cluster_network(
            positive=True, cluster=cl, network=conf.NET_1,
            usages=conf.MGMT
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.removeNetwork(
            positive=True, network=network, data_center=dc
        ):
            raise conf.NET_EXCEPTION()

    if remove_setup:
        hl_networks.remove_basic_setup(datacenter=dc, cluster=cl)

    add_host(host_resource=host_resource, host=host_name, cl=dest_cl)


def update_host_mgmt_bridge(host_resource, network, dc, nic):
    """
    Update Host MGMT bridge to be non-VM

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :param network: Network name for the MGMT
    :type network: str
    :param dc: DC where the network is located
    :type dc: str
    :param nic: NIC with the MGMT network
    :type nic: str
    :raises: Network exception
    """
    host_name = ll_hosts.get_host_name_from_engine(host_resource.ip)
    if not ll_networks.updateNetwork(
        True, network=network, data_center=dc, usages=""
    ):
        raise conf.NET_EXCEPTION()

    sample1 = utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT,
        sleep=1,
        func=hl_networks.check_host_nic_params,
        host=host_name,
        nic=nic,
        **{"bridge": False}
    )
    if not sample1.waitForFuncStatus(result=True):
        raise conf.NET_EXCEPTION()

    if ll_networks.is_host_network_is_vm(
        vds_resource=host_resource, net_name=network
    ):
        raise conf.NET_EXCEPTION()


def add_host(host_resource, host, cl):
    """
    Add host

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :param host: Host name
    :type host: str
    :param cl: Cluster name
    :type cl: str
    :raises: Network exception
    """
    if not ll_hosts.addHost(
        positive=True, name=host, root_password=conf.HOSTS_PW, cluster=cl,
        address=host_resource.ip, comment=host_resource.fqdn
    ):
        raise conf.NET_EXCEPTION(
            "Couldn't add %s to %s" % (host_resource.ip, cl)
        )


def create_setup(dc, cl=None):
    """
    Creates a new DC and Cluster in the setup

    :param dc: DC name
    :type dc: str
    :param cl: Cluster name
    :type cl: str or None
    :raises: Network exception
    """
    if not hl_networks.create_basic_setup(
        datacenter=dc, cluster=cl, version=conf.COMP_VERSION,
        storage_type=conf.STORAGE_TYPE, cpu=conf.CPU_NAME
    ):
        raise conf.NET_EXCEPTION()


def move_host_new_cl(host, cl, positive=True, activate_host=False):
    """
    Move Host to new Cluster

    :param host: Host name to move
    :type host: str
    :param cl: Destination Cluster
    :param positive: Flag if an action of moving host should succeed
    :type positive: bool
    :param activate_host: Flag if host should be activated
    :type activate_host: bool
    :type cl: str
    :raises: Network exception
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Move", obj_type="host", obj_name=host, positive=positive,
        extra_txt="to cluster %s" % cl
    )
    logger.info(log_info)
    if not ll_hosts.updateHost(positive=positive, host=host, cluster=cl):
        raise conf.NET_EXCEPTION(log_error)

    if activate_host:
        if not ll_hosts.activateHost(True, host=host):
            raise conf.NET_EXCEPTION()


def remove_persistance_nets(host_resource):
    """
    Remove networks from persistence files

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :raises: Network exception
    """
    for location in ("lib/vdsm/persistence", "run/vdsm"):
        if host_resource.executor().run_cmd(
            ["rm", "-rf", "/".join(["/var", location, "netconf/nets/*"])]
        )[0]:
            raise conf.NET_EXCEPTION(
                "Couldn't remove network from persistent file"
            )


def add_cluster(
    cl=conf.EXTRA_CLUSTER_0, dc=conf.DC_0, positive=True, **kwargs
):
    """
    Add Cluster to DC

    :param cl: Cluster name
    :type cl: str
    :param dc: DC name
    :type dc: str
    :param positive: Flag if test is positive or negative
    :type positive: bool
    :param kwargs: dict of additional params (for example MGMT network)
    :type kwargs: dict
    :raises: Network exception
    """
    if not ll_clusters.addCluster(
        positive=positive, name=cl, cpu=conf.CPU_NAME, data_center=dc,
        version=conf.COMP_VERSION, **kwargs
    ):
        raise conf.NET_EXCEPTION()


def remove_net(net=conf.NET_1, dc=conf.EXT_DC_0, positive=True, teardown=True):
    """
    Remove network from DC

    :param net: Network name
    :type net: str
    :param dc: DC name
    :type dc: str
    :param positive: Flag for removal a network
    :type positive: bool
    :param teardown: Called from teardown
    :type teardown: bool
    :raises: Network exception
    """
    if not ll_networks.removeNetwork(
        positive=positive, network=net, data_center=dc
    ):
        if teardown:
            pass
        else:
            raise conf.NET_EXCEPTION()


def virsh_remove_network(vds_resource, network):
    """
    Undefine and destroy network on virsh

    Args:
        vds_resource (VDS): VDS resource
        network (str): Network name
    """
    temp_file = create_virsh_python_file(
        vds_resource=vds_resource, network=network
    )
    out = vds_resource.run_command(["python", temp_file])[1]
    logger.info(out)
    vds_resource.fs.remove(temp_file)


def create_virsh_python_file(vds_resource, network):
    """
    Create python script for undefine and destroy network on virsh

    Args:
        vds_resource (VDS): VDS resource
        network (str): Network name

    Returns:
        str: File name with the content
    """
    username = conf.VIRSH_USER
    password = conf.VIRSH_PASS
    pe_expect = "pe.expect"
    pe_sendline = "pe.sendline"
    file_name = "/tmp/virsh_delete_%s.py" % network
    with vds_resource.executor().session() as resource_session:
        with resource_session.open_file(file_name, 'w') as resource_file:
            resource_file.write("import pexpect\n")
            resource_file.write("from time import sleep\n")
            resource_file.write("output = ''\n")
            resource_file.write(
                "sasl_cmd = 'saslpasswd2 -a libvirt %s'\n" % username
            )
            resource_file.write("pe = pexpect.spawn(sasl_cmd)\n")
            resource_file.write("%s('.*Password:')\n" % pe_expect)
            resource_file.write("%s('%s')\n" % (pe_sendline, password))
            resource_file.write("%s('Again.*:')\n" % pe_expect)
            resource_file.write("%s('%s')\n" % (pe_sendline, password))
            resource_file.write(
                "cmd_destroy = 'virsh net-destroy vdsm-%s'\n" % network
            )
            resource_file.write(
                "cmd_undefine = 'virsh net-undefine vdsm-%s'\n" % network
            )
            resource_file.write("for cmd in [cmd_undefine, cmd_destroy]:\n")
            resource_file.write("    sleep(5)\n")
            resource_file.write("    pe = pexpect.spawn(cmd)\n")
            resource_file.write("    %s('.*name:')\n" % pe_expect)
            resource_file.write("    %s('%s')\n" % (pe_sendline, username))
            resource_file.write("    %s('.*password:')\n" % pe_expect)
            resource_file.write("    %s('%s')\n" % (pe_sendline, password))
            resource_file.write("    output += pe.read()\n")
            resource_file.write("print output\n")
    return file_name
