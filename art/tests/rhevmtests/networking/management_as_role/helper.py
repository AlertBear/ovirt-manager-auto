#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by the test cases of Management As A Role
"""

import logging

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper

logger = logging.getLogger("MGMT_Net_Role_Helper")


def install_host_new_mgmt(
        dc, cl, dest_cl, net_setup, mgmt_net, host_resource=None,
        network=conf.MGMT_BRIDGE, new_setup=True, remove_setup=False,
        maintenance=True
):
    """
    Install host with MGMT network different from the previous one

    Args:
        dc (str): DC for newly created setup
        cl (str): Cluster for newly created setup
        dest_cl (str): Cluster where host should be installed
        net_setup (dict): Network setup to set on host
        mgmt_net (str): Management network name to set on host
        host_resource (VDS instance, optional): Host resource
        network (str, optional): Network name for the MGMT
        new_setup (bool, optional): Flag indicating if there is a need to
            install a new setup
        remove_setup (bool, optional): Flag indicating if there is a need to
            remove setup
        maintenance (bool, optional): Set host to maintenance before move

    Returns:
        bool: True if install host succeeded, otherwise False
    """
    if host_resource is None:
        host_resource = conf.VDS_1_HOST

    host_name = ll_hosts.get_host_name_from_engine(host_resource)

    if not host_name:
        return False

    if not prepare_host_for_installation(
        host_resource=host_resource, network=network,
        dc=dc, cl=cl, new_setup=new_setup, host_name=host_name,
        maintenance=maintenance
    ):
        return False

    return add_host_new_mgmt(
        host_rsc=host_resource, network=network, dc=dc, cl=cl,
        new_setup=new_setup, dest_cl=dest_cl, host_name=host_name,
        remove_setup=remove_setup, net_setup=net_setup, mgmt_net=mgmt_net
    )


def prepare_host_for_installation(
    host_resource, network, dc, cl, new_setup, host_name, maintenance=True
):
    """
    Prepares host for installation with new MGMT network

    Args:
        host_resource (VDS instance): Host resource
        network (str): Network name for the MGMT
        dc (str): DC for newly created setup
        cl (str): Cluster for newly created setup
        new_setup (bool): Flag indicating if there is a need to install a new
            setup
        host_name (str): Name of the Host
        maintenance (bool): Set host to maintenance before move

    Returns:
        bool: True if prepare host succeeded, otherwise False
    """
    if maintenance:
        assert ll_hosts.deactivate_host(positive=True, host=host_name)

    if new_setup:
        if not hl_networks.create_basic_setup(
            datacenter=dc, cluster=cl, version=conf.COMP_VERSION,
            cpu=conf.CPU_NAME
        ):
            return False
        if not move_host_new_cl(host=host_name, cl=cl):
            return False

    # Update Host MGMT bridge to be non-VM
    network_helper.call_function_and_wait_for_sn(
        func=ll_networks.update_network, content=network, positive=True,
        network=network, data_center=dc, usages=""
    )

    virsh_remove_network(vds_resource=conf.VDS_1_HOST, network=network)

    if not ll_hosts.removeHost(positive=True, host=host_name):
        return False

    return remove_persistence_nets(host_resource=host_resource)


def add_host_new_mgmt(
    host_rsc, network, dc, cl, new_setup, dest_cl, host_name, remove_setup,
    net_setup, mgmt_net
):
    """
    Add Host with new MGMT bridge

    Args:
        host_rsc (VDS instance): Host resource
        network (str): Network name for the MGMT
        dc (str): DC for newly created setup
        cl (str): Cluster for newly created setup
        new_setup (bool): Flag indicating if there is a need to install a new
            setup
        dest_cl (str): Cluster where host should be installed
        host_name (str): Name of the Host
        remove_setup (bool): Remove the setup
        net_setup (dict): Network setup to set on host
        mgmt_net (str): Management network name to set on host

    Returns:
        bool: True if add host succeeded, otherwise False
    """
    if new_setup:
        if not hl_networks.create_and_attach_networks(
            data_center=dc,  cluster=cl, network_dict=net_setup
        ):
            return False

        if not ll_networks.update_cluster_network(
            positive=True, cluster=cl, network=mgmt_net,
                usages=conf.MANAGEMENT_NET_USAGE
        ):
            return False

        if not ll_networks.remove_network(
            positive=True, network=network, data_center=dc
        ):
            return False

    if remove_setup:
        if not hl_networks.remove_basic_setup(datacenter=dc, cluster=cl):
            return False

    return ll_hosts.add_host(
        name=host_name, root_password=conf.HOSTS_PW,
        cluster=dest_cl, address=host_rsc.fqdn, comment=host_rsc.ip
    )


def move_host_new_cl(host, cl, positive=True, activate_host=False):
    """
    Move Host to new Cluster

    Args:
        host (str): Host name to move
        cl (str): Destination Cluster
        positive (bool): Flag if an action of moving host should succeed
        activate_host (bool): Flag if host should be activated

    Returns:
        bool: True if host move was successful, otherwise False
    """
    if not ll_hosts.updateHost(positive=positive, host=host, cluster=cl):
        return False

    if activate_host:
        if not ll_hosts.activate_host(True, host=host):
            return False

    return True


def remove_persistence_nets(host_resource):
    """
    Remove networks from persistence files

    Args:
        host_resource (VDS instance): Host resource

    Returns:
        bool: True if persistence networks were removed, otherwise False
    """
    for location in ("lib/vdsm/persistence", "run/vdsm"):
        if host_resource.executor().run_cmd(
            ["rm", "-rf", "/".join(["/var", location, "netconf/nets/*"])]
        )[0]:
            return False
    return True


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
