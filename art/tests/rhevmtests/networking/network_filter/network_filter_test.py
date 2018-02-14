#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing NetworkFilter feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""
import shlex

import pytest

from art.rhevm_api.tests_lib.high_level import vms as hl_vms
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    networks as ll_networks,
    vms as ll_vms
)
import config as nf_conf
import helper
from rhevmtests.networking import config as conf
from art.test_handler.tools import polarion, bz
from art.unittest_lib import tier2, NetworkTest, testflow
from fixtures import (
    restore_vnic_profile_filter,
    update_network_filter_on_profile,
    update_vnic_clean_traffic_param
)
from rhevmtests.fixtures import (
    start_vm,
    create_datacenters,
    create_clusters
)
from rhevmtests.networking.fixtures import (  # noqa: F401
    create_and_attach_networks,
    remove_all_networks,
    setup_networks_fixture,
    clean_host_interfaces,
    remove_vnic_profiles,
    add_vnics_to_vms,
    remove_vnics_from_vms
)


@pytest.mark.usefixtures(create_and_attach_networks.__name__)
class TestNetworkFilterCase01(NetworkTest):
    """
    Check that network filter (vdsm-no-mac-spoofing) is enabled by default for
    new network
    """
    # global parameters
    net = nf_conf.NETS[1][0]

    # create_and_attach_networks fixture parameters
    create_networks = {
        "1": {
            "data_center": conf.DC_0,
            "clusters": [conf.CL_0],
            "networks": nf_conf.CASE_01_NETS_DICT
        }
    }
    remove_dcs_networks = [conf.DC_0]

    @tier2
    @polarion("RHEVM-15078")
    def test_check_default_network_filter_new_net(self):
        """
        Check that network filter (vdsm-no-mac-spoofing) is enabled by default
        for new network
        """
        testflow.step(
            "Check that network filter (vdsm-no-mac-spoofing) is enabled by "
            "default for new network"
        )
        nf_attr_dict = ll_networks.get_vnic_profile_attr(
            name=self.net, network=self.net,
            attr_list=[nf_conf.NETWORK_FILTER_STR]
        )
        nf_res = nf_attr_dict[nf_conf.NETWORK_FILTER_STR]
        assert nf_res == conf.VDSM_NO_MAC_SPOOFING


