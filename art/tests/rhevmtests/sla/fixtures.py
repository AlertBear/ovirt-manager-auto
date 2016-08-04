"""
SLA fixtures
"""
import copy

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sds
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as sla_config
import pytest


@pytest.fixture(scope="class")
def start_vms(request):
    """
    1) Start VM's
    """
    vms_to_start = request.node.cls.vms_to_start
    wait_for_vms_ip = getattr(request.node.cls, "wait_for_vms_ip", True)

    def fin():
        """
        1) Stop VM's
        """
        ll_vms.stop_vms_safely(vms_list=vms_to_start)
    request.addfinalizer(fin)

    ll_vms.start_vms(vm_list=vms_to_start, wait_for_ip=wait_for_vms_ip)


@pytest.fixture(scope="class")
def stop_vms(request):
    vms_to_stop = request.node.cls.vms_to_stop

    def fin():
        """
        1) Stop VM's
        """
        ll_vms.stop_vms_safely(vms_list=vms_to_stop)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def run_once_vms(request):
    """
    Run once VM's
    """
    vms_to_run = request.node.cls.vms_to_run

    def fin():
        """
        1) Stop VM's
        """
        ll_vms.stop_vms_safely(vms_list=vms_to_run.keys())
    request.addfinalizer(fin)

    temp_vms_to_run = copy.deepcopy(vms_to_run)
    for vm_name, run_once_params in temp_vms_to_run.iteritems():
        host = run_once_params.get(sla_config.VM_RUN_ONCE_HOST)
        if host is not None:
            run_once_params[
                sla_config.VM_RUN_ONCE_HOST
            ] = sla_config.HOSTS[host]
    ll_vms.run_vms_once(vms=temp_vms_to_run.keys(), **temp_vms_to_run)


@pytest.fixture(scope="class")
def update_vms(request):
    """
    1) Update VM's
    """
    vms_to_params = request.node.cls.vms_to_params

    def fin():
        """
        1) Update VM's to default parameters
        """
        for vm_name in vms_to_params.iterkeys():
            ll_vms.updateVm(
                positive=True, vm=vm_name, **sla_config.DEFAULT_VM_PARAMETERS
            )
    request.addfinalizer(fin)

    temp_vms_to_params = copy.deepcopy(vms_to_params)
    for vm_name, vm_params in temp_vms_to_params.iteritems():
        if sla_config.VM_PLACEMENT_HOSTS in vm_params:
            hosts = []
            for host_index in vm_params[sla_config.VM_PLACEMENT_HOSTS]:
                hosts.append(sla_config.HOSTS[host_index])
                vm_params[sla_config.VM_PLACEMENT_HOSTS] = hosts
        if sla_config.VM_PLACEMENT_HOST in vm_params:
            vm_params[sla_config.VM_PLACEMENT_HOST] = sla_config.HOSTS[
                vm_params[sla_config.VM_PLACEMENT_HOST]
            ]
        assert ll_vms.updateVm(
            positive=True, vm=vm_name, **vm_params
        )


@pytest.fixture(scope="class")
def activate_hosts(request):
    hosts_to_activate_indexes = request.node.cls.hosts_to_activate_indexes

    def fin():
        """
        1) Activate all hosts
        """
        hosts_to_activate = [
            sla_config.HOSTS[i] for i in hosts_to_activate_indexes
        ]
        for host_to_activate in hosts_to_activate:
            hl_hosts.activate_host_if_not_up(host=host_to_activate)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def update_vms_to_default_parameters(request):
    update_to_default_params = request.node.cls.update_to_default_params

    def fin():
        """
        1) Update VM's to default parameters
        """
        for vm_name in update_to_default_params:
            ll_vms.updateVm(
                positive=True, vm=vm_name, **sla_config.DEFAULT_VM_PARAMETERS
            )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def deactivate_hosts(request):
    """
    1) Deactivate hosts
    """
    hosts_to_maintenance = request.node.cls.hosts_to_maintenance
    hosts_to_deactivate = [
        sla_config.HOSTS[i] for i in hosts_to_maintenance
    ]

    def fin():
        """
        1) Activate hosts
        """
        for host_name in hosts_to_deactivate:
            hl_hosts.activate_host_if_not_up(host=host_name)
    request.addfinalizer(fin)

    for host_name in hosts_to_deactivate:
        assert ll_hosts.deactivateHost(positive=True, host=host_name)
    assert ll_sds.waitForStorageDomainStatus(
        positive=True,
        dataCenterName=sla_config.DC_NAME[0],
        storageDomainName=sla_config.STORAGE_NAME[0],
        expectedStatus=sla_config.SD_ACTIVE
    )


@pytest.fixture(scope="class")
def update_vms_memory_to_hosts_memory(request):
    """
    1) Update VM's memory to be equal to hosts memory
    """
    update_vms_memory = request.node.cls.update_vms_memory

    def fin():
        """
        1) Update VM's to default parameters
        """
        for vm_name in update_vms_memory:
            ll_vms.updateVm(
                positive=True, vm=vm_name, **sla_config.DEFAULT_VM_PARAMETERS
            )

    request.addfinalizer(fin)

    hosts_memory = hl_vms.calculate_memory_for_memory_filter(
        hosts_list=sla_config.HOSTS[:len(update_vms_memory)]
    )
    for vm_name, vm_memory in zip(update_vms_memory, hosts_memory):
        vm_params = {
            sla_config.VM_MEMORY: vm_memory,
            sla_config.VM_MEMORY_GUARANTEED: vm_memory
        }
        assert ll_vms.updateVm(positive=True, vm=vm_name, **vm_params)


@pytest.fixture(scope="class")
def create_cluster_for_affinity_test(request):
    """
    1) Create additional cluster
    """
    additional_cluster_name = request.node.cls.additional_cluster_name

    def fin():
        """
        1) Remove additional cluster
        """
        ll_clusters.removeCluster(
            positive=True, cluster=additional_cluster_name
        )
    request.addfinalizer(fin)

    assert ll_clusters.addCluster(
        positive=True,
        name=additional_cluster_name,
        cpu=sla_config.CPU_NAME,
        version=sla_config.COMP_VERSION,
        data_center=sla_config.DC_NAME[0]
    )
