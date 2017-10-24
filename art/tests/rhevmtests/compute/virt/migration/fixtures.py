#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Migration fixture for Virt and Network
"""

import logging
import time

import pytest

import config
import migration_helper
import rhevmtests.compute.virt.helper as virt_helper
import rhevmtests.helpers as gen_helper
from art.rhevm_api.tests_lib.high_level import (
    hosts as hl_hosts,
    networks as hl_networks,
    vms as hl_vms,
    datacenters as hl_data_center
)
from art.rhevm_api.tests_lib.low_level import (
    clusters as cluster_api,
    disks as ll_disks,
    vms as ll_vms,
    storagedomains as ll_sd
)
from art.unittest_lib import testflow

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def migration_init(request):
    """
    Migration module init, prepare env for migration:
    run VM
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

    testflow.setup("Start vm %s", config.MIGRATION_VM)
    ll_vms.start_vms(
        vm_list=[config.MIGRATION_VM],
        wait_for_status=config.VM_UP,
        wait_for_ip=True
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

    testflow.setup(info_message[0] % 'none')
    for cluster_name in [config.CLUSTER_NAME[0], config.CLUSTER_NAME[1]]:
        logger.info(info_message[1] % (cluster_name, 'none'))
        assert cluster_api.updateCluster(
            positive=True,
            cluster=cluster_name,
            mem_ovrcmt_prc=0,
        ), err_message % (cluster_name, 'none')


@pytest.fixture(scope="module")
def create_vm_for_load(request):
    """
    1. Stop Migrate VM
    2. Create VM with load tool (pig) from template
    3. Update VM memory to 85% of host memory
    4. Run VM on host with maximum memory
    """
    percentage = 85
    vm_name = config.MIGRATION_VM_LOAD
    action = [
        'Create', 'Update', 'Failed to update vm memory with hosts memory',
        'Run'
        ]

    def fin():
        """
        Restart migrate vm on first host
        """
        testflow.teardown(
            "Restart migrate vm %s on first host", config.MIGRATION_VM
        )
        assert hl_vms.run_vm_once_specific_host(
            vm=config.MIGRATION_VM,
            host=config.HOSTS[0],
            wait_for_up_status=True
        )
    request.addfinalizer(fin)

    testflow.setup("Stop migrate vm %s ", config.MIGRATION_VM)
    assert ll_vms.stop_vms_safely(vms_list=[config.MIGRATION_VM])
    testflow.setup("Create VM for load %s", vm_name)
    assert virt_helper.create_vm_from_template(vm_name)
    testflow.setup("Update vm memory to 85 percent of host memory")
    assert ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        memory=gen_helper.get_gb(2),
        max_memory=gen_helper.get_gb(4),
        memory_guaranteed=config.GB,
        os_type=config.VM_OS_TYPE
    ), virt_helper.get_err_msg(action=action[1], vm_name=vm_name)
    hosts = [config.HOSTS[0], config.HOSTS[1]]
    status, host_index_max_mem = (
        hl_vms.set_vms_with_host_memory_by_percentage(
            test_hosts=hosts,
            test_vms=[vm_name],
            percentage=percentage
        )
    )
    assert status, virt_helper.get_err_msg(action[2])
    testflow.setup("Start vm on host %s", config.HOSTS[host_index_max_mem])
    assert hl_vms.run_vm_once_specific_host(
        vm=vm_name,
        wait_for_up_status=True,
        host=config.HOSTS[host_index_max_mem]
    ), virt_helper.get_err_msg(action[3], vm_name=vm_name)
    logger.info("Wait for VM to get FQDN")
    if not virt_helper.wait_for_vm_fqdn(
        config.MIGRATION_VM_LOAD, timeout=config.FQDN_TIMEOUT
    ):
        logger.warn("Failed to get FQDN for vm %s", config.MIGRATION_VM_LOAD)


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
        testflow.teardown(
            "Remove migration job. (only if case failed to cancel migration)"
        )
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
        testflow.setup("Stop vms: ", testflow)
        ll_vms.stop_vms_safely(vms_list=test_vms)
    request.addfinalizer(fin)

    testflow.setup("Start vms on different hosts")
    for host, vms in vms_to_host.items():
        for vm_to_start in vms:
            assert hl_vms.run_vm_once_specific_host(
                vm=vm_to_start,
                host=host,
                wait_for_up_status=True
            ), virt_helper.get_err_msg(action=action, vm_name=vm_to_start)