class TestNetworkFilterCase02(NetworkTest):
    """
    Check the vdsm-no-mac-spoofing in on virsh nwfilter-list
    """
    vdsm_spoofing_file = "/etc/libvirt/nwfilter/vdsm-no-mac-spoofing.xml"

    @tier2
    @polarion("RHEVM-15096")
    def test_check_network_filter_on_host(self):
        """
        Check the vdsm-no-mac-spoofing in on virsh nwfilter-list
        """
        testflow.step(
            "Check the vdsm-no-mac-spoofing in on virsh nwfilter-list"
        )
        nwfilter_list_cmd = "virsh -r nwfilter-list"
        assert conf.VDSM_NO_MAC_SPOOFING in conf.VDS_0_HOST.run_command(
            shlex.split(nwfilter_list_cmd)
        )[1]

        testflow.step(
            "Verify that file %s exist on VDSM host", self.vdsm_spoofing_file
        )
        assert conf.VDS_0_HOST.fs.listdir(self.vdsm_spoofing_file)

        testflow.step(
            "Verify content of %s", self.vdsm_spoofing_file
        )
        vdsm_spoofing_file_content = conf.VDS_0_HOST.run_command(
            ["cat", self.vdsm_spoofing_file]
        )[1]
        assert (
            "no-mac-spoofing" in vdsm_spoofing_file_content or
            "no-arp-mac-spoofing" in vdsm_spoofing_file_content
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    restore_vnic_profile_filter.__name__,
    remove_vnics_from_vms.__name__,
    setup_networks_fixture.__name__,
    start_vm.__name__,
)
class TestNetworkFilterCase03(NetworkTest):
    """
    Check that Network Filter is enabled for via dumpxml
    """
    # global parameters
    vm_name = conf.VM_0
    nic0 = conf.VM_NIC_0
    nic1 = conf.VM_NIC_1
    net = nf_conf.NETS[3][0]

    # create_and_attach_networks fixture parameters
    create_networks = {
        "1": {
            "data_center": conf.DC_0,
            "clusters": [conf.CL_0],
            "networks": nf_conf.CASE_03_NETS_DICT
        }
    }
    remove_dcs_networks = [conf.DC_0]

    # setup_networks_fixture fixture parameters
    hosts_nets_nic_dict = {
        0: {
            net: {
                "nic": 1,
                "network": net,
            }
        }
    }

    # start_vm fixture parameters
    start_vms_dict = {
        vm_name: {
            "host": 0
        }
    }

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = {
        vm_name: {
            "1": {
                "name": nic1
            }
        }
    }

    @tier2
    @polarion("RHEVM-15098")
    def test_01_check_vm_xml_with_network_filter(self):
        """
        Check that Network Filter is enabled for via dumpxml
        """
        testflow.step(
            "Check that Network Filter is enabled for via dumpxml"
        )
        assert ll_hosts.check_network_filtering_dumpxml(
            positive=True, vds_resource=conf.VDS_0_HOST, vm=self.vm_name,
            nics="1"
        )

    @tier2
    @polarion("RHEVM-15104")
    def test_02_check_network_filter_via_ebtables(self):
        """
        Check that VM NIC has network filter via ebtables
        """
        vm_macs = hl_vms.get_vm_macs(vm=self.vm_name, nics=[self.nic0])
        testflow.step("Check ebtables rules for running VM")
        assert ll_hosts.check_network_filtering_ebtables(
            host_obj=conf.VDS_0_HOST, vm_macs=vm_macs
        )

    @tier2
    @polarion("RHEVM-15099")
    def test_03_hot_plug_nic_check_xml(self):
        """
        Hot plug NIC to VM and check that NIC have filter enabled via dump XML
        """
        testflow.step(
            "Check network that filter is enabled vi dump XML for hot-plugged "
            "NIC"
        )
        assert ll_vms.addNic(
            positive=True, vm=self.vm_name, name=self.nic1, network=self.net
        )
        assert ll_hosts.check_network_filtering_dumpxml(
            positive=True, vds_resource=conf.VDS_0_HOST, vm=self.vm_name,
            nics="2"
        )

    @tier2
    @polarion("RHEVM-15106")
    def test_04_check_network_filter_via_ebtables_hotplug_nic(self):
        """
        Check that VM NIC has network filter via ebtables for hot-plugged NIC
        """
        vm_macs = hl_vms.get_vm_macs(vm=self.vm_name, nics=[self.nic1])
        testflow.step("Check ebtables rules for running VM")
        assert ll_hosts.check_network_filtering_ebtables(
            host_obj=conf.VDS_0_HOST, vm_macs=vm_macs
        )

    @tier2
    @polarion("RHEVM-15103")
    def test_05_disable_filter_running_vm(self):
        """
        Disable network filter while VM is running, should apply after VM
        reboot
        """
        testflow.step(
            "Disable network filter while VM is running, and check that "
            "network filter is disabled after VM restart"
        )
        assert ll_networks.update_vnic_profile(
            name=self.net, network=self.net, network_filter="None"
        )
        assert ll_vms.restartVm(vm=self.vm_name)
        assert not ll_hosts.check_network_filtering_dumpxml(
            positive=True, vds_resource=conf.VDS_0_HOST, vm=self.vm_name,
            nics="2"
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    remove_vnics_from_vms.__name__,
    add_vnics_to_vms.__name__
)
class TestNetworkFilterCase04(NetworkTest):
    """
    Remove network filter from vNIC profile while profile attach to stopped VM
    """
    # global parameters
    nic1 = nf_conf.VNICS[4][0]
    vm_name = conf.VM_0
    net = nf_conf.NETS[4][0]

    # create_and_attach_networks fixture parameters
    create_networks = {
        "1": {
            "data_center": conf.DC_0,
            "clusters": [conf.CL_0],
            "networks": nf_conf.CASE_04_NETS_DICT
        }
    }
    remove_dcs_networks = [conf.DC_0]

    # add_vnics_to_vms fixture parameters
    add_vnics_vms_params = {
        vm_name: {
            "1": {
                "name": nic1,
                "network": net
            }
        }
    }

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = add_vnics_vms_params

    @tier2
    @polarion("RHEVM-15102")
    def test_remove_filter_from_profile_vm_down(self):
        """
        Remove network filter from vNIC profile while profile attach to
        not running VM
        """
        testflow.step(
            "Remove network filter from vNIC profile while profile attach to "
            "not running VM"
        )
        assert ll_networks.update_vnic_profile(
            name=self.net, network=self.net, network_filter="None"
        )


