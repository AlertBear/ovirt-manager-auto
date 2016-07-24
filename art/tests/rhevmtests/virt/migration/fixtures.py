#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Migration fixture for Virt and Network
"""

import logging
import pytest
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.clusters as cluster_api
import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.helper as net_helper
import rhevmtests.virt.helper as virt_helper
from art.unittest_lib import testflow
import config
import migration_helper

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def migration_init(request):
    """
    Migration module init, prepare env for migration:
    run VM and set hosts 3, 4(if exists) to maintenance
    """

    def fin():
        """
        1. active hosts
        2. Stop migrate VM
        """
        testflow.teardown("Set hosts to the active state")
        migration_helper.activate_hosts()
        testflow.teardown("Stop VM %s", config.MIGRATION_VM)
        ll_vms.stop_vms_safely(vms_list=[config.MIGRATION_VM])
    request.addfinalizer(fin)

    testflow.setup(
        "Set all but 2 hosts in the Cluster %s to the maintenance "
        "state", config.CLUSTER_NAME[0]
    )
    virt_helper.set_host_status()
    assert net_helper.run_vm_once_specific_host(
        vm=config.MIGRATION_VM, host=config.HOSTS[0],
        wait_for_up_status=True
    )


@pytest.fixture(scope="module")
def network_migrate_init(request):
    """
    For network migration cases:
    prepare all networks (in config)
    """

    def fin():
        """
        Remove the all networks configure in setup from data center .
        """

        assert hl_networks.remove_net_from_setup(
            host=config.HOSTS[:2], data_center=config.DC_NAME[0], all_net=True
        )
    request.addfinalizer(fin)

    net_helper.prepare_networks_on_setup(
        networks_dict=config.NETS_DICT,
        dc=config.DC_NAME[0],
        cluster=config.CLUSTER_NAME[0]
    )


@pytest.fixture(scope="class")
def update_cluster_over_commit(request):
    """
    Usage in test: part of case 'over_load_test' setup
    Set cluster over commit to '0'
    """
    info_message = [
        "For all clusters update over commit to %s",
        "Update cluster %s over commit to %s"
    ]
    err_message = "Failed to update cluster %s to over commit %s"

    def fin():
        """
        Set the cluster over commit back to 200%
        """
        testflow.teardown(info_message[0] % '200')
        for cluster_name in [config.CLUSTER_NAME[0], config.CLUSTER_NAME[1]]:
            logger.info(info_message[1] % (cluster_name, '200'))
            assert cluster_api.updateCluster(
                positive=True,
                cluster=cluster_name,
                mem_ovrcmt_prc=200
            ), err_message % (cluster_name, '200')
    request.addfinalizer(fin)

    testflow.setup(info_message[0] % 'none')
    for cluster_name in [config.CLUSTER_NAME[0], config.CLUSTER_NAME[1]]:
        logger.info(info_message[1] % (cluster_name, 'none'))
        assert cluster_api.updateCluster(
            positive=True,
            cluster=cluster_name,
            mem_ovrcmt_prc=0
        ), err_message % (cluster_name, 'none')


@pytest.fixture(scope="class")
def create_vm_from_glance(request):
    """
    Part of case 'migration_load_test' setup
    Create VM with load tool (pig) from glance.
    """
    action = ['Create', 'Update']

    def fin():
        """
        1. Remove VM with load tool
        2. Start migrate vm on first host
        """

        ll_vms.safely_remove_vms(vms=[config.MIGRATION_VM_LOAD])
        hl_vms.start_vm_on_specific_host(
            vm=config.MIGRATION_VM,
            host=config.HOSTS[0],
            wait_for_ip=True
        )
    request.addfinalizer(fin)

    assert ll_vms.stop_vms_safely(vms_list=[config.MIGRATION_VM])
    assert virt_helper.create_vm_from_glance_image(
        image_name=config.MIGRATION_IMAGE_VM,
        vm_name=config.MIGRATION_VM_LOAD
    ), virt_helper.get_err_msg(
        action=action[0], vm_name=config.MIGRATION_VM_LOAD
    )
    assert ll_vms.updateVm(
        positive=True,
        vm=config.MIGRATION_VM_LOAD,
        memory=config.GB * 2,
        memory_guaranteed=config.GB,
        os_type=config.OS_RHEL_7
    ), virt_helper.get_err_msg(
        action=action[1], vm_name=config.MIGRATION_VM_LOAD
    )


@pytest.fixture(scope="class")
def cancel_migration_test(request):
    """
    Usage in 'cancel migration' case.
    Run remove migration job only if case failed to cancel migration.
    """

    def fin():
        """
        Remove migration job only if case failed to cancel migration.
        """
        if not config.CANCEL_VM_MIGRATE:
            migration_helper.remove_migration_job()
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def start_vms_on_specific_host(request):
    """
    Usage in "bidirectional migration' start 4 VMs on both hosts
    Stop vms in teardown
    """
    test_vms = config.VM_NAME[1:5]
    action = "run on specific host"
    vms_to_host = {
        config.HOSTS[0]: [config.VM_NAME[1], config.VM_NAME[2]],
        config.HOSTS[1]: [config.VM_NAME[3], config.VM_NAME[4]]
    }

    def fin():
        """
        Stop running vms
        """
        ll_vms.stop_vms_safely(vms_list=test_vms)
    request.addfinalizer(fin)

    for host, vms in vms_to_host.items():
        for vm_to_start in vms:
            assert net_helper.run_vm_once_specific_host(
                vm=vm_to_start,
                host=host,
                wait_for_up_status=True
            ), virt_helper.get_err_msg(action=action, vm_name=vm_to_start)


@pytest.fixture(scope="class")
def migration_load_test(request, create_vm_from_glance):
    """
    Usage in load testing
    1. Create VM from Glance (diff fixture)
    2. Set VM memory to 85% of Host memory
    3. Start VM
    """
    percentage = 85
    vm_name = request.node.cls.vm_name
    action = ["Failed to update vm memory with hosts memory", "Run"]

    def fin():
        """
        Stop VM with load tool
        """

        ll_vms.stop_vms_safely(vms_list=[vm_name])
    request.addfinalizer(fin)

    hosts = [config.HOSTS[0], config.HOSTS[1]]
    status, host_index_max_mem = (
        hl_vms.set_vms_with_host_memory_by_percentage(
            test_hosts=hosts,
            test_vms=[vm_name],
            percentage=percentage
        )
    )
    assert status, virt_helper.get_err_msg(action[0])
    assert net_helper.run_vm_once_specific_host(
        vm=vm_name, wait_for_up_status=True,
        host=config.HOSTS[host_index_max_mem]
    ), virt_helper.get_err_msg(action[1], vm_name=vm_name)


@pytest.fixture(scope="class")
def migration_with_two_disks(request):
    """
    Create VM with two disks
    """

    vm_name = request.node.cls.vm_name
    cow_disk = config.DISK_FORMAT_COW
    disk_interfaces = config.INTERFACE_VIRTIO
    actions = ['Create', 'Update', "Run", "Add Disk"]

    def fin():
        """
        Remove vm
        """
        ll_vms.safely_remove_vms(vms=[vm_name])
    request.addfinalizer(fin)

    master_domain = (
        ll_sd.get_master_storage_domain_name(datacenter_name=config.DC_NAME[0])
    )
    assert ll_vms.createVm(
        positive=True,
        vmName=vm_name,
        vmDescription=vm_name,
        cluster=config.CLUSTER_NAME[0],
        template=config.TEMPLATE_NAME[0],
    ), virt_helper.get_err_msg(action=actions[0], vm_name=vm_name)
    assert ll_disks.updateDisk(
        positive=True,
        vmName=vm_name,
        alias=config.TEMPLATE_NAME[0],
        bootable=True
    ), virt_helper.get_err_msg(action=actions[1], vm_name=vm_name)
    assert ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_status=config.VM_UP,
    ), virt_helper.get_err_msg(action=actions[2], vm_name=vm_name)
    testflow.setup("Add two disks to VM %s", vm_name)
    for x in xrange(0, 2):
        assert ll_vms.addDisk(
            positive=True,
            vm=vm_name,
            provisioned_size=config.GB,
            storagedomain=master_domain,
            interface=disk_interfaces,
            format=cow_disk
        ), virt_helper.get_err_msg(action=actions[3], vm_name=vm_name)


@pytest.fixture(scope="class")
def move_host_to_other_cluster(request):
    """
    Usage in no available host on cluster test,
    move host 1 to cluster 2, (one host per cluster)
    """

    def fin():
        """
        Return host 1 to cluster 1
        """
        hl_hosts.move_host_to_another_cluster(
            host=config.HOSTS[1],
            cluster=config.CLUSTER_NAME[0]
        )
    request.addfinalizer(fin)

    assert hl_hosts.move_host_to_another_cluster(
        host=config.HOSTS[1],
        cluster=config.CLUSTER_NAME[1]
    )


@pytest.fixture(scope="class")
def migrate_to_diff_dc(request):
    """
    1. Add additional DC and cluster,
    2. Move one of the host to this DC
    """

    def fin():
        """
        Remove additional DC and cluster
        """
        hl_hosts.move_host_to_another_cluster(
            host=config.HOSTS[1],
            cluster=config.CLUSTER_NAME[0]
        )
        testflow.teardown(
            "Remove additional data center %s and cluster %s",
            config.ADDITIONAL_DC_NAME, config.ADDITIONAL_CL_NAME
        )
        hl_networks.remove_basic_setup(
            datacenter=config.ADDITIONAL_DC_NAME,
            cluster=config.ADDITIONAL_CL_NAME,
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Add additional data center and cluster, and move host to "
        "additional cluster"
    )
    assert hl_networks.create_basic_setup(
        datacenter=config.ADDITIONAL_DC_NAME,
        version=config.COMP_VERSION,
        cluster=config.ADDITIONAL_CL_NAME,
        cpu=config.CPU_NAME
    )
    assert hl_hosts.move_host_to_another_cluster(
        host=config.HOSTS[1],
        cluster=config.ADDITIONAL_CL_NAME
    )


@pytest.fixture(scope="class")
def over_load_test(request, update_cluster_over_commit):
    """
    Usage in overload host
    1. Store VM os type for later update in teardown
    2. Update VM os type to RHEL7 64bit to support large memory
    3. Store VM memory for later update in teardown
    4. Updates 2 VMs to 85% of host memory
    """

    vm_default_mem = config.GB
    host_index_max_mem = -1
    vm_default_os_type = config.VM_OS_TYPE
    percentage = 85
    test_vms = request.node.cls.test_vms
    test_hosts = [config.HOSTS[0], config.HOSTS[1]]
    update_os_type = "Update os type"
    failed_update_vm_memory = "Failed to update vm memory with hosts memory"

    def fin():
        """
        1. update Vms back to configure memory and os type
        2. activate host with max memory
        3. start migrate vm on first host
        """
        ll_vms.stop_vms_safely(vms_list=test_vms)
        hl_vms.update_os_type(os_type=vm_default_os_type, test_vms=test_vms)
        hl_vms.update_vms_memory(vms_list=test_vms, memory=int(vm_default_mem))
        ll_hosts.activateHost(
            positive=True,
            host=config.HOSTS[host_index_max_mem]
        )
        hl_vms.start_vm_on_specific_host(
            vm=config.MIGRATION_VM,
            host=config.HOSTS[0],
            wait_for_ip=True
        )
    request.addfinalizer(fin)

    assert ll_vms.stop_vms_safely(vms_list=[config.MIGRATION_VM])
    assert hl_vms.update_os_type(
        os_type=config.OS_RHEL_7, test_vms=test_vms
    ), virt_helper.get_err_msg(update_os_type, vm_name=test_vms)
    status, config.HOST_INDEX_MAX_MEMORY = (
        hl_vms.set_vms_with_host_memory_by_percentage(
            test_hosts=test_hosts,
            test_vms=test_vms,
            percentage=percentage
        )
    )
    assert status, virt_helper.get_err_msg(action=failed_update_vm_memory)
    ll_vms.start_vms(vm_list=test_vms, wait_for_status=config.VM_UP)


@pytest.fixture(scope="class")
def migration_options_test(request):
    """
    Create VM with placement affinity pin to host.
    """
    vm_name = request.node.cls.vm_name
    storage_domain = ll_sd.getStorageDomainNamesForType(
        config.DC_NAME[0], config.STORAGE_TYPE_NFS
    )[0]
    actions = ["run", "create"]

    def fin():
        ll_vms.safely_remove_vms(vms=[vm_name])
    request.addfinalizer(fin)

    assert ll_vms.createVm(
        True,
        vmName=vm_name,
        vmDescription='VM_pin_to_host',
        cluster=config.CLUSTER_NAME[0],
        placement_affinity=config.VM_PINNED,
        nic=config.NIC_NAME[0],
        storageDomainName=storage_domain,
        provisioned_size=config.DISK_SIZE,
        network=config.MGMT_BRIDGE,
        display_type=config.VM_DISPLAY_TYPE,
    ), virt_helper.get_err_msg(action=actions[1], vm_name=vm_name)
    assert ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_status=config.VM_UP,
        wait_for_ip=False
    ), virt_helper.get_err_msg(action=actions[0], vm_name=vm_name)


@pytest.fixture(scope="class")
def add_nic_to_vm(request):
    """
    Add NIC to VM
    """
    vm_name = request.node.cls.vm_name
    nic = request.node.cls.nic
    network = request.node.cls.network

    def fin():
        """
        Remove NIC
        """
        ll_vms.updateNic(
            positive=True, vm=config.VM_NAME[0], nic=nic, plugged="false"
        )
        ll_vms.removeNic(positive=True, vm=config.VM_NAME[0], nic=nic)
    request.addfinalizer(fin)

    assert ll_vms.addNic(positive=True, vm=vm_name, name=nic, network=network)


@pytest.fixture(scope="class")
def update_migration_network_on_cluster(request):
    """
    Update network to be migration network on cluster
    """
    migration_network = request.node.cls.migration_network
    networks = request.node.cls.networks

    def fin():
        """
        Set network as non-required network
        """
        for network in networks:
            ll_networks.update_cluster_network(
                positive=True, cluster=config.CLUSTER_NAME[0],
                network=network, required=False, usages="vm"
            )
    request.addfinalizer(fin)

    assert ll_networks.update_cluster_network(
        positive=True, cluster=config.CLUSTER_NAME[0],
        network=migration_network, usages="migration"
    )


@pytest.fixture(scope="class")
def restart_vm(request):
    """
    Stop VM, and start on SPM host
    """

    def fin():
        """
        Stop VM, and start on SPM host
        """
        ll_vms.stop_vms_safely(vms_list=[config.MIGRATION_VM])
        hl_vms.start_vm_on_specific_host(
            vm=config.MIGRATION_VM,
            host=config.HOSTS[0],
            wait_for_ip=True
        )
    request.addfinalizer(fin)
