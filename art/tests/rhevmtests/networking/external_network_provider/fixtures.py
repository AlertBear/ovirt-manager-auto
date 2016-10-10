#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OpenStack network provider fixtures
"""

import re
import shlex

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as osnp_conf
from art.unittest_lib import testflow
import rhevmtests.helpers as global_helper
import rhevmtests.networking.helper as network_helper
from art.rhevm_api.tests_lib.low_level import external_providers
from rhevmtests.networking.fixtures import NetworkFixtures


class ExternalNetworkProviderFixtures(NetworkFixtures):
    """
    External Network Provider class
    """
    def __init__(self):
        super(ExternalNetworkProviderFixtures, self).__init__()
        self.neutron_ip = osnp_conf.PROVIDER_IP
        self.neutron_root_password = osnp_conf.ROOT_PASSWORD
        self.neutron_resource = global_helper.get_host_resource(
            ip=self.neutron_ip, password=self.neutron_root_password
        )
        self.neut = None
        self.neutron_password = None

    def get_neutron_password(self):
        """
        Get Neutron password from answer file
        """
        if not self.neutron_password:
            pattern = "CONFIG_NEUTRON_KS_PW="
            out = self.neutron_resource.fs.read_file(
                path=osnp_conf.ANSWER_FILE
            )
            assert out
            re_out = re.findall(r'{pat}.*'.format(pat=pattern), out)
            assert re_out
            self.neutron_password = re_out[0].strip(pattern)

    def set_neut_params(self):
        """
        Set neutron provider params
        """
        self.get_neutron_password()
        osnp_conf.NEUTRON_PARAMS["password"] = self.neutron_password
        osnp_conf.NEUTRON_PARAMS["network_mapping"] = (
            osnp_conf.NETWORK_MAPPING.format(
                interface=self.host_0_nics[-1], br_ext=osnp_conf.BR_EXT
            )
        )
        self.neut = external_providers.OpenStackNetworkProvider(
            **osnp_conf.NEUTRON_PARAMS
        )

    def get_all_provider_networks(self):
        """
        Get all networks from provider
        """
        if not osnp_conf.PROVIDER_NETWORKS:
            self.init()
            networks = [net.name for net in self.neut.get_all_networks()]
            assert networks
            osnp_conf.PROVIDER_NETWORKS = networks

    def init(self):
        """
        Get provider class with existing provider object
        """
        self.set_neut_params()
        self.neut.set_osp_obj()


@pytest.fixture(scope="module")
def add_neutron_provider(request):
    """
    Add neutron network provider
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    external_network_provider.set_neut_params()
    provider_name = osnp_conf.PROVIDER_NAME

    def fin():
        """
        Remove neutron provider
        """
        testflow.teardown("Remove Neutron provider %s", provider_name)
        assert external_network_provider.neut.remove(
            openstack_ep=provider_name
        )
    request.addfinalizer(fin)

    testflow.setup("Add Neutron provider %s", provider_name)
    assert external_network_provider.neut.add()


@pytest.fixture(scope="class")
def get_provider_networks(request):
    """
    Get all provider networks
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    testflow.setup("Get all Neutron provider networks")
    external_network_provider.get_all_provider_networks()


@pytest.fixture(scope="class")
def import_openstack_network(request, get_provider_networks):
    """
    Import network from OpenStack provider
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    external_network_provider.init()
    net = osnp_conf.PROVIDER_NETWORKS_NAME[0]
    cluster = external_network_provider.cluster_0

    def fin():
        """
        Remove imported network
        """
        testflow.teardown("Remove network %s", net)
        assert hl_networks.remove_networks(positive=True, networks=[net])
    request.addfinalizer(fin)

    testflow.setup(
        "Import networks from Neutron provider %s", osnp_conf.PROVIDER_NAME
    )
    assert external_network_provider.neut.import_network(
        network=net, datacenter=external_network_provider.dc_0
    )
    testflow.setup("Attach network %s to cluster %s", net, cluster)
    assert ll_networks.add_network_to_cluster(
        positive=True, network=net, required=False, cluster=cluster
    )


