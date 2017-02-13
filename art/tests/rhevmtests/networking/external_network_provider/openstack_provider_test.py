#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OpenStack Neutron network provider tests
"""

import shlex

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as osnp_conf
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import (
    add_neutron_provider, OpenStackNetworkProviderFixtures,
    get_provider_networks, import_openstack_network, run_packstack,
    add_vnic_to_vm, stop_vm, create_network
)
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces
)  # flake8: noqa


@attr(tier=3)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    add_neutron_provider.__name__,
    get_provider_networks.__name__
)
class TestOsnp01(NetworkTest):
    """
    Import network from OpenStack network provider
    Delete imported network
    """
    __test__ = False

    @polarion("RHEVM-14817")
    def test_01_add_openstack_provider(self):
        """
        Add OpenStack network provider.
        Add is done in add_neutron_provider fixture.
        """
        testflow.step("Add OpenStack network provider")
        pass

    @polarion("RHEVM-14831")
    def test_02_import_networks(self):
        """
        Import network from OpenStack network provider
        """
        neut = OpenStackNetworkProviderFixtures()
        neut.init()
        testflow.step("Import networks from Neutron provider")
        assert neut.neut.import_network(
            network=osnp_conf.PROVIDER_NETWORKS[0], datacenter=conf.DC_0
        )

    @polarion("RHEVM-14895")
    def test_03_delete_networks(self):
        """
        Delete network from OpenStack network provider
        """
        testflow.step("Import networks imported from Neutron provider")
        assert hl_networks.remove_networks(
            positive=True, networks=[osnp_conf.PROVIDER_NETWORKS[0]]
        )


@attr(tier=3)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_network.__name__,
    setup_networks_fixture.__name__,
    add_neutron_provider.__name__,
    import_openstack_network.__name__,
    run_packstack.__name__,
    add_vnic_to_vm.__name__,
    stop_vm.__name__
)
class TestOsnp02(NetworkTest):
    """
    Run VM with neutron network
    """
    __test__ = False
    vm = conf.VM_0
    nic = osnp_conf.VM_NIC
    network = osnp_conf.PROVIDER_NETWORKS_NAME[0]
    net = osnp_conf.OVS_TUNNEL_BRIDGE
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": 4,
                "network": net,
                "ip": {
                    "1": {
                        "address": osnp_conf.OVS_TUNNEL_IPS[0],
                        "netmask": 24,
                        "boot_protocol": "static"
                    }
                }
            }
        },
        1: {
            net: {
                "nic": 4,
                "network": net,
                "ip": {
                    "1": {
                        "address": osnp_conf.OVS_TUNNEL_IPS[1],
                        "netmask": 24,
                        "boot_protocol": "static"
                    }
                }
            }
        }
    }

    @polarion("RHEVM-14832")
    def test_01_run_vm_with_openstack_network(self):
        """
        Run VM with neutron network
        """
        testflow.step(
            "Run VM %s with neutron network %s", self.vm, self.network
        )
        assert ll_vms.startVm(positive=True, vm=self.vm)
        vm_resource = global_helper.get_vm_resource(vm=self.vm)
        vm_interfaces = vm_resource.network.all_interfaces()
        assert vm_interfaces
        vm_interface = vm_interfaces[-1]
        assert not vm_resource.run_command(
            command=shlex.split(
                "dhclient {interface}".format(interface=vm_interface)
            )
        )[0]
        testflow.step("Check the VM %s got IP from neutron DHCP", self.vm)
        assert ll_vms.wait_for_vm_ip(vm=self.vm, get_all_ips=True)
