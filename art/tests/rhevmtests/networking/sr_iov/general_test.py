# #! /usr/bin/python
# # -*- coding: utf-8 -*-
#
"""
SR_IOV feature tests
Non-VM related cases
"""

import helper
import logging
import config as conf
from art.unittest_lib import attr
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("SR_IOV_Cases")


def setup_module():
    """
    Add networks to DC and cluster
    """
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.GENERAL_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )


def teardown_module():
    """
    Removes networks from DC and cluster
    """
    network_helper.remove_networks_from_setup()


@attr(tier=2)
class TestSriov01(NetworkTest):
    """
    1. Create bond from 2 supported sr_iov NICs (PFs)
    2. Check that bond doesn't have sr_iov related configuration
    3. Check that bond NICs have SR_IOV related configuration
    """
    __test__ = True
    pf_bond_nics = list()
    bond1 = "bond1"

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

        if not hl_host_network.setup_networks(
            conf.HOSTS[0], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

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
        hl_host_network.clean_host_interfaces(host_name=conf.HOST_0_NAME)


@attr(tier=2)
class TestSriov02(NetworkTest):
    """
    Edit vNIC profile with passthrough property
    """
    __test__ = True
    ver = conf.COMP_VERSION
    net_qos = "net_qos"
    vnic_p_list = conf.VNIC_PROFILE[:3]
    dc = conf.DC_0
    mgmt_net = conf.MGMT_BRIDGE

    @classmethod
    def setup_class(cls):
        """
        1. Configure Engine to support multiple queues
        2. Create QoS under DC
        3. Create a vNIC profile for existing MGMT network
        4. Update vNIC profile with passthrough property
        5. Create a new vNIC with passthrough property
        6. Create a new vNIC with port mirroring enabled
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
            datacenter=cls.dc,
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
            positive=True, name=cls.vnic_p_list[0],
            data_center=cls.dc, network=cls.mgmt_net
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_vnic_profile(
            name=cls.vnic_p_list[0], network=cls.mgmt_net,
            pass_through=True, data_center=cls.dc
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.add_vnic_profile(
            positive=True, name=cls.vnic_p_list[1],
            data_center=cls.dc, network=cls.mgmt_net,
            pass_through=True
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.add_vnic_profile(
            positive=True, name=cls.vnic_p_list[2],
            data_center=cls.dc, network=cls.mgmt_net,
            port_mirroring=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6305")
    def test_01_port_mirroring_update(self):
        """
        Check that port mirroring can't be configured
        """
        if ll_networks.update_vnic_profile(
            name=self.vnic_p_list[0], network=self.mgmt_net,
            data_center=self.dc, port_mirroring=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14628")
    def test_02_network_qos_update(self):
        """
        Check that QoS can't be configured
        """
        if ll_networks.update_qos_on_vnic_profile(
            datacenter=self.dc, qos_name=self.net_qos,
            vnic_profile_name=self.vnic_p_list[0],
            network_name=self.mgmt_net
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14629")
    def test_03_queues_update(self):
        """
        Check that queues can be configured
        """
        if not ll_networks.update_vnic_profile(
            name=self.vnic_p_list[0], network=self.mgmt_net,
            data_center=self.dc, custom_properties=conf.PROP_QUEUES[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14630")
    def test_04_pm_qos_update(self):
        """
        Check that port mirroring and QoS are available after
        disabling passthrough on vNIC
        """
        if not ll_networks.update_vnic_profile(
            name=self.vnic_p_list[0], network=self.mgmt_net,
            pass_through=False, data_center=self.dc
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_vnic_profile(
            name=self.vnic_p_list[0], network=self.mgmt_net,
            data_center=self.dc, port_mirroring=True
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_qos_on_vnic_profile(
            datacenter=self.dc, qos_name=self.net_qos,
            vnic_profile_name=self.vnic_p_list[0],
            network_name=self.mgmt_net
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6310")
    def test_05_passthrough_enabled_vnic(self):
        """
        Check that passthrough property is enabled on created vNIC profile
        """
        logger.info(
            "Check passthrough on %s", self.vnic_p_list[1]
        )
        vnic_profile_obj = ll_networks.get_vnic_profile_obj(
            name=self.vnic_p_list[1], network=self.mgmt_net,
            cluster=conf.CL_0,  data_center=self.dc
        )
        if vnic_profile_obj.get_pass_through().get_mode() == "disable":
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14581")
    def test_06_port_mirroring_update_created_vnic(self):
        """
        Check that port mirroring can't be configured on vNIC profile
        with passthrough property
        """
        if ll_networks.update_vnic_profile(
            name=self.vnic_p_list[1], network=self.mgmt_net,
            data_center=self.dc, port_mirroring=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14631")
    def test_07_network_qos_update_created_vnic(self):
        """
        Check that QoS can't be configured on vNIC profile
        with passthrough property
        """
        if ll_networks.update_qos_on_vnic_profile(
            datacenter=self.dc, qos_name=self.net_qos,
            vnic_profile_name=self.vnic_p_list[1],
            network_name=self.mgmt_net
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14632")
    def test_08_pm_update_enable(self):
        """
        Try to update vNIC profile with passthrough property when pm is enabled
        """
        if ll_networks.update_vnic_profile(
            name=self.vnic_p_list[2], network=self.mgmt_net,
            pass_through=True, data_center=self.dc
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove vNIC profile
        Remove queue support from engine
        """
        for vnic in cls.vnic_p_list:
            ll_networks.removeVnicProfile(
                positive=True, vnic_profile_name=vnic,
                network=cls.mgmt_net, data_center=cls.dc
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


class TestSriov03(helper.TestSriovBase):
    """
    Create several VFs for PF and check
    a. The same number is configured on engine and on host relevant file
    b. Putting link up and down doesn't change the number of VFs
    """
    __test__ = True
    vf_list = list()
    nic_name = ""
    num_vf = 0

    @classmethod
    def setup_class(cls):
        """
        Create 2 VFs for the PF on the Host_0
        """
        cls.pf_obj = ll_sriov.SriovNicPF(
            conf.HOST_0_NAME, conf.HOST_0_PF_NAMES[0]
        )
        cls.pf_obj.set_number_of_vf(2)
        cls.vf_list = cls.pf_obj.get_all_vf_names()
        cls.nic_name = cls.pf_obj.nic_name
        cls.num_vf = cls.pf_obj.get_number_of_vf()

    @polarion("RHEVM3-6318")
    def test_same_vf_number_engine_host(self):
        """
        Check for the same number of VFs on engine and on host file
        """
        path = conf.NUM_VF_PATH % self.nic_name
        rc, out, _ = conf.VDS_0_HOST.run_command(["cat", path])
        if rc or self.num_vf != int(out):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14633")
    def test_vf_number_after_ifup_ifdown(self):
        """
        Check that putting link up and down doesn't change the number of VFs
        """
        if not ll_hosts.ifdownNic(
            host=conf.HOSTS_IP[0], root_password=conf.HOSTS_PW,
            nic=self.nic_name
        ):
            raise conf.NET_EXCEPTION()

        if not ll_hosts.ifupNic(
            host=conf.HOSTS_IP[0], root_password=conf.HOSTS_PW,
            nic=self.nic_name
        ):
            raise conf.NET_EXCEPTION()


class TestSriov04(helper.TestSriovBase):
    """
    Negative: Try to configure number of VFs when:
    a. The number is negative
    b. The number is  bigger then the max value supported by the PF
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create PF object
        """
        cls.pf_obj = ll_sriov.SriovNicPF(
            conf.HOST_0_NAME, conf.HOST_0_PF_NAMES[0]
        )

    @polarion("RHEVM3-14594")
    def test_negative_vf_number(self):
        """
        Check that it's impossible to configure negative value for num VF
        """

        logger.info("Try to configure negative VF value for PF")
        if self.pf_obj.set_number_of_vf(-2):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14635")
    def test_over_max_vf_number(self):
        """
        Check that it's impossible to configure value bigger than the max value
        supported by PF
        """
        logger.info("Try to configure value bigger than max supported by PF")
        max_vf = self.pf_obj.get_max_number_of_vf()
        if self.pf_obj.set_number_of_vf(max_vf+1):
            raise conf.NET_EXCEPTION()


class TestSriov05(helper.TestSriovBase):
    """
     Changing the number of VFs for a PF when PF contains non-free VFs
    """
    __test__ = True
    net1 = conf.GENERAL_NETS[5][0]

    @classmethod
    def setup_class(cls):
        """
        Create 3 VFs for the PF on the Host_0
        """
        cls.pf_obj = ll_sriov.SriovNicPF(
            conf.HOST_0_NAME, conf.HOST_0_PF_NAMES[0]
        )
        if not cls.pf_obj.set_number_of_vf(3):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10628")
    def test_01_change_vf_num_for_occupied_vf_network(self):
        """
        1. Add network to VF
        2. Try to change the number of VFs and fail as one VF is occupied
        """
        logger.info(
            "Negative: Try to change the number of VFs when one of the VFs is "
            "occupied by network %s attached to it", self.net1
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net1,
                    "nic": self.pf_obj.get_all_vf_names()[0]
                }
            }
        }

        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

        if self.pf_obj.set_number_of_vf(2):
            raise conf.NET_EXCEPTION()

    def test_change_vf_num_for_non_occupied_vf_network(self):
        """
        1. Remove network from VF
        2. Change the number of VFs on PF and succeed
        """
        logger.info(
            "Remove network %s and check you can change the VF number",
            self.net1
        )
        if not hl_host_network.clean_host_interfaces(
            host_name=conf.HOST_0_NAME
        ):
            raise conf.NET_EXCEPTION()

        if not self.pf_obj.set_number_of_vf(2):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        Configure the number of VFs to be 0 (default)
        """
        hl_host_network.clean_host_interfaces(conf.HOST_0_NAME)
        super(TestSriov05, cls).teardown_class()


@attr(tier=2)
class TestSriov06(NetworkTest):
    """
    Try to edit regular vNIC profile on VM to have passthrough property
     Try to edit vNIC profile with passthrough property to become regular vNIC
    """
    __test__ = True
    net1 = conf.GENERAL_NETS[6][0]
    pt_vnic = conf.VNIC_PROFILE[0]
    dc = conf.DC_0

    @classmethod
    def setup_class(cls):
        """
        1. Attach network to host NIC
        2. Create vNIC profile with passthrough property for the network
        3. Add 2 vNICs to VM (one with passthrough property and one without)
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net1,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }

        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.add_vnic_profile(
            positive=True, name=cls.pt_vnic,
            data_center=cls.dc, network=cls.net1,
            pass_through=True
        ):
            raise conf.NET_EXCEPTION()

        # add 2 vNICs - one with passthrough and one without
        for i, vnic_profile in enumerate([cls.net1, cls.pt_vnic]):
            if not ll_vms.addNic(
                positive=True, vm=conf.VM_NAME[0], name=conf.NIC_NAME[i+1],
                network=cls.net1, vnic_profile=vnic_profile,
                interface=conf.PASSTHROUGH_INTERFACE if i else "virtio"
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10630")
    def test_01_update_vnic_with_passthrough(self):
        """
        Check that it's impossible to change regular vNIC on VM to have
        passthrough property
        """
        if ll_networks.update_vnic_profile(
            name=self.net1, network=self.net1,
            data_center=self.dc, pass_through=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14641")
    def test_02_update_vnic_with_non_passthrough(self):
        """
        Check that it's impossible to change vNIC on VM with passthrough
        property to become regular vNIC
        """
        if ll_networks.update_vnic_profile(
            name=self.pt_vnic, network=self.net1,
            data_center=self.dc, pass_through=False
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove vNICs from VM
        Remove network from host
        """
        for nic in conf.NIC_NAME[1:3]:
            ll_vms.removeNic(positive=True, vm=conf.VM_NAME[0], nic=nic)

        hl_host_network.clean_host_interfaces(conf.HOST_0_NAME)
