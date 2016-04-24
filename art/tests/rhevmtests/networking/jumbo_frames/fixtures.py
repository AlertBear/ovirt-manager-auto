#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for jumbo frame
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.helper as network_helper
import rhevmtests.networking.config as conf
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
from art.rhevm_api.utils import test_utils
import helper
import rhevmtests.networking.jumbo_frames.config as jumbo_conf
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


class JumboFrame(NetworkFixtures):
    """
    Fixtures for jumbo frame
    """
    def __init__(self):
        super(JumboFrame, self).__init__()
        self.vms_list = [self.vm_0, self.vm_1]
        self.hosts_list = [self.host_0_name, self.host_1_name]
        self.host_nics_list = [self.host_0_nics, self.host_1_nics]


@pytest.fixture(scope="module")
def prepare_setup_jumbo_frame(request, network_cleanup_fixture):
    """
    Prepare setup for jumbo frame test
    """
    jumbo_frame = JumboFrame()

    def fin3():
        """
        Finalizer for remove networks from setup
        """
        hl_networks.remove_net_from_setup(
            host=jumbo_frame.hosts_list, data_center=jumbo_frame.dc_0,
            mgmt_network=jumbo_frame.mgmt_bridge, all_net=True
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Finalizer for stop VMs
        """
        ll_vms.stopVms(vms=jumbo_frame.vms_list)
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for clean hosts interfaces
        """
        network_dict = {
            "1": {
                "network": "clear_net_1",
                "nic": None
            },
            "2": {
                "network": "clear_net_1",
                "nic": None
            },
            "3": {
                "network": "clear_net_1",
                "nic": None
            }
        }

        for host, nics in zip(
            jumbo_frame.hosts_list, jumbo_frame.host_nics_list
        ):
            network_dict["1"]["nic"] = nics[1]
            network_dict["2"]["nic"] = nics[2]
            network_dict["3"]["nic"] = nics[3]
            hl_host_network.setup_networks(host_name=host, **network_dict)
            hl_host_network.clean_host_interfaces(host_name=host)
    request.addfinalizer(fin1)

    jumbo_frame.prepare_networks_on_setup(
        networks_dict=jumbo_conf.NETS_DICT, dc=jumbo_frame.dc_0,
        cluster=jumbo_frame.cluster_0
    )
    for vm, host in zip(jumbo_frame.vms_list, jumbo_frame.hosts_list):
        assert network_helper.run_vm_once_specific_host(
            vm=vm, host=host, wait_for_up_status=True
        )


@pytest.fixture(scope="class")
def teardown_all_cases(request, prepare_setup_jumbo_frame):
    """
    Teardown for all cases
    """
    def fin():
        """
        Finalizer for restore MTU on hosts
        """
        helper.restore_mtu_and_clean_interfaces()
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def fixture_case_01(request, teardown_all_cases):
    """
    Fixture for case01
    """
    jumbo_frame = JumboFrame()
    net = jumbo_conf.NETS[1][0]
    network_dict = {
        "add": {
            "1": {
                "network": net,
                "nic": jumbo_frame.host_0_nics[1]
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=jumbo_frame.host_0_name, **network_dict
    )


@pytest.fixture(scope="class")
def fixture_case_02(request, teardown_all_cases):
    """
    Fixture for case02
    """
    jumbo_frame = JumboFrame()
    net_1 = jumbo_conf.NETS[2][0]
    net_2 = jumbo_conf.NETS[2][1]
    network_dict = {
        "add": {
            "1": {
                "network": net_1,
                "nic": jumbo_frame.host_0_nics[1]
            },
            "2": {
                "network": net_2,
                "nic": jumbo_frame.host_0_nics[1]
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=jumbo_frame.host_0_name, **network_dict
    )


@pytest.fixture(scope="class")
def fixture_case_03(request, teardown_all_cases):
    """
    Fixture for case03
    """
    jumbo_frame = JumboFrame()
    net = jumbo_conf.NETS[3][0]
    mtu_5000 = conf.MTU[1]
    bond = "bond3"
    ips = network_helper.create_random_ips(num_of_ips=4, mask=24)
    jumbo_conf.CASE_3_IPS = ips

    def fin():
        """
        Finalizer for remove NICs from VMs
        """
        helper.remove_vnics_from_vms()
    request.addfinalizer(fin)

    network_dict = {
        "add": {
            "1": {
                "network": net,
                "nic": bond,
                "slaves": None,
                "ip": {
                    "1": {
                        "address": None,
                        "netmask": "24",
                        "boot_protocol": "static"
                    }
                }
            },
        }
    }

    for host, nics, ip in zip(
        jumbo_frame.hosts_list,
        jumbo_frame.host_nics_list,
        ips[2:]
    ):
        network_dict["add"]["1"]["slaves"] = nics[2:4]
        network_dict["add"]["1"]["ip"]["1"]["address"] = ip
        assert hl_host_network.setup_networks(host_name=host, **network_dict)

    assert helper.add_vnics_to_vms(ips=ips[:2], network=net, mtu=mtu_5000)


@pytest.fixture(scope="class")
def fixture_case_04(request, teardown_all_cases):
    """
    Fixture for case04
    """
    jumbo_frame = JumboFrame()
    ips = network_helper.create_random_ips(mask=24)
    bond = "bond12"
    net_1 = jumbo_conf.NETS[4][0]
    net_2 = jumbo_conf.NETS[4][1]
    net_3 = jumbo_conf.NETS[4][2]
    net_4 = jumbo_conf.NETS[4][3]
    vnic = conf.NIC_NAME[2]
    mtu_9000 = conf.MTU[0]
    mtu_5000 = str(conf.MTU[1])
    jumbo_conf.CASE_4_IPS = ips

    def fin2():
        """
        Finalizer for remove NICs from VMs
        """
        helper.remove_vnics_from_vms(nic_name=vnic)
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for remove NICs from VMs
        """
        helper.remove_vnics_from_vms()
    request.addfinalizer(fin1)

    network_dict = {
        "add": {
            "1": {
                "network": net_1,
                "nic": bond,
                "slaves": None,
            },
            "2": {
                "network": net_2,
                "nic": bond,
                "ip": {
                    "1": {
                        "address": None,
                        "netmask": "24",
                        "boot_protocol": "static"
                    }
                }
            },
            "3": {
                "network": net_3,
                "nic": bond,
            },
            "4": {
                "network": net_4,
                "nic": bond,
            },
        }
    }
    for host, nics, ip in zip(
        jumbo_frame.hosts_list,
        jumbo_frame.host_nics_list,
        ips
    ):
        network_dict["add"]["1"]["slaves"] = nics[2:4]
        network_dict["add"]["2"]["ip"]["1"]["address"] = ip
        assert hl_host_network.setup_networks(host_name=host, **network_dict)

    assert helper.add_vnics_to_vms(ips=ips, mtu=str(mtu_9000), network=net_2)
    assert helper.add_vnics_to_vms(
        ips=ips, mtu=mtu_5000, nic_name=vnic, network=net_1, set_ip=False
    )


@pytest.fixture(scope="class")
def fixture_case_05(request, teardown_all_cases):
    """
    Fixture for case05
    """
    jumbo_frame = JumboFrame()
    ips = network_helper.create_random_ips(num_of_ips=4, mask=24)
    net = jumbo_conf.NETS[5][0]
    mtu_5000 = str(conf.MTU[1])
    jumbo_conf.CASE_5_IPS = ips

    def fin2():
        """
        Finalizer for update network on cluster
        """
        ll_networks.update_cluster_network(
            positive=True, cluster=jumbo_frame.cluster_0,
            network=jumbo_frame.mgmt_bridge,
            usages="display,vm,migration,management"
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for remove NICs from VMs
        """
        helper.remove_vnics_from_vms()
    request.addfinalizer(fin1)

    assert ll_networks.update_cluster_network(
        positive=True, cluster=jumbo_frame.cluster_0, network=net,
        usages='display,vm'
    )

    network_dict = {
        "add": {
            "1": {
                "network": net,
                "nic": None,
                "ip": {
                    "1": {
                        "address": None,
                        "netmask": "24",
                        "boot_protocol": "static"
                    }
                }
            }
        }
    }
    for host, nics, ip in zip(
        jumbo_frame.hosts_list,
        jumbo_frame.host_nics_list,
        ips[2:]
    ):
        network_dict["add"]["1"]["ip"]["1"]["address"] = ip
        network_dict["add"]["1"]["nic"] = nics[1]
        assert hl_host_network.setup_networks(host_name=host, **network_dict)
    assert helper.add_vnics_to_vms(ips=ips[:2], mtu=mtu_5000, network=net)


@pytest.fixture(scope="class")
def fixture_case_07(request, teardown_all_cases):
    """
    Fixture for case07
    """
    jumbo_frame = JumboFrame()
    net_1 = jumbo_conf.NETS[7][0]
    net_2 = jumbo_conf.NETS[7][1]
    mtu_5000 = conf.MTU[1]
    ips = network_helper.create_random_ips(mask=24)
    jumbo_conf.CASE_7_IPS = ips

    def fin():
        """
        Finalizer for remove NICs from VMs
        """
        helper.remove_vnics_from_vms()
    request.addfinalizer(fin)

    network_dict = {
        "add": {
            "1": {
                "network": net_1,
                "nic": None,
            },
            "2": {
                "network": net_2,
                "nic": None
            }
        }
    }

    for host, nics in zip(
        jumbo_frame.hosts_list,
        jumbo_frame.host_nics_list
    ):
        network_dict["add"]["1"]["nic"] = nics[1]
        network_dict["add"]["2"]["nic"] = nics[1]
        assert hl_host_network.setup_networks(host_name=host, **network_dict)
    assert helper.add_vnics_to_vms(ips=ips, network=net_1, mtu=mtu_5000)


@pytest.fixture(scope="class")
def fixture_case_08(request, teardown_all_cases):
    """
    Fixture for case08
    """
    jumbo_frame = JumboFrame()
    net_1 = jumbo_conf.NETS[8][0]
    bond = "bond8"

    network_dict = {
        "add": {
            "1": {
                "network": net_1,
                "nic": bond,
                "slaves": jumbo_frame.host_0_nics[2:4]
            }
        }
    }

    assert hl_host_network.setup_networks(
        host_name=jumbo_frame.host_0_name, **network_dict
    )


@pytest.fixture(scope="class")
def fixture_case_09(request, teardown_all_cases):
    """
    Fixture for case09
    """
    jumbo_frame = JumboFrame()
    mtu_2000 = str(conf.MTU[2])
    net = jumbo_conf.NETS[9][0]

    assert test_utils.configure_temp_mtu(
        vds_resource=jumbo_frame.vds_0_host, mtu=mtu_2000,
        nic=jumbo_frame.host_0_nics[1]
    )
    network_dict = {
        "add": {
            "1": {
                "network": net,
                "nic": jumbo_frame.host_0_nics[1],
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=jumbo_frame.host_0_name, **network_dict
    )
