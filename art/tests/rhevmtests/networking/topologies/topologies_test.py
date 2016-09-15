#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Topologies feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

import logging

import pytest

import config as topologies_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import attach_network_and_update_vnic, attach_bond

logger = logging.getLogger("Topologies_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(attach_network_and_update_vnic.__name__)
class TestTopologiesCase01(NetworkTest):
    """
    Check connectivity to VM with VLAN network
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = True
    net = topologies_conf.NETS[1][0]
    bond = None
    mode = None

    @polarion("RHEVM3-12286")
    def test_vlan_network_01_virtio(self):
        """
        Check connectivity to VLAN network with VirtIO driver
        """
        testflow.step("Check connectivity to VLAN network with VirtIO driver")
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_VIRTIO, vlan=True
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12287")
    def test_vlan_network_02_e1000(self):
        """
        Check connectivity to VLAN network with e1000 driver
        """
        assert helper.update_vnic_driver(
            driver=conf.NIC_TYPE_E1000, vnic_profile=self.net
        )
        testflow.step("Check connectivity to VLAN network with e1000 driver")
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_E1000, vlan=True
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12288")
    def test_vlan_network_03_rtl8139(self):
        """
        Check connectivity to VLAN network with rtl8139 driver
        """
        assert helper.update_vnic_driver(
            driver=conf.NIC_TYPE_RTL8139, vnic_profile=self.net
        )
        testflow.step("Check connectivity to VLAN network with rtl8139 driver")
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_RTL8139, vlan=True
        )


@attr(tier=2)
@pytest.mark.usefixtures(attach_network_and_update_vnic.__name__)
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
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = True
    net = topologies_conf.NETS[2][0]
    bond = conf.BOND[0]
    mode = conf.BOND_MODES[1]

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

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12291")
    def test_vlan_over_bond_network_02_e1000(self):
        """
        Check connectivity to VLAN over BOND mode 1 network with e1000 driver
        """
        assert helper.update_vnic_driver(
            driver=conf.NIC_TYPE_E1000, vnic_profile=self.net
        )
        testflow.step(
            "Check connectivity to VLAN over BOND mode 1 network with e1000 "
            "driver"
        )
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_E1000, vlan=True, mode=self.mode
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12292")
    def test_vlan_over_bond_network_03_rtl8139(self):
        """
        Check connectivity to VLAN over BOND mode 1 network with rtl8139
        driver
        """
        assert helper.update_vnic_driver(
            driver=conf.NIC_TYPE_RTL8139, vnic_profile=self.net
        )
        testflow.step(
            "Check connectivity to VLAN over BOND mode 1 network with "
            "rtl8139 driver"
        )
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_RTL8139, vlan=True, mode=self.mode
        )


@attr(tier=2)
@pytest.mark.usefixtures(attach_network_and_update_vnic.__name__)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
class TestTopologiesCase03(NetworkTest):
    """
    Check connectivity to VM with BOND mode 2 network
    Check virtIO, e1000 and rtl8139 drivers
    """
    # bond mode 2 requires switch side configuration to work properly ! ! !

    __test__ = False  # disabled until we deal with NIC plugin for 6 NICs hosts
    net = topologies_conf.NETS[3][0]
    bond = conf.BOND[1]
    mode = conf.BOND_MODES[2]

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

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12294")
    def test_bond_network_02_e1000(self):
        """
        Check connectivity to BOND mode 2 network with e1000 driver
        """
        assert helper.update_vnic_driver(
            driver=conf.NIC_TYPE_E1000, vnic_profile=self.net
        )
        testflow.step(
            "Check connectivity to BOND mode 2 network with e1000 driver"
        )
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_E1000, mode=self.mode
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12295")
    def test_bond_network_03_rtl8139(self):
        """
        Check connectivity to BOND mode 2 network with rtl8139 driver
        """
        assert helper.update_vnic_driver(
            driver=conf.NIC_TYPE_RTL8139, vnic_profile=self.net
        )
        testflow.step(
            "Check connectivity to BOND mode 2 network with rtl8139 driver"
        )
        helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_RTL8139, mode=self.mode
        )


@attr(tier=2)
@pytest.mark.usefixtures(attach_network_and_update_vnic.__name__)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
class TestTopologiesCase04(NetworkTest):
    """
    Check connectivity to VM with BOND mode 4 network
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = True
    net = topologies_conf.NETS[4][0]
    bond = conf.BOND[2]
    mode = conf.BOND_MODES[4]

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

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12300")
    def test_bond_network_02_e1000(self):
        """
        Check connectivity to BOND mode 4 network with e1000 driver
        """
        assert helper.update_vnic_driver(
            driver=conf.NIC_TYPE_E1000, vnic_profile=self.net
        )
        testflow.step(
            "Check connectivity to BOND mode 4 network with e1000 driver"
        )
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_E1000, mode=self.mode
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12301")
    def test_bond_network_03_rtl8139(self):
        """
        Check connectivity to BOND mode 4 network with rtl8139 driver
        """
        assert helper.update_vnic_driver(
            driver=conf.NIC_TYPE_RTL8139, vnic_profile=self.net
        )
        testflow.step(
            "Check connectivity to BOND mode 4 network with rtl8139 driver"
        )
        assert helper.check_vm_connect_and_log(
            driver=conf.NIC_TYPE_RTL8139, mode=self.mode
        )


@attr(tier=2)
@pytest.mark.usefixtures(attach_bond.__name__)
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
    bond = conf.BOND[3]
    mode = conf.BOND_MODES[3]

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
@pytest.mark.usefixtures(attach_bond.__name__)
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
    bond = conf.BOND[4]
    mode = conf.BOND_MODES[0]

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
@pytest.mark.usefixtures(attach_bond.__name__)
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
    bond = conf.BOND[5]
    mode = conf.BOND_MODES[5]

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
@pytest.mark.usefixtures(attach_bond.__name__)
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
    bond = conf.BOND[6]
    mode = conf.BOND_MODES[6]

    @polarion("RHEVM3-12303")
    def test_bond_non_vm_network(self):
        """
        Check connectivity to BOND mode 6 network
        """
        testflow.step("Check connectivity to BOND mode 6 network")
        assert helper.check_vm_connect_and_log(
            mode=self.mode, vm=False, flags="-r"
        )
