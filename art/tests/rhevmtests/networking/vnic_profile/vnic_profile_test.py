#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing VNIC profile feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

import logging
from rhevmtests.networking import config
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase

from art.test_handler.exceptions import(
    NetworkException
)
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.low_level.datacenters import(
    addDataCenter, removeDataCenter
)
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, remove_net_from_setup
)
from art.rhevm_api.tests_lib.low_level.networks import(
    updateNetwork, update_vnic_profile, getNetworkVnicProfiles,
    get_vnic_profile_obj, add_vnic_profile, removeVnicProfile, findVnicProfile,
    get_vnic_profile_attr, removeNetwork
)
from art.rhevm_api.tests_lib.low_level.vms import(
    addNic, updateNic, removeNic, createVm, checkVmNicProfile, removeVm
)
from art.rhevm_api.tests_lib.low_level.templates import(
    addTemplateNic, removeTemplateNic
)

logger = logging.getLogger("VNIC_Profile_Cases")


########################################################################

########################################################################
#                             Test Cases                               #
########################################################################

@attr(tier=2)
class TestVNICProfileCase01(TestCase):

    """
    Verify that when creating the new DC  - the new VNIC profile
    is created with MGMT network name
    """
    __test__ = True
    dc_name2 = "new_DC_35_case01"

    @classmethod
    def setup_class(cls):
        """
        Create new DC on the setup
        """
        logger.info("Add DC to setup")
        if not addDataCenter(
            True, name=cls.dc_name2, version=config.COMP_VERSION,
            storage_type=config.STORAGE_TYPE
        ):
            raise NetworkException(
                "Cannot create new DataCenter %s" % cls.dc_name2
            )

    @polarion("RHEVM3-3991")
    def test_check_mgmt_profile(self):
        """
        Check MGMT VNIC profile is created when creating the new DC
        """
        logger.info(
            "Check MGMT VNIC profile is created for MGMT network when "
            "creating a new DC %s", self.dc_name2
        )
        if not get_vnic_profile_obj(
            name=config.MGMT_BRIDGE, network=config.MGMT_BRIDGE,
            data_center=self.dc_name2
        ):
            raise NetworkException(
                "MGMT VNIC profile was not created when creating a new DC"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove DC from the setup.
        """
        logger.info("Remove DC %s from setup", cls.dc_name2)
        if not removeDataCenter(
            True, datacenter=cls.dc_name2
        ):
            logger.error("Cannot remove DC %s from setup", cls.dc_name2)


@attr(tier=2)
class TestVNICProfileCase02(TestCase):

    """
    Verify uniqueness of VNIC profile
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster
        """
        local_dict = {
            config.NETWORKS[0]: {"required": "false"},
            config.NETWORKS[1]: {"required": "false"}
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create and attach networks %s" % config.NETWORKS[:2]
            )

    @polarion("RHEVM3-3973")
    def test_create_new_profiles(self):
        """
        Check you can create a profile for sw2 with the same name as sw1
        Check you can"t create profile with the same name for the same network
        """
        logger.info(
            "Creating profile %s for network %s", config.NETWORKS[0],
            config.NETWORKS[1]
        )
        if not add_vnic_profile(
            positive=True, name=config.NETWORKS[0],
            data_center=config.DC_NAME[0], network=config.NETWORKS[1]
        ):
            raise NetworkException(
                "Creating profile %s for network %s failed" %
                (config.NETWORKS[0], config.NETWORKS[1])
            )
        logger.info(
            "Try to create profile with the same name for network %s"
            " Expected result is Fail", config.NETWORKS[1]
        )
        if not add_vnic_profile(
            positive=False, name=config.NETWORKS[0],
            data_center=config.DC_NAME[0], network=config.NETWORKS[1]
        ):
            raise NetworkException(
                "Creating the same profile %s for the network %s succeeded - "
                "should fail" % (config.NETWORKS[0], config.NETWORKS[1])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove networks from DC")
        for i in range(2):
            if not removeNetwork(
                positive=True, network=config.NETWORKS[i],
                data_center=config.DC_NAME[0]
            ):
                logger.error(
                    "Couldn't remove network %s from DC", config.NETWORKS[i]
                )


@attr(tier=2)
class TestVNICProfileCase03(TestCase):

    """
    Verify that changing the VM network to non-VM makes all its VNIC
    profiles disappear
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster
        """

        local_dict = {
            config.NETWORKS[0]: {"required": "false"}
        }
        logger.info(
            "Creating network %s with default vnic profile %s",
            config.NETWORKS[0], config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

        logger.info(
            "Creating additional profile %s for network %s",
            config.NETWORKS[1], config.NETWORKS[0]
        )
        if not add_vnic_profile(
            positive=True, name=config.NETWORKS[1],
            data_center=config.DC_NAME[0], network=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Couldn't create second VNIC profile %s" % config.NETWORKS[1]
            )

    @polarion("RHEVM3-3989")
    def test_update_to_non_vm(self):
        """
        Update VM network to non-VM network
        Check that both VNIC profiles of the network were removed as a
        result of changing the state of the network to non-VM
        """
        logger.info("Updating network %s to be non-VM", config.NETWORKS[0])
        if not updateNetwork(True, config.NETWORKS[0], usages=""):
            raise NetworkException(
                "Couldn't change network %s to be non-VM" % config.NETWORKS[0]
            )
        logger.info("Check no VNIC profile exists for non-VM network")
        if getNetworkVnicProfiles(
            config.NETWORKS[0], data_center=config.DC_NAME[0]
        ):
            raise NetworkException("VNIC profiles exists for non-VM network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """

        logger.info("Remove network %s from DC/Cluster", config.NETWORKS[0])
        if not removeNetwork(
            positive=True, network=config.NETWORKS[0],
            data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Couldn't remove network %s from DC/Cluster",
                config.NETWORKS[0]
            )


@attr(tier=2)
class TestVNICProfileCase04(TestCase):

    """
    Verify that removing network from setup makes all it's all VNIC
    profiles disappear as well
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster with 2 profiles for the network
        1) the default one, 2) created for the network
        """
        local_dict = {
            config.NETWORKS[0]: {"required": "false"}
        }
        logger.info(
            "Creating network %s with default vnic profile %s",
            config.NETWORKS[0], config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

        logger.info(
            "Creating additional profile %s for network %s",
            config.NETWORKS[1], config.NETWORKS[0]
        )
        if not add_vnic_profile(
            positive=True, name=config.NETWORKS[1],
            data_center=config.DC_NAME[0], network=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Couldn't create second VNIC profile %s" % config.NETWORKS[1])

    @polarion("RHEVM3-3990")
    def test_remove_network(self):
        """
        Remove VM network
        Check that both VNIC profiles of the network were removed as a
        result of network removal
        """
        logger.info(
            "Checking VNIC profiles exists after creating network %s",
            config.NETWORKS[0]
        )
        for i in range(2):
            if not findVnicProfile(vnic_profile_name=config.NETWORKS[i]):
                raise NetworkException(
                    "VNIC profile %s doesn't exist " % config.NETWORKS[i]
                )

        logger.info("Remove network %s from DC", config.NETWORKS[0])
        if not removeNetwork(
            positive=True, network=config.NETWORKS[0],
            data_center=config.DC_NAME[0]
        ):
            raise NetworkException(
                "Couldn't remove network %s from DC" % config.NETWORKS[0]
            )

        logger.info(
            "Checking no VNIC profile exists for removed network %s",
            config.NETWORKS[0]
        )
        for i in range(2):
            if findVnicProfile(vnic_profile_name=config.NETWORKS[i]):
                raise NetworkException(
                    "VNIC profile %s exists after network removal" %
                    config.NETWORKS[i]
                )


@attr(tier=2)
class TestVNICProfileCase05(TestCase):

    """
    Verify that creating the non-VM network doesn't create default VNIC
    profile and doesn't allow you to create non-default VNIC profiles
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical non-VM network on DC/Cluster
        """
        local_dict = {
            config.NETWORKS[0]: {"required": "false", "usages": ""}
        }
        logger.info(
            "Creating network %s with default vnic profile %s",
            config.NETWORKS[0], config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3972")
    def test_check_non_vm(self):
        """
        Check no VNIC profile exists for non-VM network
        Check you can't create VNIC profile for non-VM network
        """
        logger.info("Check no VNIC profile exist for non-VM network")
        if getNetworkVnicProfiles(
            config.NETWORKS[0], data_center=config.DC_NAME[0]
        ):
            raise NetworkException("VNIC profiles exist for non-VM network")
        logger.info(
            "Trying to create profile %s for non-VM network %s",
            config.NETWORKS[1], config.NETWORKS[0]
        )
        if not add_vnic_profile(
            positive=False, name=config.NETWORKS[1],
            data_center=config.DC_NAME[0], network=config.NETWORKS[0]
        ):
            raise NetworkException("Created VNIC profile for non_VM network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """

        logger.info("Remove network %s from DC", config.NETWORKS[0])
        if not removeNetwork(
            positive=True, network=config.NETWORKS[0],
            data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Couldn't remove network %s from DC", config.NETWORKS[0]
            )


@attr(tier=2)
class TestVNICProfileCase06(TestCase):

    """
    Check that default VNIC profile is created when a new network is added
    to setup . No VNIC profile is added when creating non-VM network and when
    creating new network with profile_required flag set to false
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 3 logical networks on DC/Cluster.
        1) VM, 2) with profile_required flag set to false, 3) non-VM
        """
        local_dict = {
            config.NETWORKS[0]: {"required": "false"},
            config.NETWORKS[1]: {
                "required": "false", "profile_required": "false"
            },
            config.NETWORKS[2]: {"required": "false", "usages": ""}
        }
        logger.info(
            "Creating network %s with default vnic profile %s",
            config.NETWORKS[0], config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException("Cannot create and attach networks")

    @polarion("RHEVM3-3978")
    def test_check_profile(self):
        """"
        1) Check that VNIC profile exists for VM network
        2) Check that VNIC profile doesn't exist for non-VM network'
        3) Check that VNIC profile doesn't exist for network with the flag
        profile_required set to false
        """
        logger.info("Check VNIC profile exists for VM network")
        if not getNetworkVnicProfiles(
            config.NETWORKS[0], data_center=config.DC_NAME[0]
        ):
            raise NetworkException(
                "VNIC profiles doesn't 'exist for VM network"
            )

        logger.info("Check no VNIC profile exists for non-VM network")
        if getNetworkVnicProfiles(
            config.NETWORKS[2], data_center=config.DC_NAME[0]
        ):
            raise NetworkException("VNIC profiles exists for non-VM network")

        logger.info(
            "Check no VNIC profile exist for network with flag profile_"
            "required set to false"
        )
        if getNetworkVnicProfiles(
            config.NETWORKS[1], data_center=config.DC_NAME[0]
        ):
            raise NetworkException(
                "VNIC profiles exist for profile_required flag set to false"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        for i in range(3):
            logger.info("Remove network %s from DC", config.NETWORKS[i])
            if not removeNetwork(
                positive=True, network=config.NETWORKS[i],
                data_center=config.DC_NAME[0]
            ):
                logger.error(
                    "Couldn't remove network %s from DC", config.NETWORKS[i]
                )


@attr(tier=2)
class TestVNICProfileCase07(TestCase):

    """
    Check that attach profile to VM when the network for that profile
    doesn't exist on host fails
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 1 logical networks on DC/Cluster.
        1) VM network
        2) with profile_required flag set to false
        3) non-VM
        """
        local_dict = {
            config.NETWORKS[0]: {"required": "false"}
        }
        logger.info(
            "Creating network %s with default vnic profile %s",
            config.NETWORKS[0], config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3995")
    def test_check_profile(self):
        """"
        1) Check that VNIC profile exists for VM network
        2) Check that you can't add VNIC profile to VM if its network is
           not attached to the host
        """
        logger.info("Check VNIC profile exists for VM network")
        if not getNetworkVnicProfiles(
            config.NETWORKS[0], data_center=config.DC_NAME[0]
        ):
            raise NetworkException(
                "VNIC profiles doesn't exist for VM network"
            )
        logger.info("Try to add VNIC that doesn't exist on Host")
        if not addNic(
            False, config.VM_NAME[0], name=config.NIC_NAME[1],
            network=config.NETWORKS[0], vnic_profile=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Succeeded in adding a NIC for network that doesn't exist "
                "on Host"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from DC", config.NETWORKS[0])
        if not removeNetwork(
            positive=True, network=config.NETWORKS[0],
            data_center=config.DC_NAME[0]
        ):

            logger.error(
                "Couldn't remove network %s from DC", config.NETWORKS[0]
            )


@attr(tier=2)
class TestVNICProfileCase08(TestCase):

    """
    Verify different scenarios of changing VNIC profiles on
    the unplugged VNIC of the running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 logical vm networks on DC/Cluster with
           2 default VNIC profiles
        2) Add to the second network 2 additional VNIC profiles
        3) Put on the unplugged nic2 vnic profile sw1 of network sw1
        """
        local_dict = {
            config.NETWORKS[0]: {
                "required": "false", "vlan_id": config.VLAN_ID[0], "nic": 1
            },
            config.NETWORKS[1]: {
                "required": "false", "vlan_id": config.VLAN_ID[1], "nic": 1
            }
        }
        logger.info("Creating networks with default vnic profile")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach networks")

        logger.info(
            "Creating additional profiles for network %s", config.NETWORKS[1]
        )
        name_net1 = "_".join([config.NETWORKS[1], "1"])
        name_net2 = "_".join([config.NETWORKS[1], "2"])
        if not add_vnic_profile(
            positive=True, name=name_net1, data_center=config.DC_NAME[0],
            network=config.NETWORKS[1]
        ):
            raise NetworkException(
                "Couldn't create %s VNIC profile" % name_net1
            )
        if not add_vnic_profile(
            positive=True, name=name_net2, data_center=config.DC_NAME[0],
            network=config.NETWORKS[1], port_mirroring=True
        ):
            raise NetworkException(
                "Couldn't create %s VNIC profile" % name_net2
            )

        logger.info("Add VNIC with network %s to VM", config.NETWORKS[0])
        if not addNic(
            True, config.VM_NAME[0], name=config.NIC_NAME[1],
            network=config.NETWORKS[0], plugged="false"
        ):
            raise NetworkException("Cannot add VNIC to VM")

    @polarion("RHEVM3-3981")
    def test_update_network_unplugged_nic(self):
        """
        1) Update VNIC profile on nic2 with profile from different network
        2) Update VNIC profile on nic2 with profile from the same network
        3) Update VNIC profile on nic2 with profile from the same network
        but with port mirroring enabled
        4) Update VNIC profile on nic2 with profile having port mirroring
        enabled to different network with port mirroring disabled
        """
        logger.info(
            "Changing VNIC to have VNIC profile from another network. "
            "Change from %s to %s", config.NETWORKS[0], config.NETWORKS[1]
        )
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1],
            network=config.NETWORKS[1],
            vnic_profile=config.NETWORKS[1]
        ):
            raise NetworkException(
                "Changing VNIC to have VNIC profile from another network - "
                "%s to %s" % (config.NETWORKS[0], config.NETWORKS[1])
            )

        logger.info("Changing VNIC to have VNIC profile from the same network")
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1],
            network=config.NETWORKS[1],
            vnic_profile="_".join([config.NETWORKS[1], "1"])
        ):
            raise NetworkException(
                "Changing VNIC to have VNIC profile for the same network"
                " failed"
            )
        logger.info(
            "Changing VNIC to have VNIC profile for the same network"
            "but with port_mirroring enabled"
        )
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1],
            network=config.NETWORKS[1],
            vnic_profile="_".join([config.NETWORKS[1], "2"])
        ):
            raise NetworkException(
                "Changing VNIC to have VNIC profile from the same network"
                "but with port_mirroring enabled failed"
            )

        logger.info(
            "Changing VNIC to have VNIC profile from another network "
            "without port_mirroring"
        )
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1],
            network=config.NETWORKS[0], vnic_profile=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Changing VNIC to have VNIC profile from another network "
                "without port_mirroring failed"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove VM networks from the setup
        """
        if not removeNic(True, config.VM_NAME[0], config.NIC_NAME[1]):
            raise NetworkException("Cannot remove nic from setup")
        for i in range(2):
            logger.info("Remove network %s from setup", config.NETWORKS[i])
            if not remove_net_from_setup(
                host=config.HOSTS[0], network=[config.NETWORKS[i]]
            ):
                logger.error(
                    "Cannot remove network %s from setup", config.NETWORKS[i]
                )


@attr(tier=2)
class TestVNICProfileCase09(TestCase):

    """
    VNIC Profile on template
    """
    __test__ = True
    vm_name2 = "new_VM_case09"

    @classmethod
    def setup_class(cls):
        """
        Create logical network on DC/Cluster
        """
        local_dict = {
            config.NETWORKS[0]: {"required": "false"}
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3993")
    def test_create_new_profiles_template(self):
        """
        1) Check that you can create non-empty VNIC profile on Template
        2) Check that you can create empty VNIC profile on Template
        3) Create VM from the template with empty and non-empty profiles
        4) Make sure this VM has empty and non-empty profiles on it's NICs
        """

        logger.info(
            "Creating new profile %s for network %s on template %s",
            config.NETWORKS[0], config.NETWORKS[0], config.TEMPLATE_NAME[0]
        )
        if not addTemplateNic(
            positive=True, template=config.TEMPLATE_NAME[0],
            name=config.NIC_NAME[1], data_center=config.DC_NAME[0],
            network=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Couldn't add NIC with %s VNIC profile" % config.NETWORKS[0]
            )

        logger.info(
            "Add NIC to template with empty Network"
        )
        if not addTemplateNic(
            positive=True, template=config.TEMPLATE_NAME[0],
            name=config.NIC_NAME[2], data_center=config.DC_NAME[0],
            network=None
        ):
            raise NetworkException(
                "Couldn't add NIC with empty network to VM"
            )

        logger.info("Create VM from template")
        if not createVm(
            positive=True, vmName=self.vm_name2, vmDescription="",
            cluster=config.CLUSTER_NAME[0], template=config.TEMPLATE_NAME[0],
            network=config.MGMT_BRIDGE
        ):
            raise NetworkException("Couldn't create VM from template")

        logger.info("Check VNIC profile %s exists on VM", config.NETWORKS[0])
        if not checkVmNicProfile(
            vm=self.vm_name2, vnic_profile_name=config.NETWORKS[0],
            nic=config.NIC_NAME[1]
        ):
            raise NetworkException("Couldn't get correct VNIC profile on VM ")

        logger.info("Check empty VNIC profile exists on VM")
        if not checkVmNicProfile(
            vm=self.vm_name2, vnic_profile_name=None, nic=config.NIC_NAME[2]
        ):
            raise NetworkException("Couldn't get empty VNIC profile on VM ")

    @polarion("RHEVM3-3977")
    def test_remove_new_profiles_template(self):
        """
        1) Remove VM created from the previous test
        2) Try to remove network when template is using its VNIC profile.
           This test is the negative one
        3) Remove VNIC profile from the template
        4) Remove VNIC profile from the setup
        """
        logger.info("Remove created VM from setup")
        if not removeVm(positive=True, vm=self.vm_name2):
            raise NetworkException(
                "Couldn't remove VM %s from setup" % self.vm_name2
            )

        logger.info(
            "Try to remove network from setup and fail doing so as network "
            "resides on the template"
        )
        if removeNetwork(
            positive=True, network=config.NETWORKS[0],
            data_center=config.DC_NAME[0]
        ):
            raise NetworkException(
                "Could remove network from DC when template is using it"
            )

        logger.info("Remove NIC %s from template", config.NIC_NAME[1])
        if not removeTemplateNic(
            True, template=config.TEMPLATE_NAME[0], nic=config.NIC_NAME[1]
        ):
            raise NetworkException("Couldn't remove NIC from template")

        logger.info("Remove VNIC profile %s", config.NETWORKS[0])
        if not removeVnicProfile(
            positive=True, vnic_profile_name=config.NETWORKS[0],
            network=config.NETWORKS[0]
        ):
            raise NetworkException("Couldn't remove VNIC profile")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove NIC from template")
        if not removeTemplateNic(
            positive=True, template=config.TEMPLATE_NAME[0],
            nic=config.NIC_NAME[2]
        ):
            raise NetworkException("Couldn't remove NIC from template")

        logger.info("Remove network from setup")
        if not removeNetwork(
            positive=True, network=config.NETWORKS[0],
            data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Couldn't remove network %s from setup", config.NETWORKS[0]
            )


@attr(tier=2)
class TestVNICProfileCase10(TestCase):

    """
    Verify it's impossible to change VNIC profile without port mirroring to
    VNIC profile with port mirroring and vice versa on running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 logical vm networks on DC/Cluster with
           2 default VNIC profiles
        2) Update the second network additional VNIC profile with PM
        3) Put on the nic2 VNIC profile sw1 of network sw1 without PM
        4) Put on the nic3 VNIC profile sw2_1 of network sw2 with PM

        """
        local_dict = {
            config.NETWORKS[0]: {
                "required": "false", "vlan_id": config.VLAN_ID[0], "nic": 1
            },
            config.NETWORKS[1]: {
                "required": "false", "vlan_id": config.VLAN_ID[1], "nic": 1
            }
        }

        logger.info("Creating networks with default vnic profiles")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach networks")

        logger.info(
            "Update VNIC profile to have port mirroring enabled for %s",
            config.NETWORKS[1]
        )
        if not update_vnic_profile(
            name=config.NETWORKS[1], network=config.NETWORKS[1],
            port_mirroring=True
        ):
            raise NetworkException(
                "Couldn't to update profile to have PM enabled"
            )

        logger.info("Add NICs %s to VM", config.NIC_NAME[2:4])
        for i in range(2):
            if not addNic(
                True, config.VM_NAME[0], name="".join(["nic", str(i + 2)]),
                network=config.NETWORKS[i]
            ):
                raise NetworkException("Cannot add VNIC to VM")

    @polarion("RHEVM3-3976")
    def test_update_vnic_profile(self):
        """
        1) Try to update VNIC profile on nic2 to have port mirroring enabled
        2) Try to update VNIC profile on nic3 to have port mirroring disabled
        """

        logger.info(
            "Trying to change VNIC profile attached to VM on nic2 to have "
            "port mirroring enabled"
        )
        if update_vnic_profile(
            name=config.NETWORKS[0], network=config.NETWORKS[0],
            port_mirroring=True
        ):
            raise NetworkException("Was able to update PM on running VM")

        logger.info(
            "Trying to change VNIC profile attached to VM on nic3 to have "
            "port mirroring disabled"
        )
        if update_vnic_profile(
            name=config.NETWORKS[1], network=config.NETWORKS[1],
            port_mirroring=False
        ):
            raise NetworkException("Was able to update PM on running VM")

    @classmethod
    def teardown_class(cls):
        """
        Remove VM networks from the setup
        """
        logger.info(
            "Updating nic2 and nic3 to be unplugged and then remove them"
        )
        for nic_name in (config.NIC_NAME[1], config.NIC_NAME[2]):
            if not updateNic(
                True, config.VM_NAME[0], nic_name, plugged="false"
            ):
                logger.error("Couldn't unplug NICs")
            if not removeNic(True, config.VM_NAME[0], nic_name):
                logger.error("Cannot remove nic from setup")

        for i in range(2):
            logger.info("Remove network %s from setup", config.NETWORKS[i])
            if not remove_net_from_setup(
                host=config.HOSTS[0], network=[config.NETWORKS[i]]
            ):
                logger.error(
                    "Cannot remove network %s from setup", config.NETWORKS[i]
                )


@attr(tier=2)
class TestVNICProfileCase11(TestCase):

    """
    Verify different scenarios of changing VNIC profiles on
    plugged VNIC of the running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 logical vm networks on DC/Cluster with
           2 default VNIC profiles
        2) Add to the second network 2 additional VNIC profiles
        3) Plug nic2 vnic and attach to it profile sw1 of network sw1

        """
        local_dict = {
            config.NETWORKS[0]: {
                "required": "false", "vlan_id": config.VLAN_ID[0], "nic": 1
            },
            config.NETWORKS[1]: {
                "required": "false", "vlan_id": config.VLAN_ID[1], "nic": 1
            }
        }
        logger.info("Creating networks with default vnic profiles")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach networks")

        logger.info(
            "Creating additional profiles for network %s", config.NETWORKS[1]
        )
        name_net1 = "_".join([config.NETWORKS[1], "1"])
        name_net2 = "_".join([config.NETWORKS[1], "2"])
        if not add_vnic_profile(
            positive=True, name=name_net1, data_center=config.DC_NAME[0],
            network=config.NETWORKS[1]
        ):
            raise NetworkException(
                "Couldn't create %s VNIC profile" % name_net1
            )
        if not add_vnic_profile(
            positive=True, name=name_net2, data_center=config.DC_NAME[0],
            network=config.NETWORKS[1], port_mirroring=True
        ):
            raise NetworkException(
                "Couldn't create %s VNIC profile" % name_net2
            )
        if not addNic(
            True, config.VM_NAME[0], name=config.NIC_NAME[1],
            network=config.NETWORKS[0], plugged="true"
        ):
            raise NetworkException("Cannot add VNIC to VM")

    @polarion("RHEVM3-3986")
    def test_update_network_plugged_nic(self):
        """
        1) Update VNIC profile on nic2 with profile from different network
        2) Update VNIC profile on nic2 with profile from the same network
        3) Try to update VNIC profile on nic2 with profile from the same
        network but with port mirroring enabled (negative case)
        4) Update VNIC profile on nic2 with empty profile
        5) Update VNIC profile on nic2 with profile having port mirroring
        enabled (first unplug and after the action plug nic2)
        6) Try to update VNIC profile on nic2 with profile from the same
        network but with port mirroring disabled (negative case)
        """
        logger.info("Changing VNIC to have VNIC profile from another network")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1, func=updateNic,
            positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[1],
            network=config.NETWORKS[1], vnic_profile=config.NETWORKS[1]
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException(
                "Couldn't change VNIC profile to profile with different "
                "network"
            )
        logger.info("Changing VNIC to have VNIC profile from the same network")
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1],
            network=config.NETWORKS[1],
            vnic_profile="_".join([config.NETWORKS[1], "1"])
        ):
            raise NetworkException(
                "Changing VNIC profile to have another VNIC profile from the "
                "same network failed"
            )

        logger.info(
            "Try changing VNIC to have VNIC profile from the same network but "
            "with port_mirroring enabled (negative case)"
        )
        if not updateNic(
            False, config.VM_NAME[0], config.NIC_NAME[1],
            network=config.NETWORKS[1],
            vnic_profile="_".join([config.NETWORKS[1], "2"])
        ):
            raise NetworkException(
                "Changing VNIC profile to have port mirroring enabled "
                "succeeded when should not"
            )

        logger.info("Changing VNIC to have empty VNIC profile ")
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], network=None
        ):
            raise NetworkException(
                "Changing VNIC to have empty VNIC profile failed"
            )

        logger.info(
            "Updating nic2 to be unplugged to put there VNIC profile "
            "with port mirroring enabled"
        )
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="false"
        ):
            raise NetworkException(
                "Updating %s to be unplugged failed" % config.NIC_NAME[1]
            )

        logger.info(
            "Changing VNIC to have VNIC profile with port_mirroring enabled "
        )
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1],
            network=config.NETWORKS[1],
            vnic_profile="_".join([config.NETWORKS[1], "2"])
        ):
            raise NetworkException(
                "Updating VNIC profile to have PM enabled failed"
            )

        logger.info(
            "Updating nic2 to be plugged to test the case of changing VNIC "
            "profile with port mirroring to VNIC profile without "
            "port mirroring"
        )
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="true"
        ):
            raise NetworkException(
                "Change %s to be plugged" % config.NIC_NAME[1]
            )

        logger.info(
            "Try changing VNIC to have VNIC profile from the same "
            "network but with port mirroring disabled (negative case)"
        )
        if not updateNic(
            False, config.VM_NAME[0], config.NIC_NAME[1],
            network=config.NETWORKS[1],
            vnic_profile="_".join([config.NETWORKS[1], "1"])
        ):
            raise NetworkException(
                "Updating VNIC profile to have PM disabled succeeded"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove VM networks from the setup
        """
        logger.info("Unplug %s and then remove it", config.NIC_NAME[1])
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="false"
        ):
            logger.error("Cannot unplug %s", config.NIC_NAME[1])
        if not removeNic(True, config.VM_NAME[0], config.NIC_NAME[1]):
            logger.error("Cannot remove %s from setup", config.NIC_NAME[1])

        for i in range(2):
            logger.info("Remove network %s from setup", config.NETWORKS[i])
            if not remove_net_from_setup(
                host=config.HOSTS[0], network=[config.NETWORKS[i]]
            ):
                logger.error(
                    "Cannot remove network %s from setup", config.NETWORKS[i]
                )


