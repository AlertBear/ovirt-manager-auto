#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OpenStack network provider fixtures
"""

import re
import shlex

import pytest

import art.core_api.apis_exceptions as api_exceptions
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as osnp_conf
import helper
import rhevmtests.config as conf
import rhevmtests.helpers as global_helper
import rhevmtests.networking.helper as network_helper
from art.rhevm_api.tests_lib.low_level import external_providers
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


class OpenStackNetworkProviderFixtures(NetworkFixtures):
    """
    OpenStack external network provider class
    """
    def __init__(self):
        super(OpenStackNetworkProviderFixtures, self).__init__()
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
        Set Neutron provider params
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


@pytest.fixture(scope="class")
def remove_ovn_provider(request):
    """
    Remove OVN provider from engine
    """
    NetworkFixtures()
    name = osnp_conf.OVN_PROVIDER_NAME

    def fin():
        testflow.teardown("Removing OVN external network provider: %s", name)
        assert osnp_conf.OVN_PROVIDER.remove(openstack_ep=name)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_ovn_networks_from_provider(request):
    """
    Remove OVN network(s) and associated subnet(s) from provider
    """
    NetworkFixtures()

    def fin():
        result_list = list()

        for name, subnet in osnp_conf.OVN_NETS.iteritems():
            if subnet:
                subnet_name = subnet.get("name")
                testflow.teardown(
                    "Removing OVN subnet: %s from provider", subnet_name
                )
                result_list.append(
                    osnp_conf.OVN_PROVIDER.remove_subnet(
                        subnet_name=subnet_name
                    )
                )

            testflow.teardown("Removing OVN network: %s from provider", name)
            result_list.append(
                osnp_conf.OVN_PROVIDER.remove_network(network_name=name)
            )
        assert all(result_list)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_ovn_networks_from_engine(request):
    """
    Remove OVN networks from engine
    """
    NetworkFixtures()
    networks = osnp_conf.OVN_NET_NAMES

    def fin():
        results_list = list()

        for net in [net for net in networks if ll_networks.find_network(net)]:
            testflow.teardown("Removing network: %s from engine", net)
            results_list.append(
                ll_networks.remove_network(positive=True, network=net)
            )
        assert all(results_list)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_vnics_from_vms(request):
    """
    Remove vNIC(s) with properties from VM(s)
    """
    NetworkFixtures()
    vnics_remove_dict = request.node.cls.remove_vnics_from_vms_params

    def fin():
        results_list = list()

        for vm, vnic in vnics_remove_dict.iteritems():
            testflow.teardown("Removing vNIC: %s from VM: %s", vnic, vm)
            try:
                res = ll_vms.removeNic(positive=True, vm=vm, nic=vnic)
            except api_exceptions.EntityNotFound:
                res = True
            results_list.append(res)
        assert all(results_list)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_vnic_profiles(request):
    """
    Remove vNIC profile(s)
    """
    NetworkFixtures()
    vnic_profiles = request.node.cls.remove_vnic_profiles_params

    def fin():
        results = list()

        for name, net in vnic_profiles.iteritems():
            testflow.teardown("Removing vNIC profile: %s", name)
            if ll_networks.is_vnic_profile_exist(name):
                results.append(
                    ll_networks.remove_vnic_profile(
                        positive=True, vnic_profile_name=name, network=net
                    )
                )
        assert all(results)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_ifcfg_from_vms(request):
    """
    Remove ifcfg file from VM(s)
    """
    NetworkFixtures()

    def fin():
        testflow.teardown("Removing ifcfg files from running VM's")
        vms_resources = [
            rsc for rsc in osnp_conf.OVN_VMS_RESOURCES.values() if rsc
        ]
        assert network_helper.remove_ifcfg_files(vms_resources=vms_resources)
    request.addfinalizer(fin)


@pytest.fixture(scope="module")
def deploy_ovn(request):
    """
    Deploy OVN provider feature components: OVN provider, OVN provider driver
    and all the required OVN and OVS dependencies

    OVN provider (OVN central server) will be installed on the oVirt engine
    OVN provider driver (OVN node) will be installed in a two nodes topology,
    on servers: vds_1 and vds_2
    """
    ovn = NetworkFixtures()

    provider_server = conf.ENGINE_HOST
    provider_driver_servers = [ovn.vds_0_host, ovn.vds_1_host]
    provider_driver_servers_names = [ovn.host_0_name, ovn.host_1_name]
    all_servers = [provider_server] + provider_driver_servers

    def fin7():
        """
        Reactivate driver servers
        """
        results_list = list()

        for host in provider_driver_servers_names:
            testflow.teardown(
                "Waiting for host: %s status: up and reactivating host", host
            )
            results_list.append(
                helper.wait_for_up_state_and_reactivate(host=host)
            )
        assert results_list
    request.addfinalizer(fin7)

    def fin6():
        """
        Restore stopped services on all servers
        """
        results_list = list()

        for host, services in osnp_conf.OVN_SERVICES_RUNNING.iteritems():
            for service in services:
                testflow.teardown(
                    "Restoring service: %s state on host: %s",
                    service, host.fqdn
                )
                results_list.append(
                    helper.service_handler(
                        host=host, service=service, action="start"
                    )
                )
        assert results_list
    request.addfinalizer(fin6)

    def fin5():
        """
        Removing OVN bridge from provider driver servers
        """
        result_list = list()

        for host in provider_driver_servers:
            if host.fs.exists(osnp_conf.OVN_BRIDGE_INTERFACE_FILE):
                testflow.teardown(
                    "Removing OVN bridge from host: %s", host.fqdn
                )
                result_list.append(
                    host.run_command(
                        shlex.split(osnp_conf.OVN_CMD_DEL_OVN_BRIDGE)
                    )[0]
                )
        assert not all(result_list)
    request.addfinalizer(fin5)

    def fin4():
        """
        Removing OVN packages from provider server
        """
        result_list = list()

        for rpm_name in osnp_conf.OVN_PROVIDER_REMOVE_RPMS:
            testflow.teardown(
                "Removing OVN package: %s from OVN provider server: %s",
                rpm_name, provider_server.fqdn
            )
            result_list.append(
                provider_server.package_manager.remove(package=rpm_name)
            )
        assert all(result_list)
    request.addfinalizer(fin4)

    def fin3():
        """
        Stopping OVN service on provider server
        """
        testflow.teardown(
            "Stopping OVN service: %s on OVN provider: %s",
            osnp_conf.OVN_PROVIDER_SERVICE, provider_server.fqdn
        )
        helper.service_handler(
            host=host, service=osnp_conf.OVN_PROVIDER_SERVICE
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Removing OVN packages from driver servers
        """
        result_list = list()

        for host in provider_driver_servers:
            for rpm_name in osnp_conf.OVN_DRIVER_REMOVE_RPMS:
                testflow.teardown(
                    "Removing OVN package: %s from OVN driver driver: %s",
                    rpm_name, host.fqdn
                )
                result_list.append(
                    host.package_manager.remove(package=rpm_name)
                )
        assert all(result_list)
    request.addfinalizer(fin2)

    def fin1():
        """
        Stopping OVN service on driver servers
        """
        result_list = list()

        for host in provider_driver_servers:
            testflow.teardown(
                "Stopping service: %s on OVN driver server: %s",
                osnp_conf.OVN_DRIVER_SERVICE, host.fqdn
            )
            result_list.append(
                helper.service_handler(
                    host=host, service=osnp_conf.OVN_DRIVER_SERVICE
                )
            )
        assert all(result_list)
    request.addfinalizer(fin1)

    # Deployment actions for all servers
    for host in all_servers:
        # Stop firewall services that blocks OVN traffic as a workaround for BZ
        # ticket: https://bugzilla.redhat.com/show_bug.cgi?id=1390938
        for service in osnp_conf.OVN_FW_SERVICES:
            testflow.setup(
                "Stopping firewall service: %s on host: %s", service, host.fqdn
            )
            assert helper.service_handler(host=host, service=service)

        for service in osnp_conf.OVN_SERVICES_TO_STOP_AND_START:
            state = helper.service_handler(
                host=host, service=service, action="state"
            )
            if state:
                testflow.setup(
                    "Saving service: %s is-active state: %s on host: %s",
                    service, state, host
                )
                if host not in osnp_conf.OVN_SERVICES_RUNNING:
                    osnp_conf.OVN_SERVICES_RUNNING[host] = list()
                osnp_conf.OVN_SERVICES_RUNNING[host].append(service)

        for rpm_name in osnp_conf.OVN_COMMON_RPMS:
            testflow.setup(
                "Installing common package: %s on host: %s", rpm_name,
                host.fqdn
            )
            assert helper.rpm_install(host=host, rpm_name=rpm_name)

    # OVN provider deployment
    for rpm_name in osnp_conf.OVN_PROVIDER_RPMS:
        testflow.setup(
            "Installing OVN provider package: %s on host: %s", rpm_name,
            provider_server.fqdn
        )
        assert helper.rpm_install(host=provider_server, rpm_name=rpm_name)

    testflow.setup(
        "Reloading systemd daemon on host: %s", provider_server.fqdn
    )
    assert not provider_server.run_command(
        shlex.split(osnp_conf.OVN_CMD_SYSD_RELOAD)
    )[0]

    testflow.setup("Starting OVN provider on host: %s", provider_server.fqdn)
    assert provider_server.service(
        name=osnp_conf.OVN_PROVIDER_SERVICE
    ).start()

    # OVN driver deployment
    for host in provider_driver_servers:
        for rpm_name in osnp_conf.OVN_DRIVER_RPMS:
            testflow.setup(
                "Installing OVN controller package: %s on host: %s",
                rpm_name, host.fqdn
            )
            assert helper.rpm_install(host=host, rpm_name=rpm_name)

        testflow.setup("Reloading systemd daemon on host %s", host.fqdn)
        assert not host.run_command(
            shlex.split(osnp_conf.OVN_CMD_SYSD_RELOAD)
        )[0]

        testflow.setup("Starting OVN driver service on host: %s", host.fqdn)
        assert host.service(name=osnp_conf.OVN_DRIVER_SERVICE).start()

        testflow.setup("Configuring vdsm-tool on host: %s", host.fqdn)
        assert not host.run_command(
            shlex.split(
                osnp_conf.OVN_CMD_VDSM_TOOL.format(
                    provider_ip=provider_server.ip, host_ip=host.ip
                )
            )
        )[0]

    # Initialize OVN provider class
    osnp_conf.OVN_PROVIDER = external_providers.ExternalNetworkProvider(
        **osnp_conf.OVN_EXTERNAL_PROVIDER_PARAMS
    )

    # Check for existing OVN objects
    helper.check_for_ovn_objects()

    # Workaround for OVN bugs:
    # 1. Make sure br-int interface config file exists post OVN installation.
    # There is a bug with OVN high CPU usage
    # https://bugzilla.redhat.com/show_bug.cgi?id=1386514)
    # 2. Make sure all hosts are up and running after OVS system upgrade
    # (https://bugzilla.redhat.com/show_bug.cgi?id=1371840)

    for host, name in zip(
        provider_driver_servers, provider_driver_servers_names
    ):
        testflow.setup(
            "Verifying that OVN interface bridge config exists on host: %s",
            name
        )
        assert host.fs.exists(osnp_conf.OVN_BRIDGE_INTERFACE_FILE)

        testflow.setup(
            "Waiting for host: %s status: up and reactivating host", host
        )
        assert helper.wait_for_up_state_and_reactivate(name)


@pytest.fixture(scope="module")
def add_neutron_provider(request):
    """
    Add Neutron network provider
    """
    external_network_provider = OpenStackNetworkProviderFixtures()
    external_network_provider.set_neut_params()
    provider_name = osnp_conf.PROVIDER_NAME

    def fin():
        """
        Remove Neutron provider
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
    external_network_provider = OpenStackNetworkProviderFixtures()
    testflow.setup("Get all Neutron provider networks")
    external_network_provider.get_all_provider_networks()


@pytest.fixture(scope="class")
def import_openstack_network(request, get_provider_networks):
    """
    Import network from OpenStack provider
    """
    external_network_provider = OpenStackNetworkProviderFixtures()
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
    external_network_provider = OpenStackNetworkProviderFixtures()
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
    external_network_provider = OpenStackNetworkProviderFixtures()
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
    external_network_provider = OpenStackNetworkProviderFixtures()

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
    external_network_provider = OpenStackNetworkProviderFixtures()

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
    OpenStackNetworkProviderFixtures()
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
