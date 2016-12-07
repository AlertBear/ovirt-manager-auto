#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for SR-IOV
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as sriov_conf
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
import rhevmtests.networking.helper as network_helper
from art.core_api import apis_exceptions
from rhevmtests.networking.fixtures import NetworkFixtures


class SRIOV(NetworkFixtures):
    """
    Fixture class for SRIOV
    """
    def init(self):
        """
        Prepare SR-IOV params
        """
        sriov_conf.HOST_O_SRIOV_NICS_OBJ = (
            ll_sriov.SriovHostNics(self.host_0_name)
        )
        sriov_conf.HOST_1_SRIOV_NICS_OBJ = (
            ll_sriov.SriovHostNics(self.host_0_name)
        )
        sriov_conf.HOST_0_PF_LIST = (
            sriov_conf.HOST_O_SRIOV_NICS_OBJ.get_all_pf_nics_objects()
        )
        sriov_conf.HOST_0_PF_NAMES = (
            sriov_conf.HOST_O_SRIOV_NICS_OBJ.get_all_pf_nics_names()
        )
        pf_host_nic_name = [
            i for i in sriov_conf.HOST_0_PF_NAMES if i ==
            conf.VDS_0_HOST.nics[1]
            ]
        if not pf_host_nic_name:
            sriov_conf.HOST_0_PF_OBJECT = ll_sriov.SriovNicPF(
                conf.HOST_0_NAME, sriov_conf.HOST_0_PF_NAMES[0]
            )
        else:
            sriov_conf.HOST_0_PF_OBJECT = ll_sriov.SriovNicPF(
                conf.HOST_0_NAME, pf_host_nic_name[0]
            )
        mgmt_nic_obj = hl_networks.get_management_network_host_nic(
            host=self.host_0_name, cluster=self.cluster_0
        )

        # Remove the host NIC with management network from PF lists
        if mgmt_nic_obj.name in sriov_conf.HOST_0_PF_NAMES:
            sriov_conf.HOST_0_PF_NAMES.remove(mgmt_nic_obj.name)
            sriov_conf.HOST_0_PF_LIST = filter(
                lambda x: x.id != mgmt_nic_obj.id, sriov_conf.HOST_0_PF_LIST
            )


@pytest.fixture(scope="module")
def init_fixture():
    """
    Prepare SR-IOV params
    """
    SRIOV().init()


@pytest.fixture(scope="module")
def prepare_setup_general(request):
    """
    Prepare networks for general cases
    """
    sriov_general = SRIOV()

    def fin():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        assert network_helper.remove_networks_from_setup(
            hosts=sriov_general.host_0_name
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Create networks %s on datacenter %s and cluster %s",
        sriov_conf.GENERAL_DICT, sriov_general.dc_0, sriov_general.cluster_0
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=sriov_conf.GENERAL_DICT, dc=sriov_general.dc_0,
        cluster=sriov_general.cluster_0
    )


