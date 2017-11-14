#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OVN provider feature tests

The following elements will be used for the testing:
2 OVN providers, 3 external OVN networks (one with OVN subnet),
2 VM's (VM-0, VM-1), 1 extra vNIC on VM's, 1 vNIC profile
"""

import shlex

import netaddr
import pytest

import config as ovn_conf
import helper
import rhevmtests.networking.config as net_conf
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks, vms as ll_vms
)
from art.test_handler.tools import bz, polarion
from art.unittest_lib import NetworkTest, testflow, tier2, tier3
from fixtures import (
    check_ldap_availability,
    set_cluster_external_network_provider,
    reinstall_hosts,
    configure_provider_plugin,
    create_ovn_networks_on_provider,
    import_ovn_networks,
    remove_ifcfg_from_vms,
    add_ovn_provider,
    get_default_ovn_provider,
    setup_vms_ovn_interface,
    benchmark_file_transfer,
    save_vm_resources
)
from rhevmtests import helpers
from rhevmtests.fixtures import start_vm
from rhevmtests.networking.fixtures import (
    remove_vnic_profiles, add_vnics_to_vms, remove_vnics_from_vms,
    setup_ldap_integration
)


class TestOVNDeployment(NetworkTest):
    """
    1. Test deployment of OVN packages on engine (OVN central)
    2. Test deployment of OVN packages on hosts
    3. Test deployment of firewalld service
    """

    @tier2
    @polarion("RHEVM-22395")
    def test_ovn_central_server(self):
        """
        Test deployment of OVN packages on OVN central (by engine-setup)
        """
        assert net_conf.ENGINE_HOST.package_manager.exist(
            package="ovirt-provider-ovn"
        ), "OVN provider package is not installed on engine"

    @tier2
    @polarion("RHEVM-22396")
    def test_ovn_host(self):
        """
        Test deployment of OVN packages on OVN hosts (by ovirt-host dependency)
        """
        for ovn_host in net_conf.VDS_HOSTS:
            assert ovn_host.package_manager.exist(
                package="ovirt-provider-ovn-driver"
            ), "OVN driver is not installed on host: %s" % ovn_host.fqdn

    @tier2
    @polarion("RHEVM-24245")
    def test_firewalld_service(self):
        """
        1. Test if firewalld service is running on engine (OVN central)
        2. Test if firewalld service is running on OVN hosts
        """
        testflow.step("Testing if firewalld service is running on engine")
        assert helper.service_handler(
            host=net_conf.ENGINE_HOST, service="firewalld", action="active"
        )
        for ovn_host in net_conf.VDS_HOSTS:
            testflow.step(
                "Testing if firewalld service is running on host: %s",
                ovn_host.fqdn
            )
            assert helper.service_handler(
                host=ovn_host, service="firewalld", action="active"
            )

    @tier2
    @polarion("RHEVM-23228")
    def test_firewall_ports_configuration(self):
        """
        1. Test connection to the provider port
        2. Test connection to the provider keystone service port
        3. Test connection to OVN northbound port
        4. Test connection to OVN southbound port
        """
        http_services = [
            ("provider", ovn_conf.OVN_EXTERNAL_PROVIDER_PARAMS["api_url"]),
            ("keystone", ovn_conf.OVN_EXTERNAL_PROVIDER_PARAMS["keystone_url"])
        ]
        for service, url in http_services:
            testflow.step(
                "Test connection to the {service} port".format(service=service)
            )
            assert not net_conf.ENGINE_HOST.run_command(
                shlex.split(
                    ovn_conf.OVN_CMD_TEST_HTTP_RESPONSE.format(url=url)
                )
            )[0]

        for service, tcp_port in ovn_conf.OVN_NETWORK_SERVICE_PORTS:
            testflow.step(
                "Test connection to the OVN {service} port".format(
                    service=service
                )
            )
            assert helper.is_tcp_port_open(
                host=net_conf.ENGINE_HOST.ip, port=tcp_port
            )


@pytest.mark.usefixtures(
    add_ovn_provider.__name__,
    check_ldap_availability.__name__,
    setup_ldap_integration.__name__,
    configure_provider_plugin.__name__,
)
class TestOVNAuthorization(NetworkTest):
    """
    1. Test OVN provider authorization with JDBC user
    2. NEGATIVE: Test OVN provider authorization with wrong JDBC user
    3. Test OVN provider authorization with LDAP user
    4. NEGATIVE: Test OVN provider authorization with wrong LDAP user
    """
    # setup_ldap_integration fixture parameters
    ldap_services = ["ad"]

    # Provider name to be used in authorization tests
    provider_name = "%s-auth-test" % ovn_conf.OVN_PROVIDER_NAME

    # Test case parameters = [
    #   Username to be used in authentication,
    #   Password to be used in authentication,
    #   Plugin to be used in authentication,
    #   True for positive test, False for negative test
    # ]

    # JDBC username test case parameters
    jdbc_group_with_user = [
        ovn_conf.OVN_JDBC_USERNAME, ovn_conf.OVN_JDBC_USERNAME_PASSWORD,
        ovn_conf.OVN_JDBC_GROUP, "JDBC", True
    ]

    # NEGATIVE: JDBC username with wrong password test case parameters
    jdbc_group_with_wrong_user = [
        ovn_conf.OVN_JDBC_USERNAME, ovn_conf.OVN_WRONG_PASSWORD,
        ovn_conf.OVN_JDBC_GROUP, "JDBC", False
    ]

    # LDAP username test case parameters
    ldap_group_with_user = [
        ovn_conf.OVN_LDAP_USERNAME, ovn_conf.OVN_LDAP_USERNAME_PASSWORD,
        ovn_conf.OVN_LDAP_GROUP, "LDAP", True
    ]

    # NEGATIVE: LDAP username with wrong password test case parameters
    ldap_group_with_wrong_user = [
        ovn_conf.OVN_LDAP_USERNAME, ovn_conf.OVN_WRONG_PASSWORD,
        ovn_conf.OVN_LDAP_GROUP, "LDAP", False
    ]

    @tier2
    @pytest.mark.parametrize(
        ("username", "password", "group", "plugin", "positive"),
        [
            pytest.param(
                *jdbc_group_with_user, marks=(polarion("RHEVM-21662"))
            ),
            pytest.param(
                *jdbc_group_with_wrong_user, marks=(polarion("RHEVM-21800"))
            ),
            pytest.param(
                *ldap_group_with_user, marks=(polarion("RHEVM-21683"))
            ),
            pytest.param(
                *ldap_group_with_wrong_user, marks=(polarion("RHEVM-21801"))
            )
        ],
        ids=[
            "ovn_provider_jdbc_group_with_user_test",
            "ovn_provider_jdbc_group_with_wrong_password_test",
            "ovn_provider_ldap_group_with_user_test",
            "ovn_provider_ldap_group_with_wrong_user_test",
        ]
    )
    def test_ovn_authentication_plugin(
        self, username, password, group, plugin, positive
    ):
        """
        Test OVN provider authorization plugin
        """
        _id = helpers.get_test_parametrize_ids(
            item=self.test_ovn_authentication_plugin.parametrize,
            params=[username, password, group, plugin, positive]
        )
        testflow.step(_id)

        testflow.step(
            "Testing plugin: %s on network provider: %s", plugin,
            self.provider_name
        )
        assert ovn_conf.OVN_PROVIDER.update(
            username=username, password=password
        )
        assert positive == ovn_conf.OVN_PROVIDER.test_connection()


@pytest.mark.incremental
@pytest.mark.usefixtures(
    set_cluster_external_network_provider.__name__,
    reinstall_hosts.__name__,
    get_default_ovn_provider.__name__,
    create_ovn_networks_on_provider.__name__,
    import_ovn_networks.__name__,
    remove_vnic_profiles.__name__,
    remove_vnics_from_vms.__name__,
    add_vnics_to_vms.__name__,
    start_vm.__name__,
    save_vm_resources.__name__,
    remove_ifcfg_from_vms.__name__
)
class TestOVNComponent(NetworkTest):
    """
    1. Try to add additional subnet to OVN network with subnet
    2. Hot-add vNIC with OVN network on a live VM
    3. Ping between VM's on the same OVN network and host
    4. Hot-unplug and hot-plug vNIC with OVN network
    5. Hot-update (unplug and plug) vNIC profile with OVN network
    6. OVN networks separation ping tests
    7. Migrate a VM with OVN network
    8. Copy big file between two VM's with OVN network that hosted on
       different hosts
    9. OVN network with subnet DHCP
    10. OVN network with subnet configuration validation tests
    11. OVN network with subnet ping test
    12. Change MAC address of vNIC attached to OVN network
    13. Migrate a VM with OVN network and subnet
    14. Check assignments of long network names
    15. VM IP assignment on OVN subnet without gateway
    """
    # Common settings
    provider_name = ovn_conf.OVN_PROVIDER_NAME
    dc = net_conf.DC_0
    cl = net_conf.CL_0
    vms_ips = []

    # create_ovn_networks_on_provider fixture parameters
    add_ovn_networks_to_provider = dict(
        ovn_conf.OVN_NETS, **ovn_conf.OVN_LONG_NETS
    )
    remove_ovn_networks_from_provider = add_ovn_networks_to_provider

    # import_ovn_networks fixture parameters
    import_ovn_networks_to_engine = ovn_conf.OVN_NETS
    remove_ovn_networks_from_engine = remove_ovn_networks_from_provider.keys()

    # add_vnics_to_vms fixture parameters
    add_vnics_vms_params = {
        net_conf.VM_0: {
            "1": {
                "name": ovn_conf.OVN_VNIC,
                "network": ovn_conf.OVN_NET_NO_SUB_1,
                "plugged": True
            }
        }
    }

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = {
        net_conf.VM_0: {
            1: {
                "name": ovn_conf.OVN_VNIC
            }
        },
        net_conf.VM_1: {}
    }

    # start_vm fixture parameters
    start_vms_dict = {
        net_conf.VM_0: {
            "host": 0
        }
    }
    vms_to_stop = [net_conf.VM_0, net_conf.VM_1]

    # remove_vnic_profile fixture parameters
    remove_vnic_profile_params = {}

    # save_vm_resources fixture parameters
    save_vm_resources_params = [net_conf.VM_0]

    # reinstall_hosts fixture parameters
    hosts_to_reinstall = ovn_conf.OVN_HOSTS_TO_REINSTALL

    @tier2
    @polarion("RHEVM-24286")
    def test_01_add_additional_subnet_to_ovn_network(self):
        """
        1. Create OVN subnet
        2. Try to attach additional OVN subnet to OVN network
           (only one subnet is allowed per OVN network)
        """
        net_id = ovn_conf.OVN_PROVIDER.get_network_id(
            network_name=ovn_conf.OVN_NET_SUB_TO_BE_ATTACHED
        )
        assert net_id, (
            "Unable to get network ID of network: %s" %
            ovn_conf.OVN_NET_SUB_TO_BE_ATTACHED
        )
        assert not ovn_conf.OVN_PROVIDER.create_subnet(
            subnet={
                "name": "ovn_subnet_should_not_be_attached",
                "cidr": "10.1.0.0/24",
                "enable_dhcp": True,
                "ip_version": 4,
                "network_id": net_id
            }
        )

    @tier2
    @polarion("RHEVM3-17296")
    def test_02_hot_add_vnic_with_ovn_network_on_live_vm(self):
        """
        1. Start VM-1 on HOST-0
        2. Hot-add vNIC attached to network: OVN_NET_1 on VM-1
        """
        testflow.step(
            "Starting VM: %s on host: %s", net_conf.VM_1, net_conf.HOST_0_NAME
        )
        assert helper.run_vm_and_wait_for_ip(
            vm=net_conf.VM_1, host=net_conf.HOST_0_NAME
        )

        testflow.step(
            "Hot-adding vNIC: %s with OVN network: %s on live VM: %s",
            ovn_conf.OVN_VNIC, ovn_conf.OVN_NET_NO_SUB_1, net_conf.VM_1
        )
        assert ll_vms.addNic(
            positive=True, vm=net_conf.VM_1, name=ovn_conf.OVN_VNIC,
            network=ovn_conf.OVN_NET_NO_SUB_1, plugged=True
        )
        # Remove vNIC during teardown
        self.remove_vnics_vms_params[net_conf.VM_1]["1"] = {
            "name": ovn_conf.OVN_VNIC
        }

    @tier2
    @polarion("RHEVM3-16927")
    def test_03_ping_same_ovn_network_and_host(self):
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

    @tier2
    @polarion("RHEVM3-16928")
    def test_04_hot_unplug_and_hot_plug_vnic_with_ovn_network(self):
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

    @tier2
    @polarion("RHEVM3-16930")
    def test_05_hot_update_vnic_profile_with_ovn_network(self):
        """
        1. Create vNIC profile: OVN_VNIC_PROFILE attached to net: OVN_NET_1
        2. Hot-unplug OVN vNIC on VM-0
        3. Change VM-0 OVN vNIC profile to: OVN_VNIC_PROFILE
        4. Hot-plug OVN vNIC on VM-0
        5. Assign static IP on OVN vNIC
        6. Test ping from VM-0 to VM-1 IP
        """
        testflow.step(
            "Creating vNIC profile: %s attached to network: %s",
            ovn_conf.OVN_VNIC_PROFILE, ovn_conf.OVN_NET_NO_SUB_1
        )
        assert ll_networks.add_vnic_profile(
            positive=True, name=ovn_conf.OVN_VNIC_PROFILE,
            data_center=self.dc, cluster=self.cl,
            network=ovn_conf.OVN_NET_NO_SUB_1
        )
        # Remove vNIC profile during teardown
        self.remove_vnic_profile_params["1"] = {
            "name": ovn_conf.OVN_VNIC_PROFILE,
            "network": ovn_conf.OVN_NET_NO_SUB_1
        }

        testflow.step(
            "Hot-unplug vNIC: %s on VM: %s, change vNIC profile to: %s, "
            "and hot-plug it back", ovn_conf.OVN_VNIC, net_conf.VM_0,
            ovn_conf.OVN_VNIC_PROFILE
        )
        assert helper.check_hot_unplug_and_plug(
            vm=net_conf.VM_0, vnic=ovn_conf.OVN_VNIC,
            vnic_profile=ovn_conf.OVN_VNIC_PROFILE,
            network=ovn_conf.OVN_NET_NO_SUB_1
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

    @tier2
    @polarion("RHEVM3-17064")
    def test_06_ovn_networks_separation(self):
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
            ovn_conf.OVN_NET_NO_SUB_2
        )
        assert helper.check_hot_unplug_and_plug(
            vm=net_conf.VM_0, vnic=ovn_conf.OVN_VNIC,
            vnic_profile=ovn_conf.OVN_NET_NO_SUB_2,
            network=ovn_conf.OVN_NET_NO_SUB_2
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
            ovn_conf.OVN_NET_NO_SUB_2
        )
        assert helper.check_hot_unplug_and_plug(
            vm=net_conf.VM_1, vnic=ovn_conf.OVN_VNIC,
            network=ovn_conf.OVN_NET_NO_SUB_2
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

    @tier2
    @polarion("RHEVM3-17062")
    def test_07_migrate_vm_different_host(self):
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

    @tier2
    @polarion("RHEVM3-21702")
    def test_08_copy_test_file_between_vms_on_different_hosts(self):
        """
        Copy big file between two VM's with OVN network that hosted on
        different hosts
        """
        vm_0_rsc = ovn_conf.OVN_VMS_RESOURCES[net_conf.VM_0]
        vm_1_rsc = ovn_conf.OVN_VMS_RESOURCES[net_conf.VM_1]

        # On OVN tunnel connections, MTU should be set to 1400 for TCP transfer
        # to work successfully over tunnel
        for vm in [vm_0_rsc, vm_1_rsc]:
            assert helper.set_vm_non_mgmt_interface_mtu(vm=vm, mtu=1400)

        testflow.step(
            "Copying file of size: %s MB from source VM: %s "
            "to destination VM: %s on IP: %s", ovn_conf.OVN_COPY_FILE_SIZE_MB,
            vm_0_rsc, vm_1_rsc, ovn_conf.OVN_VM_1_IP
        )
        assert helper.check_ssh_file_copy(
            src_host=ovn_conf.OVN_VMS_RESOURCES[net_conf.VM_0],
            dst_host=ovn_conf.OVN_VMS_RESOURCES[net_conf.VM_1],
            dst_ip=ovn_conf.OVN_VM_1_IP,
            size=ovn_conf.OVN_COPY_FILE_SIZE_MB
        )[0]

        for vm in [vm_0_rsc, vm_1_rsc]:
            assert helper.set_vm_non_mgmt_interface_mtu(vm=vm, mtu=1500)

    @tier2
    @polarion("RHEVM3-17236")
    def test_09_ovn_network_with_subnet(self):
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
                ovn_conf.OVN_NET_SUB
            )
            assert helper.check_hot_unplug_and_plug(
                vm=vm_name, vnic=ovn_conf.OVN_VNIC,
                vnic_profile=ovn_conf.OVN_NET_SUB, network=ovn_conf.OVN_NET_SUB
            )

            testflow.step("Requesting IP from DHCP on VM: %s", vm_name)
            ip = helper.set_ip_non_mgmt_nic(vm=vm_name, address_type="dynamic")

            testflow.step(
                "Verifying that VM: %s received valid IP: %s", vm_name, ip
            )
            assert netaddr.IPAddress(ip) in netaddr.IPNetwork(
                ovn_conf.OVN_NETS_CIDR
            )
            self.vms_ips.append(ip)

    @tier2
    @polarion("RHEVM3-17436")
    def test_10_ovn_network_with_subnet_validation(self):
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

    @tier2
    @polarion("RHEVM3-17437")
    def test_11_ovn_network_with_subnet_ping(self):
        """
        Test ping from VM-0 to VM-1 IP address
        """
        testflow.step(
            "Testing ping from VM: %s to VM: %s", net_conf.VM_0, net_conf.VM_1
        )
        assert helper.check_ping(vm=net_conf.VM_0, dst_ip=self.vms_ips[1])

    @tier2
    @polarion("RHEVM-19599")
    def test_12_static_mac_change_on_ovn_network(self):
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
            vm=net_conf.VM_0, address_type="dynamic"
        )

        testflow.step(
            "Testing ping from VM: %s to VM: %s", net_conf.VM_0, net_conf.VM_1
        )
        # Sample ping requests due to MAC update problem with RHEL 7.4 beta
        sampler = TimeoutingSampler(
            timeout=60, sleep=1, func=helper.check_ping, vm=net_conf.VM_0,
            dst_ip=self.vms_ips[1]
        )
        assert sampler.waitForFuncStatus(result=True)

    @tier2
    @polarion("RHEVM3-17365")
    def test_13_migrate_vm_with_subnet(self):
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

    @tier2
    @polarion("RHEVM-22212")
    def test_14_long_network_names(self):
        """
        1. Import network with long name to engine
        2. Attach network to OVN vNIC on VM-0 and VM-1
        3. Get DHCP IP on OVN vNIC on VM-0 and VM-1
        4. Test ping from VM-0 to VM-1 over OVN IP
        """
        for net_name in ovn_conf.OVN_LONG_NETS.keys():
            testflow.step("Importing network: %s to engine", net_name)
            assert ovn_conf.OVN_PROVIDER.import_network(
                network=net_name, datacenter=self.dc, cluster=self.cl
            )

        ip = ""
        for vm in (net_conf.VM_0, net_conf.VM_1):
            testflow.step(
                "Hot-unplug vNIC: %s on VM: %s, "
                "change vNIC network to: %s, and hot-plug it back",
                ovn_conf.OVN_VNIC, vm, ovn_conf.OVN_LONG_NET_256_CHARS_SPECIAL
            )
            assert helper.check_hot_unplug_and_plug(
                vm=vm, vnic=ovn_conf.OVN_VNIC,
                network=ovn_conf.OVN_LONG_NET_256_CHARS_SPECIAL
            )

            testflow.step("Requesting IP from DHCP on VM: %s", vm)
            ip = helper.set_ip_non_mgmt_nic(vm=vm, address_type="dynamic")
            assert ip, "Failed to get IP from DHCP on VM: %s" % vm

        # At this point, VM_0 and VM_1 should have OVN IPs
        # Last ip is assigned on VM_1
        testflow.step(
            "Testing ping from VM: %s to IP: %s", net_conf.VM_0, ip
        )
        assert helper.check_ping(vm=net_conf.VM_0, dst_ip=ip, count=3)

    @tier2
    @bz({"1503566": {}})
    @polarion("RHEVM-24247")
    def test_15_ovn_subnet_without_gateway(self):
        """
        VM IP assignment on OVN network subnet without gateway
        """
        testflow.step(
            "Hot-unplug vNIC: %s on VM: %s, change vNIC network to: %s, "
            "and hot-plug it back", ovn_conf.OVN_VNIC, net_conf.VM_0,
            ovn_conf.OVN_NET_SUB_NO_GW
        )
        assert helper.check_hot_unplug_and_plug(
            vm=net_conf.VM_0, vnic=ovn_conf.OVN_VNIC,
            vnic_profile=ovn_conf.OVN_NET_SUB_NO_GW,
            network=ovn_conf.OVN_NET_SUB_NO_GW
        )

        testflow.step("Requesting IP from DHCP on VM: %s", net_conf.VM_0)
        ip = helper.set_ip_non_mgmt_nic(
            vm=net_conf.VM_0, address_type="dynamic"
        )

        testflow.step(
            "Verifying that VM: %s received valid IP: %s", net_conf.VM_0, ip
        )
        assert netaddr.IPAddress(ip) in netaddr.IPNetwork(
            ovn_conf.OVN_NETS_CIDR
        )


@pytest.mark.usefixtures(
    set_cluster_external_network_provider.__name__,
    reinstall_hosts.__name__,
    get_default_ovn_provider.__name__,
    create_ovn_networks_on_provider.__name__,
    import_ovn_networks.__name__,
    remove_vnics_from_vms.__name__,
    add_vnics_to_vms.__name__,
    start_vm.__name__,
    save_vm_resources.__name__,
    setup_vms_ovn_interface.__name__,
    benchmark_file_transfer.__name__
)
class TestOVNPerformance(NetworkTest):
    """
    Test OVN performance over OVN tunneling protocol
    """
    # Common settings
    provider_name = ovn_conf.OVN_PROVIDER_NAME
    dc = net_conf.DC_0
    cl = net_conf.CL_0

    # create_ovn_networks_on_provider fixture parameters
    add_ovn_networks_to_provider = ovn_conf.OVN_NETS_PERF

    # import_ovn_networks fixture parameters
    import_ovn_networks_to_engine = ovn_conf.OVN_NETS_PERF.keys()

    # add_vnics_to_vms fixture parameters
    add_vnics_vms_params = {
        net_conf.VM_0: {
            "1": {
                "name": ovn_conf.OVN_VNIC,
                "network": ovn_conf.OVN_NET_PERF
            }
        },
        net_conf.VM_1: {
            "1": {
                "name": ovn_conf.OVN_VNIC,
                "network": ovn_conf.OVN_NET_PERF
            }
        }
    }

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = add_vnics_vms_params

    # start_vm fixture parameters
    start_vms_dict = {
        net_conf.VM_0: {
            "host": 0
        },
        net_conf.VM_1: {
            "host": 1
        }
    }

    # setup_vms_ovn_interface fixture parameters
    set_vms_ips = {
        net_conf.VM_0: ovn_conf.OVN_VM_0_NET,
        net_conf.VM_1: ovn_conf.OVN_VM_1_NET
    }

    # save_vm_resources fixture parameters
    save_vm_resources_params = [net_conf.VM_0, net_conf.VM_1]

    # get_default_ovn_provider fixture parameters
    test_provider_connection = True

    # reinstall_hosts fixture parameters
    hosts_to_reinstall = ovn_conf.OVN_HOSTS_TO_REINSTALL

    @tier3
    @polarion("RHEVM-22061")
    def test_ovn_over_tunnel_traffic(self):
        """
        1. Copy 1 GB file from VM-0 to VM-1 over OVN tunnel while collecting
           performance counters
        2. Compare VM-to-VM and Host-to-Host benchmarks
        """
        copy_file_res, hosts_perf = helper.copy_file_benchmark(
            src_host=ovn_conf.OVN_VMS_RESOURCES[net_conf.VM_0],
            dst_host=ovn_conf.OVN_VMS_RESOURCES[net_conf.VM_1],
            dst_ip=ovn_conf.OVN_VM_1_IP, size=1000
        )
        assert copy_file_res[0], "Failed to copy file over OVN tunnel"

        # 1. CPU usage should be at lower than maximum 150% of baseline
        # In total, CPU usage should be lower than 70% usage
        cpu_value = round(ovn_conf.OVN_HOST_PERF_COUNTERS[0] * 1.5)
        cpu_baseline_value = max(min(cpu_value, 70), cpu_value)
        testflow.step(
            "Checking if CPU benchmark value: %s <= expected value: %s ",
            hosts_perf[0], cpu_baseline_value
        )
        assert hosts_perf[0] <= cpu_baseline_value, (
            "VM-to-VM host CPU average: %s > %s (expected value)"
            % (hosts_perf[0], cpu_baseline_value)
        )

        # 2. Memory usage should be at maximum 120% of baseline
        # In total, memory usage CPU usage should be lower than 90% usage
        mem_value = round(ovn_conf.OVN_HOST_PERF_COUNTERS[1] * 1.2)
        mem_baseline_value = max(min(mem_value, 90), mem_value)
        testflow.step(
            "Checking if memory benchmark value: %s <= expected value: %s ",
            hosts_perf[1], mem_baseline_value
        )
        assert hosts_perf[1] <= mem_baseline_value, (
            "VM-to-VM host memory average: %s > %s (expected value)"
            % (hosts_perf[1], mem_baseline_value)
        )

        # 3. VM-to-VM transfer rate should be at minimum 80% of baseline
        min_transfer_rate = round(ovn_conf.OVN_HOST_PERF_COUNTERS[2] * 0.8)
        testflow.step(
            "Checking if transfer benchmark value: %s >= expected value: %s ",
            copy_file_res[1], min_transfer_rate
        )
        assert copy_file_res[1] >= min_transfer_rate, (
            "VM-to-VM transfer rate (MB/s): %s "
            "< minimum transfer rate (MB/s): %s (expected value)" %
            (copy_file_res[1], min_transfer_rate)
        )
