#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for sanity
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as sanity_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
import rhevmtests.networking.mac_pool_range_per_dc.helper as mac_pool_helper
import rhevmtests.networking.required_network.helper as required_network_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def create_networks(request):
    """
    Create networks
    """
    sanity = NetworkFixtures()

    def fin1():
        """
        Remove networks from setup
        """
        sanity.remove_networks_from_setup(hosts=sanity.host_0_name)
    request.addfinalizer(fin1)

    sanity.prepare_networks_on_setup(
        networks_dict=sanity_conf.SN_DICT, dc=sanity.dc_0,
        cluster=sanity.cluster_0
    )


@pytest.fixture(scope="module")
def create_dummies(request):
    """
    Create dummies
    """
    sanity = NetworkFixtures()

    def fin2():
        """
        Remove dummies from host
        """
        sanity.remove_dummies(host_resource=sanity.vds_0_host)
    request.addfinalizer(fin2)

    sanity.prepare_dummies(host_resource=sanity.vds_0_host, num_dummy=20)


@pytest.fixture(scope="class")
def clean_host_interfaces(request):
    """
    Clean host interfaces
    """
    sanity = NetworkFixtures()

    def fin():
        """
        Clean host interfaces
        """
        hl_host_network.clean_host_interfaces(host_name=sanity.host_0_name)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def attach_networks(request):
    """
    Attach networks to host NICs
    """
    sanity = NetworkFixtures()
    nets = request.node.cls.nets
    nic = request.node.cls.nic
    ip_addr_dict = request.node.cls.ip_addr_dict
    bond = request.node.cls.bond

    sn_dict = {
        "add": {}
    }
    if not nets:
        sn_dict["add"]["1"] = {
            "slaves": sanity_conf.DUMMYS[:2],
            "nic": bond
        }
    else:
        for net in nets:
            sn_dict["add"][net] = {
                "network": net,
                "nic": sanity.vds_0_host.nics[nic],
            }
            if ip_addr_dict:
                sn_dict["add"][net]["ip"] = ip_addr_dict

    assert hl_host_network.setup_networks(
        host_name=sanity.host_0_name, **sn_dict
    )


@pytest.fixture(scope="class")
def add_vnic_profile(request):
    """
    Add vNIC profile
    """
    NetworkFixtures()
    vnic_profile = request.node.cls.vnic_profile
    dc = request.node.cls.dc
    net = request.node.cls.net
    description = request.node.cls.description

    def fin():
        """
        Remove vNIC profile
        """
        ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=vnic_profile, network=net
        )
    request.addfinalizer(fin)

    assert ll_networks.add_vnic_profile(
        positive=True, name=vnic_profile, data_center=dc,
        network=net, port_mirroring=True, description=description
    )