@attr(tier=2)
class TestVNICProfileCase12(TestCase):

    """
    Verify uniqueness of VNIC profile
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm networks on DC/Cluster
        """
        local_dict = {
            config.NETWORKS[0]: {"required": "false"},
            config.NETWORKS[1]: {"required": "false"}
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-3975")
    def test_create_new_profiles(self):
        """
        Negative case: Try to update network for existing profile
        """
        logger.info(
            "Try updating profile %s with  another network %s",
            config.NETWORKS[0], config.NETWORKS[1]
        )
        if update_vnic_profile(
            name=config.NETWORKS[0], network=config.NETWORKS[0],
            cluster=config.CLUSTER_NAME[0], new_network=config.NETWORKS[1]
        ):
            raise NetworkException(
                "Could update VNIC profile with another network while the "
                "update should fail"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove networks from DC")
        for i in range(2):
            if not removeNetwork(
                positive=True, network=config.NETWORKS[i],
                data_center=config.DC_NAME[0]
            ):
                logger.error(
                    "Couldn't remove network %s from setup", config.NETWORKS[i]
                )


@attr(tier=2)
class TestVNICProfileCase13(TestCase):

    """
    Verify hotplug, link/unlink works on the running VM
    Try to remove VNIC profile when VM is using it (negative case)
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 1 logical vm networks on DC/Cluster/Host/VM with
        default VNIC profile
        """
        local_dict = {
            config.NETWORKS[0]: {"required": "false", "nic": 1}
        }
        logger.info("Creating network with default vnic profile")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach networks")

    @polarion("RHEVM3-3987")
    def test_hotplug_link_unlink(self):
        """
        1) Hotplug VNIC profile to the VMs nic2
        2) Unlink nic2
        3) Link nic2
        """

        logger.info("Hotplug %s profile to VM on nic2", config.NETWORKS[0])
        if not addNic(
            True, config.VM_NAME[0], name=config.NIC_NAME[1],
            network=config.NETWORKS[0], plugged="true"
        ):
            raise NetworkException("Cannot add VNIC to VM")

        logger.info("Changing VNIC to unlink")
        sample = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1, func=updateNic,
            positive=True, vm=config.VM_NAME[0],  nic=config.NIC_NAME[1],
            linked="false"
        )
        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't update correct linked state")

        logger.info("Changing VNIC to linked")
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], linked="true"
        ):
            raise NetworkException(
                "Changing %s to linked stated failed" % config.NIC_NAME[1]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove VM networks from the setup
        """
        logger.info("Unplug and then remove %s", config.NIC_NAME[1])
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="false"
        ):
            logger.error("Cannot unplug %s", config.NIC_NAME[1])
        if not removeNic(True, config.VM_NAME[0], config.NIC_NAME[1]):
            logger.error("Cannot remove %s from setup", config.NIC_NAME[1])

        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(
            host=config.HOSTS[0], network=[config.NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )


@attr(tier=2)
class TestVNICProfileCase14(TestCase):

    """
    Try to remove VNIC profile when VM is using it (negative case)
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 1 logical vm networks on DC/Cluster/Host/VM with
        default VNIC profile
        2) Add NIC2 to VM
        """
        local_dict = {
            config.NETWORKS[0]: {
                "required": "false", "nic": 1
            }
        }

        logger.info("Creating network with default vnic profile")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach networks")

        logger.info("Hotplug %s profile to VM on nic2", config.NETWORKS[0])
        if not addNic(
            True, config.VM_NAME[0], name=config.NIC_NAME[1],
            network=config.NETWORKS[0], plugged="true"
        ):
            raise NetworkException("Cannot add VNIC to VM")

    @polarion("RHEVM3-3985")
    def test_remove_used_profile(self):
        """
        Try to remove VNIC profile while VM is using it (negative case)
        """
        logger.info(
            "Try to remove %s profile when VM is using it", config.NETWORKS[0]
        )
        if not removeVnicProfile(
            positive=False, vnic_profile_name=config.NETWORKS[0],
            network=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Could remove VNIC profile although VM is using it"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove VM networks from the setup
        """
        logger.info("Unplug and then remove %s", config.NIC_NAME[1])
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="false"
        ):
            logger.error("Cannot unplug %s", config.NIC_NAME[1])
        if not removeNic(True, config.VM_NAME[0], config.NIC_NAME[1]):
            logger.error("Cannot remove %s from setup", config.NIC_NAME[1])

        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(
            host=config.HOSTS[0], network=[config.NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )


@attr(tier=2)
class TestVNICProfileCase15(TestCase):

    """
    Create new VNIC profile and make sure all its parameters exist in API
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster
        Create additional VNIC profile with Description, Port mirroring
        """
        local_dict = {config.NETWORKS[0]: {"required": "false"}}

        logger.info(
            "Creating network %s with default vnic profile %s",
            config.NETWORKS[0], config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException("Cannot create and attach network")

        logger.info(
            "Creating additional profile %s for network %s",
            config.NETWORKS[1], config.NETWORKS[0]
        )
        if not add_vnic_profile(
            positive=True, name=config.NETWORKS[1],
            data_center=config.DC_NAME[0], network=config.NETWORKS[0],
            port_mirroring=True, description="vnic_p_desc"
        ):
            raise NetworkException("Couldn't create second VNIC profile")

    @polarion("RHEVM3-3970")
    def test_check_attr(self):
        """
        Check VNIC profile created with parameters has these parameters
        """
        attr_dict = get_vnic_profile_attr(
            name=config.NETWORKS[1], network=config.NETWORKS[0],
            attr_list=["description", "port_mirroring", "name"]
        )
        if (
                attr_dict.get("description") != "vnic_p_desc" or
                attr_dict.get("port_mirroring") is not True or
                attr_dict.get("name") != config.NETWORKS[1]
        ):
            raise NetworkException("Attributes are not equal to what was set")

    @classmethod
    def teardown_class(cls):
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(
            host=config.HOSTS[0], network=[config.NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )
