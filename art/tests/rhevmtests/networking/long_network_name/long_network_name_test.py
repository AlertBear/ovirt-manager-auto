#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Tests for long network name
"""

import pytest
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion, bz
from art.unittest_lib import tier2, NetworkTest
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    vms as ll_vms,
    host_network as ll_host_network
)
from art.rhevm_api.tests_lib.high_level import (
    networks as hl_networks,
    host_network as hl_host_network
)
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces_fixture_function,
    remove_all_networks,
    add_vnics_to_vms,
    remove_vnics_from_vms,
    create_and_attach_networks,
    setup_networks_fixture,
    clean_host_interfaces
)


@pytest.mark.usefixtures(
    remove_all_networks.__name__,
    clean_host_interfaces_fixture_function.__name__
)
class TestLongNetworkName01(NetworkTest):
    """
    Create network, attach the network and check that VDSM report the
    correct name (Network name in case of network with less 16 characters and
    prefix + 13 UUID for network with more then 16 characters

    1. Verify that network short names created as expected - less 16 characters
    2. Attach network with long name to host

    """
    # General params
    dc = conf.DC_0
    old_network_name = "15_characters__"
    long_network_name = "long_network_name_" + "@_!" * 79

    # clean_host_interfaces_fixture_function params
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # remove_all_networks params
    remove_dcs_networks = [dc]

    @tier2
    @pytest.mark.parametrize(
        "network",
        [
            pytest.param(old_network_name, marks=(polarion("RHEVM-21966"))),
            pytest.param(
                long_network_name, marks=(
                    (polarion("RHEVM-21970"), bz({"1477569": {}}))
                )
            )
        ],
        ids=[
            "Create_network_with_old_restriction",
            "Create network with long name",
        ]
    )
    def test_create_network_and_check_vdsm(self, network):
        """
        Create network and check that VDSM report the correct name according to
        the network name length
        """
        network_dict = {
            network: {
                "required": "false"
            }
        }
        sn_dict = {
            "add": {
                "1": {
                    "network": network,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        assert hl_networks.create_and_attach_networks(
            data_center=conf.DC_0, cluster=conf.CL_0, network_dict=network_dict
        )

        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )

        network_object = ll_networks.find_network(
            network=network, data_center=self.dc
        )
        vdsm_network_name = (
            network if len(network) < 16 else "no{_id}".format(
                _id=network_object.id[:13]
            )
        )
        vds_caps = conf.VDS_0_HOST.vds_client("getCapabilities")
        assert vds_caps
        assert vds_caps.get('networks').get(vdsm_network_name)


@pytest.mark.usefixtures(
    remove_vnics_from_vms.__name__,
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    add_vnics_to_vms.__name__
)
class TestLongNetworkName02(NetworkTest):
    """
    1. Start VM that use network with long name

    """
    # General params
    vm = conf.VM_0
    dc = conf.DC_0
    long_network_name = "long_network_name_" + "!_@" * 79

    # add_vnics_to_vms params
    add_vnics_vms_params = {
        "1":
            {
                "vm": vm,
                "name": long_network_name,
                "network": long_network_name
            }
    }

    # remove_vnics_from_vms params
    remove_vnics_vms_params = add_vnics_vms_params

    # create_and_attach_network params
    create_networks = {
        "1": {
            "datacenter": dc,
            "cluster": conf.CL_0,
            "networks": long_network_name
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            long_network_name: {
                "nic": 1,
                "network": long_network_name
            }
        }
    }

    @tier2
    @bz({"1477569": {}})
    def test_run_vm_with_long_network_name(self, network):
        """
        Start VM that use network with long name
        """
        assert ll_vms.startVm(positive=True, vm=self.vm)


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
)
class TestLongNetworkName03(NetworkTest):
    """
    1. Make sure unmanaged network reported as prefix+uuid for network with
    long name

    """
    # General params
    vm = conf.VM_0
    dc = conf.DC_0
    long_network_name = "long_network_name_" + "!_@" * 79

    # create_and_attach_network params
    create_networks = {
        "1": {
            "datacenter": dc,
            "cluster": conf.CL_0,
            "networks": long_network_name
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            long_network_name: {
                "nic": 1,
                "network": long_network_name
            }
        }
    }

    @tier2
    @bz({"1477569": {}})
    def test_unmanaged_network_reported_as_prefis_uuid(self):
        """
        Make sure unmanaged network reported as prefix+uuid for network with
        long name
        """
        network_object = ll_networks.find_network(
            network=self.long_network_name, data_center=self.dc
        )
        vdsm_network_name = "no{_id}".format(_id=network_object.id[:13])
        assert ll_networks.remove_network(
            positive=True, network=self.long_network_name
        )
        assert ll_host_network.get_host_unmanaged_networks(
            host_name=conf.HOST_0_NAME, networks=[vdsm_network_name]
        )