@pytest.fixture(scope="class")
def setting_migration_vm(request, create_vm_for_load):
    """
    Setting migration vm for cases with load and large memory
    With vm created from template
    """

    def fin():
        """
        Stop VM with load tool
        """
        testflow.teardown("Stop vm: %s ", config.MIGRATION_VM_LOAD)
        ll_vms.stop_vms_safely(vms_list=[config.MIGRATION_VM_LOAD])

    request.addfinalizer(fin)

    testflow.setup("Start vm: %s ", config.MIGRATION_VM_LOAD)
    ll_vms.start_vms(
        vm_list=[config.MIGRATION_VM_LOAD],
        wait_for_status=config.VM_UP,
        wait_for_ip=True
    )
    if not virt_helper.wait_for_vm_fqdn(
        config.MIGRATION_VM_LOAD, timeout=config.FQDN_TIMEOUT
    ):
        logger.warn("Failed to get FQDN for vm %s", config.MIGRATION_VM_LOAD)


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
        testflow.teardown("Remove vm %s", vm_name)
        ll_vms.safely_remove_vms(vms=[vm_name])
    request.addfinalizer(fin)

    master_domain = (
        ll_sd.get_master_storage_domain_name(datacenter_name=config.DC_NAME[0])
    )
    testflow.setup("Create vm with 2 disks on master domain")
    assert ll_vms.createVm(
        positive=True,
        vmName=vm_name,
        vmDescription=vm_name,
        cluster=config.CLUSTER_NAME[0],
        template=config.TEMPLATE_NAME[0],
    ), virt_helper.get_err_msg(action=actions[0], vm_name=vm_name)
    first_disk_id = ll_disks.getObjDisks(name=vm_name, get_href=False)[0].id
    assert ll_disks.updateDisk(
        positive=True,
        vmName=vm_name,
        id=first_disk_id,
        bootable=True
    ), virt_helper.get_err_msg(action=actions[1], vm_name=vm_name)
    testflow.setup("Start vm %s", vm_name)
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
def migrate_to_diff_dc(request):
    """
    1. Start migrate VM on first host
    2. Add new DC and cluster
    3. Move hosts 2,3 to this new DC under new cluster
    """

    def fin():
        """
        1. Move hosts back to cluster 1
        2. Remove new DC and cluster
        """
        testflow.teardown("Move host 2,3 to GE cluster 1")
        for host_name in config.HOSTS[1:3]:
            hl_hosts.move_host_to_another_cluster(
                host=host_name,
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
        "Stop vm and run in on host %s only host in cluster", config.HOSTS[0]
    )
    ll_vms.stop_vms_safely([config.MIGRATION_VM])
    assert hl_vms.run_vm_once_specific_host(
        vm=config.MIGRATION_VM,
        host=config.HOSTS[0],
        wait_for_up_status=True
    )
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
    testflow.setup("Move host 2,3 to new cluster")
    for host_name in config.HOSTS[1:3]:
        assert hl_hosts.move_host_to_another_cluster(
            host=host_name,
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
    vm_default_os_type = config.VM_OS_TYPE
    percentage = 85
    test_vms = request.node.cls.test_vms
    test_hosts = [config.HOSTS[0], config.HOSTS[1]]
    update_os_type = "Update os type"
    failed_update_vm_memory = "Failed to update vm memory with hosts memory"

    def fin():
        """
        1. update Vms back to configure memory and os type
        2. activate hosts
        3. start migrate vm on first host
        """
        ll_vms.stop_vms_safely(vms_list=test_vms)
        testflow.teardown("Set hosts to the active state")
        migration_helper.activate_hosts()
        hl_vms.update_os_type(os_type=vm_default_os_type, test_vms=test_vms)
        hl_vms.update_vms_memory(
            vms_list=test_vms, memory=int(vm_default_mem),
            max_memory=gen_helper.get_gb(4)
        )
        assert ll_vms.startVm(
            positive=True, vm=config.MIGRATION_VM, wait_for_ip=True
        )

    request.addfinalizer(fin)
    testflow.setup("Stop vm %s", config.MIGRATION_VM)
    assert ll_vms.stop_vms_safely(vms_list=[config.MIGRATION_VM])
    testflow.setup("Activate all hosts")
    virt_helper.set_host_status()
    testflow.setup("Updates 2 VMs %s to 85 percent of host memory", test_vms)
    assert hl_vms.update_os_type(
        os_type=config.VM_OS_TYPE, test_vms=test_vms
    ), virt_helper.get_err_msg(update_os_type, vm_name=test_vms)
    status, config.HOST_INDEX_MAX_MEMORY = (
        hl_vms.set_vms_with_host_memory_by_percentage(
            test_hosts=test_hosts,
            test_vms=test_vms,
            percentage=percentage
        )
    )
    assert status, virt_helper.get_err_msg(action=failed_update_vm_memory)
    testflow.setup("Start vms %s", test_vms)
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
        testflow.teardown("Stop vm %s", vm_name)
        ll_vms.safely_remove_vms(vms=[vm_name])
    request.addfinalizer(fin)

    testflow.setup("Create vm %s", vm_name)
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
    testflow.setup("Start vm %s", vm_name)
    assert ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_status=config.VM_UP,
        wait_for_ip=False
    ), virt_helper.get_err_msg(action=actions[0], vm_name=vm_name)


