#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing network VM QoS feature.
1 DC, 1 Cluster, 2 Hosts and 1 VM will be created for testing.
Create, update, remove and migration tests will be done for Network QoS feature
"""

import logging

import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import helper
import pytest
from _pytest_art.marks import tier2
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest as TestCase
from art.unittest_lib import attr

logger = logging.getLogger("Network_VNIC_QoS_Tests")


########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@tier2
@attr(tier=2)
class TestNetQOSCase01(TestCase):
    """
    Add new network QOS
    """
    __test__ = True
    qos_name = config.QOS_NAME[1][0]
    vnic_profile = config.VNIC_PROFILE[0]

    @polarion("RHEVM3-3998")
    def test_add_network_qos(self):
        """
        1) Create new Network QoS profile under DC
        2) Provide Inbound and Outbound parameters for this QOS
        3) Create VNIC profile with configured QoS and add it to the NIC of
        the VM
        4) Check that provided bw values are the same as the values
        configured on libvirt

        """
        logger.info("Create new Network QoS profile under DC")
        if not ll_datacenters.add_qos_to_datacenter(
            datacenter=config.DC_NAME,
            qos_name=self.qos_name, qos_type=config.QOS_TYPE,
            inbound_average=config.BW_PARAMS[0],
            inbound_peak=config.BW_PARAMS[1],
            inbound_burst=config.BW_PARAMS[2],
            outbound_average=config.BW_PARAMS[0],
            outbound_peak=config.BW_PARAMS[1],
            outbound_burst=config.BW_PARAMS[2]
        ):
            raise config.NET_EXCEPTION("Couldn't create Network QOS under DC")

        logger.info("Create VNIC profile with QoS and add it to the VNIC")
        helper.add_qos_profile_to_nic(
            qos_name=self.qos_name, vnic_profile_name=self.vnic_profile
        )
        inbound_dict = {
            "average": config.BW_PARAMS[0],
            "peak": config.BW_PARAMS[1],
            "burst": config.BW_PARAMS[2]
        }
        outbound_dict = {
            "average": config.BW_PARAMS[0],
            "peak": config.BW_PARAMS[1],
            "burst": config.BW_PARAMS[2]
        }

        dict_compare = helper.build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME_0, nic=config.NIC_NAME_1
        )

        logger.info(
            "Compare provided QoS %s and %s exists with libvirt values",
            inbound_dict, outbound_dict
        )
        if not helper.compare_qos(
            host_obj=config.VDS_HOST, vm_name=config.VM_NAME_0,
            **dict_compare
        ):
            raise config.NET_EXCEPTION(
                "Provided QoS values %s and %s are not equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )

    @classmethod
    def teardown_class(cls):
        """
        1) Remove VNIC from VM.
        2) Remove VNIC profile
        3) Remove Network QoS
        """
        logger.info(
            "Remove VNIC %s from VM %s", config.NIC_NAME_1, config.VM_NAME_0
        )
        if not ll_vms.updateNic(
            True, config.VM_NAME_0, config.NIC_NAME_1, plugged="false"
        ):
            logger.error("Couldn't unplug NIC %s", config.NIC_NAME_1)

        if not ll_vms.removeNic(True, config.VM_NAME_0, config.NIC_NAME_1):
            logger.error(
                "Couldn't remove VNIC %s from VM %s",
                config.NIC_NAME_1, config.VM_NAME_0
            )
        logger.info("Remove VNIC profile %s", cls.vnic_profile)
        if not ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=cls.vnic_profile,
            network=config.MGMT_BRIDGE, data_center=config.DC_NAME
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", cls.vnic_profile
            )
        if not ll_datacenters.delete_qos_from_datacenter(
            config.DC_NAME, cls.qos_name
        ):
            logger.error(
                "Couldn't delete the QoS %s from DC %s",
                cls.qos_name, config.DC_NAME
            )


@tier2
@attr(tier=2)
@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class TestNetQOSCase02(TestCase):
    """
    Update Network QoS
    """
    __test__ = True
    qos_name = config.QOS_NAME[2][0]
    vnic_profile = config.VNIC_PROFILE[1]

    @classmethod
    def setup_class(cls):
        """
        1) Create new Network QoS profile under DC
        2) Provide Inbound and Outbound parameters for this QOS
        3) Create VNIC profile with configured QoS and add it to the NIC of
        the VM
        """
        logger.info("Create new Network QoS profile under DC")
        if not ll_datacenters.add_qos_to_datacenter(
            datacenter=config.DC_NAME,
            qos_name=cls.qos_name, qos_type=config.QOS_TYPE,
            inbound_average=config.BW_PARAMS[0],
            inbound_peak=config.BW_PARAMS[1],
            inbound_burst=config.BW_PARAMS[2],
            outbound_average=config.BW_PARAMS[0],
            outbound_peak=config.BW_PARAMS[1],
            outbound_burst=config.BW_PARAMS[2]
        ):
            raise config.NET_EXCEPTION(
                "Couldn't create Network QOS %s under DC" % cls.qos_name
            )
        logger.info(
            "Create VNIC profile with QoS %s and add it to the VNIC on %s",
            cls.qos_name, config.VM_NAME_0
        )
        helper.add_qos_profile_to_nic(
            qos_name=cls.qos_name, vnic_profile_name=cls.vnic_profile
        )

        logger.info(
            "Add VNIC with VNIC profile %s with QOS %s to VM %s",
            cls.vnic_profile, cls.qos_name, config.VM_NAME_1
        )
        if not ll_vms.addNic(
            True, config.VM_NAME_1, name=config.NIC_NAME_1,
            network=config.MGMT_BRIDGE, vnic_profile=cls.vnic_profile
        ):
            raise config.NET_EXCEPTION(
                "Couldn't add VNIC with QoS to VM %s" % config.VM_NAME_1
            )

    @polarion("RHEVM3-3999")
    def test_update_network_qos(self):
        """
        1) Update existing QoS profile for DC
        2) Change the name of QoS and provide Inbound and
        Outbound parameters different than before
        3) Check that for VM that is down, the specific VNIC profile got
        the changes of QoS (when started)
        4) Check that VM that is up will get the change of VNIC profile
         after the VM reboot (or unplug/plug)
        """
        logger.info(
            "Update existing Network QoS profile under DC"
        )
        if not ll_datacenters.update_qos_in_datacenter(
            datacenter=config.DC_NAME,
            qos_name=self.qos_name, new_name="newQoS",
            inbound_average=config.UPDATED_BW_PARAMS[0],
            inbound_peak=config.UPDATED_BW_PARAMS[1],
            inbound_burst=config.UPDATED_BW_PARAMS[2],
            outbound_average=config.UPDATED_BW_PARAMS[0],
            outbound_peak=config.UPDATED_BW_PARAMS[1],
            outbound_burst=config.UPDATED_BW_PARAMS[2]
        ):
            raise config.NET_EXCEPTION("Couldn't update Network QOS under DC")

        inbound_dict = {
            "average": config.UPDATED_BW_PARAMS[0],
            "peak": config.UPDATED_BW_PARAMS[1],
            "burst": config.UPDATED_BW_PARAMS[2]
        }
        outbound_dict = {
            "average": config.UPDATED_BW_PARAMS[0],
            "peak": config.UPDATED_BW_PARAMS[1],
            "burst": config.UPDATED_BW_PARAMS[2]
        }
        dict_compare = helper.build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME_0, nic=config.NIC_NAME_1
        )

        logger.info(
            "Check provided QoS %s and %s doesn't match libvirt values",
            inbound_dict, outbound_dict
        )
        if helper.compare_qos(
            host_obj=config.VDS_HOST, vm_name=config.VM_NAME_0,
            **dict_compare
        ):
            raise config.NET_EXCEPTION(
                "Provided QoS values %s and %s are equal to what was found on"
                " libvirt, but shouldn't" % (inbound_dict, outbound_dict)
            )

        logger.info(
            "Start vm %s on host %s", config.VM_NAME_1, config.HOST
        )
        if not ll_vms.startVm(
            positive=True, vm=config.VM_NAME_1, placement_host=config.HOST
        ):
            raise config.NET_EXCEPTION(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME_1, config.HOST)
            )

        logger.info(
            "Unplug and plug %s on %s", config.NIC_NAME_1, config.VM_NAME_0
        )
        if not ll_vms.updateNic(
            True, config.VM_NAME_0, config.NIC_NAME_1, plugged="false"
        ):
            logger.error("Couldn't unplug %s", config.NIC_NAME_1)

        if not ll_vms.updateNic(
            True, config.VM_NAME_0, config.NIC_NAME_1, plugged="true"
        ):
            logger.error("Couldn't plug %s", config.NIC_NAME_1)

        logger.info(
            "Check that provided QoS values %s and %s are equal to what was"
            " found on libvirt for both VMs", inbound_dict, outbound_dict
        )
        for i in range(2):
            if not helper.compare_qos(
                host_obj=config.VDS_HOST, vm_name=config.VM_NAME[i],
                **dict_compare
            ):
                raise config.NET_EXCEPTION(
                    "Provided QoS values %s and %s are not equal to what was "
                    "found on libvirt" % (inbound_dict, outbound_dict)
                )

    @classmethod
    def teardown_class(cls):
        """
        1) Stop second VM
        2) Remove VNIC from VMs.
        3) Remove Network QoS
        4) Remove VNIC profile
        """
        logger.info("Stop VM %s", config.VM_NAME_1)
        if not ll_vms.stopVm(True, vm=config.VM_NAME_1):
            logger.error("Couldn't stop VM %s", config.VM_NAME_1)

        logger.info("Remove VNIC from VMs %s", config.VM_NAME[:2])
        for i in range(2):
            if not ll_vms.updateNic(
                True, config.VM_NAME[i], config.NIC_NAME_1, plugged="false"
            ):
                logger.error("Couldn't unplug NIC on %s", config.VM_NAME[i])
            if not ll_vms.removeNic(
                True, config.VM_NAME[i], config.NIC_NAME_1
            ):
                logger.error(
                    "Couldn't remove VNIC from VM %s", config.VM_NAME[i]
                )
        logger.info("Remove the QoS newQoS from DC")
        if not ll_datacenters.delete_qos_from_datacenter(
            config.DC_NAME, "newQoS"
        ):
            logger.error(
                "Couldn't delete the QoS newQoS from DC %s", config.DC_NAME
            )
        logger.info("Remove VNIC profile %s", cls.vnic_profile)
        if not ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=cls.vnic_profile,
            network=config.MGMT_BRIDGE, data_center=config.DC_NAME
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", cls.vnic_profile
            )


@tier2
@attr(tier=2)
@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class TestNetQOSCase03(TestCase):
    """
    Remove Network QoS
    """
    __test__ = True
    qos_name = config.QOS_NAME[3][0]
    vnic_profile = config.VNIC_PROFILE[2]

    @classmethod
    def setup_class(cls):
        """
        1) Create new Network QoS profile under DC
        2) Provide Inbound and Outbound parameters for this QOS
        3) Create VNIC profile with configured QoS and add it to the NIC of
        the VM that is up and to the NIC of the VM that is down
        """
        logger.info("Create new Network QoS profile under DC")
        if not ll_datacenters.add_qos_to_datacenter(
            datacenter=config.DC_NAME,
            qos_name=cls.qos_name, qos_type=config.QOS_TYPE,
            inbound_average=config.BW_PARAMS[0],
            inbound_peak=config.BW_PARAMS[1],
            inbound_burst=config.BW_PARAMS[2],
            outbound_average=config.BW_PARAMS[0],
            outbound_peak=config.BW_PARAMS[1],
            outbound_burst=config.BW_PARAMS[2]
        ):
            raise config.NET_EXCEPTION(
                "Couldn't create Network QOS %s under DC" % cls.qos_name
            )
        logger.info(
            "Create VNIC profile with QoS %s and add it to the VNIC on %s",
            cls.qos_name, config.VM_NAME_0
        )
        helper.add_qos_profile_to_nic(
            qos_name=cls.qos_name, vnic_profile_name=cls.vnic_profile
        )
        logger.info(
            "Add VNIC with VNIC profile %s with QOS %s to non-running VM %s",
            cls.vnic_profile, cls.qos_name, config.VM_NAME_1
        )
        if not ll_vms.addNic(
            True, config.VM_NAME_1, name=config.NIC_NAME_1,
            network=config.MGMT_BRIDGE, vnic_profile=cls.vnic_profile
        ):
            raise config.NET_EXCEPTION(
                "Couldn't add VNIC with QoS %s to VM %s" %
                (cls.qos_name, config.VM_NAME_1)
            )

    @polarion("RHEVM3-4000")
    def test_remove_network_qos(self):
        """
        1) Remove QoS profile
        2) Check that the change is applicable on the VM that is down and
        it got "unlimited" QoS (after start VM)
        3) Check that the change is applicable on the VM that is up after
        unplug/plug
        """

        logger.info("Remove the QoS from DC")
        if not ll_datacenters.delete_qos_from_datacenter(
            config.DC_NAME, self.qos_name
        ):
            raise config.NET_EXCEPTION(
                "Couldn't delete the QoS %s from DC %s" %
                (self.qos_name, config.DC_NAME)
            )

        dict_compare = helper.build_dict(
            inbound_dict={}, outbound_dict={},
            vm=config.VM_NAME_0, nic=config.NIC_NAME_1
        )

        logger.info(
            "Check that after deletion of QoS libvirt is not updated with "
            "unlimited values till plug/unplug action"
        )
        if helper.compare_qos(
            host_obj=config.VDS_HOST, vm_name=config.VM_NAME_0,
            **dict_compare
        ):
            raise config.NET_EXCEPTION(
                "Libvirt has unlimited bandwidth configuration but shouldn't"
            )

        logger.info(
            "Start vm %s on host %s", config.VM_NAME_1, config.HOST
        )
        if not ll_vms.startVm(
            positive=True, vm=config.VM_NAME_1, placement_host=config.HOST
        ):
            raise config.NET_EXCEPTION(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME_1, config.HOST)
            )

        logger.info("Unplug and plug NIC on %s", config.VM_NAME_0)
        if not ll_vms.updateNic(
            True, config.VM_NAME_0, config.NIC_NAME_1, plugged="false"
        ):
            raise config.NET_EXCEPTION(
                "Couldn't unplug NIC %s" % config.NIC_NAME_1
            )
        if not ll_vms.updateNic(
            True, config.VM_NAME_0, config.NIC_NAME_1, plugged="true"
        ):
            raise config.NET_EXCEPTION(
                "Couldn't plug NIC %s" % config.NIC_NAME_1
            )

        logger.info(
            "Check that libvirt Network QoS values were updated to be "
            "unlimited"
        )
        for i in range(2):
            if not helper.compare_qos(
                host_obj=config.VDS_HOST, vm_name=config.VM_NAME[i],
                **dict_compare
            ):
                raise config.NET_EXCEPTION(
                    "Libvirt Network QoS values were not updated to be "
                    "unlimited"
                )

    @classmethod
    def teardown_class(cls):
        """
       1) Stop second VM
       2) Remove VNIC from VMs.
       3) Remove VNIC profile
       """
        logger.info("Stop VM %s", config.VM_NAME_1)
        if not ll_vms.stopVm(True, vm=config.VM_NAME_1):
            logger.error("Couldn't stop VM %s", config.VM_NAME_1)

        logger.info("Remove VNIC from VMs %s", config.VM_NAME[:2])
        for i in range(2):
            if not ll_vms.updateNic(
                True, config.VM_NAME[i], config.NIC_NAME_1, plugged="false"
            ):
                logger.error(
                    "Couldn't unplug NIC %s on VM %s",
                    config.NIC_NAME_1, config.VM_NAME[i]
                )
            if not ll_vms.removeNic(
                True, config.VM_NAME[i], config.NIC_NAME_1
            ):
                logger.error(
                    "Couldn't remove VNIC %s from VM %s",
                    config.NIC_NAME_1, config.VM_NAME[i]
                )

        logger.info("Remove VNIC profile %s", cls.vnic_profile)
        if not ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=cls.vnic_profile,
            network=config.MGMT_BRIDGE, data_center=config.DC_NAME
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", cls.vnic_profile
            )


@tier2
@attr(tier=2)
@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class TestNetQOSCase04(TestCase):
    """
    Network QoSs, configured on several VNIC profiles
    """
    __test__ = True
    qos_names = config.QOS_NAME[4][:2]
    vnic_profiles = config.VNIC_PROFILE[3:5]

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 Network QoS profiles under DC
        2) Provide Inbound and Outbound parameters for this QOS
        3) Create VNIC profile with configured QoS and add it to the NIC of
        the VM that is up
        4) Create additional VNIC profile on VM
        5) Update its Network QoS value
        """
        logger.info("Create new Network QoS profiles under DC")
        for qos_name in cls.qos_names:
            if not ll_datacenters.add_qos_to_datacenter(
                datacenter=config.DC_NAME,
                qos_name=qos_name, qos_type=config.QOS_TYPE,
                inbound_average=config.BW_PARAMS[0],
                inbound_peak=config.BW_PARAMS[1],
                inbound_burst=config.BW_PARAMS[2],
                outbound_average=config.BW_PARAMS[0],
                outbound_peak=config.BW_PARAMS[1],
                outbound_burst=config.BW_PARAMS[2]
            ):
                raise config.NET_EXCEPTION(
                    "Couldn't create Network QOS %s under DC" % qos_name
                )
        logger.info(
            "Create VNIC profile with QoS and add it to the VNIC on running VM"
        )

        helper.add_qos_profile_to_nic(
            qos_name=cls.qos_names[0], vnic_profile_name=cls.vnic_profiles[0]
        )

        logger.info(
            "Add VNIC with VNIC profile %s with QOS %s to VM %s",
            cls.vnic_profiles[0], cls.qos_names[0], config.VM_NAME_0
        )
        logger.info(
            "Update QoS %s on plugged NIC with VNIC profile %s",
            cls.qos_names[1], cls.vnic_profiles[1]
        )
        helper.add_qos_profile_to_nic(
            qos_name=cls.qos_names[1],
            vnic_profile_name=cls.vnic_profiles[1], nic=config.NIC_NAME_2,
            update_libvirt=False
        )

    def test_several_network_qos(self):
        """
        1) Check that provided bw values are the same as the values
        configured on libvirt for QoSProfile1
        2) Check that provided bw values are different from the values
        configured on libvirt for QoSProfile2
        3) Restart VM
        4) Check that provided bw values are the same as the values
        configured on libvirt for QoSProfile2 and QoSProfile1
        """
        inbound_dict = {
            "average": config.BW_PARAMS[0],
            "peak": config.BW_PARAMS[1],
            "burst": config.BW_PARAMS[2]
        }
        outbound_dict = {
            "average": config.BW_PARAMS[0],
            "peak": config.BW_PARAMS[1],
            "burst": config.BW_PARAMS[2]
        }

        dict_compare = helper.build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME_0, nic=config.NIC_NAME_1
        )

        logger.info(
            "Check that provided QoS %s and %s are the same as libvirt values"
            "for the VNIC profile %s with Network QoS %s plugged on VM",
            inbound_dict, outbound_dict, self.vnic_profiles[0],
            self.qos_names[0]
        )
        if not helper.compare_qos(
            host_obj=config.VDS_HOST, vm_name=config.VM_NAME_0,
            **dict_compare
        ):
            raise config.NET_EXCEPTION(
                "Provided QoS values %s and %s are not equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )

        dict_compare = helper.build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME_0, nic=config.NIC_NAME_2
        )

        logger.info(
            "Compare provided QoS %s and %s are not equal to libvirt values"
            "when Network QoS %s was updated after the VNIC profile "
            "%s already existed on VM",
            inbound_dict, outbound_dict, self.qos_names[1],
            self.vnic_profiles[1]
        )
        if helper.compare_qos(
            host_obj=config.VDS_HOST, vm_name=config.VM_NAME_0,
            **dict_compare
        ):
            raise config.NET_EXCEPTION(
                "Provided QoS values %s and %s are equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )

        logger.info("Restart VM %s", config.VM_NAME_0)
        if not ll_vms.restartVm(
            vm=config.VM_NAME_0, placement_host=config.HOST
        ):
            raise config.NET_EXCEPTION(
                "Couldn't restart VM %s" % config.VM_NAME_0
            )

        logger.info(
            "Check that after restart VM the QoS %s is equal to "
            "libvirt values", self.qos_names[1]
        )
        if not helper.compare_qos(
            host_obj=config.VDS_HOST, vm_name=config.VM_NAME_0,
            **dict_compare
        ):
            raise config.NET_EXCEPTION(
                "Provided QoS values %s and %s are not equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )

    @classmethod
    def teardown_class(cls):
        """
        1) Remove VNIC from VM.
        2) Remove VNIC profile
        3) Remove Network QoS
        """
        logger.info("Remove VNIC from VM %s", config.VM_NAME_0)
        for nic in (config.NIC_NAME_1, config.NIC_NAME_2):
            if not ll_vms.updateNic(
                True, config.VM_NAME_0, nic, plugged="false"
            ):
                logger.error(
                    "Couldn't unplug NIC %s from %s", nic, config.VM_NAME_0
                )
            if not ll_vms.removeNic(True, config.VM_NAME_0, nic):
                logger.error(
                    "Couldn't remove NIC %s from VM %s", nic, config.VM_NAME_0
                )

        logger.info("Remove VNIC profiles %s", cls.vnic_profiles)
        for vnic_profile in cls.vnic_profiles:
            if not ll_networks.remove_vnic_profile(
                positive=True, vnic_profile_name=vnic_profile,
                network=config.MGMT_BRIDGE, data_center=config.DC_NAME
            ):
                logger.error(
                    "Couldn't remove VNIC profile %s", vnic_profile
                )

        logger.info("Remove Network QoSs from setup")
        for qos_profile in cls.qos_names:
            if not ll_datacenters.delete_qos_from_datacenter(
                config.DC_NAME, qos_profile
            ):
                logger.error(
                    "Couldn't delete the QoS %s from DC", qos_profile
                )


@tier2
@attr(tier=2)
@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class TestNetQOSCase05(TestCase):
    """
    Migrate VM with network QOS on its NIC
    """
    __test__ = True
    qos_name = config.QOS_NAME[5][0]
    vnic_profile = config.VNIC_PROFILE[5]

    @classmethod
    def setup_class(cls):
        """
        1) Create new Network QoS profile under DC
        2) Provide Inbound and Outbound parameters for this QOS
        3) Create VNIC profile with configured QoS and add it to the NIC of
        the VM that is up
        """
        logger.info("Create new Network QoS profile under DC")
        if not ll_datacenters.add_qos_to_datacenter(
            datacenter=config.DC_NAME,
            qos_name=cls.qos_name, qos_type=config.QOS_TYPE,
            inbound_average=config.BW_PARAMS[0],
            inbound_peak=config.BW_PARAMS[1],
            inbound_burst=config.BW_PARAMS[2],
            outbound_average=config.BW_PARAMS[0],
            outbound_peak=config.BW_PARAMS[1],
            outbound_burst=config.BW_PARAMS[2]
        ):
            raise config.NET_EXCEPTION(
                "Couldn't create Network QOS %s under DC" % cls.qos_name
            )
        logger.info(
            "Create VNIC profile %s with QoS %s and add it to the %s",
            cls.vnic_profile, cls.qos_name, config.NIC_NAME_1
        )
        helper.add_qos_profile_to_nic(
            qos_name=cls.qos_name, vnic_profile_name=cls.vnic_profile
        )

    def test_migrate_network_qos(self):
        """
        1) Check that provided bw values are the same as the values
        configured on libvirt
        2) Migrate VM to another Host
        3) Check that provided bw values are the same as the values
        configured on libvirt after migration
        """
        inbound_dict = {
            "average": config.BW_PARAMS[0],
            "peak": config.BW_PARAMS[1],
            "burst": config.BW_PARAMS[2]
        }
        outbound_dict = {
            "average": config.BW_PARAMS[0],
            "peak": config.BW_PARAMS[1],
            "burst": config.BW_PARAMS[2]
        }

        dict_compare = helper.build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME_0, nic=config.NIC_NAME_1
        )

        logger.info(
            "Compare provided QoS %s and %s exists with libvirt values",
            inbound_dict, outbound_dict
        )
        if not helper.compare_qos(
            host_obj=config.VDS_HOST, vm_name=config.VM_NAME_0,
            **dict_compare
        ):
            raise config.NET_EXCEPTION(
                "Provided QoS values %s and %s are not equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )
        logger.info(
            "Migrate VM to Host %s", config.VDS_HOSTS[1]
        )
        if not ll_vms.migrateVm(
            True, config.VM_NAME_0, config.HOSTS[1]
        ):
            raise config.NET_EXCEPTION(
                "Couldn't migrate VM to %s" % config.HOSTS[1]
            )

        if not helper.compare_qos(
            host_obj=config.VDS_HOSTS[1], vm_name=config.VM_NAME_0,
            **dict_compare
        ):
            raise config.NET_EXCEPTION(
                "Provided QoS values %s and %s are not equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )

    @classmethod
    def teardown_class(cls):
        """
        1) Remove VNIC from VM.
        2) Remove VNIC profile
        3) Remove Network QoS
        """
        logger.info("Remove VNIC from VM %s", config.VM_NAME_0)
        if not ll_vms.updateNic(
            True, config.VM_NAME_0, config.NIC_NAME_1, plugged="false"
        ):
            logger.error(
                "Couldn't unplug NIC %s from %s", config.NIC_NAME_1,
                config.VM_NAME_0
            )
        if not ll_vms.removeNic(
            True, config.VM_NAME_0, config.NIC_NAME_1
        ):
            logger.error(
                "Couldn't remove VNIC %s from VM %s", config.NIC_NAME_1,
                config.VM_NAME_0
            )

        logger.info("Remove VNIC profile %s", cls.vnic_profile)
        if not ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=cls.vnic_profile,
            network=config.MGMT_BRIDGE, data_center=config.DC_NAME
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", cls.vnic_profile
            )
        if not ll_datacenters.delete_qos_from_datacenter(
            config.DC_NAME, cls.qos_name
        ):
            logger.error(
                "Couldn't delete the QoS %s from DC", cls.qos_name
            )
        logger.info(
            "Stop Vm %s and start it on original host %s",
            config.VM_NAME_0, config.HOST
        )
        if not ll_vms.restartVm(
            vm=config.VM_NAME_0, placement_host=config.HOST
        ):
            logger.error(
                "Couldn't return VM back to it's original host %s",
                config.HOST
            )
