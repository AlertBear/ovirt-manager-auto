#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for host_network_api
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.host_network as ll_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import config as hna_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.rhevm_api.utils import test_utils
from rhevmtests.networking.fixtures import (
    network_cleanup_fixture, NetworkFixtures
)  # flake8: noqa


class HostNetworkApi(NetworkFixtures):
    """
    Fixture for host_network_api
    """
    def attach_net_to_host_nic(self, network):
        """
        Attach network to host NIC

        Args:
            network (str): Network name
        """
        network_dict = {
            "network": network
        }
        assert helper.attach_network_attachment(
            host_nic=self.host_0_nics[1], **network_dict
        )

    def attach_net_to_host(self, network, nic):
        """
        Attach network to host NIC

        Args:
            network (str): Network name
            nic (str): NIC name
        """
        network_dict = {
            "network": network,
            "nic": nic
        }
        assert helper.attach_network_attachment(**network_dict)


#  Prepare setup for all host_network_api modules
@pytest.fixture(scope="module")
def host_network_api_prepare_setup(request, network_cleanup_fixture):
    """
    Prepare setup for all modules
    """
    hna = HostNetworkApi()

    def fin2():
        """
        Finalizer for activate host
        """
        hl_hosts.activate_host_if_not_up(hna.host_0_name)
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for remove dummies
        """
        hna.remove_dummies(host_resource=hna.vds_0_host)
    request.addfinalizer(fin1)

    hna.prepare_dummies(
        host_resource=hna.vds_0_host, num_dummy=hna_conf.NUM_DUMMYS
    )


#  Prepare setup for host_nic_test module
@pytest.fixture(scope="module")
def host_nic_api_prepare_setup(request, host_network_api_prepare_setup):
    """
    Prepare setup for host_nic tests
    """
    hna = HostNetworkApi()

    def fin():
        """
        Finalizer for remove networks from setup
        """
        hna.remove_networks_from_setup(hosts=hna.host_0_name)
    request.addfinalizer(fin)

    hna.prepare_networks_on_setup(
        networks_dict=hna_conf.NIC_DICT, dc=hna.dc_0, cluster=hna.cluster_0
    )


#  Teardown for all host_nic_test cases
@pytest.fixture(scope="class")
def teardown_all_cases_host_nic(request, host_nic_api_prepare_setup):
    """
    Teardown for all host_nic cases
    """
    def fin():
        """
        Finalizer for remove networks from host
        """
        network_helper.remove_networks_from_host()
    request.addfinalizer(fin)


#  Fixture for host_nic
@pytest.fixture(scope="class")
def host_nic_case_08(request, teardown_all_cases_host_nic):
    """
    Fixture for host_nic case08
    """
    hna = HostNetworkApi()
    hna.attach_net_to_host_nic(network=hna_conf.NIC_NETS[8][0])


#  Fixture for host_nic
@pytest.fixture(scope="class")
def host_nic_case_09(request, teardown_all_cases_host_nic):
    """
    Fixture for host_nic case09
    """
    hna = HostNetworkApi()
    hna.attach_net_to_host_nic(network=hna_conf.NIC_NETS[9][0])


#  Fixture for host_nic
@pytest.fixture(scope="class")
def host_nic_case_10(request, teardown_all_cases_host_nic):
    """
    Fixture for host_nic case10
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "network": hna_conf.NIC_NETS[10][0],
                "nic": hna.host_0_nics[1]
            },
            "2": {
                "network": hna_conf.NIC_NETS[10][1],
                "nic": hna.host_0_nics[2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for host_nic
@pytest.fixture(scope="class")
def host_nic_case_11(request, teardown_all_cases_host_nic):
    """
    Fixture for host_nic case11
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "nic": "bond11",
                "slaves": hna_conf.DUMMYS[:2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for host_nic
@pytest.fixture(scope="class")
def host_nic_case_12(request, teardown_all_cases_host_nic):
    """
    Fixture for host_nic case12
    """
    hna = HostNetworkApi()
    bond = "bond12"
    sn_dict = {
        "add": {
            "1": {
                "nic": bond,
                "slaves": hna_conf.DUMMYS[:2]
            },
            "2": {
                "nic": bond,
                "network": hna_conf.NIC_NETS[12][0]
            },
            "3": {
                "nic": bond,
                "network": hna_conf.NIC_NETS[12][1]
            },
            "4": {
                "nic": bond,
                "network": hna_conf.NIC_NETS[12][2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for host_nic
@pytest.fixture(scope="class")
def host_nic_case_15(request, teardown_all_cases_host_nic):
    """
    Fixture for host_nic case15
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "nic": "bond15",
                "slaves": hna_conf.DUMMYS[:2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Prepare setup for host_test module
@pytest.fixture(scope="module")
def host_api_prepare_setup(request, host_network_api_prepare_setup):
    """
    Prepare setup for host tests
    """
    hna = HostNetworkApi()

    def fin():
        """
        Finalizer for remove networks from setup
        """
        hna.remove_networks_from_setup(hosts=hna.host_0_name)
    request.addfinalizer(fin)

    hna.prepare_networks_on_setup(
        networks_dict=hna_conf.HOST_DICT, dc=hna.dc_0, cluster=hna.cluster_0
    )


#  Teardown for all host_test cases
@pytest.fixture(scope="class")
def teardown_all_cases_host(request, host_api_prepare_setup):
    """
    Teardown for all host cases
    """
    def fin():
        """
        Finalizer for remove networks from host
        """
        network_helper.remove_networks_from_host()
    request.addfinalizer(fin)


#  Fixture for host
@pytest.fixture(scope="class")
def host_case_08(request, teardown_all_cases_host):
    """
    Fixture for host case08
    """
    hna = HostNetworkApi()
    hna.attach_net_to_host(
        network=hna_conf.HOST_NETS[8][0], nic=hna.host_0_nics[1]
    )


#  Fixture for host
@pytest.fixture(scope="class")
def host_case_09(request, teardown_all_cases_host):
    """
    Fixture for host case09
    """
    hna = HostNetworkApi()
    hna.attach_net_to_host(
        network=hna_conf.HOST_NETS[9][0], nic=hna.host_0_nics[1]
    )


#  Fixture for host
@pytest.fixture(scope="class")
def host_case_10(request, teardown_all_cases_host):
    """
    Fixture for host case10
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "network": hna_conf.HOST_NETS[10][0],
                "nic": hna.host_0_nics[1]
            },
            "2": {
                "network": hna_conf.HOST_NETS[10][1],
                "nic": hna.host_0_nics[2]
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=hna.host_0_name, **sn_dict
    )


#  Fixture for host
@pytest.fixture(scope="class")
def host_case_11(request, teardown_all_cases_host):
    """
    Fixture for host case11
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "nic": "bond11",
                "slaves": hna_conf.DUMMYS[:2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for host
@pytest.fixture(scope="class")
def host_case_12(request, teardown_all_cases_host):
    """
    Fixture for host case12
    """
    hna = HostNetworkApi()
    bond = "bond12"
    sn_dict = {
        "add": {
            "1": {
                "nic": bond,
                "slaves": hna_conf.DUMMYS[:2]
            },
            "2": {
                "nic": bond,
                "network": hna_conf.HOST_NETS[12][0]
            },
            "3": {
                "nic": bond,
                "network": hna_conf.HOST_NETS[12][1]
            },
            "4": {
                "nic": bond,
                "network": hna_conf.HOST_NETS[12][2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for host
@pytest.fixture(scope="class")
def host_case_13(request, teardown_all_cases_host):
    """
    Fixture for host case13
    """
    hna = HostNetworkApi()
    network_dict = {
        "unman_net_13": {
            "required": "false"
        }
    }
    assert hl_networks.createAndAttachNetworkSN(
        data_center=hna.dc_0, cluster=hna.cluster_0, network_dict=network_dict
    )
    network_host_api_dict = {
        "network": "unman_net_13",
        "nic": hna.host_0_nics[1]
    }
    helper.attach_network_attachment(**network_host_api_dict)
    assert ll_networks.removeNetwork(
        positive=True, network="unman_net_13", data_center=hna.dc_0
    )
    assert ll_host_network.get_host_unmanaged_networks(
        host_name=hna.host_0_name, networks=["unman_net_13"]
    )


#  Fixture for host
@pytest.fixture(scope="class")
def host_case_16(request, teardown_all_cases_host):
    """
    Fixture for host case16
    """
    hna = HostNetworkApi()
    network_dict = {
        "unman_host16": {
            "required": "false"
        }
    }
    assert hl_networks.createAndAttachNetworkSN(
        data_center=hna.dc_0, cluster=hna.cluster_0, network_dict=network_dict
    )
    sn_dict = {
        "add": {
            "1": {
                "nic": "bond16",
                "slaves": hna_conf.DUMMYS[:2]
            },
            "2": {
                "nic": "bond16",
                "network": "unman_host16"
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_networks.removeNetwork(
        positive=True, network="unman_host16", data_center=hna.dc_0
    )
    assert ll_host_network.get_host_unmanaged_networks(
        host_name=hna.host_0_name, networks=["unman_host16"]
    )


#  Fixture for host
@pytest.fixture(scope="class")
def host_case_17(request, teardown_all_cases_host):
    """
    Fixture for host case17
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "nic": "bond17",
                "slaves": hna_conf.DUMMYS[:2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for host
@pytest.fixture(scope="class")
def host_case_18(request, teardown_all_cases_host):
    """
    Fixture for host case18
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "nic": hna.host_0_nics[1],
                "network": hna_conf.HOST_NETS[18][0]
            },
            "2": {
                "nic": hna.host_0_nics[2],
                "network": hna_conf.HOST_NETS[18][1]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Prepare setup for host_test module
@pytest.fixture(scope="module")
def sn_prepare_setup(request, host_network_api_prepare_setup):
    """
    Prepare setup for sn tests
    """
    hna = HostNetworkApi()

    def fin():
        """
        Finalizer for remove networks from setup
        """
        hna.remove_networks_from_setup(hosts=hna.host_0_name)
    request.addfinalizer(fin)

    hna.prepare_networks_on_setup(
        networks_dict=hna_conf.SN_DICT, dc=hna.dc_0, cluster=hna.cluster_0
    )


#  Teardown for all setupnetworks_test cases
@pytest.fixture(scope="class")
def teardown_all_cases_sn(request, sn_prepare_setup):
    """
    Teardown for all sn cases
    """
    def fin():
        """
        Finalizer for remove networks from host
        """
        network_helper.remove_networks_from_host()
    request.addfinalizer(fin)


#  Fixture for sn
@pytest.fixture(scope="class")
def sn_case_09(request, teardown_all_cases_sn):
    """
    Fixture for sn case09
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "network": hna_conf.SN_NETS[9][0],
                "nic": hna.host_0_nics[1]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for sn
@pytest.fixture(scope="class")
def sn_case_10(request, teardown_all_cases_sn):
    """
    Fixture for sn case10
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "network": hna_conf.SN_NETS[10][0],
                "nic": hna.host_0_nics[1]
            },
            "2": {
                "network": hna_conf.SN_NETS[10][1],
                "nic": hna.host_0_nics[2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for sn
@pytest.fixture(scope="class")
def sn_case_11(request, teardown_all_cases_sn):
    """
    Fixture for sn case11
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "nic": "bond11",
                "slaves": hna_conf.DUMMYS[:2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for sn
@pytest.fixture(scope="class")
def sn_case_15(request, teardown_all_cases_sn):
    """
    Fixture for sn case15
    """
    hna = HostNetworkApi()
    bond = "bond15"
    sn_dict = {
        "add": {
            "1": {
                "nic": bond,
                "slaves": hna_conf.DUMMYS[:2]
            },
            "2": {
                "network": hna_conf.SN_NETS[15][0],
                "nic": bond
            },
            "3": {
                "nic": bond,
                "network": hna_conf.SN_NETS[15][1]
            },
            "4": {
                "nic": bond,
                "network": hna_conf.SN_NETS[15][2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for sn
@pytest.fixture(scope="class")
def sn_case_16(request, teardown_all_cases_sn):
    """
    Fixture for sn case16
    """
    hna = HostNetworkApi()
    unmamanged_net = "unman_sn_16"
    bond = "bond16"
    network_dict = {
        unmamanged_net: {
            "required": "false"
        }
    }
    assert hl_networks.createAndAttachNetworkSN(
        data_center=hna.dc_0, cluster=hna.cluster_0, network_dict=network_dict
    )
    sn_dict = {
        "add": {
            "1": {
                "nic": bond,
                "slaves": hna_conf.DUMMYS[:2]
            },
            "2": {
                "nic": bond,
                "network": unmamanged_net
            }
        }
    }

    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_networks.removeNetwork(
        positive=True, network=unmamanged_net, data_center=hna.dc_0
    )
    assert ll_host_network.get_host_unmanaged_networks(
        host_name=hna.host_0_name, networks=[unmamanged_net]
    )


#  Fixture for sn
@pytest.fixture(scope="class")
def sn_case_17(request, teardown_all_cases_sn):
    """
    Fixture for sn case17
    """
    hna = HostNetworkApi()
    unmamanged_net = "unman_sn_17"

    network_dict = {
        unmamanged_net: {
            "required": "false"
        }
    }
    assert hl_networks.createAndAttachNetworkSN(
        data_center=hna.dc_0, cluster=hna.cluster_0, network_dict=network_dict
    )

    sn_dict = {
        "add": {
            "1": {
                "nic": hna.host_0_nics[1],
                "network": unmamanged_net
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_networks.removeNetwork(
        positive=True, network=unmamanged_net, data_center=hna.dc_0
    )
    assert ll_host_network.get_host_unmanaged_networks(
        host_name=hna.host_0_name, networks=[unmamanged_net]
    )


#  Fixture for sn
@pytest.fixture(scope="class")
def sn_case_24(request, teardown_all_cases_sn):
    """
    Fixture for sn case24
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "nic": "bond281",
                "slaves": hna_conf.DUMMYS[:2]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for sn
@pytest.fixture(scope="class")
def sn_case_25(request, teardown_all_cases_sn):
    """
    Fixture for sn case25
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "nic": hna.host_0_nics[1],
                "network": hna_conf.SN_NETS[25][0]
            },
            "2": {
                "nic": hna.host_0_nics[2],
                "network": hna_conf.SN_NETS[25][1]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Fixture for sn
@pytest.fixture(scope="class")
def sn_case_26(request, teardown_all_cases_sn):
    """
    Fixture for sn case26
    """
    hna = HostNetworkApi()
    net_case_pre_vm = hna_conf.SN_NETS[26][0]
    net_case_pre_vlan = hna_conf.SN_NETS[26][1]
    bond_1 = "bond261"
    bond_2 = "bond262"
    bond_3 = "bond263"
    dummys_1 = hna_conf.DUMMYS[:2]
    dummys_2 = hna_conf.DUMMYS[2:4]
    dummys_3 = hna_conf.DUMMYS[4:6]

    sn_dict = {
        "add": {
            "1": {
                "nic": bond_1,
                "slaves": dummys_1
            },
            "2": {
                "nic": bond_2,
                "slaves": dummys_2
            },
            "3": {
                "nic": bond_3,
                "slaves": dummys_3
            },
            "4": {
                "nic": bond_1,
                "network": net_case_pre_vm
            },
            "5": {
                "nic": bond_2,
                "network": net_case_pre_vlan
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)


#  Prepare setup for sync_test module
@pytest.fixture(scope="module")
def sync_prepare_setup(request, host_network_api_prepare_setup):
    """
    Prepare setup for sync tests
    """
    hna = HostNetworkApi()

    def fin3():
        """
        Finalizer for activate host
        """
        ll_hosts.activateHost(positive=True, host=hna.host_0_name)
    request.addfinalizer(fin3)

    def fin2():
        """
        Finalizer for remove networks
        """
        hl_networks.remove_net_from_setup(
            host=hna.host_0_name, all_net=True, mgmt_network=hna.mgmt_bridge
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for remove basic setup
        """
        hl_networks.remove_basic_setup(
            datacenter=hna_conf.SYNC_DC, cluster=hna_conf.SYNC_CL
        )
    request.addfinalizer(fin1)

    assert hl_networks.create_basic_setup(
        datacenter=hna_conf.SYNC_DC, storage_type=conf.STORAGE_TYPE,
        version=conf.COMP_VERSION, cluster=hna_conf.SYNC_CL,
        cpu=conf.CPU_NAME
    )

    hna.prepare_networks_on_setup(
        networks_dict=hna_conf.SYNC_DICT_1, dc=hna.dc_0, cluster=hna.cluster_0
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=hna_conf.SYNC_DICT_2, dc=hna_conf.SYNC_DC,
        cluster=hna_conf.SYNC_CL
    )
    assert ll_hosts.deactivateHost(positive=True, host=hna.host_0_name)


#  Teardown for all sync_test cases
@pytest.fixture(scope="class")
def teardown_all_cases_sync(request, sync_prepare_setup):
    """
    Teardown for all sync cases
    """
    hna = HostNetworkApi()

    def fin2():
        """
        Finalizer for move host
        """
        if request.cls.move_host:
            ll_hosts.updateHost(
                positive=True, host=hna.host_0_name, cluster=hna.cluster_0
            )
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for remove networks from host
        """
        network_helper.remove_networks_from_host()
    request.addfinalizer(fin1)


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_01(request, teardown_all_cases_sync):
    """
    Fixture for sync case01
    """
    hna = HostNetworkApi()
    sn_dict = {
        "add": {
            "1": {
                "network": hna_conf.SYNC_NETS_DC_1[1][0],
                "nic": hna.host_0_nics[1],
                "datacenter": hna.dc_0
            },
            "2": {
                "network": hna_conf.SYNC_NETS_DC_1[1][1],
                "nic": hna.host_0_nics[2],
                "datacenter": hna.dc_0
            },
            "3": {
                "network": hna_conf.SYNC_NETS_DC_1[1][2],
                "nic": hna.host_0_nics[3],
                "datacenter": hna.dc_0
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_hosts.updateHost(
        positive=True, host=hna.host_0_name, cluster=hna_conf.SYNC_CL
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_02(request, teardown_all_cases_sync):
    """
    Fixture for sync case02
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[2][0]
    net_case_2 = hna_conf.SYNC_NETS_DC_1[2][1]
    net_case_3 = hna_conf.SYNC_NETS_DC_1[2][2]
    bond_1 = "bond21"
    bond_2 = "bond22"
    bond_3 = "bond23"
    dummys_1 = hna_conf.DUMMYS[:2]
    dummys_2 = hna_conf.DUMMYS[2:4]
    dummys_3 = hna_conf.DUMMYS[4:6]

    sn_dict = {
        "add": {
            "1": {
                "nic": bond_1,
                "slaves": dummys_1
            },
            "2": {
                "nic": bond_2,
                "slaves": dummys_2
            },
            "3": {
                "nic": bond_3,
                "slaves": dummys_3
            },
            "4": {
                "network": net_case_1,
                "nic": bond_1,
                "datacenter": hna.dc_0
            },
            "5": {
                "network": net_case_2,
                "nic": bond_2,
                "datacenter": hna.dc_0
            },
            "6": {
                "network": net_case_3,
                "nic": bond_3,
                "datacenter": hna.dc_0
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_hosts.updateHost(
        positive=True, host=hna.host_0_name, cluster=hna_conf.SYNC_CL
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_03(request, teardown_all_cases_sync):
    """
    Fixture for sync case03
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[3][0]
    net_case_2 = hna_conf.SYNC_NETS_DC_1[3][1]
    net_case_3 = hna_conf.SYNC_NETS_DC_1[3][2]

    sn_dict = {
        "add": {
            "1": {
                "network": net_case_1,
                "nic": hna.host_0_nics[1],
                "datacenter": hna.dc_0
            },
            "2": {
                "network": net_case_2,
                "nic": hna.host_0_nics[2],
                "datacenter": hna.dc_0
            },
            "3": {
                "network": net_case_3,
                "nic": hna.host_0_nics[3],
                "datacenter": hna.dc_0
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_hosts.updateHost(
        positive=True, host=hna.host_0_name, cluster=hna_conf.SYNC_CL
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_04(request, teardown_all_cases_sync):
    """
    Fixture for sync case04
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[4][0]
    net_case_2 = hna_conf.SYNC_NETS_DC_1[4][1]
    net_case_3 = hna_conf.SYNC_NETS_DC_1[4][2]
    bond_1 = "bond31"
    bond_2 = "bond32"
    bond_3 = "bond33"
    dummys_1 = hna_conf.DUMMYS[:2]
    dummys_2 = hna_conf.DUMMYS[2:4]
    dummys_3 = hna_conf.DUMMYS[4:6]

    sn_dict = {
        "add": {
            "1": {
                "nic": bond_1,
                "slaves": dummys_1
            },
            "2": {
                "nic": bond_2,
                "slaves": dummys_2
            },
            "3": {
                "nic": bond_3,
                "slaves": dummys_3
            },
            "4": {
                "network": net_case_1,
                "nic": bond_1,
                "datacenter": hna.dc_0
            },
            "5": {
                "network": net_case_2,
                "nic": bond_2,
                "datacenter": hna.dc_0
            },
            "6": {
                "network": net_case_3,
                "nic": bond_3,
                "datacenter": hna.dc_0
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_hosts.updateHost(
        positive=True, host=hna.host_0_name, cluster=hna_conf.SYNC_CL
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_05(request, teardown_all_cases_sync):
    """
    Fixture for sync case05
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[5][0]
    net_case_2 = hna_conf.SYNC_NETS_DC_1[5][1]

    sn_dict = {
        "add": {
            "1": {
                "network": net_case_1,
                "nic": hna.host_0_nics[1],
                "datacenter": hna.dc_0
            },
            "2": {
                "network": net_case_2,
                "nic": hna.host_0_nics[2],
                "datacenter": hna.dc_0
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_hosts.updateHost(
        positive=True, host=hna.host_0_name, cluster=hna_conf.SYNC_CL
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_06(request, teardown_all_cases_sync):
    """
    Fixture for sync case06
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[6][0]
    net_case_2 = hna_conf.SYNC_NETS_DC_1[6][1]
    bond_1 = "bond61"
    bond_2 = "bond62"
    dummys_1 = hna_conf.DUMMYS[:2]
    dummys_2 = hna_conf.DUMMYS[2:4]

    sn_dict = {
        "add": {
            "1": {
                "nic": bond_1,
                "slaves": dummys_1
            },
            "2": {
                "nic": bond_2,
                "slaves": dummys_2
            },
            "3": {
                "network": net_case_1,
                "nic": bond_1,
                "datacenter": hna.dc_0
            },
            "4": {
                "network": net_case_2,
                "nic": bond_2,
                "datacenter": hna.dc_0
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_hosts.updateHost(
        positive=True, host=hna.host_0_name, cluster=hna_conf.SYNC_CL
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_07(request, teardown_all_cases_sync):
    """
    Fixture for sync case07
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[7][0]

    sn_dict = {
        "add": {
            "1": {
                "network": net_case_1,
                "nic": hna.host_0_nics[1],
                "datacenter": hna.dc_0
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_hosts.updateHost(
        positive=True, host=hna.host_0_name, cluster=hna_conf.SYNC_CL
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_08(request, teardown_all_cases_sync):
    """
    Fixture for sync case08
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[8][0]
    bond_1 = "bond81"
    dummys = hna_conf.DUMMYS[:2]

    sn_dict = {
        "add": {
            "1": {
                "nic": bond_1,
                "slaves": dummys
            },
            "2": {
                "network": net_case_1,
                "nic": bond_1,
                "datacenter": hna.dc_0
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_hosts.updateHost(
        positive=True, host=hna.host_0_name, cluster=hna_conf.SYNC_CL
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_09(request, teardown_all_cases_sync):
    """
    Fixture for sync case09
    """
    hna = HostNetworkApi()
    ip_netmask = hna_conf.IPS[37]
    net_case_1 = hna_conf.SYNC_NETS_DC_1[9][0]
    net_case_1_ip_actual = "10.10.10.10"

    hna_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = ip_netmask
    sn_dict = {
        "add": {
            "1": {
                "network": net_case_1,
                "nic": hna.host_0_nics[1],
                "ip": hna_conf.BASIC_IP_DICT_NETMASK,
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    helper.manage_ip_and_refresh_capabilities(
        ip=net_case_1_ip_actual, interface=net_case_1
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_10(request, teardown_all_cases_sync):
    """
    Fixture for sync case10
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[10][0]
    net_case_1_netmask_actual = "255.255.255.255"
    ip_netmask = hna_conf.IPS[37]

    hna_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = ip_netmask
    sn_dict = {
        "add": {
            "1": {
                "network": net_case_1,
                "nic": hna.host_0_nics[1],
                "ip": hna_conf.BASIC_IP_DICT_NETMASK,
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    helper.manage_ip_and_refresh_capabilities(
        interface=net_case_1, netmask=net_case_1_netmask_actual
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_11(request, teardown_all_cases_sync):
    """
    Fixture for sync case11
    """
    hna = HostNetworkApi()
    move_host = False
    net_case_1 = hna_conf.SYNC_NETS_DC_1[11][0]
    net_case_1_netmask_prefix_actual = "255.255.255.255"
    ip_prefix = hna_conf.IPS[41]

    hna_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = ip_prefix
    sn_dict = {
        "add": {
            "1": {
                "network": net_case_1,
                "nic": hna.host_0_nics[1],
                "ip": hna_conf.BASIC_IP_DICT_PREFIX,
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    helper.manage_ip_and_refresh_capabilities(
        interface=net_case_1,
        netmask=net_case_1_netmask_prefix_actual
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_12(request, teardown_all_cases_sync):
    """
    Fixture for sync case12
    """
    hna = HostNetworkApi()
    ip_netmask = hna_conf.IPS[36]
    net_case_1 = hna_conf.SYNC_NETS_DC_1[12][0]
    net_case_1_ip_actual = "10.10.10.10"
    bond_1 = "bond121"
    dummys = hna_conf.DUMMYS[:2]

    hna_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = ip_netmask
    sn_dict = {
        "add": {
            "1": {
                "nic": bond_1,
                "slaves": dummys
            },
            "2": {
                "network": net_case_1,
                "nic": bond_1,
                "ip": hna_conf.BASIC_IP_DICT_NETMASK,
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    helper.manage_ip_and_refresh_capabilities(
        ip=net_case_1_ip_actual, interface=net_case_1
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_13(request, teardown_all_cases_sync):
    """
    Fixture for sync case13
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[13][0]
    net_case_1_netmask_actual = "255.255.255.255"
    bond_1 = "bond131"
    ip_netmask = hna_conf.IPS[35]
    dummys = hna_conf.DUMMYS[:2]

    hna_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = ip_netmask
    sn_dict = {
        "add": {
            "1": {
                "nic": bond_1,
                "slaves": dummys
            },
            "2": {
                "network": net_case_1,
                "nic": bond_1,
                "ip": hna_conf.BASIC_IP_DICT_NETMASK,
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    helper.manage_ip_and_refresh_capabilities(
        interface=net_case_1, netmask=net_case_1_netmask_actual
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_14(request, teardown_all_cases_sync):
    """
    Fixture for sync case14
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[14][0]
    net_case_1_netmask_prefix_actual = "255.255.255.255"
    bond_1 = "bond141"
    ip_prefix = hna_conf.IPS[40]
    dummys = hna_conf.DUMMYS[:2]

    hna_conf.BASIC_IP_DICT_PREFIX["ip"]["address"] = ip_prefix
    sn_dict = {
        "add": {
            "1": {
                "nic": bond_1,
                "slaves": dummys
            },
            "2": {
                "network": net_case_1,
                "nic": bond_1,
                "ip": hna_conf.BASIC_IP_DICT_PREFIX,
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    helper.manage_ip_and_refresh_capabilities(
        interface=net_case_1,
        netmask=net_case_1_netmask_prefix_actual
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_15(request, teardown_all_cases_sync):
    """
    Fixture for sync case15
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[15][0]
    net_case_1_ip = "10.10.10.10"

    sn_dict = {
        "add": {
            "1": {
                "network": net_case_1,
                "nic": hna.host_0_nics[1],
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    helper.manage_ip_and_refresh_capabilities(
        ip=net_case_1_ip, interface=net_case_1
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_16(request, teardown_all_cases_sync):
    """
    Fixture for sync case16
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[16][0]
    net_case_1_ip = "10.10.10.10"
    bond_1 = "bond161"
    dummys = hna_conf.DUMMYS[:2]

    sn_dict = {
        "add": {
            "1": {
                "nic": bond_1,
                "slaves": dummys
            },
            "2": {
                "network": net_case_1,
                "nic": bond_1,

            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    helper.manage_ip_and_refresh_capabilities(
        ip=net_case_1_ip, interface=net_case_1
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_17(request, teardown_all_cases_sync):
    """
    Fixture for sync case17
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[17][0]
    ip_netmask = hna_conf.IPS[34]

    hna_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = ip_netmask
    sn_dict = {
        "add": {
            "1": {
                "network": net_case_1,
                "nic": hna.host_0_nics[1],
                "ip": hna_conf.BASIC_IP_DICT_NETMASK,
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    helper.manage_ip_and_refresh_capabilities(
        interface=net_case_1, set_ip=False
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_18(request, teardown_all_cases_sync):
    """
    Fixture for sync case18
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[18][0]
    ip_netmask = hna_conf.IPS[33]

    hna_conf.BASIC_IP_DICT_NETMASK["ip"]["address"] = ip_netmask
    sn_dict = {
        "add": {
            "1": {
                "network": net_case_1,
                "nic": hna.host_0_nics[1],
                "ip": hna_conf.BASIC_IP_DICT_NETMASK,
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    helper.manage_ip_and_refresh_capabilities(
        interface=net_case_1, set_ip=False
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_19(request, teardown_all_cases_sync):
    """
    Fixture for sync case19
    """
    hna = HostNetworkApi()
    net_case_1 = hna_conf.SYNC_NETS_DC_1[19][0]
    net_case_2 = hna_conf.SYNC_NETS_DC_1[19][1]
    net_case_3 = hna_conf.SYNC_NETS_DC_1[19][2]

    sn_dict = {
        "add": {
            "1": {
                "network": net_case_1,
                "nic": hna.host_0_nics[1],
                "datacenter": hna.dc_0
            },
            "2": {
                "network": net_case_2,
                "nic": hna.host_0_nics[2],
                "datacenter": hna.dc_0
            },
            "3": {
                "network": net_case_3,
                "nic": hna.host_0_nics[3],
                "datacenter": hna.dc_0
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_hosts.updateHost(
        positive=True, host=hna.host_0_name, cluster=hna_conf.SYNC_CL
    )


#  Fixture for sync
@pytest.fixture(scope="class")
def sync_case_20(request, teardown_all_cases_sync):
    """
    Fixture for sync case20
    """
    hna = HostNetworkApi()
    bond_1 = "bond201"
    bond_2 = "bond202"
    bond_3 = "bond203"
    dummys_1 = hna_conf.DUMMYS[:2]
    dummys_2 = hna_conf.DUMMYS[2:4]
    dummys_3 = hna_conf.DUMMYS[4:6]
    net_case_1 = hna_conf.SYNC_NETS_DC_1[20][0]
    net_case_2 = hna_conf.SYNC_NETS_DC_1[20][1]
    net_case_3 = hna_conf.SYNC_NETS_DC_1[20][2]

    sn_dict = {
        "add": {
            "1": {
                "nic": bond_1,
                "slaves": dummys_1
            },
            "2": {
                "nic": bond_2,
                "slaves": dummys_2
            },
            "3": {
                "nic": bond_3,
                "slaves": dummys_3,
            },
            "4": {
                "network": net_case_1,
                "nic": bond_1,
                "datacenter": hna.dc_0
            },
            "5": {
                "network": net_case_2,
                "nic": bond_2,
                "datacenter": hna.dc_0
            },
            "6": {
                "network": net_case_3,
                "nic": bond_3,
                "datacenter": hna.dc_0
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=hna.host_0_name, **sn_dict)
    assert ll_hosts.updateHost(
        positive=True, host=hna.host_0_name, cluster=hna_conf.SYNC_CL
    )
