#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for SR-IOV
"""
import shlex
import time

import pytest

from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_storagedomains,
    datacenters as ll_datacenters,
    templates as ll_templates,
    networks as ll_networks,
    vms as ll_vms
)

import config as sriov_conf
import helper
import rhevmtests.helpers as global_helper
from rhevmtests.networking import (
    helper as network_helper,
    config as conf
)
from art.unittest_lib import testflow


@pytest.fixture(scope="module")
def sr_iov_init(request):
    """
    Prepare SR-IOV params
    """
    sriov_conf.SD_NAME = ll_storagedomains.getStorageDomainNamesForType(
        datacenter_name=conf.DC_0, storage_type=conf.STORAGE_TYPE
    )[0]


@pytest.fixture(scope="class")
def create_qos(request):
    """
    Add QoS to data-center
    """
    net_qos = request.node.cls.net_qos

    def fin():
        """
        Remove QoS from date-center
        """
        testflow.teardown(
            "Delete QoS %s from datacenter %s", net_qos, conf.DC_0,
        )
        assert ll_datacenters.delete_qos_from_datacenter(
            datacenter=conf.DC_0, qos_name=net_qos
        )
    request.addfinalizer(fin)

    testflow.setup("Add QoS to datacenter %s", conf.DC_0)
    assert ll_datacenters.add_qos_to_datacenter(
        datacenter=conf.DC_0, qos_name=net_qos,
        qos_type=conf.NET_QOS_TYPE,
        inbound_average=sriov_conf.BW_VALUE,
        inbound_peak=sriov_conf.BW_VALUE,
        inbound_burst=sriov_conf.BURST_VALUE,
        outbound_average=sriov_conf.BW_VALUE,
        outbound_peak=sriov_conf.BW_VALUE,
        outbound_burst=sriov_conf.BURST_VALUE
    )


@pytest.fixture(scope="class")
def set_num_of_vfs(request):
    """
    Set number of VFs on host
    """
    num_of_vfs = getattr(request.node.cls, "num_of_vfs", 0)
    hosts = getattr(request.node.cls, "hosts", [0])
    pf_index = getattr(request.node.cls, "set_num_of_vfs_host_nic_index", 1)

    for host in hosts:
        for pf in range(pf_index):
            host_pf = "HOST_%s_PF_OBJECT_%s" % (host, pf + 1)
            pf_object = getattr(sriov_conf, host_pf)
            testflow.setup(
                "Set number %s of virtual functions on host %s", num_of_vfs,
                conf.HOSTS[host]
            )
            pf_object.set_number_of_vf(num_of_vfs)


@pytest.fixture(scope="class")
def add_vnics_to_vm(request):
    """
    Add vNICs to VM with/without passthrough
    """
    nics = request.node.cls.nics
    pass_through_vnic = getattr(request.node.cls, "pass_through_vnic", None)
    remove_vnics = getattr(request.node.cls, "remove_vnics", True)
    profiles = getattr(request.node.cls, "profiles", None)
    nets = getattr(request.node.cls, "nets", None)
    vms = getattr(request.node.cls, "vms", [conf.VM_0])
    add_vm_nic = getattr(request.node.cls, "add_vm_nic", True)
    result_list = list()

    def fin():
        """
        Remove vNICs from VM
        """
        if remove_vnics:
            for vm in vms:
                vm_nics = ll_vms.get_vm_nics_obj(vm)
                for nic in vm_nics:
                    if nic.name != conf.NIC_NAME[0]:
                        result_list.append(
                            ll_vms.removeNic(
                                positive=True, vm=vm, nic=nic.name
                            )
                        )
        assert all(result_list)
    request.addfinalizer(fin)

    if add_vm_nic:
        for vm, nic, passthrough, profile, net in zip(
            vms, nics, pass_through_vnic, profiles, nets
        ):
            testflow.setup("Add NIC %s to VM %s", nic, vm)
            assert ll_vms.addNic(
                positive=True, vm=vm, name=nic, network=net,
                vnic_profile=profile,
                interface=(
                    conf.PASSTHROUGH_INTERFACE if passthrough else "virtio"
                )
            )


@pytest.fixture(scope="class")
def reset_host_sriov_params(request):
    """
    1. Set number of VFs to 0
    2. Set all networks allowed to True
    """
    hosts = getattr(request.node.cls, "hosts", [0])
    results = list()
    hosts_and_pfs = dict(
        [
            (conf.HOSTS[idx], getattr(sriov_conf, "HOST_%s_PF_OBJECTS" % idx))
            for idx in hosts
        ]
    )
    msg_set_property = (
        "Setting PF: {pf} property: {prop} to {val_set} on host: {host}"
    )
    err_set_property = (
        "Failed to set PF: {pf} property: {prop}"
    )

    def fin3():
        """
        Raise error if one if the finalizers failed
        """
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin3)

    def fin2():
        """
        Set all networks allowed to True
        """
        prop = "all networks allowed"
        for host_name, pfs in hosts_and_pfs.iteritems():
            for pf in pfs:
                testflow.teardown(
                    msg_set_property.format(
                        pf=pf.nic_name, prop=prop, val_set=True,
                        host=host_name
                    )
                )
                results.append(
                    (
                        pf.set_all_networks_allowed(enable=True),
                        err_set_property.format(pf=pf.nic_name, prop=prop)
                    )
                )
    request.addfinalizer(fin2)

    def fin1():
        """
        Set number of VFs to 0
        """
        prop = "number of VFs"
        for host_name, pfs in hosts_and_pfs.iteritems():
            # In some cases we need to wait to make sure the VF is free to
            # remove
            time.sleep(5)
            for pf in pfs:
                testflow.teardown(
                    msg_set_property.format(
                        pf=pf.nic_name, prop=prop, val_set=0,
                        host=host_name
                    )
                )
                res = pf.set_number_of_vf(0)
                if not res:
                    # In some cases we need to wait to make sure the VF is
                    # free to remove
                    time.sleep(5)
                    res = pf.set_number_of_vf(0)
                results.append(
                    (res, err_set_property.format(pf=pf.nic_name, prop=prop))
                )
    request.addfinalizer(fin1)


@pytest.fixture(scope="class")
def update_qos(request):
    """
    update QOS on vNIC profile.
    """
    dc = request.node.cls.dc
    net = request.node.cls.net_3
    net_qos = request.node.cls.net_qos
    testflow.setup("Update QoS %s to vNIC profile %s", net_qos, net)
    assert ll_networks.update_qos_on_vnic_profile(
        datacenter=dc, qos_name=net_qos, vnic_profile_name=net,
        network_name=net
    )


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
def add_vnic_profile(request):
    """
    Add vNIC profile.
    """
    pass_through_vnic = request.node.cls.pass_through_vnic
    port_mirroring = request.node.cls.port_mirroring
    net_1 = request.node.cls.net_1
    profiles = request.node.cls.profiles
    exclude_profile = getattr(request.node.cls, "net_3", "")
    result_list = list()

    def fin1():
        """
        Remove vNIC profile from VM
        """
        testflow.teardown("Remove vNIC profile %s", profiles)
        for profile in profiles:
            if profile == exclude_profile:
                continue

            result_list.append(
                ll_networks.remove_vnic_profile(
                    positive=True, vnic_profile_name=profile,
                    network=net_1, data_center=conf.DC_0
                )
            )
        assert all(result_list)
    request.addfinalizer(fin1)

    for passthrough, portmirroring, profile in zip(
        pass_through_vnic, port_mirroring, profiles
    ):
        testflow.setup("Add new vNIC profile %s to network %s", profile, net_1)
        assert ll_networks.add_vnic_profile(
            positive=True, name=profile, network=net_1, data_center=conf.DC_0,
            pass_through=passthrough, port_mirroring=portmirroring
        )


@pytest.fixture()
def set_all_networks_allowed(request):
    """
    Disable set_all_networks_allowed
    """
    testflow.setup("Set all_networks_allowed to False")
    assert sriov_conf.HOST_0_PF_OBJECT_1.set_all_networks_allowed(enable=False)


@pytest.fixture(scope="class")
def set_ip_on_vm_interface(request):
    """
    Set IP on VM interface
    """
    vm_ips = request.node.cls.vm_ips

    for vm, ips in vm_ips.iteritems():
        vm_resource = conf.VMS_TO_STORE.get(vm).get("resource")
        inter = ips.get("inter")
        ip = ips.get("ip")
        testflow.setup(
            "Get VM %s interface excluding mgmt interface", vm
        )
        interface = (
            [inter] if inter else network_helper.get_non_mgmt_nic_name(
                vm_resource=vm_resource
            )
        )
        assert interface, "Failed to get interface from %s" % vm

        testflow.setup(
            "Configure temporary static IP %s on specific interface %s",
            ip, interface[0]
        )
        assert network_helper.configure_temp_static_ip(
            vds_resource=vm_resource, ip=ip, nic=interface[0]
        )


@pytest.fixture(scope="class")
def add_sriov_host_device_to_vm(request):
    """
    Add SR-IOV host device to a VM
    """
    host_index = getattr(request.node.cls, "add_host_device_host_index")
    vm = getattr(request.node.cls, "add_host_device_vm")
    hostname = conf.HOSTS[host_index]
    device_name = helper.get_first_free_vf_host_device(hostname=hostname)
    assert device_name

    def fin():
        """
        Remove SR-IOV host device from VM
        """
        testflow.teardown(
            "Removing VF host device: %s from VM: %s", device_name, vm
        )
        assert ll_vms.remove_vm_host_device(
            vm_name=vm, device_name=device_name
        )
    request.addfinalizer(fin)

    testflow.step(
        "Assigning free VF host device: %s to VM: %s", device_name, vm
    )
    assert ll_vms.add_vm_host_device(
        vm_name=vm, host_name=hostname, device_name=device_name
    )


@pytest.fixture(scope="class")
def modify_ifcfg_nm_controlled(request):
    """
    Remove NM_CONTROLLED=no from ifcfg files
    """
    vm_name = getattr(request.node.cls, "vm_name")
    vm_resource = global_helper.get_vm_resource(vm=vm_name, start_vm=False)
    ifcfg_files = "{ifcfg_path}/ifcfg-*".format(
        ifcfg_path=network_helper.IFCFG_PATH
    )
    nmcli_reload = "nmcli con reload"
    nm_control_cmd = (
        "sed -i s/NM_CONTROLLED=no/NM_CONTROLLED=yes/g {ifcfg_file}".format(
            ifcfg_file=ifcfg_files
        )
    )
    assert not vm_resource.run_command(shlex.split(nm_control_cmd))[0]
    assert not vm_resource.run_command(shlex.split(nmcli_reload))[0]


@pytest.fixture(scope="class")
def pin_vm_to_host(request):
    """
    Pin VM to host
    """
    vm = getattr(request.node.cls, "vm")

    def fin():
        """
        Remove pin VM to host
        """
        assert ll_vms.updateVm(
            positive=True, vm=vm, placement_host=conf.VM_ANY_HOST,
            placement_affinity=conf.VM_MIGRATABLE
        )
    request.addfinalizer(fin)

    assert ll_vms.updateVm(
        positive=True, vm=vm, placement_host=conf.HOST_0_NAME,
        placement_affinity=conf.VM_PINNED
    )


@pytest.fixture(scope="class")
def create_vm_fixture(request):
    """
    Create VM
    """
    vm = getattr(request.node.cls, "vm")
    cluster = getattr(request.node.cls, "cluster")

    testflow.setup("Create VM %s", vm)
    assert ll_vms.createVm(
        positive=True, vmName=vm, vmDescription="",
        cluster=cluster, storageDomainName=sriov_conf.SD_NAME,
        provisioned_size=conf.VM_DISK_SIZE
    )


@pytest.fixture(scope="class")
def create_template_fixture(request):
    """
    Create template
    """
    results = list()
    vm = getattr(request.node.cls, "vm")
    templates_list = getattr(request.node.cls, "templates_list")
    export_template_name = getattr(request.node.cls, "export_template_name")

    def fin():
        """
        Remove templates
        """
        for template in templates_list:
            testflow.teardown("Remove template %s", template)
            results.append(
                ll_templates.remove_template(positive=True, template=template)
            )
    request.addfinalizer(fin)

    testflow.setup("Create new template")
    assert ll_templates.createTemplate(
        positive=True, vm=vm, name=export_template_name
    )


@pytest.fixture(scope="class")
def remove_vm_fixture(request):
    """
    Remove VMs from engine
    """
    vms_list = getattr(request.node.cls, "vms_list")

    def fin():
        """
        Remove VMs from engine
        """
        testflow.teardown("Remove VMs %s", vms_list)
        assert ll_vms.removeVms(positive=True, vms=vms_list)
    request.addfinalizer(fin)