@pytest.mark.usefixtures(
    remove_vnic_profiles.__name__
)
class TestNetworkFilterCase05(NetworkTest):
    """
    Create new vNIC profile with custom network_filter, no network
    filter and default network filter
    Update vNIC profile with custom network_filter, no network
    filter and default network filter

    """
    # General params
    vnic_pro_1 = nf_conf.VNIC_PROFILES[5][0]
    vnic_pro_2 = nf_conf.VNIC_PROFILES[5][1]
    vnic_pro_3 = nf_conf.VNIC_PROFILES[5][2]

    # remove_vnic_profiles params
    remove_vnic_profile_params = {
        vnic_pro_1: {
            "name": vnic_pro_1,
        },
        vnic_pro_2: {
            "name": vnic_pro_2,
        },
        vnic_pro_3: {
            "name": vnic_pro_3,
        }
    }

    @tier2
    @polarion("RHEVM-15476")
    def test_01_create_new_vnic_profile(self):
        """
        Create new vNIC profile with custom network_filter, no network
        filter and default network filter
        """
        testflow.step("Create new vNIC profile with default network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_1
        )
        testflow.step("Create new vNIC profile with no network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_2,
            network_filter="None"
        )
        testflow.step("Create new vNIC profile with custom network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_3,
            network_filter=nf_conf.ARP_FILTER
        )

    @tier2
    @polarion("RHEVM-15477")
    def test_02_update_vnic_profile(self):
        """
        Update vNIC profile with custom network_filter, no network
        filter and default network filter
        """
        testflow.step("Update vNIC profile with custom network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1,
            network_filter=nf_conf.ARP_FILTER
        )
        testflow.step("Update vNIC profile without network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1,
            network_filter="None"
        )
        testflow.step(
            "Update vNIC profile without send network profile. network "
            "filter should't update and stay the same"
        )
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1
        )


@pytest.mark.usefixtures(
    create_datacenters.__name__,
    create_clusters.__name__
)
class TestNetworkFilterCase06(NetworkTest):
    """
    1. Create and update vNIC profile network filter on old datacenter
    2. Create new vNIC profile with custom network_filter, no network
       filter and default network filter
    3. Update vNIC profile with custom network_filter, no network
       filter and default network filter
    """
    # global parameters
    ext_dc = "NetworkFilter-DC-3-6"
    ext_cl = "NetworkFilter-CL-3-6"
    clusters_dict = {
        ext_cl: {
            "name": ext_cl,
            "data_center": ext_dc,
            "version": conf.COMP_VERSION_4_0[0],
            "cpu": conf.CPU_NAME,
        }
    }
    datacenters_dict = {
        ext_dc: {
            "name": ext_dc,
            "version": conf.COMP_VERSION_4_0[0],
        }
    }
    vnic_pro_1 = nf_conf.VNIC_PROFILES[6][0]
    vnic_pro_2 = nf_conf.VNIC_PROFILES[6][1]
    vnic_pro_3 = nf_conf.VNIC_PROFILES[6][2]

    @tier2
    @polarion("RHEVM-15109")
    def test_create_update_network_filter_pre_cluster(self):
        """
        1. Create and update vNIC profile network filter on old datacenter
        2. Create new vNIC profile with custom network_filter, no network
           filter and default network filter
        3. Update vNIC profile with custom network_filter, no network
           filter and default network filter
        """
        testflow.step("Create new vNIC profile with default network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_1, datacenter=self.ext_dc
        )
        testflow.step("Create new vNIC profile with no network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_2, datacenter=self.ext_dc,
            network_filter="None"
        )
        testflow.step("Create new vNIC profile with custom network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="add", vnic_profile=self.vnic_pro_3, datacenter=self.ext_dc,
            network_filter=nf_conf.ARP_FILTER
        )
        testflow.step("Update vNIC profile with custom network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1,
            datacenter=self.ext_dc, network_filter=nf_conf.ARP_FILTER
        )
        testflow.step("Update vNIC profile without network filter")
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1,
            datacenter=self.ext_dc, network_filter="None"
        )
        testflow.step(
            "Update vNIC profile without send network profile. network "
            "filter should't update and stay the same"
        )
        assert helper.add_update_vnic_profile_and_check_filter(
            action="update", vnic_profile=self.vnic_pro_1,
            datacenter=self.ext_dc
        )


