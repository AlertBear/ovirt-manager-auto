#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Topologies feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

import pytest

import config as topologies_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import update_vnic_network
from rhevmtests.fixtures import start_vm
from rhevmtests.networking.fixtures import (
    NetworkFixtures, setup_networks_fixture, clean_host_interfaces
)  # flake8: noqa


@pytest.fixture(scope="module", autouse=True)
def topologies_prepare_setup(request):
    """
    prepare setup
    """
    topologies = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from engine")
        assert network_helper.remove_networks_from_setup(
            hosts=topologies.host_0_name
        )
    request.addfinalizer(fin)

    testflow.setup("Create networks on engine")
    network_helper.prepare_networks_on_setup(
        networks_dict=topologies_conf.NETS_DICT, dc=topologies.dc_0,
        cluster=topologies.cluster_0
    )


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    update_vnic_network.__name__,
    start_vm.__name__,
)
class TestTopologiesCase01(NetworkTest):
    """
    Check connectivity to VM with VLAN network
    """
    __test__ = True
    net = topologies_conf.NETS[1][0]
    vm_name = conf.VM_0
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": 1,
                "network": net
            }
        }
    }
    start_vms_dict = {
        vm_name: {
            "host": 0
        }
    }

    @polarion("RHEVM3-12286")
    def test_vlan_network_01_virtio(self):
        """
        Check connectivity to VLAN network with VirtIO driver
        """
        testflow.step("Check connectivity to VLAN network with VirtIO driver")
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_VIRTIO, vlan=True
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    update_vnic_network.__name__,
    start_vm.__name__,
)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
@pytest.mark.skipif(
    conf.NO_EXTRA_BOND_MODE_SUPPORT,
    reason=conf.NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG
)
class TestTopologiesCase02(NetworkTest):
    """
    Check connectivity to VM with VLAN over BOND mode 1 network
    """
    __test__ = True
    net = topologies_conf.NETS[2][0]
    vm_name = conf.VM_0
    mode = 1
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": "bond20",
                "network": net,
                "slaves": [2, 3],
                "mode": mode
            }
        }
    }
    start_vms_dict = {
        vm_name: {
            "host": 0
        }
    }

    @polarion("RHEVM3-12290")
    def test_vlan_over_bond_network_01_virtio(self):
        """
        Check connectivity to VLAN over BOND mode 1 network with virtIO driver
        """
        testflow.step(
            "Check connectivity to VLAN over BOND mode 1 network with virtIO "
            "driver"
        )
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_VIRTIO, vlan=True, mode=self.mode
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    update_vnic_network.__name__,
    start_vm.__name__,
)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
class TestTopologiesCase03(NetworkTest):
    """
    Check connectivity to VM with BOND mode 2 network
    """
    # bond mode 2 requires switch side configuration to work properly ! ! !

    __test__ = False  # disabled until we deal with NIC plugin for 6 NICs hosts
    net = topologies_conf.NETS[3][0]
    vm_name = conf.VM_0
    mode = 2
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": "bond30",
                "network": net,
                "slaves": [2, 3],
                "mode": mode
            }
        }
    }
    start_vms_dict = {
        vm_name: {
            "host": 0
        }
    }

    @polarion("RHEVM3-12293")
    def test_bond_network_01_virtio(self):
        """
        Check connectivity to BOND mode 2 network with virtIO driver
        """
        testflow.step(
            "Check connectivity to BOND mode 2 network with virtIO driver"
        )
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_VIRTIO, mode=self.mode
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    update_vnic_network.__name__,
    start_vm.__name__,
)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
class TestTopologiesCase04(NetworkTest):
    """
    Check connectivity to VM with BOND mode 4 network
    """
    __test__ = True
    net = topologies_conf.NETS[4][0]
    vm_name = conf.VM_0
    mode = 4
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": "bond40",
                "network": net,
                "slaves": [2, 3],
                "mode": mode
            }
        }
    }
    start_vms_dict = {
        vm_name: {
            "host": 0
        }
    }

    @polarion("RHEVM3-12299")
    def test_bond_network_01_virtio(self):
        """
        Check connectivity to BOND mode 4 network with virtIO driver
        """
        testflow.step(
            "Check connectivity to BOND mode 4 network with virtIO driver"
        )
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_VIRTIO, mode=self.mode
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
@pytest.mark.skipif(
    conf.NO_EXTRA_BOND_MODE_SUPPORT,
    reason=conf.NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG
)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestTopologiesCase05(NetworkTest):
    """
    Check connectivity to BOND mode 3 network
    This is non-VM network test, we check connectivity from host to the IP:
    10.35.147.62 configured on switch
    !!! NOTE: bond mode 3 is officially not supported with VM networks!!!
    """
    __test__ = True
    net = topologies_conf.NETS[5][0]
    mode = 3
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": "bond50",
                "network": net,
                "slaves": [2, 3],
                "mode": mode,
                "ip": topologies_conf.NON_VM_BOND_IP
            }
        }
    }

    @polarion("RHEVM3-12289")
    def test_bond_non_vm_network(self):
        """
        Check connectivity to BOND mode 3 network
        """
        testflow.step("Check connectivity to BOND mode 3 network")
        assert helper.check_vm_connect_and_log(
            mode=self.mode, vm=False, flags="-r"
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
@pytest.mark.skipif(
    conf.NO_EXTRA_BOND_MODE_SUPPORT,
    reason=conf.NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG
)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestTopologiesCase06(NetworkTest):
    """
    Check connectivity to BOND mode 0 network
    This is non-VM network test, we check connectivity from host to to the IP:
    10.35.147.62 configured on switch
    """
    __test__ = True
    net = topologies_conf.NETS[6][0]
    mode = 0
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": "bond60",
                "network": net,
                "slaves": [2, 3],
                "mode": mode,
                "ip": topologies_conf.NON_VM_BOND_IP
            }
        }
    }

    @polarion("RHEVM3-12289")
    def test_bond_non_vm_network(self):
        """
        Check connectivity to BOND mode 0 network
        """
        testflow.step("Check connectivity to BOND mode 0 network")
        assert helper.check_vm_connect_and_log(
            mode=self.mode, vm=False, flags="-r"
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
@pytest.mark.skipif(
    conf.NO_EXTRA_BOND_MODE_SUPPORT,
    reason=conf.NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG
)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestTopologiesCase07(NetworkTest):
    """
    Check connectivity to BOND mode 5 network
    This is non-VM network test, we check connectivity from host to to the IP:
    10.35.147.62 configured on switch
    """
    __test__ = True
    net = topologies_conf.NETS[7][0]
    mode = 5
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": "bond70",
                "network": net,
                "slaves": [2, 3],
                "mode": mode,
                "ip": topologies_conf.NON_VM_BOND_IP
            }
        }
    }

    @polarion("RHEVM3-12302")
    def test_bond_non_vm_network(self):
        """
        Check connectivity to BOND mode 5 network
        """
        testflow.step("Check connectivity to BOND mode 5 network")
        assert helper.check_vm_connect_and_log(
            mode=self.mode, vm=False, flags="-r"
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
@pytest.mark.skipif(
    conf.NO_EXTRA_BOND_MODE_SUPPORT,
    reason=conf.NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG
)
class TestTopologiesCase08(NetworkTest):
    """
    Check connectivity to BOND mode 6 network
    This is non-VM network test, we check connectivity from host to to the IP:
    10.35.147.62 configured on switch
    """
    __test__ = True
    net = topologies_conf.NETS[8][0]
    mode = 6
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": "bond80",
                "network": net,
                "slaves": [2, 3],
                "mode": mode,
                "ip": topologies_conf.NON_VM_BOND_IP
            }
        }
    }

    @polarion("RHEVM3-12303")
    def test_bond_non_vm_network(self):
        """
        Check connectivity to BOND mode 6 network
        """
        testflow.step("Check connectivity to BOND mode 6 network")
        assert helper.check_vm_connect_and_log(
            mode=self.mode, vm=False, flags="-r"
        )