@pytest.fixture(scope="class")
def restore_default_policy_on_cluster(request):
    def fin():
        """
        update cluster migration policy and bandwidth to default
        (minimal_downtime, auto)
        """
        testflow.teardown("update cluster migration policy to default")
        migration_helper.update_migration_policy_on_cluster(
            migration_policy=config.MIGRATION_POLICY_NAMES[0],
            cluster_name=config.CLUSTER_NAME[0],
            bandwidth=config.BW_AUTO
        )

    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def restore_default_policy_on_vm(request):
    def fin():
        """
        update vm migration policy to default
        (policy=minimal_downtime, auto_converge=false,compressed=false)
        """
        vm_name = request.node.cls.vm_name
        testflow.teardown("update vm migration policy to default")
        migration_helper.update_migration_policy_on_vm(
            vm_name=vm_name,
            migration_policy=config.MIGRATION_POLICY_INHERIT
        )

    request.addfinalizer(fin)


@pytest.fixture(scope='class')
def load_vm(request):
    """
    Run load vm
    """

    vm_name = config.MIGRATION_VM_LOAD
    load_size = request.node.cls.load_size
    time_to_run_load = request.node.cls.time_to_run_load

    testflow.setup(
        "Run load on vm %s. Load size:%d Duration:%d",
        vm_name, load_size, time_to_run_load
    )
    assert virt_helper.load_vm_memory_with_load_tool(
        vm_name=vm_name,
        load=load_size,
        time_to_run=time_to_run_load,
        start_vm=False
    )


@pytest.fixture(scope="class")
def start_vm_on_spm(request):
    """
    Run VM on SPM host
    """
    ll_vms.stop_vms_safely([config.MIGRATION_VM])
    time.sleep(config.ENGINE_STAT_UPDATE_INTERVAL)
    testflow.setup("Run VM %s on SPM host", config.MIGRATION_VM)
    spm_host = hl_data_center.get_spm_host(
        positive=True,
        datacenter=config.DATA_CENTER_NAME
    )
    assert hl_vms.run_vm_once_specific_host(
        vm=config.MIGRATION_VM,
        host=spm_host.get_name(),
        wait_for_up_status=True
    )


@pytest.fixture(scope="module")
def teardown_migration(request):
    """
    Stop and remove load vm
    """

    def fin():
        testflow.teardown("Remove vm %s", config.MIGRATION_VM_LOAD)
        assert ll_vms.safely_remove_vms(vms=[config.MIGRATION_VM_LOAD])

    request.addfinalizer(fin)
