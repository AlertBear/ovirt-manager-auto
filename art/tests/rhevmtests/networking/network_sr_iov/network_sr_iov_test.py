# #! /usr/bin/python
# # -*- coding: utf-8 -*-
#
"""
SR_IOV feature tests
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Network/3_6_Network_SR_IOV
"""

import helper
import logging
import config as conf
from art.unittest_lib import attr
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("SR_IOV_Cases")


@attr(tier=2)
class TestSriov01(TestCase):
    """
    1. Create bond from 2 supported sr_iov NICs
    2. Check that bond doesn't have sr_iov related configuration
    3. Check that Bond NICs have sr_iov related configuration
    """
    pf_bond_nics = list()
    bond1 = "bond1"
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Create a new bond from sr_iov NICs
        """
        cls.pf_bond_nics = conf.HOST_0_PF_NAMES[:2]
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": cls.bond1,
                    "slaves": cls.pf_bond_nics
                }
            }
        }

        logger.info("Creating bond1 on %s", conf.HOSTS[0])
        if not hl_host_network.setup_networks(
            conf.HOSTS[0], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create bond on %s" % conf.HOSTS[0]
            )

    @polarion("RHEVM3-6550")
    def test_bond_sriov_config(self):
        """
        1. Check that bond doesn't have sr_iov related configuration
        2. Check that Bond NICs have sr_iov related configuration
        """
        helper.update_host_nics()
        pf_list_names = conf.HOST_O_SRIOV_NICS_OBJ.get_all_pf_nics_objects()

        logger.info(
            "Check that bond name is not in sr_iov pf names list"
        )
        if self.bond1 in pf_list_names:
            raise conf.NET_EXCEPTION()

        logger.info(
            "Check that bond NICs are still sr_iov pfs when being part of a "
            "bond by trying to create a PF object"
        )
        [ll_sriov.SriovNicPF(conf.HOST_0_NAME, pf) for pf in self.pf_bond_nics]

    @classmethod
    def teardown_class(cls):
        """
        Remove bond
        """
        if not hl_host_network.clean_host_interfaces(
            host_name=conf.HOST_0_NAME
        ):
            logger.error(
                "Failed to remove bond from %s", conf.HOST_0_NAME
            )


@attr(tier=2)
class TestSriov02(TestCase):
    """
    Edit vNIC profile with passthrough property
    """
    __test__ = True
    ver = conf.COMP_VERSION
    net_qos = "net_qos"

    @classmethod
    def setup_class(cls):
        """
        Configure Engine to support multiple queues
        Create QoS under DC
        Create a vNIC profile for existing MGMT network
        Update vNIC profile with passthrough property
        """

        logger.info(
            "Configuring engine to support queues for %s version", cls.ver
        )
        param = [
            "CustomDeviceProperties="
            "'{type=interface;prop={queues=[1-9][0-9]*}}'",
            "'--cver=%s'" % cls.ver
        ]
        if not test_utils.set_engine_properties(
            engine_obj=conf.ENGINE, param=param
        ):
            raise conf.NET_EXCEPTION(
                "Failed to enable queue via engine-config"
            )

        logger.info("Create new Network QoS profile under DC")
        if not ll_datacenters.add_qos_to_datacenter(
            datacenter=conf.DC_NAME[0],
            qos_name=cls.net_qos, qos_type=conf.NET_QOS_TYPE,
            inbound_average=conf.BW_VALUE,
            inbound_peak=conf.BW_VALUE,
            inbound_burst=conf.BURST_VALUE,
            outbound_average=conf.BW_VALUE,
            outbound_peak=conf.BW_VALUE,
            outbound_burst=conf.BURST_VALUE
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.add_vnic_profile(
            positive=True, name=conf.VNIC_PROFILE[0],
            data_center=conf.DC_NAME[0], network=conf.MGMT_BRIDGE
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_vnic_profile(
            name=conf.VNIC_PROFILE[0], network=conf.MGMT_BRIDGE,
            pass_through=True, data_center=conf.DC_NAME[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6305")
    def test_port_mirroring_update(self):
        """
        Check that port mirroring can't be configured
        """
        if ll_networks.update_vnic_profile(
            name=conf.VNIC_PROFILE[0], network=conf.MGMT_BRIDGE,
            data_center=conf.DC_NAME[0], port_mirroring=True
        ):
            raise conf.NET_EXCEPTION()

    def test_network_qos_update(self):
        """
        Check that QoS can't be configured
        """
        if ll_networks.update_qos_on_vnic_profile(
            datacenter=conf.DC_NAME[0], qos_name=self.net_qos,
            vnic_profile_name=conf.VNIC_PROFILE[0],
            network_name=conf.MGMT_BRIDGE
        ):
            raise conf.NET_EXCEPTION()

    def test_queues_update(self):
        """
        Check that queues can be configured
        """
        if not ll_networks.update_vnic_profile(
            name=conf.VNIC_PROFILE[0], network=conf.MGMT_BRIDGE,
            data_center=conf.DC_NAME[0], custom_properties=conf.PROP_QUEUES[0]
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove vNIC profile
        Remove queue support from engine
        """
        if not ll_networks.removeVnicProfile(
            positive=True, vnic_profile_name=conf.VNIC_PROFILE[0],
            network=conf.MGMT_BRIDGE, data_center=conf.DC_NAME[0]
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", conf.VNIC_PROFILE[0]
            )

        logger.info(
            "Removing queues support from engine for %s version", cls.ver
        )
        param = ["CustomDeviceProperties=''", "'--cver=%s'" % cls.ver]
        if not test_utils.set_engine_properties(
            engine_obj=conf.ENGINE, param=param
        ):
            logger.error(
                "Failed to remove queues support via engine-config"
            )
