#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for MultiHost
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as multi_host_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


class MultiHost(NetworkFixtures):
    """
    Fixtures for host_network_qos
    """
    def __init__(self):
        super(MultiHost, self).__init__()
        conf.HOSTS_LIST = [self.host_0_name, self.host_1_name]
        conf.VDS_HOSTS_LIST = [self.vds_0_host, self.vds_1_host]

    def attach_network_to_host_nic(
        self, network, nic, hosts=None, slaves=None
    ):
        """
        Attach network to host NIC

        Args:
            network (str): Network name
            nic (str): Host NIC name
            hosts (list): Hosts list
            slaves (list): BOND slaves if NIC is BOND
        """
        hosts = hosts if hosts else [self.host_0_name]
        local_dict = {
            "add": {
                "1": {
                    "network": network,
                    "nic": nic
                }
            }
        }
        if slaves:
            local_dict["add"]["1"]["slaves"] = slaves

        for host in hosts:
            assert hl_host_network.setup_networks(
                host_name=host, **local_dict
            )


@pytest.fixture(scope="module")
def multi_host_prepare_setup(request, network_cleanup_fixture):
    """
    Prepare setup
    """
    multi_host = MultiHost()

    def fin3():
        """
        Remove ve dummies interfaces from host
        """
        multi_host.remove_dummies(host_resource=multi_host.vds_0_host)
    request.addfinalizer(fin3)

    def fin2():
        """
        Stop VM
        """
        multi_host.stop_vm(positive=True, vm=multi_host.vm_0)
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove networks from setup
        """
        multi_host.remove_networks_from_setup(hosts=multi_host.host_0_name)
    request.addfinalizer(fin1)

    multi_host.prepare_dummies(
        host_resource=multi_host.vds_0_host, num_dummy=conf.NUM_DUMMYS
    )
    multi_host.prepare_networks_on_setup(
        networks_dict=multi_host_conf.NETS_DICT, dc=multi_host.dc_0,
        cluster=multi_host.cluster_0
    )
    assert network_helper.run_vm_once_specific_host(
        vm=multi_host.vm_0, host=multi_host.host_0_name,
        wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def teardown_all_cases(request, multi_host_prepare_setup):
    """
    Restore host interfaces MTU and remove unneeded networks
    """
    multi_host = MultiHost()

    def fin2():
        """
        Clean hosts interfaces
        """
        for host in conf.HOSTS_LIST:
            hl_host_network.clean_host_interfaces(host_name=host)
    request.addfinalizer(fin2)

    def fin1():
        """
        Restore interfaces default MTU
        """
        if request.node.cls.restore_mtu:
            net = request.node.cls.net
            mtu_1500 = request.node.cls.mtu_1500
            helper.update_network_and_check_changes(
                net=net, mtu=mtu_1500, hosts=conf.HOSTS_LIST,
                vds_hosts=conf.VDS_HOSTS_LIST
            )
    request.addfinalizer(fin1)


@pytest.fixture(scope="class")
def fixture_case_01_02(request, teardown_all_cases):
    """
    Attach network to host NIC
    """
    multi_host = MultiHost()
    net = request.node.cls.net
    multi_host.attach_network_to_host_nic(
        network=net, nic=multi_host.host_0_nics[1]
    )


@pytest.fixture(scope="class")
def fixture_case_03(request, teardown_all_cases):
    """
    Attach network to host NIC
    Add vNIC to VMs
    """
    multi_host = MultiHost()
    net = request.node.cls.net
    vm_nic = request.node.cls.vm_nic
    vm_list = request.node.cls.vm_list
    vm_0 = request.node.cls.vm_0

    def fin():
        """
        Un-plug vNIC
        Remove vNIC from VMs
        """
        assert ll_vms.updateNic(
            positive=True, vm=vm_0, nic=vm_nic, plugged="false"
        )
        for vm in vm_list:
            assert ll_vms.removeNic(positive=True, vm=vm, nic=vm_nic)
    request.addfinalizer(fin)

    multi_host.attach_network_to_host_nic(
        network=net, nic=multi_host.host_0_nics[1]
    )
    for vm in vm_list:
        assert ll_vms.addNic(positive=True, vm=vm, name=vm_nic, network=net)


@pytest.fixture(scope="class")
def fixture_case_04(request, teardown_all_cases):
    """
    Attach network to host NIC
    AddvNIC to template
    """
    multi_host = MultiHost()
    net = request.node.cls.net
    vm_nic = request.node.cls.vm_nic
    dc = request.node.cls.dc
    template = request.node.cls.template

    def fin():
        """
        Remove vNIC from template
        """
        ll_templates.removeTemplateNic(
            positive=True, template=template, nic=vm_nic
        )
    request.addfinalizer(fin)

    multi_host.attach_network_to_host_nic(
        network=net, nic=multi_host.host_0_nics[1]
    )
    assert ll_templates.addTemplateNic(
        positive=True, template=conf.TEMPLATE_NAME[0], name=vm_nic,
        data_center=dc, network=net
    )


@pytest.fixture(scope="class")
def fixture_case_05(request, teardown_all_cases):
    """
    Attach network to host NIC
    """
    multi_host = MultiHost()
    net = request.node.cls.net
    multi_host.attach_network_to_host_nic(
        network=net, nic=multi_host.host_0_nics[1], hosts=conf.HOSTS_LIST
    )


@pytest.fixture(scope="class")
def fixture_case_06(request, teardown_all_cases):
    """
    Attach network to host NIC
    Create new cluster
    Move host to new cluster
    """
    multi_host = MultiHost()
    net = request.node.cls.net
    dc = request.node.cls.dc
    cl = request.node.cls.cl
    cpu = request.node.cls.cpu
    version = request.node.cls.version
    cl_name2 = request.node.cls.cl_name2

    def fin2():
        """
        Remove extra cluster
        """
        ll_clusters.removeCluster(positive=True, cluster=cl_name2)
    request.addfinalizer(fin2)

    def fin1():
        """
        Move host back to original cluster
        """
        hl_hosts.move_host_to_another_cluster(
            host=multi_host.host_1_name, cluster=cl
        )
    request.addfinalizer(fin1)

    assert ll_clusters.addCluster(
        positive=True, name=cl_name2, cpu=cpu, data_center=dc, version=version
    )
    assert ll_networks.add_network_to_cluster(
        positive=True, network=net,cluster=cl_name2, required=False
    )
    assert hl_hosts.move_host_to_another_cluster(
        host=multi_host.host_1_name, cluster=cl_name2
    )
    multi_host.attach_network_to_host_nic(
        network=net, nic=multi_host.host_0_nics[1], hosts=conf.HOSTS_LIST
    )


@pytest.fixture(scope="class")
def fixture_case_07(request, teardown_all_cases):
    """
    Attach network to host NIC
    """
    multi_host = MultiHost()
    net = request.node.cls.net
    slaves = conf.DUMMYS[:2]
    bond = request.node.cls.bond

    multi_host.attach_network_to_host_nic(network=net, nic=bond, slaves=slaves)
