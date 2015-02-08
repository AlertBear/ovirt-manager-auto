#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing network VM QoS feature.
1 DC, 1 Cluster, 2 Hosts and 1 VM will be created for testing.
Create, update, remove and migration tests will be done for Network QoS feature
"""
import logging
from rhevmtests.networking import config
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase

from art.test_handler.exceptions import NetworkException
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level.datacenters import(
    add_qos_to_datacenter, update_qos_in_datacenter,
    delete_qos_from_datacenter
)
from art.rhevm_api.tests_lib.low_level.networks import removeVnicProfile
from art.rhevm_api.tests_lib.low_level.vms import(
    addNic, updateNic, removeNic, stopVm, migrateVm, restartVm, startVm
)
from rhevmtests.networking.network_qos.helper import(
    compare_qos, build_dict, add_qos_profile_to_nic
)

logger = logging.getLogger("Network_VNIC_QoS_Tests")

QOS_NAME = ("QoSProfile1", "QoSProfile2")
QOS_TYPE = "network"
BW_PARAMS = (10, 10, 100)
UPDATED_BW_PARAMS = (5, 5, 50)
########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class TestNetQOSCase01(TestCase):
    """
    Add new network QOS
    """
    __test__ = True

    @tcms(10090, 293060)
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
        if not add_qos_to_datacenter(
                datacenter=config.DC_NAME[0],
                qos_name=QOS_NAME[0], qos_type=QOS_TYPE,
                inbound_average=BW_PARAMS[0], inbound_peak=BW_PARAMS[1],
                inbound_burst=BW_PARAMS[2],
                outbound_average=BW_PARAMS[0], outbound_peak=BW_PARAMS[1],
                outbound_burst=BW_PARAMS[2]
        ):
            raise NetworkException("Couldn't create Network QOS under DC")
        logger.info(
            "Create VNIC profile with QoS and add it to the VNIC"
        )
        add_qos_profile_to_nic()
        inbound_dict = {
            "average": BW_PARAMS[0], "peak": BW_PARAMS[1],
            "burst": BW_PARAMS[2]
        }
        outbound_dict = {
            "average": BW_PARAMS[0], "peak": BW_PARAMS[1],
            "burst": BW_PARAMS[2]
        }

        dict_compare = build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        )

        logger.info(
            "Compare provided QoS %s and %s exists with libvirt values",
            inbound_dict, outbound_dict
        )
        if not compare_qos(
            host_obj=config.VDS_HOSTS[0], vm_name=config.VM_NAME[0],
            **dict_compare
        ):
            raise NetworkException(
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
            "Remove VNIC %s from VM %s", config.NIC_NAME[1], config.VM_NAME[0]
        )
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="false"
        ):
            logger.error("Couldn't unplug NIC %s", config.NIC_NAME[1])

        if not removeNic(True, config.VM_NAME[0], config.NIC_NAME[1]):
            logger.error(
                "Couldn't remove VNIC %s from VM %s",
                config.NIC_NAME[1], config.VM_NAME[0]
            )

        logger.info(
            "Remove VNIC profile %s", config.VNIC_PROFILE[0]
        )
        if not removeVnicProfile(
            positive=True, vnic_profile_name=config.VNIC_PROFILE[0],
            network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", config.VNIC_PROFILE[0]
            )
        if not delete_qos_from_datacenter(config.DC_NAME[0], QOS_NAME[0]):
            logger.error(
                "Couldn't delete the QoS %s from DC %s",
                QOS_NAME[0], config.DC_NAME[0]
            )


@attr(tier=1)
class TestNetQOSCase02(TestCase):
    """
    Update Network QoS
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create new Network QoS profile under DC
        2) Provide Inbound and Outbound parameters for this QOS
        3) Create VNIC profile with configured QoS and add it to the NIC of
        the VM
        """
        logger.info(
            "Create new Network QoS profile under DC"
        )
        if not add_qos_to_datacenter(
            datacenter=config.DC_NAME[0],
            qos_name=QOS_NAME[0], qos_type=QOS_TYPE,
            inbound_average=BW_PARAMS[0], inbound_peak=BW_PARAMS[1],
            inbound_burst=BW_PARAMS[2],
            outbound_average=BW_PARAMS[0], outbound_peak=BW_PARAMS[1],
            outbound_burst=BW_PARAMS[2]
        ):
            raise NetworkException(
                "Couldn't create Network QOS %s under DC" % QOS_NAME[0]
            )
        logger.info(
            "Create VNIC profile with QoS %s and add it to the VNIC on %s",
            QOS_NAME[0], config.VM_NAME[0]
        )
        add_qos_profile_to_nic()

        logger.info(
            "Add VNIC with VNIC profile %s with QOS %s to VM %s",
            config.VNIC_PROFILE[0], QOS_NAME[0], config.VM_NAME[1]
        )
        if not addNic(
            True, config.VM_NAME[1], name=config.NIC_NAME[1],
            network=config.MGMT_BRIDGE, vnic_profile=config.VNIC_PROFILE[0]
        ):
            raise NetworkException(
                "Couldn't add VNIC with QoS to VM %s" % config.VM_NAME[1]
            )

    @tcms(10090, 293066)
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
        if not update_qos_in_datacenter(
            datacenter=config.DC_NAME[0],
            qos_name=QOS_NAME[0], new_name="newQoS",
            inbound_average=UPDATED_BW_PARAMS[0],
            inbound_peak=UPDATED_BW_PARAMS[1],
            inbound_burst=UPDATED_BW_PARAMS[2],
            outbound_average=UPDATED_BW_PARAMS[0],
            outbound_peak=UPDATED_BW_PARAMS[1],
            outbound_burst=UPDATED_BW_PARAMS[2]
        ):
            raise NetworkException("Couldn't update Network QOS under DC")

        inbound_dict = {
            "average": UPDATED_BW_PARAMS[0], "peak": UPDATED_BW_PARAMS[1],
            "burst": UPDATED_BW_PARAMS[2]
        }
        outbound_dict = {
            "average": UPDATED_BW_PARAMS[0], "peak": UPDATED_BW_PARAMS[1],
            "burst": UPDATED_BW_PARAMS[2]
        }
        dict_compare = build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        )

        logger.info(
            "Check provided QoS %s and %s doesn't match libvirt values",
            inbound_dict, outbound_dict
        )
        if compare_qos(
            host_obj=config.VDS_HOSTS[0], vm_name=config.VM_NAME[0],
            **dict_compare
        ):
            raise NetworkException(
                "Provided QoS values %s and %s are equal to what was found on"
                " libvirt, but shouldn't" % (inbound_dict, outbound_dict)
            )

        logger.info(
            "Start vm %s on host %s", config.VM_NAME[1], config.HOSTS[0]
        )
        if not startVm(
            positive=True, vm=config.VM_NAME[1], placement_host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME[1], config.HOSTS[0])
            )

        logger.info(
            "Unplug and plug %s on %s", config.NIC_NAME[1], config.VM_NAME[0]
        )
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="false"
        ):
            logger.error(
                "Couldn't unplug %s", config.NIC_NAME[1]
            )
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="true"
        ):
            logger.error(
                "Couldn't plug %s", config.NIC_NAME[1]
            )

        logger.info(
            "Check that provided QoS values %s and %s are equal to what was"
            " found on libvirt for both VMs", inbound_dict, outbound_dict
        )
        for i in range(2):
            if not compare_qos(
                host_obj=config.VDS_HOSTS[0], vm_name=config.VM_NAME[i],
                **dict_compare
            ):
                raise NetworkException(
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
        logger.info(
            "Stop VM %s", config.VM_NAME[1]
        )
        if not stopVm(
            True, vm=config.VM_NAME[1]
        ):
            logger.error(
                "Couldn't stop VM %s", config.VM_NAME[1]
            )

        logger.info(
            "Remove VNIC from VMs %s", config.VM_NAME[:2]
        )
        for i in range(2):
            if not updateNic(
                True, config.VM_NAME[i], config.NIC_NAME[1], plugged="false"
            ):
                logger.error(
                    "Couldn't unplug NIC on %s", config.VM_NAME[i]
                )
            if not removeNic(
                True, config.VM_NAME[i], config.NIC_NAME[1]
            ):
                logger.error(
                    "Couldn't remove VNIC from VM %s", config.VM_NAME[i]
                )
        logger.info("Remove the QoS newQoS from DC")
        if not delete_qos_from_datacenter(config.DC_NAME[0], "newQoS"):
            logger.error(
                "Couldn't delete the QoS newQoS from DC %s", config.DC_NAME[0]
            )
        logger.info(
            "Remove VNIC profile %s", config.VNIC_PROFILE[0]
        )
        if not removeVnicProfile(
            positive=True, vnic_profile_name=config.VNIC_PROFILE[0],
            network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", config.VNIC_PROFILE[0]
            )


@attr(tier=1)
class TestNetQOSCase03(TestCase):
    """
    Remove Network QoS
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create new Network QoS profile under DC
        2) Provide Inbound and Outbound parameters for this QOS
        3) Create VNIC profile with configured QoS and add it to the NIC of
        the VM that is up and to the NIC of the VM that is down
        """
        logger.info("Create new Network QoS profile under DC")
        if not add_qos_to_datacenter(
            datacenter=config.DC_NAME[0],
            qos_name=QOS_NAME[0], qos_type=QOS_TYPE,
            inbound_average=BW_PARAMS[0], inbound_peak=BW_PARAMS[1],
            inbound_burst=BW_PARAMS[2],
            outbound_average=BW_PARAMS[0], outbound_peak=BW_PARAMS[1],
            outbound_burst=BW_PARAMS[2]
        ):
            raise NetworkException(
                "Couldn't create Network QOS %s under DC" % QOS_NAME[0]
            )
        logger.info(
            "Create VNIC profile with QoS %s and add it to the VNIC on %s",
            QOS_NAME[0], config.VM_NAME[0]
        )
        add_qos_profile_to_nic()
        logger.info(
            "Add VNIC with VNIC profile %s with QOS %s to non-running VM %s",
            config.VNIC_PROFILE[0], QOS_NAME[0], config.VM_NAME[1]
        )
        if not addNic(
            True, config.VM_NAME[1], name=config.NIC_NAME[1],
            network=config.MGMT_BRIDGE, vnic_profile=config.VNIC_PROFILE[0]
        ):
            raise NetworkException(
                "Couldn't add VNIC with QoS %s to VM %s" %
                (QOS_NAME[0], config.VM_NAME[1])
            )

    @tcms(10090, 293068)
    def test_remove_network_qos(self):
        """
        1) Remove QoS profile
        2) Check that the change is applicable on the VM that is down and
        it got "unlimited" QoS (after start VM)
        3) Check that the change is applicable on the VM that is up after
        unplug/plug
        """

        logger.info("Remove the QoS from DC")
        if not delete_qos_from_datacenter(
            config.DC_NAME[0], QOS_NAME[0]
        ):
            raise NetworkException(
                "Couldn't delete the QoS %s from DC %s" %
                (QOS_NAME[0], config.DC_NAME[0])
            )

        dict_compare = build_dict(
            inbound_dict={}, outbound_dict={},
            vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        )

        logger.info(
            "Check that after deletion of QoS libvirt is not updated with "
            "unlimited values till plug/unplug action"
        )
        if compare_qos(
            host_obj=config.VDS_HOSTS[0], vm_name=config.VM_NAME[0],
            **dict_compare
        ):
            raise NetworkException(
                "Libvirt has unlimited bandwidth configuration but shouldn't"
            )

        logger.info(
            "Start vm %s on host %s", config.VM_NAME[1], config.HOSTS[0]
        )
        if not startVm(
            positive=True, vm=config.VM_NAME[1], placement_host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME[1], config.HOSTS[0])
            )

        logger.info("Unplug and plug NIC on %s", config.VM_NAME[0])
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="false"
        ):
            raise NetworkException(
                "Couldn't unplug NIC %s" % config.NIC_NAME[1]
            )
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="true"
        ):
            raise NetworkException("Couldn't plug NIC %s" % config.NIC_NAME[1])

        logger.info(
            "Check that libvirt Network QoS values were updated to be "
            "unlimited"
        )
        for i in range(2):
            if not compare_qos(
                host_obj=config.VDS_HOSTS[0], vm_name=config.VM_NAME[i],
                **dict_compare
            ):
                raise NetworkException(
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
        logger.info("Stop VM %s", config.VM_NAME[1])
        if not stopVm(True, vm=config.VM_NAME[1]):
            logger.error(
                "Couldn't stop VM %s", config.VM_NAME[1]
            )

        logger.info("Remove VNIC from VMs %s", config.VM_NAME[:2])
        for i in range(2):
            if not updateNic(
                True, config.VM_NAME[i], config.NIC_NAME[1], plugged="false"
            ):
                logger.error(
                    "Couldn't unplug NIC %s on VM %s",
                    config.NIC_NAME[1], config.VM_NAME[i]
                )
            if not removeNic(
                True, config.VM_NAME[i], config.NIC_NAME[1]
            ):
                logger.error(
                    "Couldn't remove VNIC %s from VM %s",
                    config.NIC_NAME[1], config.VM_NAME[i]
                )

        logger.info(
            "Remove VNIC profile %s", config.VNIC_PROFILE[0]
        )
        if not removeVnicProfile(
            positive=True, vnic_profile_name=config.VNIC_PROFILE[0],
            network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", config.VNIC_PROFILE[0]
            )


@attr(tier=1)
class TestNetQOSCase04(TestCase):
    """
    Network QoSs, configured on several VNIC profiles
    """
    __test__ = True

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
        for qos_name in QOS_NAME:
            if not add_qos_to_datacenter(
                datacenter=config.DC_NAME[0],
                qos_name=qos_name, qos_type=QOS_TYPE,
                inbound_average=BW_PARAMS[0], inbound_peak=BW_PARAMS[1],
                inbound_burst=BW_PARAMS[2],
                outbound_average=BW_PARAMS[0], outbound_peak=BW_PARAMS[1],
                outbound_burst=BW_PARAMS[2]
            ):
                raise NetworkException(
                    "Couldn't create Network QOS %s under DC" % qos_name
                )
        logger.info(
            "Create VNIC profile with QoS and add it to the VNIC on running VM"
        )

        add_qos_profile_to_nic()

        logger.info(
            "Add VNIC with VNIC profile %s with QOS %s to VM %s",
            config.VNIC_PROFILE[1], QOS_NAME[1], config.VM_NAME[0]
        )
        logger.info(
            "Update QoS %s on plugged NIC with VNIC profile %s",
            QOS_NAME[1], config.VNIC_PROFILE[1]
        )
        add_qos_profile_to_nic(
            qos_name=QOS_NAME[1], vnic_profile_name=config.VNIC_PROFILE[1],
            nic=config.NIC_NAME[2], update_libvirt=False
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
            "average": BW_PARAMS[0], "peak": BW_PARAMS[1],
            "burst": BW_PARAMS[2]
        }
        outbound_dict = {
            "average": BW_PARAMS[0], "peak": BW_PARAMS[1],
            "burst": BW_PARAMS[2]
        }

        dict_compare = build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        )

        logger.info(
            "Check that provided QoS %s and %s are the same as libvirt values"
            "for the VNIC profile %s with Network QoS %s plugged on VM",
            inbound_dict, outbound_dict, config.VNIC_PROFILE[0], QOS_NAME[0]
        )
        if not compare_qos(
            host_obj=config.VDS_HOSTS[0], vm_name=config.VM_NAME[0],
            **dict_compare
        ):
            raise NetworkException(
                "Provided QoS values %s and %s are not equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )

        dict_compare = build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME[0], nic=config.NIC_NAME[2]
        )

        logger.info(
            "Compare provided QoS %s and %s are not equal to libvirt values"
            "when Network QoS %s was updated after the VNIC profile "
            "%s already existed on VM",
            inbound_dict, outbound_dict, QOS_NAME[1], config.VNIC_PROFILE[1]
        )
        if compare_qos(
            host_obj=config.VDS_HOSTS[0], vm_name=config.VM_NAME[0],
            **dict_compare
        ):
            raise NetworkException(
                "Provided QoS values %s and %s are equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )

        logger.info("Restart VM %s", config.VM_NAME[0])
        if not restartVm(
            vm=config.VM_NAME[0], placement_host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Couldn't restart VM %s" % config.VM_NAME[0]
            )

        logger.info(
            "Check that after restart VM the QoS %s is equal to "
            "libvirt values", QOS_NAME[1]
        )
        if not compare_qos(
            host_obj=config.VDS_HOSTS[0], vm_name=config.VM_NAME[0],
            **dict_compare
        ):
            raise NetworkException(
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
        logger.info("Remove VNIC from VM %s", config.VM_NAME[0])
        for nic in (config.NIC_NAME[1], config.NIC_NAME[2]):
            if not updateNic(
                True, config.VM_NAME[0], nic, plugged="false"
            ):
                logger.error(
                    "Couldn't unplug NIC %s from %s", nic, config.VM_NAME[0]
                )
            if not removeNic(True, config.VM_NAME[0], nic):
                logger.error(
                    "Couldn't remove NIC %s from VM %s", nic, config.VM_NAME[0]
                )

        logger.info("Remove VNIC profiles %s", config.VNIC_PROFILE[:2])
        for vnic_profile in (config.VNIC_PROFILE[:2]):
            if not removeVnicProfile(
                positive=True, vnic_profile_name=vnic_profile,
                network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
            ):
                logger.error(
                    "Couldn't remove VNIC profile %s", vnic_profile
                )

        logger.info("Remove Network QoSs from setup")
        for qos_profile in QOS_NAME:
            if not delete_qos_from_datacenter(
                config.DC_NAME[0], qos_profile
            ):
                logger.error(
                    "Couldn't delete the QoS %s from DC", qos_profile
                )


@attr(tier=1)
class TestNetQOSCase05(TestCase):
    """
    Migrate VM with network QOS on its NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create new Network QoS profile under DC
        2) Provide Inbound and Outbound parameters for this QOS
        3) Create VNIC profile with configured QoS and add it to the NIC of
        the VM that is up
        """
        logger.info("Create new Network QoS profile under DC")
        if not add_qos_to_datacenter(
            datacenter=config.DC_NAME[0],
            qos_name=QOS_NAME[0], qos_type=QOS_TYPE,
            inbound_average=BW_PARAMS[0], inbound_peak=BW_PARAMS[1],
            inbound_burst=BW_PARAMS[2],
            outbound_average=BW_PARAMS[0], outbound_peak=BW_PARAMS[1],
            outbound_burst=BW_PARAMS[2]
        ):
            raise NetworkException(
                "Couldn't create Network QOS %s under DC" % QOS_NAME[0]
            )
        logger.info(
            "Create VNIC profile %s with QoS %s and add it to the %s",
            config.VNIC_PROFILE[0], QOS_NAME[0], config.NIC_NAME[1]
        )
        add_qos_profile_to_nic()

    def test_migrate_network_qos(self):
        """
        1) Check that provided bw values are the same as the values
        configured on libvirt
        2) Migrate VM to another Host
        3) Check that provided bw values are the same as the values
        configured on libvirt after migration
        """
        inbound_dict = {
            "average": BW_PARAMS[0], "peak": BW_PARAMS[1],
            "burst": BW_PARAMS[2]
        }
        outbound_dict = {
            "average": BW_PARAMS[0], "peak": BW_PARAMS[1],
            "burst": BW_PARAMS[2]
        }

        dict_compare = build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        )

        logger.info(
            "Compare provided QoS %s and %s exists with libvirt values",
            inbound_dict, outbound_dict
        )
        if not compare_qos(
            host_obj=config.VDS_HOSTS[0], vm_name=config.VM_NAME[0],
            **dict_compare
        ):
            raise NetworkException(
                "Provided QoS values %s and %s are not equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )
        logger.info(
            "Migrate VM to Host %s", config.VDS_HOSTS[1]
        )
        if not migrateVm(
            True, config.VM_NAME[0], config.HOSTS[1]
        ):
            raise NetworkException(
                "Couldn't migrate VM to %s" % config.HOSTS[1]
            )

        if not compare_qos(
            host_obj=config.VDS_HOSTS[1], vm_name=config.VM_NAME[0],
            **dict_compare
        ):
            raise NetworkException(
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
        logger.info("Remove VNIC from VM %s", config.VM_NAME[0])
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged="false"
        ):
            logger.error(
                "Couldn't unplug NIC %s from %s", config.NIC_NAME[1],
                config.VM_NAME[0]
            )
        if not removeNic(
            True, config.VM_NAME[0], config.NIC_NAME[1]
        ):
            logger.error(
                "Couldn't remove VNIC %s from VM %s", config.NIC_NAME[1],
                config.VM_NAME[0]
            )

        logger.info(
            "Remove VNIC profile %s", config.VNIC_PROFILE[0]
        )
        if not removeVnicProfile(
            positive=True, vnic_profile_name=config.VNIC_PROFILE[0],
            network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", config.VNIC_PROFILE[0]
            )
        if not delete_qos_from_datacenter(
            config.DC_NAME[0], QOS_NAME[0]
        ):
            logger.error(
                "Couldn't delete the QoS %s from DC", QOS_NAME[0]
            )
        logger.info(
            "Stop Vm %s and start it on original host %s",
            config.VM_NAME[0], config.HOSTS[0]
        )
        if not restartVm(vm=config.VM_NAME[0], placement_host=config.HOSTS[0]):
            logger.error(
                "Couldn't return VM back to it's original host %s",
                config.HOSTS[0]
            )
