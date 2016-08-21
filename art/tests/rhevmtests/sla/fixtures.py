"""
SLA fixtures
"""
import copy

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as sla_config
import pytest
import rhevmtests.helpers as rhevm_helpers
from art.core_api import apis_exceptions
from art.rhevm_api.utils import test_utils
from concurrent.futures import ThreadPoolExecutor


logger = sla_config.logging.getLogger(__name__)


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

    ll_vms.start_vms(
        vm_list=vms_to_start,
        wait_for_ip=wait_for_vms_ip,
        max_workers=len(vms_to_start)
    )


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


@pytest.fixture(scope="class")
def update_vms_memory_to_hosts_memory(request):
    """
    1) Update VM's memory to be equal to hosts memory
    """
    update_vms_memory = request.node.cls.update_vms_memory

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


@pytest.fixture(scope="class")
def stop_guest_agent_service(request):
    """
    1) Stop the agent service
    """
    stop_guest_agent_vm = request.node.cls.stop_guest_agent_vm
    vm_resource = rhevm_helpers.get_host_resource(
        ip=hl_vms.get_vm_ip(stop_guest_agent_vm),
        password=sla_config.VMS_LINUX_PW
    )

    def fin():
        """
        1) Start the agent service
        """
        logger.info("Start %s service", sla_config.SERVICE_GUEST_AGENT)
        vm_resource.service(name=sla_config.SERVICE_GUEST_AGENT).start()
    request.addfinalizer(fin)

    logger.info("Stop %s service", sla_config.SERVICE_GUEST_AGENT)
    assert vm_resource.service(name=sla_config.SERVICE_GUEST_AGENT).stop()


@pytest.fixture(scope="class")
def update_cluster_to_default_parameters(request):
    def fin():
        """
        1) Update cluster to default parameters
        """
        ll_clusters.updateCluster(
            positive=True,
            cluster=sla_config.CLUSTER_NAME[0],
            ksm_enabled=False,
            ballooning_enabled=False,
            mem_ovrcmt_prc=sla_config.CLUSTER_OVERCOMMITMENT_DESKTOP
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def create_vms(request):
    """
    1) Create VM's
    """
    vms_create_params = request.node.cls.vms_create_params

    def fin():
        """
        1) Remove VM's
        """
        ll_vms.safely_remove_vms(vms=vms_create_params.iterkeys())
    request.addfinalizer(fin)

    results = []
    with ThreadPoolExecutor(max_workers=len(vms_create_params)) as executor:
        for vm_name, vm_params in vms_create_params.iteritems():
            if sla_config.VM_PLACEMENT_HOSTS in vm_params:
                hosts = []
                for host_index in vm_params[sla_config.VM_PLACEMENT_HOSTS]:
                    hosts.append(sla_config.HOSTS[host_index])
                vm_params[sla_config.VM_PLACEMENT_HOSTS] = hosts
            if sla_config.VM_PLACEMENT_HOST in vm_params:
                vm_params[sla_config.VM_PLACEMENT_HOST] = sla_config.HOSTS[
                    vm_params[sla_config.VM_PLACEMENT_HOST]
                ]
            results.append(
                executor.submit(
                    ll_vms.createVm, True, vm_name, **vm_params
                )
            )
    for result in results:
        if result.exception():
            raise result.exception()


@pytest.fixture(scope="module")
def choose_specific_host_as_spm(request):
    """
    1) Choose given host as SPM
    """
    host_as_spm = request.node.module.host_as_spm

    logger.info("Wait until all async tasks will be gone from the engine")
    try:
        test_utils.wait_for_tasks(
            vdc=sla_config.VDC_HOST,
            vdc_password=sla_config.VDC_ROOT_PASSWORD,
            datacenter=sla_config.DC_NAME[0]
        )
    except apis_exceptions.APITimeout:
        logger.error("Engine has async tasks that still running")
        return False
    assert ll_hosts.select_host_as_spm(
        positive=True,
        host=sla_config.HOSTS[host_as_spm],
        data_center=sla_config.DC_NAME[0]
    )
