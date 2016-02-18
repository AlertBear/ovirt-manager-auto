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
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

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
    network_helper.remove_networks_from_setup(hosts=conf.HOSTS)


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
            vm=self.extra_vm, host=conf.HOST_0_NAME, wait_for_up_status=True
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

    @polarion("RHEVM3-6316")
    def test_09_hotplug_hotunplug(self):
        """
        Start VM
        Try to hotunplug vNIC with passthrough profile
        Try to hotplug new vNIC profile with passthrough property
        Try to edit vNIC profile with passthrough property to be vitIO
        Stop VM
        Remove vNIC from VM
        """
        if not network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.vm_nic, plugged="false"
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=False, vm=self.vm, name=self.extra_vm_nic,
            network=self.net_2, vnic_profile=self.net_2,
            interface=conf.PASSTHROUGH_INTERFACE
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


class TestSriovVm02(helper.TestSriovBase):
    """
    Test run VM with VLAN
    """
    __test__ = True
    vm = conf.VM_0
    vm_nic = conf.NIC_NAME[1]
    net_1 = conf.VM_NETS[2][0]
    vlan_id = conf.VLAN_IDS[2]
    dc = conf.DC_0

    @classmethod
    def setup_class(cls):
        """
        Set number of VFs to 1
        Update vNIC profile with passthrough
        Add vNIC to VM
        Run VM
        """
        cls.pf_obj = ll_sriov.SriovNicPF(
            conf.HOST_0_NAME, conf.HOST_0_PF_NAMES[0]
        )
        if not cls.pf_obj.set_number_of_vf(1):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_vnic_profile(
            name=cls.net_1, network=cls.net_1, data_center=conf.DC_0,
            pass_through=True
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=cls.vm, name=cls.vm_nic, network=cls.net_1,
            interface=conf.PASSTHROUGH_INTERFACE
        ):
            raise conf.NET_EXCEPTION()

        if not network_helper.run_vm_once_specific_host(
            vm=cls.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6314")
    def test_01_vm_with_vlan(self):
        """
        Check that VLAN tag passed to virsh XML
        """
        vlan_from_xml = helper.get_vlan_id_from_vm_xml(vm=self.vm)
        if not vlan_from_xml == self.vlan_id:
            raise conf.NET_EXCEPTION(
                "VLAN tag on XML is %s but should be %s" %
                (vlan_from_xml, self.vlan_id)
            )

    @classmethod
    def teardown_class(cls):
        """
        Stop VM
        Remove vNIC
        """
        if not ll_vms.stopVm(positive=True, vm=cls.vm):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(positive=True, vm=cls.vm, nic=cls.vm_nic):
            raise conf.NET_EXCEPTION()

        super(TestSriovVm02, cls).teardown_class()


class TestSriovVm03(helper.TestSriovBase):
    """
    Try to edit vNIC to be passthrough interface when it has regular profile
    Try to add passthrough vNIC to virtIO interface
    Run VM with passthrough, port mirroring and network QoS profiles
    """
    __test__ = True
    vm = conf.VM_0
    vm_nic_1 = conf.NIC_NAME[1]
    vm_nic_2 = conf.NIC_NAME[2]
    vm_nic_3 = conf.NIC_NAME[3]
    vm_nic_4 = conf.NIC_NAME[4]
    net_1 = conf.VM_NETS[3][0]
    net_2 = conf.VM_NETS[3][1]
    net_3 = conf.VM_NETS[3][2]
    net_4 = conf.VM_NETS[3][3]
    net_list = [net_1, net_2, net_3]
    vm_nic_list = [vm_nic_1, vm_nic_2, vm_nic_3]
    dc = conf.DC_0

    @classmethod
    def setup_class(cls):
        """
        Set 2 VFs for the PF
        Update 2 vNICs profiles with passthrough, and another 2 with
        port mirroring and QoS
        Add 3 vNIC to VM (having passthrough, port mirroring and qos profiles
         appropriately)
        """
        cls.pf_obj = ll_sriov.SriovNicPF(
            conf.HOST_0_NAME, conf.HOST_0_PF_NAMES[0]
        )
        if not cls.pf_obj.set_number_of_vf(2):
            raise conf.NET_EXCEPTION()

        # updating vNIC profile with passthrough for test 2 and test 3
        for net in (cls.net_1, cls.net_4):
            if not ll_networks.update_vnic_profile(
                name=net, network=net, data_center=cls.dc,
                pass_through=True
            ):
                raise conf.NET_EXCEPTION()

        if not ll_networks.update_vnic_profile(
            name=cls.net_2, network=cls.net_2, data_center=cls.dc,
            port_mirroring=True
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.update_qos_on_vnic_profile(
            datacenter=cls.dc, qos_name=conf.NETWORK_QOS,
            vnic_profile_name=cls.net_3, network_name=cls.net_3
        ):
            raise conf.NET_EXCEPTION()

        for net, vm_nic in zip(cls.net_list, cls.vm_nic_list):
            if not ll_vms.addNic(
                positive=True, vm=cls.vm, name=vm_nic, network=net,
                vnic_profile=net, interface=(
                    conf.INTERFACE_VIRTIO if net != cls.net_1 else
                    conf.PASSTHROUGH_INTERFACE
                )
            ):
                raise conf.NET_EXCEPTION()

        network_host_api_dict = {
            "add": {
                "1": {
                    "network": cls.net_2,
                    "nic": conf.HOST_0_NICS[1]
                },
                "2": {
                    "network": cls.net_3,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }

        if not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10632")
    def test_01_edit_interface_passthrough(self):
        """
        Try to edit vNIC with regular profile to become passthrough interface
        """
        if not ll_vms.updateNic(
            positive=False, vm=self.vm, nic=self.vm_nic_2,
            interface=conf.PASSTHROUGH_INTERFACE
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6552")
    def test_02_add_passthroug_vnic_incomp_interface(self):
        """
        Try to add passthrough vNIC to the interface with virtIO type
        """
        if not ll_vms.addNic(
            positive=False, vm=self.vm, name=self.vm_nic_4,
            network=self.net_4, vnic_profile=self.net_4
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10631")
    def test_03_run_multiple_vnics(self):
        """
        Run VM with different types of vNIC profile
        """
        if not network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Stop VM
        Remove vNICs
        """
        ll_vms.stopVm(positive=True, vm=cls.vm)

        for vm_nic in cls.vm_nic_list:
            ll_vms.removeNic(positive=True, vm=cls.vm, nic=vm_nic)

        super(TestSriovVm03, cls).teardown_class()


class TestSriovVm04(helper.TestSriovBase):
    """
    Allowed networks and labels
    """
    __test__ = True
    vm = conf.VM_0
    vm_nic = conf.NIC_NAME[1]
    net_1 = conf.VM_NETS[4][0]
    net_2 = conf.VM_NETS[4][1]
    net_3 = conf.VM_NETS[4][2]
    net_4 = conf.VM_NETS[4][3]
    net_list = [net_1, net_2, net_3, net_4]
    label_1 = conf.LABELS[4][0]
    label_2 = conf.LABELS[4][1]
    label_list = [label_1, label_2]
    dc = conf.DC_0

    @classmethod
    def setup_class(cls):
        """
        Set number of VFs to 1
        Add labels to networks
        Update vNIC profiles with passthrough
        """
        cls.pf_obj = ll_sriov.SriovNicPF(
            conf.HOST_0_NAME, conf.HOST_0_PF_NAMES[0]
        )
        if not cls.pf_obj.set_number_of_vf(1):
            raise conf.NET_EXCEPTION()

        for net in cls.net_list:
            if not ll_networks.update_vnic_profile(
                name=net, network=net, data_center=conf.DC_0, pass_through=True
            ):
                raise conf.NET_EXCEPTION()

        for net, label in zip(cls.net_list[2:], cls.label_list):
            if not ll_networks.add_label(networks=[net], label=label):
                raise conf.NET_EXCEPTION()

    def setUp(self):
        """
        Set all_allowed_networks to False
        """
        self.pf_obj.set_all_networks_allowed(enable=False)

    def tearDown(self):
        """
        Stop VM
        Remove vNIC from VM
        Set all_allowed_networks to True
        """
        if not ll_vms.stopVm(positive=True, vm=self.vm):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(positive=True, vm=self.vm, nic=self.vm_nic):
            raise conf.NET_EXCEPTION()

        self.pf_obj.set_all_networks_allowed(enable=True)

    @polarion("RHEVM3-9373")
    def test_01_all_networks_allowed_specific_net(self):
        """
        Add vNIC to VM
        Add network to all_networks_allowed
        Run VM
        """
        if not ll_vms.addNic(
            positive=True, vm=self.vm, name=self.vm_nic,
            network=self.net_1, interface=conf.PASSTHROUGH_INTERFACE
        ):
            raise conf.NET_EXCEPTION()

        self.pf_obj.add_network_to_allowed_networks(network=self.net_1)
        if not network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14640")
    def test_02_all_networks_allowed_specific_net_negative(self):
        """
        Add vNIC to VM
        Try to run VM with network not specified in all_networks_allowed
        """
        if not ll_vms.addNic(
            positive=True, vm=self.vm, name=self.vm_nic,
            network=self.net_2, interface=conf.PASSTHROUGH_INTERFACE
        ):
            raise conf.NET_EXCEPTION()

        if network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-10627")
    def test_03_all_networks_allowed_specific_label(self):
        """
        Add vNIC to VM
        Set all_networks_allowed to specific label
        Run VM
        """
        if not ll_vms.addNic(
            positive=True, vm=self.vm, name=self.vm_nic,
            network=self.net_3, interface=conf.PASSTHROUGH_INTERFACE
        ):
            raise conf.NET_EXCEPTION()

        self.pf_obj.add_label_to_allowed_labels(label=self.label_1)
        if not network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-14639")
    def test_04_all_networks_allowed_specific_label_negative(self):
        """
        Add vNIC to VM
        Try to run VM with label not specified in all_networks_allowed
        """
        if not ll_vms.addNic(
            positive=True, vm=self.vm, name=self.vm_nic,
            network=self.net_4, interface=conf.PASSTHROUGH_INTERFACE
        ):
            raise conf.NET_EXCEPTION()

        if network_helper.run_vm_once_specific_host(
            vm=self.vm, host=conf.HOST_0_NAME, wait_for_up_status=True
        ):
            raise conf.NET_EXCEPTION()


class TestSriovVm05(helper.TestSriovBase):
    """
    Check connectivity between VMs using VF and bridge vNICs
    """
    __test__ = True
    dc = conf.DC_0
    vm_1 = conf.VM_0
    vm_2 = conf.VM_1
    vm_list = [vm_1, vm_2]
    mgmt_vm_nic = conf.NIC_NAME[0]
    vm_2_ip = None
    passthrough_profile = "mgmt_passthrough"
    mgmt_network = conf.MGMT_BRIDGE

    @classmethod
    def setup_class(cls):
        """
        Set number of VFs to 1 on PFs of two hosts
        Create passthrough vNIC profile
        Update vNIC to profile with passthrough
        Start VMs
        """
        cls.pf_obj = ll_sriov.SriovNicPF(
            conf.HOST_0_NAME, conf.HOST_0_PF_NAMES[0]
        )

        if not cls.pf_obj.set_number_of_vf(1):
            raise conf.NET_EXCEPTION()

        if not ll_networks.add_vnic_profile(
            positive=True, name=cls.passthrough_profile,
            network=cls.mgmt_network, data_center=cls.dc, pass_through=True
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.updateNic(
            positive=True, vm=cls.vm_1, nic=cls.mgmt_vm_nic,
            network=cls.mgmt_network, interface=conf.PASSTHROUGH_INTERFACE,
            vnic_profile=cls.passthrough_profile
        ):
            raise conf.NET_EXCEPTION()

        for vm, host in zip(
            cls.vm_list, [conf.HOST_0_NAME, conf.HOST_1_NAME]
        ):
            if not network_helper.run_vm_once_specific_host(
                vm=vm, host=host, wait_for_up_status=True
            ):
                raise conf.NET_EXCEPTION()

        cls.vm_2_ip = hl_vms.get_vm_ip(vm_name=cls.vm_2, start_vm=False)

    @polarion("RHEVM3-6728")
    def test_01_check_connectivity(self):
        """
        Ping between VMs using VF and bridge vNICs
        """
        vm_resource = global_helper.get_vm_resource(vm=self.vm_1)
        if not vm_resource.network.send_icmp(dst=self.vm_2_ip):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Stop VMs
        Update management profile to be non passthrough
        Remove extra vNIC profile
        """
        ll_vms.stop_vms_safely(vms_list=cls.vm_list)
        ll_vms.updateNic(
            positive=True, vm=cls.vm_1, nic=cls.mgmt_vm_nic,
            network=cls.mgmt_network, interface=conf.INTERFACE_VIRTIO,
            vnic_profile=cls.mgmt_network
        )
        ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=cls.passthrough_profile,
            network=cls.mgmt_network, data_center=cls.dc
        )
        super(TestSriovVm05, cls).teardown_class()
