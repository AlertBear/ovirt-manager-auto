#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for sanity
"""
import re
import shlex

import pytest

from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_storage,
    networks as hl_networks
)
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    datacenters as ll_dc,
    networks as ll_networks,
    storagedomains as ll_storage,
    vms as ll_vms
)
import config as sanity_conf
import rhevmtests.networking.config as conf
from rhevmtests.networking.acquire_network_manager_connections import helper
from rhevmtests.networking.mac_pool_range_per_cluster import (
    helper as mac_pool_helper
)
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def add_vnic_profile(request):
    """
    Add vNIC profile
    """
    vnic_profile = request.node.cls.vnic_profile
    dc = request.node.cls.dc
    net = request.node.cls.net
    description = request.node.cls.description

    def fin():
        """
        Remove vNIC profile
        """
        testflow.teardown("Remove vNIC profile %s", vnic_profile)
        assert ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=vnic_profile, network=net
        )
    request.addfinalizer(fin)

    testflow.setup("Add vNIC profile %s", vnic_profile)
    assert ll_networks.add_vnic_profile(
        positive=True, name=vnic_profile, data_center=dc,
        network=net, port_mirroring=True, description=description
    )


@pytest.fixture(scope="class")
def remove_qos(request):
    """
    Remove QoS from setup
    """
    qos_name = request.node.cls.qos_name

    def fin():
        """
        Remove QoS from setup
        """
        testflow.teardown("Remove QoS %s", qos_name)
        assert ll_dc.delete_qos_from_datacenter(
            datacenter=conf.DC_0, qos_name=qos_name
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def create_vnics_on_vm(request):
    """
    Create 5 VNICs on VM with different params for plugged/linked
    """
    nets = request.node.cls.nets
    vm = request.node.cls.vm_name
    vnics = request.node.cls.vnics

    def fin():
        """
        Remove vNICs from VM
        """
        results = list()
        for nic in vnics[:5]:
            results.append(ll_vms.removeNic(positive=True, vm=vm, nic=nic))
        assert all(results)
    request.addfinalizer(fin)

    plug_link_param_list = [
        ("true", "true"),
        ("true", "false"),
        ("false", "true"),
        ("false", "false"),
        ("true", "true"),
    ]
    for i in range(len(plug_link_param_list)):
        nic_name = vnics[i]
        network = nets[i] if i != 4 else None
        assert ll_vms.addNic(
            positive=True, vm=vm, name=nic_name,
            network=network, plugged=plug_link_param_list[i][0],
            linked=plug_link_param_list[i][1]
        )


@pytest.fixture(scope="class")
def create_cluster(request):
    """
    Create new cluster
    """
    ext_cl = request.node.cls.ext_cl

    def fin():
        """
        Remove cluster
        """
        testflow.teardown("Remove cluster %s", ext_cl)
        assert ll_clusters.removeCluster(positive=True, cluster=ext_cl)
    request.addfinalizer(fin)

    testflow.setup("Create cluster %s", ext_cl)
    mac_pool_helper.create_cluster_with_mac_pool(mac_pool_name="")


@pytest.fixture(scope="class")
def add_network_to_dc(request):
    """
    Add network to datacenter
    """
    dc = request.node.cls.dc
    net = request.node.cls.net

    net_dict = {
        net: {
            "required": "true",
        }
    }
    assert hl_networks.create_and_attach_networks(
        networks=net_dict, data_center=dc,
    )


@pytest.fixture(scope="class")
def update_vnic_profile(request):
    """
    Update vNIC profile with queue
    """
    dc = request.node.cls.dc
    prop_queue = request.node.cls.prop_queue
    mgmt_bridge = request.node.cls.mgmt_bridge

    def fin():
        """
        Remove queue from vNIC profile
        """
        testflow.teardown(
            "Remove custom properties from vNIC profile %s", mgmt_bridge
        )
        assert ll_networks.update_vnic_profile(
            name=mgmt_bridge, network=mgmt_bridge,
            data_center=dc, custom_properties="clear"
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Set queues custom properties on vNIC profile %s", mgmt_bridge
    )
    assert ll_networks.update_vnic_profile(
        name=mgmt_bridge, network=mgmt_bridge,
        data_center=dc, custom_properties=prop_queue
    )


@pytest.fixture(scope="class")
def add_labels(request):
    """
    Add labels
    """
    labels = request.node.cls.labels

    for lb, nets in labels.iteritems():
        label_dict = {
            lb: {
                "networks": nets
            }
        }
        testflow.setup("Add label %s to %s", lb, nets)
        assert ll_networks.add_label(**label_dict)


@pytest.fixture(scope="class")
def prepare_setup_for_register_domain(request):
    """
    Add storage domain to setup.
    Create VM.
    """
    gluster = False
    storage_name = sanity_conf.EXTRA_SD_NAME
    if conf.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES:
        storage_address = conf.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0]
        storage_path = conf.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0]
        gluster = True
    else:
        storage_address = conf.UNUSED_DATA_DOMAIN_ADDRESSES[0]
        storage_path = conf.UNUSED_DATA_DOMAIN_PATHS[0]
    dc = conf.DC_0
    cluster = conf.CL_0
    host = conf.HOST_0_NAME
    vm = request.node.cls.vm
    mac = sanity_conf.MAC_NOT_IN_POOL
    network = request.node.cls.net
    vm_nic = request.node.cls.vm_nic

    def fin():
        """
        Remove storage domain from setup
        """
        testflow.teardown(
            "Remove storage domain %s from DC %s", storage_name, dc
        )
        assert hl_storage.remove_storage_domain(
            name=storage_name, datacenter=dc, host=host,
            format_disk=True, engine=conf.ENGINE
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Add %s storage domain %s to DC %s", "gluster" if gluster
        else "NFS", storage_name, dc
    )
    if gluster:
        assert hl_storage.addGlusterDomain(
            host=host, name=storage_name, data_center=dc,
            address=storage_address, path=storage_path,
            vfs_type=conf.ENUMS["vfs_type_glusterfs"]
        )
    else:
        assert hl_storage.addNFSDomain(
            host=host, storage=storage_name, data_center=dc,
            address=storage_address, path=storage_path
        )
    testflow.setup(
        "Create VM %s with: %s, %s", vm, network, mac or "MAC from pool"
    )
    assert ll_vms.createVm(
        positive=True, vmName=vm, cluster=cluster, network=network,
        vnic_profile=network, mac_address=mac, nic=vm_nic
    )
    testflow.setup(
        "Remove storage domain %s from DC %s", storage_name, dc
    )
    assert hl_storage.remove_storage_domain(
        name=storage_name, datacenter=dc, host=host, engine=conf.ENGINE
    )
    testflow.setup("Remove VMs: %s", vm)
    assert ll_vms.removeVm(positive=True, vm=vm)

    testflow.setup("Remove networks %s from setup", network)
    assert ll_networks.remove_network(positive=True, network=network)

    testflow.setup("Import storage domain %s", storage_name)
    assert ll_storage.importStorageDomain(
        positive=True,
        type=conf.ENUMS['storage_dom_type_data'],
        storage_type=conf.STORAGE_TYPE_GLUSTER if gluster else
        conf.STORAGE_TYPE_NFS,
        address=storage_address,
        path=storage_path, host=host,
        vfs_type=conf.ENUMS["vfs_type_glusterfs"] if gluster else None
    )
    testflow.setup("Attach storage domain to data center %s", dc)
    assert ll_storage.attachStorageDomain(
        positive=True, datacenter=dc, storagedomain=storage_name
    )


@pytest.fixture(scope="class")
def nmcli_create_networks(request):
    """
    Create networks on host via nmcli (NetworkManager)
    """
    nic_type = request.node.cls.flat_type
    network = request.node.cls.flat_connection
    vlan_id = None
    host_nics = [conf.HOST_0_NICS[1]]

    def fin():
        """
        Clean all NetworkManager networks from the host
        """
        all_connections = "nmcli connection show"
        delete_cmd = "nmcli connection delete {uuid}"
        rc, out, _ = conf.VDS_0_HOST.run_command(
            command=shlex.split(all_connections)
        )
        assert not rc

        for match in re.findall(r'\w+-\w+-\w+-\w+-\w+', out):
            testflow.teardown(
                "Remove connection %s from NetworkManager", match
            )
            conf.VDS_0_HOST.run_command(
                command=shlex.split(delete_cmd.format(uuid=match))
            )
    request.addfinalizer(fin)

    testflow.setup("Remove existing NetworkManager connections")
    helper.remove_nm_controlled(nics=host_nics)
    testflow.setup("Reload NetworkManager")
    helper.reload_nm()

    testflow.setup("Create connection via NetworkManager")
    helper.create_eth_connection(
        nic_type=nic_type, nics=host_nics, vlan_id=vlan_id,
        connection=network
    )