@pytest.mark.usefixtures(
    update_network_filter_on_profile.__name__,
    restore_vnic_profile_filter.__name__,
    start_vm.__name__,
    update_vnic_clean_traffic_param.__name__
)
class TestNetworkFilterCase07(NetworkTest):
    """
    1. Add the VM IP to clean traffic and check connectivity to VM
    2. Negative: Add the fake IP to clean traffic and check connectivity to VM
    """
    # update_network_filter_on_profile params
    network_filter = "clean-traffic"

    # restore_vnic_profile_filter params
    net = conf.MGMT_BRIDGE

    # update_vnic_clean_traffic_param params
    vm = conf.VM_0

    # start_vm params
    start_vms_dict = {
        vm: {}
    }

    @tier2
    @pytest.mark.parametrize(
        ("vnic", "positive"),
        [
            pytest.param(
                *[conf.VM_NIC_0, True], marks=(polarion("RHEVM3-21765"))
            ),
            pytest.param(
                *[conf.VM_NIC_0, False], marks=(
                    (polarion("RHEVM3-21766"), bz({"1482034": {}}))
                )
            ),
        ],
        ids=(
            "Positive test",
            "Negative test",
        )
    )
    def test_clean_traffic(self, vnic, positive):
        """
        Test clean traffic filter
        """
        ip = nf_conf.VM_INFO.get("ip")
        vm_resource = nf_conf.VM_INFO.get("resource")
        # Since we restart the VM and don't wait for IP we need to make sure
        # that VM resource is ready
        if positive:
            vm_resource.executor().wait_for_connectivity_state(
                positive=positive
            )

        assert positive == vm_resource.network.send_icmp(dst=ip, count="5")


@pytest.mark.incremental
@pytest.mark.usefixtures(
    update_network_filter_on_profile.__name__,
    restore_vnic_profile_filter.__name__,
)
class TestNetworkFilterCase08(NetworkTest):
    """
    1. Add clean traffic filter with parameters
    2. Update clean traffic filter parameters
    3. Delete clean traffic filter parameters
    """
    # General params
    vm = conf.VM_0

    # update_network_filter_on_profile params
    network_filter = "clean-traffic"

    # restore_vnic_profile_filter params
    net = conf.MGMT_BRIDGE

    @tier2
    @pytest.mark.parametrize(
        ("vnic", "action"),
        [
            pytest.param(
                *[conf.VM_NIC_0, "add"], marks=(polarion("RHEVM3-21767"))
            ),
            pytest.param(
                *[conf.VM_NIC_0, "update"], marks=(polarion("RHEVM3-21768"))
            ),
            pytest.param(
                *[conf.VM_NIC_0, "delete"], marks=(polarion("RHEVM3-21769"))
            ),
        ],
        ids=(
            "Add filter with parameters",
            "Update filter with parameters",
            "Delete filter with parameters",
        )
    )
    def test_clean_traffic(self, vnic, action):
        """
        Test add/update/delete traffic filter parameters
        """
        filter_object = ll_vms.get_vnic_network_filter_parameters(
            vm=self.vm, nic=vnic
        )
        if action == "add":
            assert ll_vms.add_vnic_network_filter_parameters(
                vm=self.vm, nic=vnic, param_name=nf_conf.IP_NAME,
                param_value=nf_conf.FAKE_IP_1
            )

        if action == "update":
            filter_object = filter_object[0]
            assert ll_vms.update_vnic_network_filter_parameters(
                nf_object=filter_object, param_name=nf_conf.IP_NAME,
                param_value=nf_conf.FAKE_IP_2
            )

        if action == "delete":
            filter_object = filter_object[0]
            assert ll_vms.delete_vnic_network_filter_parameters(
                nf_object=filter_object
            )
