# #! /usr/bin/python
# # -*- coding: utf-8 -*-
#
"""
SR_IOV feature tests for VFs on VM
"""

import helper
import logging
import config as conf
from art.unittest_lib import attr
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov
import art.rhevm_api.tests_lib.low_level.networks as ll_networks

logger = logging.getLogger("SR_IOV_Cases")


def setup_module():
    """
    Add networks to DC and cluster
    """
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.VM_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )


def teardown_module():
    """
    Removes networks from DC and cluster
    """
    network_helper.remove_networks_from_setup()


@attr(tier=2)
class TestSriovVM01(helper.TestSriovBase):
    """
    Changing the number of VFs for a PF when PF contains non-free VFs
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Create 3 VFs for the PF on the Host_0
        Create vNIC with passthrough profile for the network
        """
        cls.pf_obj = ll_sriov.SriovNicPF(
            conf.HOST_0_NAME, conf.HOST_0_PF_NAMES[0]
        )
        if not cls.pf_obj.set_number_of_vf(3):
            raise conf.NET_EXCEPTION()

        if not ll_networks.add_vnic_profile(
            positive=True, name=conf.VNIC_PROFILE[0],
            data_center=conf.DC_0, network=conf.VM_NETS[1][0],
            pass_through=True
        ):
            raise conf.NET_EXCEPTION()

    def test_01_change_vf_num_for_occupied_vf_on_vm(self):
        """
        1. Add NIC with passthrough profile to VM and run VM
        2. Try to change the number of VFs and fail as one VF is occupied
        """
        logger.info(
            "Negative: Try to change the number of VFs when one of the VFs is "
            "occupied by VM NIC"
        )
        if not ll_vms.addNic(
            positive=True, vm=conf.VM_NAME[0], name=conf.NIC_NAME[1],
            network=conf.VM_NETS[1][0], vnic_profile=conf.VNIC_PROFILE[0]
        ):
            raise conf.NET_EXCEPTION()

        if not network_helper.run_vm_once_specific_host(
            vm=conf.VM_NAME[0], host=conf.HOSTS[0], wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

        if self.pf_obj.set_number_of_vf(2):
            raise conf.NET_EXCEPTION()

    def test_02_change_vf_num_for_non_occupied_vf_on_vm(self):
        """
        1. Stop VM
        2. Change the number of VFs and succeed
        """
        logger.info("Stop VM and check you can change the VF number")
        if not ll_vms.stopVm(positive=True, vm=conf.VM_NAME[0]):
            raise conf.NET_EXCEPTION()

        if not self.pf_obj.set_number_of_vf(4):
            raise conf.NET_EXCEPTION()