@pytest.fixture(scope="module")
def prepare_hosts_for_neutron(request):
    """
    Prepare hosts for Neutron
    Install vdsm-hook-openstacknet on hosts
    Install rhos-release 8 on hosts
    Delete "reject ICMP" iptable rule from hosts
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    vdsm_hook = osnp_conf.OSNP_VDSM_HOOK
    iptable_rule = osnp_conf.DELETE_IPTABLE_RULE
    rhos_cmd = osnp_conf.RHOS_CMD
    cmd = "yum reinstall %s -y" % osnp_conf.RHOS_LATEST
    testflow.setup(
        "Install %s and %s on hosts and delete REJECT ICMP iptable rule",
        vdsm_hook, rhos_cmd
    )
    for vds in external_network_provider.vds_list:
        assert vds.package_manager.install(
            package=vdsm_hook
        )
        vds.run_command(shlex.split(cmd))
        assert not vds.run_command(command=shlex.split(rhos_cmd))[0]
        vds.run_command(command=shlex.split(iptable_rule))


@pytest.fixture(scope="module")
def prepare_packstack_answer_file(request):
    """
    Prepare packstack answer file
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    testflow.setup("Prepare packstack answer file for deploy")
    hosts_cmd = list()
    ifaces_cmd = list()
    sed_cmd = "sed -i s/{old_value}/{new_value}/g %s" % osnp_conf.ANSWER_FILE
    hosts_ips = "{host_ip_0},{host_ip_1}".format(
        host_ip_0=external_network_provider.host_0_ip,
        host_ip_1=external_network_provider.host_1_ip
    )
    hosts_interrfaces = [
        i for i in external_network_provider.host_0_nics if "dummy" not in i
        ]
    before_last_interface, last_interface = hosts_interrfaces[-2:]
    # Set hosts IPs as compute hosts in neutron answer file
    for val in osnp_conf.ANSWER_FILE_HOSTS_PARAMS:
        if val == osnp_conf.NETWORK_HOSTS:
            # Only the first host is 'networker' host
            hosts_ips = external_network_provider.host_0_ip

        new_val = "{old_val}{new_val}".format(
            old_val=val.strip(".*"), new_val=hosts_ips
        )
        hosts_cmd.append(
            shlex.split(sed_cmd.format(old_value=val, new_value=new_val))
        )

    # Set interfaces for br-ext and ovs-tunnel
    for val, iface in zip(
        osnp_conf.ANSWER_FILE_HOSTS_IFACES,
        [before_last_interface, last_interface]
    ):
        # Ovs bridge interface need mapping to host interface
        if val == osnp_conf.OVS_BRIDGE_IFACES:
            iface = "{bridge}:{interface}".format(
                bridge=osnp_conf.BR_EXT, interface=iface
            )
        new_val = "{old_val}{new_val}".format(
            old_val=val.strip(".*"), new_val=iface
        )
        ifaces_cmd.append(
            shlex.split(sed_cmd.format(old_value=val, new_value=new_val))
        )

    for cmd in hosts_cmd + ifaces_cmd:
        assert not external_network_provider.neutron_resource.run_command(
            command=cmd
        )[0]


@pytest.fixture(scope="module")
def run_packstack(
    request, prepare_hosts_for_neutron, prepare_packstack_answer_file
):
    """
    Run packstack
    """
    external_network_provider = ExternalNetworkProviderFixtures()

    def fin3():
        """
        Stop openvswitch service
        """
        testflow.teardown("Stop openvswitch service")
        for vds in external_network_provider.vds_list:
            vds.service("openvswitch").stop()
    request.addfinalizer(fin3)

    def fin2():
        """
        Kill dnsmasq process
        """
        testflow.teardown("Kill dnsmasq process")
        for vds in external_network_provider.vds_list:
            vds.run_command(command=shlex.split("killall dnsmasq"))
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove Neutron RPMs
        """
        testflow.teardown("Remove all Neutron packages")
        for vds in external_network_provider.vds_list:
            neutron_packages = vds.run_command(
                command=shlex.split("rpm -qa | grep neutron")
            )[1]
            for pkg in neutron_packages.split("\n"):
                vds.package_manager.remove(package=pkg)
    request.addfinalizer(fin1)

    testflow.setup("Set passwordless SSH from Neutron to hosts")
    for vds in external_network_provider.vds_list:
        assert global_helper.set_passwordless_ssh(
            src_host=external_network_provider.neutron_resource, dst_host=vds
        )

    testflow.setup("Run packstack")
    assert not external_network_provider.neutron_resource.run_command(
        command=shlex.split(osnp_conf.PACKSTACK_CMD)
    )[0]
    # Set other-config:forward-bpdu=true to all ovs bridges
    ovs_bridges_out = external_network_provider.vds_0_host.run_command(
        command=shlex.split(osnp_conf.OVS_SHOW_CMD)
    )[1]
    ovs_bridges = [i for i in ovs_bridges_out.split()]
    testflow.setup("set other-config:forward-bpdu=true on all ovs bridges")
    for br in ovs_bridges:
        cmd = shlex.split(osnp_conf.PBDU_FORWARD.format(bridge=br))
        assert not external_network_provider.vds_0_host.run_command(
            command=cmd
        )[0]
    testflow.setup("Restart neutron-server service")
    external_network_provider.neutron_resource.service(
        name="neutron-server"
    ).restart()


@pytest.fixture(scope="class")
def create_network(request):
    """
    Create networks on datacenter
    """
    external_network_provider = ExternalNetworkProviderFixtures()

    def fin():
        """
        Remove network from setup
        """
        testflow.teardown("Remove all networks")
        assert hl_networks.remove_all_networks(
            datacenter=external_network_provider.dc_0
        )
    request.addfinalizer(fin)

    net_dict = {
        osnp_conf.OVS_TUNNEL_BRIDGE: {
            "usages": "",
            "required": "false"
        }
    }
    testflow.setup("Create network %s", osnp_conf.OVS_TUNNEL_BRIDGE)
    network_helper.prepare_networks_on_setup(
        networks_dict=net_dict, dc=external_network_provider.dc_0,
        cluster=external_network_provider.cluster_0
    )


@pytest.fixture(scope="class")
def add_vnic_to_vm(request):
    """
    Add vNIC to VM
    """
    ExternalNetworkProviderFixtures()
    vm = request.node.cls.vm
    nic = request.node.cls.nic
    network = request.node.cls.network

    def fin():
        """
        Remove vNIC from VM
        """
        testflow.teardown("Remove vNIC %s from VM %s", nic, vm)
        assert ll_vms.removeNic(positive=True, vm=vm, nic=nic)
    request.addfinalizer(fin)

    testflow.setup("Add vNIC %s to VM %s", nic, vm)
    assert ll_vms.addNic(positive=True, vm=vm, name=nic, network=network)


@pytest.fixture(scope="class")
def stop_vm(request):
    """
    Stop VM
    """
    vm = request.node.cls.vm

    def fin():
        """
        Stop VM
        """
        testflow.teardown("Stop VM %s", vm)
        assert ll_vms.stop_vms_safely(vms_list=[vm])
    request.addfinalizer(fin)