@pytest.fixture(scope="class")
def remove_qos(request):
    """
    Remove QoS from setup
    """
    NetworkFixtures()
    qos_name = request.node.cls.qos_name

    def fin():
        """
        Remove QoS from setup
        """
        network_helper.remove_qos_from_dc(qos_name=qos_name)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def start_vm(request):
    """
    Start VM
    """
    NetworkFixtures()
    vm = request.node.cls.vm

    def fin():
        """
        Stop VM
        """
        ll_vms.stopVm(positive=True, vm=vm)
    request.addfinalizer(fin)

    assert network_helper.run_vm_once_specific_host(
        vm=vm, host=conf.HOST_0_NAME, wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def case_06_fixture(request):
    """
    Create 5 VNICs on VM with different params for plugged/linked
    """
    NetworkFixtures()
    nets = request.node.cls.nets
    vm = request.node.cls.vm

    def fin():
        """
        Remove vNICs from VM
        """
        for nic in conf.NIC_NAME[1:6]:
            ll_vms.removeNic(positive=True, vm=vm, nic=nic)
    request.addfinalizer(fin)

    plug_link_param_list = [
        ("true", "true"),
        ("true", "false"),
        ("false", "true"),
        ("false", "false")
    ]
    for i in range(len(plug_link_param_list)):
        nic_name = conf.NIC_NAME[i+1]
        assert ll_vms.addNic(
            positive=True, vm=vm, name=nic_name,
            network=nets[i], plugged=plug_link_param_list[i][0],
            linked=plug_link_param_list[i][1]
        )

    assert ll_vms.addNic(
        positive=True, vm=vm, name=conf.NIC_NAME[5], network=None,
        plugged="true", linked="true"
    )


@pytest.fixture(scope="class")
def case_07_fixture(request):
    """
    Create new datacenter
    """
    NetworkFixtures()
    ext_dc = request.node.cls.ext_dc

    def fin():
        """
        Remove datacenter
        """
        ll_dc.remove_datacenter(positive=True, datacenter=ext_dc)
    request.addfinalizer(fin)

    mac_pool_helper.create_dc(mac_pool_name="")


@pytest.fixture(scope="class")
def case_08_fixture(request):
    """
    Create new datacenter
    Add network to datacenter
    """
    NetworkFixtures()
    dc = request.node.cls.dc
    cluster_1 = request.node.cls.cluster_1
    cluster_2 = request.node.cls.cluster_2
    net = request.node.cls.net

    def fin2():
        """
        Remove datacenter
        """
        ll_dc.remove_datacenter(positive=True, datacenter=dc)
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove clusters
        """
        for cl in (cluster_1, cluster_2):
            ll_clusters.removeCluster(positive=True, cluster=cl)
    request.addfinalizer(fin1)

    net_dict = {
        net: {
            "required": "true",
        }
    }
    assert hl_networks.create_basic_setup(
        datacenter=dc, version=conf.COMP_VERSION,
        storage_type=conf.STORAGE_TYPE, cpu=conf.CPU_NAME
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=net_dict, dc=dc,
    )


@pytest.fixture(scope="class")
def update_vnic_profile(request):
    """
    Update vNIC profile with queue
    """
    NetworkFixtures()
    dc = request.node.cls.dc
    prop_queue = request.node.cls.prop_queue
    mgmt_bridge = request.node.cls.mgmt_bridge

    def fin():
        """
        Remove queue from vNIC profile
        """
        ll_networks.update_vnic_profile(
            name=mgmt_bridge, network=mgmt_bridge,
            data_center=dc, custom_properties="clear"
        )
    request.addfinalizer(fin)

    assert ll_networks.update_vnic_profile(
        name=mgmt_bridge, network=mgmt_bridge,
        data_center=dc, custom_properties=prop_queue
    )


@pytest.fixture(scope="class")
def add_labels(request):
    """
    Add labels
    """
    NetworkFixtures()
    labels = request.node.cls.labels
    bond = request.node.cls.bond

    def fin():
        """
        Remove labels
        """
        ll_networks.remove_label(
            host_nic_dict={
                conf.HOST_0_NAME: [bond]
            }
        )
    request.addfinalizer(fin)

    for lb, nets in labels.iteritems():
        assert ll_networks.add_label(label=lb, networks=nets)


@pytest.fixture(scope="class")
def deactivate_hosts(request):
    """
    Deactivate hosts
    """
    sanity = NetworkFixtures()

    def fin():
        """
        Activate hosts
        """
        required_network_helper.activate_hosts()
    request.addfinalizer(fin)

    assert required_network_helper.deactivate_hosts(host=sanity.host_0_name)


@pytest.fixture(scope="class")
def set_host_nic_down(request):
    """
    Set host NIC down
    """
    sanity = NetworkFixtures()

    def fin():
        """
        Set host NIC up
        """
        sanity.vds_0_host.network.if_up(nic=sanity.host_0_nics[1])
    request.addfinalizer(fin)

    assert sanity.vds_0_host.network.if_down(nic=sanity.host_0_nics[1])
