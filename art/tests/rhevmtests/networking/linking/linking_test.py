#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Linking/Plugging feature.
1 DC, 1 Cluster, 1 Hosts and 2 VMs will be created for testing.
Linking/Plugging will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for different states of VNIC on stopped/running VM.
"""

import logging
from art.rhevm_api.tests_lib.high_level.vms import start_vm_on_specific_host
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from rhevmtests.networking import config
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.core_api.apis_utils import TimeoutingSampler
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import removeNetwork
from art.rhevm_api.tests_lib.low_level.networks import(
    addNetwork, addNetworkToCluster, addVnicProfile, removeVnicProfile
)
from art.rhevm_api.tests_lib.low_level.vms import(
    addNic, getVmNicLinked, getVmNicPlugged, removeNic,
    updateNic, getVmNicNetwork, startVm, stopVm, waitForVMState
)

logger = logging.getLogger("Linking_Cases")

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################
# If updateNic fails in one of the test, then use waitForFuncStatus function
# This func is supposed to solve async problem between vdsm and libvirt/qemu


@attr(tier=1)
class TestLinkedCase1(TestCase):
    """
    Create permutation for the Plugged/Linked option on VNIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 5 VNICs on VM with different params for plugged/linked
        """
        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [
            ("true", "true"), ("true", "false"), ("false", "true"),
            ("false", "false")
        ]
        for i in range(len(plug_link_param_list)):
            if not addNic(
                    True, config.VM_NAME[0], name=config.NIC_NAME[i+1],
                    network=config.VLAN_NETWORKS[i],
                    plugged=plug_link_param_list[i][0],
                    linked=plug_link_param_list[i][1]
            ):
                raise NetworkException(
                    "Cannot add VNIC %s to VM" % config.NIC_NAME[i+1]
                )
        if not addNic(
                True, config.VM_NAME[0], name=config.NIC_NAME[5], network=None,
                plugged="true", linked="true"
        ):
            raise NetworkException(
                "Cannot add VNIC %s to VM" % config.NIC_NAME[5]
            )

    @tcms(8046, 231692)
    def test_check_combination_plugged_linked_values(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info("Checking Linked on nic2, nic4, nic6 is True")
        for nic_name in (
            config.NIC_NAME[1], config.NIC_NAME[3], config.NIC_NAME[5]
        ):
            if not getVmNicLinked(config.VM_NAME[0], nic=nic_name):
                raise NetworkException(
                    "NIC %s is not linked but should be" % nic_name
                )
        logger.info("Checking Plugged on nic2, nic3, nic6 is True")
        for nic_name in (
            config.NIC_NAME[1], config.NIC_NAME[2], config.NIC_NAME[5]
        ):
            if not getVmNicPlugged(config.VM_NAME[0], nic=nic_name):
                raise NetworkException(
                    "NIC %s is not plugged but should be" % nic_name
                )
        logger.info("Checking Linked on nic3, nic5 is False")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[4]):
            if getVmNicLinked(config.VM_NAME[0], nic=nic_name):
                raise NetworkException(
                    "NIC %s is linked but shouldn't be" % nic_name
                )
        logger.info("Checking Plugged on nic5, nic4 is False")
        for nic_name in (config.NIC_NAME[3], config.NIC_NAME[4]):
            if getVmNicPlugged(config.VM_NAME[0], nic=nic_name):
                raise NetworkException(
                    "NIC %s is plugged but shouldn't be" % nic_name
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info(
            "Updating all the networks besides mgmt network to unplugged"
        )
        for nic_name in (
            config.NIC_NAME[1], config.NIC_NAME[2], config.NIC_NAME[5]
        ):
            if not updateNic(
                    True, config.VM_NAME[0], nic_name, plugged="false"
            ):
                logger.error("Couldn't unplug %s", nic_name)
        logger.info("Removing all the VNICs besides mgmt network")
        for i in range(5):
            if not removeNic(True, config.VM_NAME[0], config.NIC_NAME[i+1]):
                logger.error(
                    "Cannot remove nic %s from setup", config.NIC_NAME[i+1]
                )


@attr(tier=1)
class TestLinkedCase2(TestCase):
    """
    Add a new network to VM with default plugged and linked states
    Checked that plugged and linked are True by default
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 1 VNIC on stopped VM with default plugged/linked states
        """
        logger.info("Creating VNICs with default plugged/linked states")
        if not addNic(
                True, config.VM_NAME[1], name=config.NIC_NAME[1],
                network=config.VLAN_NETWORKS[0]
        ):
            raise NetworkException(
                "Cannot add VNIC %s to VM" % config.NIC_NAME[1]
            )

    @tcms(8046, 231696)
    def test_check_default_values(self):
        """
        Check the default values for the Plugged/Linked options on VNIC
        """
        logger.info(" Checking linked state of nic2 to be True")
        if not getVmNicLinked(config.VM_NAME[1], nic=config.NIC_NAME[1]):
            raise NetworkException(
                "%s is not linked but should be" % config.VM_NAME[1]
            )
        logger.info("Checking Plugged state on nic2 to be True")
        if not getVmNicPlugged(config.VM_NAME[1], nic=config.NIC_NAME[1]):
            raise NetworkException(
                "%s is not plugged but should be" % config.VM_NAME[1]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating the network on nic2 to unplugged")
        if not updateNic(
            True, config.VM_NAME[1], config.NIC_NAME[1], plugged="false"
        ):
            logger.error("Cannot unplug %s", config.VM_NAME[1])

        logger.info("Removing the nic2 from the VM ")
        if not removeNic(True, config.VM_NAME[1], config.NIC_NAME[1]):
            logger.error("Cannot remove nic %s from setup", config.VM_NAME[1])


@attr(tier=1)
class TestLinkedCase3(TestCase):
    """
    Create permutation for the Plugged/Linked VNIC
    Use e1000 and rtl8139 drivers
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 2 VNICs on stopped VM with different nic type for plugged/linked
        """
        logger.info("Creating VNICs with different nic types for stopped VM")
        if not addNic(
                True, config.VM_NAME[1], name=config.NIC_NAME[1],
                network=config.VLAN_NETWORKS[0],
                interface=config.NIC_TYPE_RTL8139, plugged="true",
                linked="true"
        ):
            raise NetworkException(
                "Cannot add VNIC %s to VM" % config.NIC_NAME[1]
            )

        if not addNic(
                True, config.VM_NAME[1], name=config.NIC_NAME[2],
                interface=config.NIC_TYPE_E1000,
                network=config.VLAN_NETWORKS[1], plugged="true", linked="false"
        ):
            raise NetworkException(
                "Cannot add VNIC %s to VM" % config.NIC_NAME[2]
            )

    @tcms(8046, 231697)
    def test_check_ombination_plugged_linked_values(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info(
            "Checking linked state of nic3 is False and Updating its state "
            "to True"
        )
        if getVmNicLinked(config.VM_NAME[1], nic=config.NIC_NAME[2]):
            raise NetworkException(
                "%s is linked, but shouldn't be" % config.NIC_NAME[2]
            )
        if not updateNic(
            True, config.VM_NAME[1], config.NIC_NAME[2], linked="true"
        ):
            raise NetworkException("Couldn't update linked to True")

        logger.info(
            "Checking linked state on nic2 is True and Updating its state to "
            "False"
        )
        if not getVmNicLinked(config.VM_NAME[1], nic=config.NIC_NAME[1]):
            raise NetworkException(
                "%s is not linked, but should be" % config.NIC_NAME[1]
            )
        if not updateNic(
            True, config.VM_NAME[1], config.NIC_NAME[1], linked="false"
        ):
            raise NetworkException("Couldn't update linked to false")

        logger.info("Checking that linked state on nics was correctly updated")
        if getVmNicLinked(config.VM_NAME[1], nic=config.NIC_NAME[1]):
            raise NetworkException(
                "%s is linked, but it shouldn't be" % config.NIC_NAME[1]
            )
        if not getVmNicLinked(config.VM_NAME[1], nic=config.NIC_NAME[2]):
            raise NetworkException(
                "%s is not linked, but it should be" % config.NIC_NAME[2]
            )

        logger.info("Updating both NICs with empty networks")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if not updateNic(True, config.VM_NAME[1], nic_name, network=None):
                raise NetworkException("Couldn't update NICs with empty net")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if getVmNicNetwork(config.VM_NAME[1], nic=nic_name):
                raise NetworkException(
                    "Update NIC %s with empty Net failed" % nic_name
                )

        logger.info(
            "Updating both NICs with its original networks and unplugging "
            "them"
        )
        for i in range(2):
            if not updateNic(
                    True, config.VM_NAME[1], config.NIC_NAME[i+1],
                    network=config.VLAN_NETWORKS[i],
                    vnic_profile=config.VLAN_NETWORKS[i], plugged="false"
            ):
                raise NetworkException(
                    "Couldn't update nic with original network or couldn't "
                    "unplug nic"
                )

        logger.info(
            "Testing that update nics with non-empty networks succeeded"
        )
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if not getVmNicNetwork(config.VM_NAME[1], nic=nic_name):
                raise NetworkException(
                    "Update %s with non-empty Net failed" % nic_name
                )

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if getVmNicPlugged(config.VM_NAME[1], nic=nic_name):
                raise NetworkException(
                    "NIC %s is plugged but shouldn't" % nic_name
                )

        logger.info("Updating both NICs with empty networks")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if not updateNic(True, config.VM_NAME[1], nic_name, network=None):
                raise NetworkException("Couldn't update nic with empty net")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if getVmNicNetwork(config.VM_NAME[1], nic=nic_name):
                raise NetworkException(
                    "Update %s with empty Net failed" % nic_name
                )

        logger.info(
            "Updating both NICs with its original networks and plugging them"
        )
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if not updateNic(
                    True, config.VM_NAME[1], nic_name, plugged="true"
            ):
                raise NetworkException(
                    "Couldn't update nic with original network or couldn't "
                    "plug them"
                )

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if not getVmNicPlugged(config.VM_NAME[1], nic=nic_name):
                raise NetworkException(
                    "NIC %s isn't plugged but should be" % nic_name
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the nics besides mgmt network to unplugged")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if not updateNic(
                    True, config.VM_NAME[1], nic_name, plugged="false"
            ):
                logger.error(
                    "Couldn't update nic %s to be unplugged", nic_name
                )

        logger.info("Removing all the VNICs besides mgmt network")
        for i in range(2):
            if not removeNic(True, config.VM_NAME[1], config.NIC_NAME[i+1]):
                logger.error(
                    "Cannot remove nic %s from setup", config.NIC_NAME[i + 1]
                )


@attr(tier=1)
class TestLinkedCase4(TestCase):
    """
    Try to run VM with network attached to Cluster but not to the host
    The test should fail as VM can't run when there is no network on
    at least one host of the Cluster
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create network on DC/Cluster and add it to VM
        """
        logger.info(
            "Creating network %s on DC, Cluster", config.NETWORKS[0]
        )
        if not addNetwork(
                True, name=config.NETWORKS[0], data_center=config.DC_NAME[0]
        ):
            raise NetworkException("Cannot add network to DC")

        if not addNetworkToCluster(
                True, network=config.NETWORKS[0],
                cluster=config.CLUSTER_NAME[0], required="false"
        ):
            raise NetworkException("Cannot add network to Cluster")

        logger.info("Adding network to VM")
        if not addNic(
                True, config.VM_NAME[1], name=config.NIC_NAME[5],
                network=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Cannot add VNIC %s to VM" % config.NIC_NAME[5]
            )

    @tcms(8046, 231691)
    def test_check_start_vm(self):
        """
        Try to start VM when there is no network on the host
        """
        logger.info(
            "Try to start VM with network that is not present on the host in "
            "the Cluster. NIC: nic6, Network: %s", config.VLAN_NETWORKS[0]
        )
        startVm(positive=None, vm=config.VM_NAME[1])
        if not waitForVMState(vm=config.VM_NAME[1], state="down"):
            raise NetworkException(
                "%s is up, should be down" % config.VM_NAME[1]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the NICs besides MGMT network to unplugged")
        if not updateNic(
            True, config.VM_NAME[1], config.NIC_NAME[5], plugged="false"
        ):
            logger.error(
                "Couldn't update nic %s to be unplugged", config.NIC_NAME[5]
            )

        if not removeNic(True, config.VM_NAME[1], config.NIC_NAME[5]):
            logger.error(
                "Cannot remove nic %s from setup", config.NIC_NAME[5]
            )

        if not removeNetwork(
                True, network=config.NETWORKS[0],
                data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Cannot remove network %s from DC", config.NETWORKS[0]
            )


@attr(tier=1)
class TestLinkedCase5(TestCase):
    """
    Editing plugged VNIC with port mirroring enabled on running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 1 plugged/linked VNIC with port mirroring enabled
        on running VM
        """
        if not addVnicProfile(
                positive=True, name=config.VNIC_PROFILE[0],
                cluster=config.CLUSTER_NAME[0],
                network=config.VLAN_NETWORKS[0], port_mirroring=True
        ):
            logger.error(
                "Failed to add %s profile with %s network to %s",
                config.VNIC_PROFILE[0], config.VLAN_NETWORKS[0],
                config.CLUSTER_NAME[0]
            )

        logger.info("Creating plugged/linked VNIC with port mirroring on sw1")
        if not addNic(
                True, vm=config.VM_NAME[0], name=config.NIC_NAME[1],
                vnic_profile=config.VNIC_PROFILE[0],
                network=config.VLAN_NETWORKS[0]
        ):
            raise NetworkException(
                "Cannot add VNIC %s to VM" % config.NIC_NAME[1]
            )

    @tcms(8046, 239344)
    def test_check_port_mirroring_network(self):
        """
        Check scenarios for port mirroring network
        """
        logger.info("Try to switch link down ")
        if not updateNic(
            False, config.VM_NAME[0], config.NIC_NAME[1], linked="false"
        ):
            raise NetworkException("Unlink NIC2 failed")
        logger.info("Unplug VNIC")
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="false"
        ):
            raise NetworkException("Unplug NIC2 failed")
        logger.info("Plugging VNIC back")
        if not updateNic(
                True, config.VM_NAME[0], config.NIC_NAME[1], plugged="true"
        ):
            raise NetworkException("Plug NIC2 failed")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating the nics besides mgmt network to unplugged")
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="false"
        ):
            logger.error("Couldn't update nics to be unplugged")

        logger.info("Removing all the VNICs besides mgmt network")
        if not removeNic(True, config.VM_NAME[0], config.NIC_NAME[1]):
            logger.error("Cannot remove nic from setup")

        logger.info("Removing vnic profile")
        if not removeVnicProfile(
                positive=True, vnic_profile_name=config.VNIC_PROFILE[0],
                network=config.VLAN_NETWORKS[0]
        ):
            logger.error("Failed to remove %s profile", config.VNIC_PROFILE[0])


@attr(tier=1)
class TestLinkedCase6(TestCase):
    """
    Create VNICs with linked/unlinked states on running VM.
    Change network parameters for both VNICs:
    Change nic names, link/plugged states
    Assign and unassign empty network to the NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 2 VNICs on running VM with different linked states for VNICs
        """
        logger.info("Creating VNICs with different link states on running VM")
        link_param_list = ["true", "false"]
        for i in range(len(link_param_list)):
            if not addNic(
                    True, config.VM_NAME[0], name=config.NIC_NAME[i+1],
                    network=config.VLAN_NETWORKS[0], plugged="true",
                    linked=link_param_list[i]
            ):
                raise NetworkException(
                    "Cannot add VNIC %s to VM" % config.NIC_NAME[i + 1]
                )

    @tcms(8046, 239348)
    def test_change_net_param_values(self):
        """
        Check network parameters changes for VNICS
        Change NIC names, update linked/plugged states
        Remove and return network from the VNIC
        """
        link_param_list = ["false", "true"]
        logger.info("Checking linked state of nic2/nic3 to be True/False")
        if not getVmNicLinked(config.VM_NAME[0], nic=config.NIC_NAME[1]):
            raise NetworkException(
                "NIC2  isn't linked but should be"
            )
        if getVmNicLinked(config.VM_NAME[0], nic=config.NIC_NAME[2]):
            raise NetworkException(
                "NIC3 is linked but shouldn't be"
            )
        logger.info("Changing the NICs names and Updating opposite link state")
        for i in range(2):
            if not updateNic(
                    True, config.VM_NAME[0], config.NIC_NAME[i+1],
                    name="vnic%s" % (i + 2)
            ):
                logger.error("Couldn't update the NICs name")

        for i in range(2):
            sample = TimeoutingSampler(
                timeout=config.SAMPLER_TIMEOUT, sleep=1, func=updateNic,
                positive=True, vm=config.VM_NAME[0], nic="vnic%s" % (i + 2),
                network=config.VLAN_NETWORKS[0],
                vnic_profile=config.VLAN_NETWORKS[0],
                linked=link_param_list[i]
            )
            if not sample.waitForFuncStatus(result=True):
                raise NetworkException("Couldn't update correct linked state")

        logger.info("Checking linked state on vnic2/vnic3 to be False/True")
        if not getVmNicLinked(config.VM_NAME[0], nic="vnic3"):
            raise NetworkException(
                "VNIC3 isn't linked but should be"
            )
        if getVmNicLinked(config.VM_NAME[0], nic="vnic2"):
            raise NetworkException(
                "VNIC2 is linked but shouldn't be"
            )

        logger.info("Updating both NICs with empty networks")
        for nic_name in ("vnic3", "vnic2"):
            if not updateNic(True, config.VM_NAME[0], nic_name, network=None):
                logger.error("Couldn't update NIC with empty network")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in ("vnic3", "vnic2"):
            if getVmNicNetwork(config.VM_NAME[0], nic=nic_name):
                raise NetworkException(
                    "Update %s with empty network failed" % nic_name
                )
        logger.info(
            "Update both NICs with their original networks and unplug them"
        )
        if not (
                updateNic(
                True, config.VM_NAME[0], "vnic3",
                network=config.VLAN_NETWORKS[1],
                vnic_profile=config.VLAN_NETWORKS[1], plugged="false"
                )
                and updateNic(
                True, config.VM_NAME[0], "vnic2",
                network=config.VLAN_NETWORKS[0],
                vnic_profile=config.VLAN_NETWORKS[0], plugged="false"
                )
        ):
            logger.error(
                "Couldn't update NICs with original network and couldn't "
                "unplug them"
            )

        logger.info(
            "Testing that update NICs with non-empty networks succeeds"
        )
        for nic_name in ("vnic3", "vnic2"):
            if not getVmNicNetwork(config.VM_NAME[0], nic=nic_name):
                raise NetworkException(
                    "Update %s with non-empty Net failed" % nic_name
                )

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in ("vnic3", "vnic2"):
            if getVmNicPlugged(config.VM_NAME[0], nic=nic_name):
                raise NetworkException(
                    "%s is plugged, but shouldn't be" % nic_name
                )

        logger.info("Changing the NICs names to the original ones")
        if not (updateNic(
                True, config.VM_NAME[0], "vnic3", name=config.NIC_NAME[2])
                and
                updateNic(
                True, config.VM_NAME[0], "vnic2", name=config.NIC_NAME[1])
                ):
            raise NetworkException("Couldn't update NICs with original names")

        logger.info("Updating both NICs with empty networks")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if not updateNic(True, config.VM_NAME[0], nic_name, network=None):
                raise NetworkException("Couldn't update NICs to empty nets")

        logger.info("Testing that update nics with empty networks succeeded")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if getVmNicNetwork(config.VM_NAME[0], nic=nic_name):
                raise NetworkException(
                    "Update %s with empty Net failed" % nic_name
                )

        logger.info("Updating both NICs to be plugged")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if not updateNic(
                    True, config.VM_NAME[0], nic_name, plugged="true"
            ):
                raise NetworkException("Couldn't update NIC to be plugged")

        logger.info("Checking that plugged state on NICs was updated")
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if not getVmNicPlugged(config.VM_NAME[0], nic=nic_name):
                raise NetworkException(
                    "%s is not plugged, but should be" % nic_name
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info(
            "Updating all the networks besides mgmt network to unplugged"
        )
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[1]):
            if not updateNic(
                    True, config.VM_NAME[0], nic_name, plugged="false"
            ):
                logger.error("Couldn't unplugg nic2/nic3 networks ")

        logger.info("Removing all the VNICs besides mgmt network")
        for index in range(2):
            if not removeNic(
                True, config.VM_NAME[0], config.NIC_NAME[index+1]
            ):
                logger.error("Cannot remove nic from setup")


@attr(tier=1)
class TestLinkedCase7(TestCase):
    """
    Changing several network parameters at once on non-running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 1 VNIC on non-running VM
        """
        logger.info("Creating VNICs on non-running VM")
        if not addNic(
                True, config.VM_NAME[1], name=config.NIC_NAME[1],
                network=config.VLAN_NETWORKS[0], plugged="true",
                linked="true"
        ):
            raise NetworkException("Cannot add VNIC to VM")

        if not addVnicProfile(
                positive=True, name=config.VNIC_PROFILE[0],
                cluster=config.CLUSTER_NAME[0],
                network=config.VLAN_NETWORKS[1], port_mirroring=True
        ):
            raise NetworkException(
                "Failed to add %s profile with %s network to %s" % (
                    config.VNIC_PROFILE[0], config.VLAN_NETWORKS[1],
                    config.CLUSTER_NAME[0])
            )

    @tcms(8046, 239368)
    def test_change_net_param_values(self):
        """
        Change plugged, network and name at once on VNIC of VM
        """
        logger.info("Changing nic2 plugged, network and name params")
        if not updateNic(
                True, config.VM_NAME[1], config.NIC_NAME[1], name="vnic2",
                network=config.VLAN_NETWORKS[1],
                vnic_profile=config.VLAN_NETWORKS[1], plugged="false"
        ):
            raise NetworkException(
                "Couldn't update nic with plugged, network and name params"
            )
        logger.info("Checking plugged state on nic2 to be False")
        if getVmNicPlugged(config.VM_NAME[1], nic="vnic2"):
            raise NetworkException(
                "VNIC2 is plugged, but shouldn't be"
            )

        logger.info("Changing nic2 linked, network and name params")
        if not updateNic(
                True, config.VM_NAME[1], "vnic2", name=config.NIC_NAME[1],
                network=config.VLAN_NETWORKS[0],
                vnic_profile=config.VLAN_NETWORKS[0], linked="false"
        ):
            raise NetworkException(
                "Couldn't update nic with linked, network and name params"
            )
        if getVmNicLinked(config.VM_NAME[1], nic=config.NIC_NAME[1]):
            raise NetworkException(
                "NIC2 is linked, but shouldn't be"
            )

        if not start_vm_on_specific_host(
            vm=config.VM_NAME[1], host=config.HOSTS[0], wait_for_ip=True
        ):
            raise NetworkException(
                "Cannot start VM %s at host %s" %
                (config.VM_NAME[1], config.HOSTS[0])
            )
        logger.info("Changing linked and plugged to True ")
        logger.info("Changing network and turning on port mirroring")
        if not updateNic(
                True, config.VM_NAME[1], config.NIC_NAME[1], linked="true",
                plugged="true", network=config.VLAN_NETWORKS[1],
                vnic_profile=config.VNIC_PROFILE[0]
        ):
            raise NetworkException("Cannot change net and turn pm on")

        logger.info("Try updating nic with new mac and interface type:")
        logger.info("Test should fail updating")
        if not updateNic(
            False, config.VM_NAME[1], config.NIC_NAME[1],
            interface=config.NIC_TYPE_RTL8139, mac_address="12:22:33:44:55:66"
        ):
            raise NetworkException(
                "Updating NIC with new MAC and int type succeeded"
            )
        if not updateNic(
                True, config.VM_NAME[1], config.NIC_NAME[1],
                network=config.VLAN_NETWORKS[1],
                vnic_profile=config.VLAN_NETWORKS[1], linked="false",
                plugged="false"
        ):
            raise NetworkException("Cannot update linked state")

        logger.info("Updating nic with new mac and interface type")
        if not updateNic(
            True, config.VM_NAME[1], config.NIC_NAME[1],
            interface=config.NIC_TYPE_RTL8139, mac_address="00:22:33:44:55:66"
        ):
            raise NetworkException(
                "Updating NIC2 with new MAC and int type failed"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating all the NICs besides mgmt network to unplugged")

        logger.info("Updating nics to be unplugged")
        if not updateNic(
            True, config.VM_NAME[1], config.NIC_NAME[1], plugged="false"
        ):
            logger.error("Cannot unplugged nic %s ", config.NIC_NAME[1])

        logger.info("Removing all the VNICs besides MGMT network")
        if not removeNic(True, config.VM_NAME[1], config.NIC_NAME[1]):
            logger.error(
                "Cannot remove nic %s from setup", config.NIC_NAME[1]
            )

        if not removeVnicProfile(
                positive=True, vnic_profile_name=config.VNIC_PROFILE[0],
                network=config.VLAN_NETWORKS[1]
        ):
            logger.error(
                "Cannot remove VNIC profile %s", config.VNIC_PROFILE[0])

        if not stopVm(True, vm=config.VM_NAME[1]):
            logger.error("Cannot stop VM %s", config.VM_NAME[1])
