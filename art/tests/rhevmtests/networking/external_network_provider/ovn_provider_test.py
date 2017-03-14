#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OVN provider feature tests

The following elements will be used for the testing:
OVN provider, 3 external OVN networks (one with OVN subnet),
2 VM's (VM-0, VM-1), 1 extra vNIC on VM's, 1 vNIC profile
"""

import netaddr
import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as ovn_conf
import helper
import rhevmtests.networking.config as net_conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import (
    deploy_ovn, remove_ovn_provider, remove_ovn_networks_from_provider,
    remove_ovn_networks_from_engine, remove_vnics_from_vms,
    remove_vnic_profiles, remove_ifcfg_from_vms
)
from rhevmtests.fixtures import start_vm


@attr(tier=3)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    deploy_ovn.__name__,
    remove_ovn_provider.__name__,
    remove_ovn_networks_from_provider.__name__,
    remove_ovn_networks_from_engine.__name__,
    remove_vnic_profiles.__name__,
    remove_vnics_from_vms.__name__,
    start_vm.__name__,
    remove_ifcfg_from_vms.__name__
)
class TestOVNProvider01(NetworkTest):
    """
    1. Add OVN external network provider
    2. Create networks on OVN provider
    3. Import networks from OVN provider
    4. Start VM with OVN network
    5. Hot-add vNIC with OVN network on a live VM
    6. Ping between VM's on the same OVN network and host
    7. Hot-unplug and hot-plug vNIC with OVN network
    8. Hot-update (unplug and plug) vNIC profile with OVN network
    9. OVN networks separation ping tests
    10. Migrate a VM with OVN network
    11. OVN network with subnet DHCP
    12. OVN network with subnet configuration validation tests
    13. OVN network with subnet ping test
    14. Change MAC address of vNIC attached to OVN network
    15. Migrate a VM with OVN network and subnet
    """
    dc = net_conf.DC_0
    cl = net_conf.CL_0

    remove_vnics_from_vms_params = {
        net_conf.VM_0: ovn_conf.OVN_VNIC,
        net_conf.VM_1: ovn_conf.OVN_VNIC
    }
    vms_to_stop = [net_conf.VM_0, net_conf.VM_1]
    remove_vnic_profiles_params = {
        ovn_conf.OVN_VNIC_PROFILE: ovn_conf.OVN_NET_1
    }
    remove_ifcfg_from_vms_parms = [net_conf.VM_0, net_conf.VM_1]
    vms_ips = list()

    @polarion("RHEVM3-16894")
    def test_01_add_ovn_network_provider(self):
        """
        Add OVN external network provider
        """
        testflow.step(
            "Adding OVN network provider: %s", ovn_conf.OVN_PROVIDER_NAME
        )
        assert ovn_conf.OVN_PROVIDER.add()

    @polarion("RHEVM3-16925")
    def test_02_create_networks_on_ovn_provider(self):
        """
        Create networks on OVN provider
        """
        for net_name, subnet in ovn_conf.OVN_NETS.iteritems():
            txt = " with subnet: %s" % subnet.get("name") if subnet else ""
            testflow.setup(
                "Creating network: %s%s on OVN provider", net_name, txt
            )
            assert ovn_conf.OVN_PROVIDER.add_network(
                network_name=net_name, subnet_dict=subnet
            )

    @polarion("RHEVM3-17046")
    def test_03_import_networks_from_ovn_provider(self):
        """
        Import networks from OVN provider
        """
        for net_name in ovn_conf.OVN_NET_NAMES:
            testflow.setup(
                "Importing OVN provider network: %s to DC: %s Cluster: %s",
                net_name, self.dc, self.cl
            )
            assert ovn_conf.OVN_PROVIDER.import_network(
                network=net_name, datacenter=self.dc, cluster=self.cl
            )

    @polarion("RHEVM3-17439")
    def test_04_start_vm_with_ovn_network(self):
        """
        1. Add vNIC attached to network: OVN_NET_1 to VM-0
        2. Start VM-0
        """
        testflow.setup(
            "Adding vNIC: %s to VM: %s", ovn_conf.OVN_VNIC, net_conf.VM_0
        )
        assert ll_vms.addNic(
            positive=True, vm=net_conf.VM_0, name=ovn_conf.OVN_VNIC,
            network=ovn_conf.OVN_NET_1, plugged=True
        )

        testflow.step(
            "Starting VM: %s on host: %s", net_conf.VM_0, net_conf.HOST_0_NAME
        )
        helper.run_vm_on_host(vm=net_conf.VM_0, host=net_conf.HOST_0_NAME)

    @polarion("RHEVM3-17296")
    def test_05_hot_add_vnic_with_ovn_network_on_live_vm(self):
        """
        1. Start VM-1 on HOST-0
        2. Hot-add vNIC attached to network: OVN_NET_1 on VM-1
        """
        testflow.step(
            "Starting VM: %s on host: %s", net_conf.VM_1, net_conf.HOST_0_NAME
        )
        helper.run_vm_on_host(vm=net_conf.VM_1, host=net_conf.HOST_0_NAME)

        testflow.step(
            "Hot-adding vNIC: %s with OVN network: %s on live VM: %s",
            ovn_conf.OVN_VNIC, ovn_conf.OVN_NET_1, net_conf.VM_1
        )
        assert ll_vms.addNic(
            positive=True, vm=net_conf.VM_1, name=ovn_conf.OVN_VNIC,
            network=ovn_conf.OVN_NET_1, plugged=True
        )

    @polarion("RHEVM3-16927")
    def test_06_ping_same_ovn_network_and_host(self):
        """
        1. Assign static IP on VM-0 OVN vNIC
        2. Assign static IP on VM-1 OVN vNIC
        3. Test ping from VM-0 to VM-1 IP
        """
        for vm_name, net in zip(
            (net_conf.VM_0, net_conf.VM_1),
            (ovn_conf.OVN_VM_0_NET, ovn_conf.OVN_VM_1_NET)
        ):
            testflow.step("Setting IP network: %s on VM: %s", net, vm_name)
            assert helper.set_ip_non_mgmt_nic(vm=vm_name, ip_network=net)

        testflow.step(
            "Testing ping from VM: %s to IP: %s", net_conf.VM_0,
            ovn_conf.OVN_VM_1_IP
        )
        assert helper.check_ping(
            vm=net_conf.VM_0, dst_ip=ovn_conf.OVN_VM_1_IP
        )

    @polarion("RHEVM3-16928")
    def test_07_hot_unplug_and_hot_plug_vnic_with_ovn_network(self):
        """
        1. Hot-unplug OVN vNIC on VM-0
        2. Hot-plug OVN vNIC on VM-0
        3. Assign static IP on VM-0 OVN vNIC
        4. Test ping from VM-0 to VM-1 IP
        """
        testflow.step(
            "Hot-unplugging and hot-plugging vNIC: %s on VM: %s",
            ovn_conf.OVN_VNIC, net_conf.VM_0
        )
        assert helper.check_hot_unplug_and_plug(
            vm=net_conf.VM_0, vnic=ovn_conf.OVN_VNIC
        )

        testflow.step(
            "Setting IP network: %s on VM: %s", ovn_conf.OVN_VM_0_NET,
            net_conf.VM_0
        )
        assert helper.set_ip_non_mgmt_nic(
            vm=net_conf.VM_0, ip_network=ovn_conf.OVN_VM_0_NET
        )

        testflow.step(
            "Testing ping from VM: %s to IP: %s", net_conf.VM_0,
            ovn_conf.OVN_VM_1_IP
        )
        assert helper.check_ping(
            vm=net_conf.VM_0, dst_ip=ovn_conf.OVN_VM_1_IP
        )

    @polarion("RHEVM3-16930")
    def test_08_hot_update_vnic_profile_with_ovn_network(self):
        """
        1. Create vNIC profile: OVN_VNIC_PROFILE attached to net: OVN_NET_1
        2. Hot-unplug OVN vNIC on VM-0
        3. Change VM-0 OVN vNIC profile to: OVN_VNIC_PROFILE
        4. Hot-plug OVN vNIC on VM-0
        5. Assign static IP on OVN vNIC
        6. Test ping from VM-0 to VM-1 IP
        """
        testflow.setup(
            "Creating vNIC profile: %s attached to network: %s",
            ovn_conf.OVN_VNIC_PROFILE, ovn_conf.OVN_NET_1
        )
        assert ll_networks.add_vnic_profile(
            positive=True, name=ovn_conf.OVN_VNIC_PROFILE,
            data_center=self.dc, cluster=self.cl, network=ovn_conf.OVN_NET_1
        )

        testflow.step(
            "Hot-unplug vNIC: %s on VM: %s, change vNIC profile to: %s, "
            "and hot-plug it back", ovn_conf.OVN_VNIC, net_conf.VM_0,
            ovn_conf.OVN_VNIC_PROFILE
        )
        assert helper.check_hot_unplug_and_plug(
            vm=net_conf.VM_0, vnic=ovn_conf.OVN_VNIC,
            vnic_profile=ovn_conf.OVN_VNIC_PROFILE, network=ovn_conf.OVN_NET_1
        )

        testflow.step(
            "Setting IP network: %s on VM: %s", ovn_conf.OVN_VM_0_NET,
            net_conf.VM_0
        )
        assert helper.set_ip_non_mgmt_nic(
            vm=net_conf.VM_0, ip_network=ovn_conf.OVN_VM_0_NET
        )

        testflow.step(
            "Testing ping from VM: %s to IP: %s", net_conf.VM_0,
            ovn_conf.OVN_VM_1_IP
        )
        assert helper.check_ping(
            vm=net_conf.VM_0, dst_ip=ovn_conf.OVN_VM_1_IP
        )

    @polarion("RHEVM3-17064")
    def test_09_ovn_networks_separation(self):
        """
        1. Hot-unplug OVN vNIC from VM-0
        2. Attach VM-0 OVN vNIC with OVN network: OVN_NET_2
        3. Hot-plug OVN vNIC on VM-0
        4. Assign static IP on VM-0 OVN vNIC
        5. Negative: test ping from VM-1 to VM-0 IP
        6. Hot-unplug OVN vNIC from VM-1
        7. Attach VM-1 OVN vNIC with OVN network: OVN_NET_2
        8. Hot-plug OVN vNIC on VM-1
        9. Assign static IP on VM-1 OVN NIC
        10. Test ping from VM-0 to VM-1 IP
        """
        testflow.step(
            "Hot-unplug vNIC: %s on VM: %s, change vNIC network to: %s, "
            "and hot-plug it back", ovn_conf.OVN_VNIC, net_conf.VM_0,
            ovn_conf.OVN_NET_2
        )
        assert helper.check_hot_unplug_and_plug(
            vm=net_conf.VM_0, vnic=ovn_conf.OVN_VNIC,
            vnic_profile=ovn_conf.OVN_NET_2, network=ovn_conf.OVN_NET_2
        )

        testflow.step(
            "Setting IP network: %s on VM: %s", ovn_conf.OVN_VM_0_NET,
            net_conf.VM_0
        )
        assert helper.set_ip_non_mgmt_nic(
            vm=net_conf.VM_0, ip_network=ovn_conf.OVN_VM_0_NET
        )

        testflow.step(
            "NEGATIVE: testing ping from VM: %s to IP: %s", net_conf.VM_0,
            ovn_conf.OVN_VM_1_IP
        )
        assert not helper.check_ping(
            vm=net_conf.VM_0, dst_ip=ovn_conf.OVN_VM_1_IP
        )

        testflow.step(
            "Hot-unplug vNIC: %s on VM: %s, change vNIC network to: %s, "
            "and hot-plug it back", ovn_conf.OVN_VNIC, net_conf.VM_1,
            ovn_conf.OVN_NET_2
        )
        assert helper.check_hot_unplug_and_plug(
            vm=net_conf.VM_1, vnic=ovn_conf.OVN_VNIC,
            network=ovn_conf.OVN_NET_2
        )

        testflow.step(
            "Setting IP network: %s on VM: %s", ovn_conf.OVN_VM_1_NET,
            net_conf.VM_1
        )
        assert helper.set_ip_non_mgmt_nic(
            vm=net_conf.VM_1, ip_network=ovn_conf.OVN_VM_1_NET
        )

        testflow.step(
            "Testing ping from VM: %s to IP: %s", net_conf.VM_0,
            ovn_conf.OVN_VM_1_IP
        )
        assert helper.check_ping(
            vm=net_conf.VM_0, dst_ip=ovn_conf.OVN_VM_1_IP
        )

    @polarion("RHEVM3-17062")
    def test_10_migrate_vm_different_host(self):
        """
        1. Migrate VM-0 from host-0 to host-1
        2. Test ping from VM-1 to VM-0 IP during migration
        """
        ping_kwargs = {
            "vm": net_conf.VM_1,
            "dst_ip": ovn_conf.OVN_VM_0_IP,
            "max_loss": ovn_conf.OVN_MIGRATION_PING_LOSS_COUNT,
            "count": ovn_conf.OVN_MIGRATION_PING_COUNT
        }
        migrate_kwargs = {
            "vms_list": [net_conf.VM_0],
            "src_host": net_conf.HOST_0_NAME,
            "dst_host": net_conf.HOST_1_NAME,
            "vm_os_type": "rhel",
            "vm_user": net_conf.VMS_LINUX_USER,
            "vm_password": net_conf.VMS_LINUX_PW,
        }

        testflow.step(
            "Migrating VM: %s from host: %s to host: %s and testing ping "
            "from VM: %s to VM: %s", net_conf.VM_0, net_conf.HOST_0_NAME,
            net_conf.HOST_1_NAME, net_conf.VM_1, net_conf.VM_0
        )
        assert helper.check_ping_during_vm_migration(
            ping_kwargs=ping_kwargs, migration_kwargs=migrate_kwargs
        )

    @polarion("RHEVM3-17236")
    def test_11_ovn_network_with_subnet(self):
        """
        1. Create ifcfg file that prevents default route change
        2. Hot-unplug OVN vNIC on VM-0
        3. Attach VM-0 OVN vNIC network: OVN_NET_3
        4. Hot-plug OVN vNIC on VM-0
        5. Request DHCP IP address on OVN vNIC
        6. Verify that VM-0 acquired IP address from DHCP
        7. Hot-unplug OVN vNIC on VM-1
        8. Attach VM-1 OVN vNIC network: OVN_NET_3
        9. Hot-plug OVN vNIC on VM-1
        10. Request DHCP IP address on OVN vNIC
        11. Verify that VM-1 acquired IP address from DHCP
        """
        for vm_name in (net_conf.VM_0, net_conf.VM_1):
            testflow.step(
                "Creating ifcfg file on VM: %s that prevents route change",
                vm_name
            )
            assert helper.create_ifcfg_on_vm(vm=vm_name)

            testflow.step(
                "Hot-unplug vNIC: %s on VM: %s, change vNIC network to: %s, "
                "and hot-plug it back", ovn_conf.OVN_VNIC, vm_name,
                ovn_conf.OVN_NET_3
            )
            assert helper.check_hot_unplug_and_plug(
                vm=vm_name, vnic=ovn_conf.OVN_VNIC,
                vnic_profile=ovn_conf.OVN_NET_3, network=ovn_conf.OVN_NET_3
            )

            testflow.step("Requesting IP from DHCP on VM: %s", vm_name)
            ip = helper.set_ip_non_mgmt_nic(vm=vm_name, address_type="dhcp")

            testflow.step(
                "Verifying that VM: %s received valid IP: %s", vm_name, ip
            )
            assert netaddr.IPAddress(ip) in netaddr.IPNetwork(
                ovn_conf.OVN_NETS_CIDR
            )
            self.vms_ips.append(ip)

    @polarion("RHEVM3-17436")
    def test_12_ovn_network_with_subnet_validation(self):
        """
        1. Check that VM-0 has DNS configured
        2. Check that VM-1 has DNS configured
        3. Verify that OVN vNIC on VM-0 has unique IP
        """
        for vm_name in (net_conf.VM_0, net_conf.VM_1):
            testflow.step(
                "Verifying that VM: %s has DNS server: %s configured", vm_name,
                ovn_conf.OVN_NETS_DNS[0]
            )
            assert helper.check_dns_resolver(
                vm=vm_name, ip_address=ovn_conf.OVN_NETS_DNS[0]
            )

        testflow.step("Verifying that IP: %s is unique", self.vms_ips[0])
        assert self.vms_ips[0] != self.vms_ips[1]

    @polarion("RHEVM3-17437")
    def test_13_ovn_network_with_subnet_ping(self):
        """
        Test ping from VM-0 to VM-1 IP address
        """
        testflow.step(
            "Testing ping from VM: %s to VM: %s", net_conf.VM_0, net_conf.VM_1
        )
        assert helper.check_ping(
            vm=net_conf.VM_0, dst_ip=self.vms_ips[1]
        )

    @polarion("RHEVM-19599")
    def test_14_static_mac_change_on_ovn_network(self):
        """
        Change MAC address of vNIC attached to OVN network and check
        network connectivity
        """
        assert helper.check_hot_unplug_and_plug(
            vm=net_conf.VM_0, vnic=ovn_conf.OVN_VNIC,
            mac_address=ovn_conf.OVN_ARBITRARY_MAC_ADDRESS
        )

        testflow.step("Requesting IP from DHCP on VM: %s", net_conf.VM_0)
        assert helper.set_ip_non_mgmt_nic(
            vm=net_conf.VM_0, address_type="dhcp"
        )

        testflow.step(
            "Testing ping from VM: %s to VM: %s", net_conf.VM_0, net_conf.VM_1
        )
        assert helper.check_ping(
            vm=net_conf.VM_0, dst_ip=self.vms_ips[1]
        )

    @polarion("RHEVM3-17365")
    def test_15_migrate_vm_with_subnet(self):
        """
        1. Migrate VM-0 from host-1 to host-0
        2. Test ping from VM-1 to VM-0 IP during VM-0 migration
        """
        ping_kwargs = {
            "vm": net_conf.VM_1,
            "dst_ip": self.vms_ips[0],
            "max_loss": ovn_conf.OVN_MIGRATION_PING_LOSS_COUNT,
            "count": ovn_conf.OVN_MIGRATION_PING_COUNT
        }
        migrate_kwargs = {
            "vms_list": [net_conf.VM_0],
            "src_host": net_conf.HOST_1_NAME,
            "dst_host": net_conf.HOST_0_NAME,
            "vm_os_type": "rhel",
            "vm_user": net_conf.VMS_LINUX_USER,
            "vm_password": net_conf.VMS_LINUX_PW,
        }

        testflow.step(
            "Migrating VM: %s from host: %s to host: %s and testing ping "
            "from VM: %s to VM: %s", net_conf.VM_0, net_conf.HOST_1_NAME,
            net_conf.HOST_0_NAME, net_conf.VM_1, net_conf.VM_0
        )
        assert helper.check_ping_during_vm_migration(
            ping_kwargs=ping_kwargs, migration_kwargs=migrate_kwargs
        )