@pytest.fixture(scope="class")
def prepare_setup_import_export(request):
    """
    Prepare networks for Import/Export cases
    """
    sriov_import_export = SRIOV()

    net_list = request.node.cls.net_list
    dc = request.node.cls.dc
    vm = request.node.cls.vm
    cluster = request.node.cls.cluster
    vm_nic_list = request.node.cls.vm_nic_list
    export_template_name = request.node.cls.export_template_name
    templates_list = request.node.cls.templates_list
    export_domain = request.node.cls.export_domain
    vms_list = request.node.cls.vms_list
    sd_name = request.node.cls.sd_name

    def fin6():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        assert network_helper.remove_networks_from_setup(
            hosts=sriov_import_export.host_0_name
        )
    request.addfinalizer(fin6)

    def fin5():
        """
        Remove template from export domain
        """
        testflow.teardown(
            "Remove template %s from export domain", export_template_name
        )
        ll_templates.removeTemplateFromExportDomain(
            positive=True, template=export_template_name,
            export_storagedomain=export_domain
        )
    request.addfinalizer(fin5)

    def fin4():
        """
        Remove templates
        """
        for template in templates_list:
            testflow.teardown("Remove template %s", template)
            ll_templates.removeTemplate(positive=True, template=template)
    request.addfinalizer(fin4)

    def fin3():
        """
        Remove VM from export domain
        """
        testflow.teardown("Remove VM %s from export domain", vm)
        ll_vms.remove_vm_from_export_domain(
            positive=True, vm=vm, datacenter=dc,
            export_storagedomain=export_domain
        )
    request.addfinalizer(fin3)

    def fin2():
        testflow.teardown("Remove VMs %s", vms_list)
        ll_vms.removeVms(positive=True, vms=vms_list)
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VMS
        """
        testflow.teardown("Stop VMs %s", vms_list)
        ll_vms.stop_vms_safely(vms_list=vms_list)
    request.addfinalizer(fin1)

    testflow.setup(
        "Create networks %s on datacenter %s and cluster %s",
        sriov_conf.IMPORT_EXPORT_DICT, sriov_import_export.dc_0,
        sriov_import_export.cluster_0
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=sriov_conf.IMPORT_EXPORT_DICT,
        dc=sriov_import_export.dc_0, cluster=sriov_import_export.cluster_0
    )
    assert sriov_conf.HOST_0_PF_OBJECT.set_number_of_vf(4)

    for net in net_list:
        testflow.setup("Update vNIC profile")
        assert ll_networks.update_vnic_profile(
            name=net, network=net, data_center=dc, pass_through=True
        )
    testflow.setup("Create VM %s", vm)
    assert ll_vms.createVm(
        positive=True, vmName=vm, vmDescription="",
        cluster=cluster, storageDomainName=sd_name,
        provisioned_size=conf.VM_DISK_SIZE
    )
    for net, vm_nic in zip(net_list, vm_nic_list):
        testflow.setup("Add NIC %s to VM %s", vm_nic, vm)
        assert ll_vms.addNic(
            positive=True, vm=vm, name=vm_nic, network=net,
            vnic_profile=net, interface=conf.PASSTHROUGH_INTERFACE
        )
    testflow.setup("Create new template")
    assert ll_templates.createTemplate(
        positive=True, vm=vm, name=export_template_name
    )


@pytest.fixture(scope="module")
def prepare_setup_vm(request):
    """
    Prepare networks for VM cases
    """
    sriov_vm = SRIOV()

    def fin():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        assert network_helper.remove_networks_from_setup(
            hosts=sriov_vm.host_0_name
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Create networks %s on datacenter %s and cluster %s",
        sriov_conf.VM_DICT, sriov_vm.dc_0, sriov_vm.cluster_0
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=sriov_conf.VM_DICT, dc=sriov_vm.dc_0,
        cluster=sriov_vm.cluster_0
    )


@pytest.fixture(scope="class")
def create_qos(request):
    """
    Add QoS to data-center
    """
    sriov = SRIOV()
    net_qos = request.node.cls.net_qos

    def fin():
        """
        Remove QoS from date-center
        """
        testflow.teardown(
            "Delete QoS %s from datacenter %s", net_qos, sriov.dc_0,
        )
        ll_datacenters.delete_qos_from_datacenter(
            datacenter=sriov.dc_0, qos_name=net_qos
        )
    request.addfinalizer(fin)

    testflow.setup("Add QoS to datacenter %s", sriov.dc_0)
    assert ll_datacenters.add_qos_to_datacenter(
        datacenter=sriov.dc_0, qos_name=net_qos,
        qos_type=conf.NET_QOS_TYPE,
        inbound_average=sriov_conf.BW_VALUE,
        inbound_peak=sriov_conf.BW_VALUE,
        inbound_burst=sriov_conf.BURST_VALUE,
        outbound_average=sriov_conf.BW_VALUE,
        outbound_peak=sriov_conf.BW_VALUE,
        outbound_burst=sriov_conf.BURST_VALUE
    )


@pytest.fixture(scope="class")
def add_update_vnic_profile(request):
    """
    Create a vNIC profile for existing MGMT network
    Update vNIC profile with passthrough property
    Create a new vNIC with passthrough property
    Create a new vNIC with port mirroring enabled
    """
    sriov = SRIOV()
    vnic_p_list = request.node.cls.vnic_p_list
    net_1 = request.node.cls.net_1
    dc = request.node.cls.dc
    update_vnic = request.node.cls.update_vnic
    pass_through = request.node.cls.pass_through

    def fin():
        """
        Remove vNICs profiles
        """
        for vnic in vnic_p_list:
            testflow.teardown("Remove vNIC profile %s", vnic)
            ll_networks.remove_vnic_profile(
                positive=True, vnic_profile_name=vnic, network=net_1,
                data_center=dc
            )
    request.addfinalizer(fin)

    testflow.setup(
        "Add new vNIC profile %s to network %s", vnic_p_list[0], net_1
    )
    assert ll_networks.add_vnic_profile(
        positive=True, name=vnic_p_list[0], data_center=dc, network=net_1,
        pass_through=pass_through
    )
    if update_vnic:
        testflow.setup("Update vNIC profile %s", vnic_p_list[0])
        assert ll_networks.update_vnic_profile(
            name=vnic_p_list[0], network=net_1, pass_through=True,
            data_center=sriov.dc_0
        )
        testflow.setup(
            "Add new vNIC profile %s to network %s", vnic_p_list[1], net_1
        )
        assert ll_networks.add_vnic_profile(
            positive=True, name=vnic_p_list[1], data_center=dc,
            network=net_1, pass_through=True
        )
        testflow.setup(
            "Add new vNIC profile %s to network %s", vnic_p_list[2], net_1
        )
        assert ll_networks.add_vnic_profile(
            positive=True, name=vnic_p_list[2], data_center=dc,
            network=net_1, port_mirroring=True
        )


@pytest.fixture(scope="class")
def set_num_of_vfs(request):
    """
    Set number of VFs on host
    """
    SRIOV()
    num_of_vfs = request.node.cls.num_of_vfs
    testflow.setup("Set number %s of virtual functions", num_of_vfs)
    sriov_conf.HOST_0_PF_OBJECT.set_number_of_vf(num_of_vfs)
    conf.HOST_0_VFS_LIST = sriov_conf.HOST_0_PF_OBJECT.get_all_vf_names()


@pytest.fixture(scope="class")
def add_vnics_to_vm(request):
    """
    Add vNICs to VM with/without passthrough
    """
    sriov = SRIOV()
    nics = request.node.cls.nics
    pass_through_vnic = request.node.cls.pass_through_vnic
    profiles = request.node.cls.profiles
    nets = request.node.cls.nets

    for nic, passthrough, profile, net in zip(
        nics, pass_through_vnic, profiles, nets
    ):
        testflow.setup("Add NIC %s to VM %s", nic, sriov.vm_0)
        assert ll_vms.addNic(
            positive=True, vm=sriov.vm_0, name=nic, network=net,
            vnic_profile=profile,
            interface=conf.PASSTHROUGH_INTERFACE if passthrough else "virtio"
        )


@pytest.fixture(scope="class")
def update_vnic_profiles(request):
    """
    Update vNICs  profiles with pass_through = True
    """
    sriov = SRIOV()
    vnics_profiles = request.node.cls.vnics_profiles
    for vnic in vnics_profiles:
        testflow.setup("Update vNIC profile %s", vnic)
        assert ll_networks.update_vnic_profile(
            name=vnic, network=vnic, data_center=sriov.dc_0, pass_through=True
        )


@pytest.fixture(scope="class")
def stop_vms(request):
    """
    Stop VMs
    """
    vms_list = request.node.cls.vms_list

    def fin():
        """
        Stop VM
        """
        testflow.setup("Stop VMs %s", vms_list)
        ll_vms.stop_vms_safely(vms_list=vms_list)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def reset_host_sriov_params(request):
    """
    Set number of VFs to 0
    Set all_networks_allowed to True
    """
    def fin():
        """
        Set number of VFs to 0
        Set all_networks_allowed to True
        """
        testflow.teardown("Set number of VFs to 0")
        sriov_conf.HOST_0_PF_OBJECT.set_number_of_vf(0)
        testflow.teardown("Set all_networks_allowed to True")
        sriov_conf.HOST_0_PF_OBJECT.set_all_networks_allowed(enable=True)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def start_vm(request):
    """
    Start VM
    """
    sriov = SRIOV()
    vm = request.node.cls.vm
    testflow.setup("Run VM %s once on specific host %s", vm, sriov.host_0_name)
    assert network_helper.run_vm_once_specific_host(
        vm=vm, host=sriov.host_0_name, wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def vm_case_03(request):
    """
    Setup for VM case03
    """
    dc = request.node.cls.dc
    net_2 = request.node.cls.net_2
    net_3 = request.node.cls.net_3
    net_qos = request.node.cls.net_qos
    testflow.setup("Update vNIC profile %s", net_2)
    assert ll_networks.update_vnic_profile(
        name=net_2, network=net_2, data_center=dc, port_mirroring=True
    )
    testflow.setup("Update QoS %s to vNIC profile %s", net_qos, net_3)
    assert ll_networks.update_qos_on_vnic_profile(
        datacenter=dc, qos_name=net_qos, vnic_profile_name=net_3,
        network_name=net_3
    )


@pytest.fixture(scope="class")
def remove_vnics_from_vm(request):
    """
    Remove vNICs from VM
    """
    sriov = SRIOV()
    nics = request.node.cls.nics

    def fin():
        """
        Remove vNICs from VM
        """
        for nic in nics:
            try:
                testflow.teardown("Remove NIC %s from VM %s", nic, sriov.vm_0)
                ll_vms.removeNic(positive=True, vm=sriov.vm_0, nic=nic)
            except apis_exceptions.EntityNotFound:
                pass
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def add_labels(request):
    """
    Add labels to networks
    """
    net_list = request.node.cls.net_list
    label_list = request.node.cls.label_list
    for net, label in zip(net_list[2:], label_list):
        label_dict = {
            label: {
                "networks": [net]
            }
        }
        testflow.setup("Add label %s to network %s", label, net)
        assert ll_networks.add_label(**label_dict)


@pytest.fixture(scope="class")
def vm_case_05(request):
    """
    Update
    """
    vm_1 = request.node.cls.vm_1
    mgmt_vm_nic = request.node.cls.mgmt_vm_nic
    mgmt_network = request.node.cls.mgmt_network
    passthrough_profile = request.node.cls.passthrough_profile
    dc = request.node.cls.dc
    vms_list = request.node.cls.vms_list

    def fin2():
        """
        Remove vNIC profile from VM
        """
        testflow.teardown("Remove vNIC profile %s", passthrough_profile)
        ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=passthrough_profile,
            network=mgmt_network, data_center=dc
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Update vNIC profile to virtIO
        """
        testflow.teardown("Update VM %s NIC %s", vm_1, mgmt_vm_nic)
        ll_vms.updateNic(
            positive=True, vm=vm_1, nic=mgmt_vm_nic,
            network=mgmt_network, interface=conf.INTERFACE_VIRTIO,
            vnic_profile=mgmt_network
        )
    request.addfinalizer(fin1)

    testflow.setup(
        "Add new vNIC profile %s to network %s", passthrough_profile,
        mgmt_network
    )
    assert ll_networks.add_vnic_profile(
        positive=True, name=passthrough_profile,
        network=mgmt_network, data_center=dc, pass_through=True
    )
    testflow.setup("Update VM %s NIC %s", vm_1, mgmt_vm_nic)
    assert ll_vms.updateNic(
        positive=True, vm=vm_1, nic=mgmt_vm_nic,
        network=mgmt_network, interface=conf.PASSTHROUGH_INTERFACE,
        vnic_profile=passthrough_profile
    )
    for vm, host in zip(vms_list, [conf.HOST_0_NAME, conf.HOST_1_NAME]):
        testflow.setup("Run vm %s once one specific host %s", vm, host)
        assert network_helper.run_vm_once_specific_host(
            vm=vm, host=host, wait_for_up_status=True
        )


@pytest.fixture()
def vm_case_04(request):
    """
    Disable set_all_networks_allowed
    Remove vNIC1 from VM
    Stop VM
    """
    SRIOV()
    vm_nic_1 = request.node.cls.vm_nic_1
    vm = request.node.cls.vm

    def fin2():
        """
        Remove vNIC1 from VM for SR-IOV VM case04
        """
        testflow.teardown("Remove NIC %s from VM %s", vm_nic_1, vm)
        ll_vms.removeNic(positive=True, vm=vm, nic=vm_nic_1)
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VM
        """
        testflow.teardown("Stop VM %s", vm)
        ll_vms.stop_vms_safely(vms_list=[vm])
    request.addfinalizer(fin1)

    testflow.setup("Set all_networks_allowed to False")
    assert sriov_conf.HOST_0_PF_OBJECT.set_all_networks_allowed(
        enable=False
    )
