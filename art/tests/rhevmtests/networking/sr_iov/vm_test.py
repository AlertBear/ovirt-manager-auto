# #! /usr/bin/python
# # -*- coding: utf-8 -*-
#
"""
SR_IOV feature tests for VFs on VM
"""

import helper
import logging
import config as conf
import rhevmtests.helpers as global_helper
from art.test_handler.tools import polarion  # pylint: disable=E0611
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


class TestSriovVm01(helper.TestSriovBase):
    """
    Cases for VFs on VM
    """
    __test__ = True
    vm = conf.VM_0
    extra_vm = conf.VM_NAME[1]
    vm_nic = conf.NIC_NAME[1]
    extra_vm_nic = conf.NIC_NAME[2]
    net_1 = conf.VM_NETS[1][0]
    net_2 = conf.VM_NETS[1][1]
    vm_resource = None
    vm_interfaces = list()

    @classmethod
    def setup_class(cls):
        """
        Update vNICs profiles with pass-through for networks
        Get VM resource object and its interface
        Add NIC with pass-through profile to VM and run VM
        """
        cls.pf_obj = ll_sriov.SriovNicPF(
            conf.HOST_0_NAME, conf.HOST_0_PF_NAMES[0]
        )

        for net in cls.net_1, cls.net_2:
            if not ll_networks.update_vnic_profile(
                name=net, network=net, data_center=conf.DC_0, pass_through=True
            ):
                raise conf.NET_EXCEPTION()

        if not ll_vms.startVm(positive=True, vm=cls.vm):
            raise conf.NET_EXCEPTION()

        cls.vm_resource = global_helper.get_vm_resource(vm=cls.vm)
        cls.vm_interfaces = cls.vm_resource.network.all_interfaces()

        if not ll_vms.stopVm(positive=True, vm=cls.vm):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=cls.vm, name=cls.vm_nic, network=cls.net_1,
            interface="pci_passthrough"
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6614")
    def test_01_run_vm_zero_vfs(self):
        """
        Try to run VM when there are zero VFs
        """
        if network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10628")
    def test_02_change_vf_num_for_occupied_vf_on_vm(self):
        """
        Create one VF and run VM (using that VF)
        Try to change the number of VFs and fail when the only VF is occupied
        """
        if not self.pf_obj.set_number_of_vf(1):
            raise conf.NET_EXCEPTION()

        if not network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

        logger.info(
            "Negative: Try to change the number of VFs when one of the VFs is "
            "occupied by VM NIC"
        )
        if self.pf_obj.set_number_of_vf(2):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10653")
    def test_03_check_mac_of_vf_on_vm(self):
        """
        Check the same MAC address exists on VF attached to VM in engine and
        in vm appropriate file
        """
        mac_addr = ll_vms.get_vm_nic_mac_address(vm=self.vm, nic=self.vm_nic)

        nic = filter(
            lambda x: x not in self.vm_interfaces,
            self.vm_resource.network.all_interfaces()
        )[0]
        path = conf.MAC_ADDR_FILE % nic
        rc, out, _ = self.vm_resource.run_command(["cat", path])
        if rc or mac_addr != out.strip():
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10663")
    def test_04_run_vm_occupied_vfs(self):
        """
        Add vNIC to the second VM
        Try to run second VM when there is only one VF that is already
        occupied by the first VM
        Remove vNIC from VM
        """
        if not ll_vms.addNic(
            positive=True, vm=self.extra_vm, name=self.vm_nic,
            network=self.net_2, interface=conf.PASSTHROUGH_INTERFACE
        ):
            raise conf.NET_EXCEPTION()

        if network_helper.run_vm_once_specific_host(
            vm=conf.VM_NAME[1], host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(
            positive=True, vm=self.extra_vm, nic=self.vm_nic
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14596")
    def test_05_check_no_vf_on_host_while_run_vm(self):
        """
        Check that the VF disappeared when VM is using it
        """
        logger.info(
            "Check that the number of VFs was decreased by 1 under %s PF when "
            "VM was running",
            self.pf_obj.nic_name
        )
        if self.pf_obj.get_all_vf_names():
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14638")
    def test_06_check_vf_exists_when_vm_is_down(self):
        """
        Stop VM
        Check that the VF is back to the host after stopping VM that use the VF
        """
        logger.info("Stop VM and check that there is 1 VF")
        if not ll_vms.stopVm(positive=True, vm=self.vm):
            raise conf.NET_EXCEPTION()

        if not len(self.pf_obj.get_all_vf_names()) == 1:
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14638")
    def test_07_change_vf_num_non_occupied_vfs(self):
        """
        Change the number of VFs and succeed
        """
        if not self.pf_obj.set_number_of_vf(3):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14595")
    def test_08_check_vf_while_passthrough_attached_to_non_running_vm(self):
        """
        Check that set number of VF is working while pass-through network
        reside on non running VM
        """
        if not self.pf_obj.set_number_of_vf(4):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-9373")
    def test_09_all_networks_allowed_specific_net(self):
        """
        Set all_networks_allowed to specific network
        Add network to all_networks_allowed
        Run VM
        """
        self.pf_obj.set_all_networks_allowed(enable=False)
        self.pf_obj.add_network_to_allowed_networks(network=self.net_1)
        if not network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6316")
    def test_10_hotplug_hotunplug(self):
        """
        1. Try to hotunplug vNIC with passthrough profile
        2. Try to hotplug new vNIC profile with passthrough property
        3. Try to edit vNIC profile with passthrough property to be vitIO
        4. Stop VM
        5. Remove vNIC from VM
        """
        if not ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.vm_nic, plugged="false"
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=False, vm=self.vm, name=self.extra_vm_nic,
            network=self.net_2, vnic_profile=self.net_2
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.vm_nic,
            interface=conf.INTERFACE_VIRTIO
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.stopVm(positive=True, vm=self.vm):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(positive=True, vm=self.vm, nic=self.vm_nic):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14640")
    def test_11_all_networks_allowed_specific_net_negative(self):
        """
        Add vNIC to VM
        Try to run VM with network not specified in all_networks_allowed
        Remove vNIC from VM
        """
        if not ll_vms.addNic(
            positive=True, vm=self.vm, name=self.vm_nic, network=self.net_2,
            interface="pci_passthrough"
        ):
            raise conf.NET_EXCEPTION()

        if network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(positive=True, vm=self.vm, nic=self.vm_nic):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Stop VM
        Set all_networks_allowed to True (all networks allowed)
        """
        if not ll_vms.stopVm(positive=True, vm=cls.vm):
            raise conf.NET_EXCEPTION()

        cls.pf_obj.set_all_networks_allowed(enable=True)
        super(TestSriovVm01, cls).teardown_class()
