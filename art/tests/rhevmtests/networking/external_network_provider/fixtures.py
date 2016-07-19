#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OpenStack network provider fixtures
"""

import re
import shlex

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as osnp_conf
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
        self.neutron_reaource = global_helper.get_host_resource(
            ip=osnp_conf.PROVIDER_IP, password=osnp_conf.ROOT_PASSWORD
        )

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
            osnp_conf.NETWORK_MAPPING.format(interface=self.host_0_nics[-1])
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

    def fin():
        """
        Remove neutron provider
        """
        external_network_provider.neut.remove(
            openstack_ep=osnp_conf.PROVIDER_NAME
        )
    request.addfinalizer(fin)

    assert external_network_provider.neut.add()


@pytest.fixture(scope="class")
def get_provider_networks(request):
    """
    Get all provider networks
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    external_network_provider.get_all_provider_networks()


@pytest.fixture(scope="class")
def import_openstack_network(request, get_provider_networks):
    """
    Import network from OpenStack provider
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    external_network_provider.init()
    net = osnp_conf.PROVIDER_NETWORKS_NAME[0]

    def fin():
        """
        Remove imported network
        """
        hl_networks.remove_networks(positive=True, networks=[net])
    request.addfinalizer(fin)

    assert external_network_provider.neut.import_network(
        network=net, datacenter=external_network_provider.dc_0
    )
    assert ll_networks.add_network_to_cluster(
        positive=True, network=net, required=False,
        cluster=external_network_provider.cluster_0
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
    for vds in external_network_provider.vds_list:
        assert vds.package_manager.install(
            package=osnp_conf.OSNP_VDSM_HOOK
        )
        vds.package_manager.install(package=osnp_conf.RHOS_LATEST)
        assert not vds.run_command(command=shlex.split(osnp_conf.RHOS_CMD))[0]
        vds.run_command(command=shlex.split(osnp_conf.DELETE_IPTABLE_RULE))


@pytest.fixture(scope="module")
def prepare_packstack_answer_file(request):
    """
    Prepare packstack answer file
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    hosts_cmd = list()
    ifaces_cmd = list()
    sed_cmd = "sed -i s/{old_value}/{new_value}/g %s" % osnp_conf.ANSWER_FILE
    hosts_ips = "{host_ip_0},{host_ip_1}".format(
        host_ip_0=external_network_provider.host_0_ip,
        host_ip_1=external_network_provider.host_1_ip
    )
    before_last_interface = external_network_provider.host_0_nics[-2]
    last_interface = external_network_provider.host_0_nics[-1]
    # Set hosts IPs as compute hosts in neutron answer file
    for val in osnp_conf.ANSWER_FILE_HOSTS_PARAMS:
        if val == osnp_conf.NETWORK_HOSTS:
            # Only the first host is networker host
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
        assert not external_network_provider.neutron_reaource.run_command(
            command=cmd
        )[0]


@pytest.fixture(scope="module")
def run_packstack(
    request, create_attach_network_to_hosts, prepare_hosts_for_neutron,
    prepare_packstack_answer_file
):
    """
    Run packstack
    """
    external_network_provider = ExternalNetworkProviderFixtures()

    def fin3():
        """
        Stop openvswitch service
        """
        for vds in external_network_provider.vds_list:
            vds.service("openvswitch").stop()
    request.addfinalizer(fin3)

    def fin2():
        """
        Kill dnsmasq process
        """
        for vds in external_network_provider.vds_list:
            vds.run_command(command=shlex.split("killall dnsmasq"))
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove Neutron RPMs
        """
        for vds in external_network_provider.vds_list:
            neutron_packages = vds.run_command(
                command=shlex.split("rpm -qa | grep neutron")
            )[1]
            for pkg in neutron_packages.split("\n"):
                vds.package_manager.remove(package=pkg)
    request.addfinalizer(fin1)

    for vds in external_network_provider.vds_list:
        assert global_helper.set_passwordless_ssh(
            src_host=external_network_provider.neutron_reaource, dst_host=vds
        )

    assert not external_network_provider.neutron_reaource.run_command(
        command=shlex.split(osnp_conf.PACKSTACK_CMD)
    )[0]
    # Set other-config:forward-bpdu=true to all ovs bridges
    ovs_bridges_out = external_network_provider.vds_0_host.run_command(
        command=shlex.split(osnp_conf.OVS_SHOW_CMD)
    )[1]
    ovs_bridges = [i for i in ovs_bridges_out.split()]
    for br in ovs_bridges:
        cmd = shlex.split(osnp_conf.PBDU_FORWARD.format(bridge=br))
        assert not external_network_provider.vds_0_host.run_command(
            command=cmd
        )[0]


@pytest.fixture(scope="module")
def create_attach_network_to_hosts(request):
    """
    Attach br-ext network to hosts interface
    """
    external_network_provider = ExternalNetworkProviderFixtures()

    def fin2():
        """
        Remove network from setup
        """
        hl_networks.remove_all_networks(
            datacenter=external_network_provider.dc_0
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Clean hosts interfaces
        """
        for host in external_network_provider.hosts_list:
            hl_host_network.clean_host_interfaces(host_name=host)
    request.addfinalizer(fin1)

    net_dict = {
        osnp_conf.OVS_TUNNEL_BRIDGE: {
            "usages": "",
            "required": "false"
        }
    }
    network_helper.prepare_networks_on_setup(
        networks_dict=net_dict, dc=external_network_provider.dc_0,
        cluster=external_network_provider.cluster_0
    )
    for host, vds, ip in zip(
        external_network_provider.hosts_list,
        external_network_provider.vds_list,
        osnp_conf.OVS_TUNNEL_IPS
    ):
        sn_dict = {
            "add": {
                "1": {
                    "network": osnp_conf.OVS_TUNNEL_BRIDGE,
                    "nic": vds.nics[-1],
                    "ip": {
                        "1": {
                            "address": ip,
                            "netmask": 24,
                            "boot_protocol": "static"
                        }
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(host_name=host, **sn_dict)


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
        assert ll_vms.removeNic(positive=True, vm=vm, nic=nic)
    request.addfinalizer(fin)

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
        assert ll_vms.stop_vms_safely(vms_list=[vm])
    request.addfinalizer(fin)
