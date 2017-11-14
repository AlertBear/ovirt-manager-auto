"""
SLA fixtures
"""
import copy
import socket
import time
from datetime import datetime

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.events as ll_events
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as sla_config
import helpers as sla_helpers
import pytest
import rhevmtests.compute.sla.scheduler_tests.helpers as sch_helpers
import rhevmtests.helpers as rhevm_helpers
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
    wait_for_vms_state = getattr(
        request.node.cls, "wait_for_vms_state", sla_config.VM_POWERING_UP
    )

    def fin():
        """
        1) Stop VM's
        """
        ll_vms.stop_vms_safely(vms_list=vms_to_start)
        time.sleep(sla_config.ENGINE_STAT_UPDATE_INTERVAL)
    request.addfinalizer(fin)

    u_libs.testflow.setup("Start VM's %s", vms_to_start)
    ll_vms.start_vms(
        vm_list=vms_to_start,
        wait_for_ip=wait_for_vms_ip,
        max_workers=len(vms_to_start),
        wait_for_status=wait_for_vms_state
    )


@pytest.fixture(scope="class")
def stop_vms(request):
    vms_to_stop = request.node.cls.vms_to_stop

    def fin():
        """
        1) Stop VM's
        """
        u_libs.testflow.teardown("Stop VM's %s", vms_to_stop)
        ll_vms.stop_vms_safely(vms_list=vms_to_stop)
        time.sleep(sla_config.ENGINE_STAT_UPDATE_INTERVAL)
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
        u_libs.testflow.teardown("Stop VM's %s", vms_to_run.keys())
        ll_vms.stop_vms_safely(vms_list=vms_to_run.keys())
        time.sleep(sla_config.ENGINE_STAT_UPDATE_INTERVAL)
    request.addfinalizer(fin)

    temp_vms_to_run = copy.deepcopy(vms_to_run)
    for vm_name, run_once_params in temp_vms_to_run.iteritems():
        host = run_once_params.get(sla_config.VM_RUN_ONCE_HOST)
        if host is not None:
            run_once_params[
                sla_config.VM_RUN_ONCE_HOST
            ] = sla_config.HOSTS[host]
    u_libs.testflow.setup(
        "Run VM's once %s with params: %s",
        temp_vms_to_run.keys(), temp_vms_to_run.values()
    )
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
            temp_default_params = copy.deepcopy(
                sla_config.DEFAULT_VM_PARAMETERS
            )
            if sla_config.VM_CPU_PROFILE in vm_params:
                cpu_profile_id = ll_clusters.get_cpu_profile_id_by_name(
                    cluster_name=sla_config.CLUSTER_NAME[0],
                    cpu_profile_name=sla_config.CLUSTER_NAME[0]
                )
                temp_default_params[sla_config.VM_CPU_PROFILE] = cpu_profile_id
            ll_vms.updateVm(positive=True, vm=vm_name, **temp_default_params)
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
        if sla_config.VM_CPU_PROFILE in vm_params:
            cpu_profile_id = ll_clusters.get_cpu_profile_id_by_name(
                cluster_name=sla_config.CLUSTER_NAME[0],
                cpu_profile_name=vm_params[sla_config.VM_CPU_PROFILE]
            )
            vm_params[sla_config.VM_CPU_PROFILE] = cpu_profile_id
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
        hosts_resources = [
            sla_config.VDS_HOSTS[i] for i in hosts_to_activate_indexes
        ]
        for host_to_activate, host_resource in zip(
            hosts_to_activate, hosts_resources
        ):
            hl_hosts.activate_host_if_not_up(
                host=host_to_activate, host_resource=host_resource
            )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def update_vms_to_default_parameters(request):
    update_to_default_params = request.node.cls.update_to_default_params

    def fin():
        """
        1) Update VM's to default parameters
        """
        for vm_name in update_to_default_params:
            u_libs.testflow.teardown(
                "Update the VM %s to default parameters", vm_name
            )
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
    hosts_resources = [
        sla_config.VDS_HOSTS[i] for i in hosts_to_maintenance
    ]

    def fin():
        """
        1) Activate hosts
        """
        for host_to_deactivate, host_resource in zip(
            hosts_to_deactivate, hosts_resources
        ):
            hl_hosts.activate_host_if_not_up(
                host=host_to_deactivate, host_resource=host_resource
            )
    request.addfinalizer(fin)

    for host_to_deactivate, host_resource in zip(
        hosts_to_deactivate, hosts_resources
    ):
        assert hl_hosts.deactivate_host_if_up(
            host=host_to_deactivate, host_resource=host_resource
        )


@pytest.fixture(scope="class")
def update_vms_memory_to_hosts_memory(request):
    """
    1) Update VM's memory to be equal to hosts memory
    """
    update_vms_memory = request.node.cls.update_vms_memory

    hosts_memory = hl_vms.calculate_memory_for_memory_filter(
        hosts_list=sla_config.HOSTS[:len(update_vms_memory)], difference=20
    )
    for vm_name, vm_memory in zip(update_vms_memory, hosts_memory):
        vm_params = {
            sla_config.VM_MEMORY: vm_memory,
            sla_config.VM_MEMORY_GUARANTEED: vm_memory,
            sla_config.VM_MAX_MEMORY: vm_memory + sla_config.GB
        }
        u_libs.testflow.setup(
            "Update the VM %s with params %s", vm_name, vm_params
        )
        assert ll_vms.updateVm(positive=True, vm=vm_name, **vm_params)


@pytest.fixture(scope="class")
def create_additional_cluster(request):
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

    u_libs.testflow.setup(
        "Create the additional cluster %s", additional_cluster_name
    )
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
    1) Stop the guest agent service
    """
    stop_guest_agent_vm = request.node.cls.stop_guest_agent_vm
    vm_resource = rhevm_helpers.get_host_resource(
        ip=hl_vms.get_vm_ip(stop_guest_agent_vm),
        password=sla_config.VMS_LINUX_PW
    )

    def fin():
        """
        1) Start guest the agent service
        """
        u_libs.testflow.teardown(
            "Start %s service", sla_config.SERVICE_GUEST_AGENT
        )
        vm_resource.service(name=sla_config.SERVICE_GUEST_AGENT).start()
    request.addfinalizer(fin)

    u_libs.testflow.setup("Stop %s service", sla_config.SERVICE_GUEST_AGENT)
    assert vm_resource.service(name=sla_config.SERVICE_GUEST_AGENT).stop()
    time.sleep(sla_config.GUEST_AGENT_TIMEOUT)


@pytest.fixture(scope="class")
def update_cluster_to_default_parameters(request):
    """
    1) Update cluster to default parameters
    """
    def fin():
        u_libs.testflow.teardown(
            "Update cluster %s to default parameters %s",
            sla_config.CLUSTER_NAME[0], sla_config.DEFAULT_CLUSTER_PARAMETERS
        )
        ll_clusters.updateCluster(
            positive=True,
            cluster=sla_config.CLUSTER_NAME[0],
            **sla_config.DEFAULT_CLUSTER_PARAMETERS
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
        u_libs.testflow.teardown(
            "Remove VM's %s", vms_create_params.keys()
        )
        ll_vms.safely_remove_vms(vms=vms_create_params.keys())
    request.addfinalizer(fin)

    results = []
    u_libs.testflow.setup(
        "Create VM's %s with parameters: %s",
        vms_create_params.keys(), vms_create_params.values()
    )
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
            for quota_type in (sla_config.VM_QUOTA, sla_config.VM_DISK_QUOTA):
                if quota_type in vm_params:
                    quota_id = ll_datacenters.get_quota_id_by_name(
                        dc_name=sla_config.DC_NAME[0],
                        quota_name=vm_params[quota_type]
                    )
                    vm_params[quota_type] = quota_id
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

    if not sla_config.PPC_ARCH or host_as_spm != 2:
        u_libs.testflow.setup(
            "Wait until all async tasks will be gone from the engine"
        )
        test_utils.wait_for_tasks(
            engine=sla_config.ENGINE,
            datacenter=sla_config.DC_NAME[0]
        )
        u_libs.testflow.setup(
            "Wait until all SPM tasks will be gone from the SPM host"
        )
        assert sla_helpers.wait_for_spm_tasks_on_host()
        assert sla_helpers.wait_for_dc_and_storagedomains()
        u_libs.testflow.setup("Choose the host %s as SPM", host_as_spm)
        assert ll_hosts.select_host_as_spm(
            positive=True,
            host=sla_config.HOSTS[host_as_spm],
            data_center=sla_config.DC_NAME[0]
        )
        time.sleep(sla_config.ENGINE_STAT_UPDATE_INTERVAL)
        assert sla_helpers.wait_for_dc_and_storagedomains()


@pytest.fixture(scope="class")
def export_vm(request):
    """
    1) Export VM
    """
    vm_to_export = request.node.cls.vm_to_export

    def fin():
        """
        1) Remove VM from export domain
        """
        u_libs.testflow.teardown(
            "Remove VM %s from the export domain", vm_to_export
        )
        ll_vms.remove_vm_from_export_domain(
            positive=True,
            vm=vm_to_export,
            datacenter=sla_config.DC_NAME[0],
            export_storagedomain=sla_config.EXPORT_DOMAIN_NAME
        )

    request.addfinalizer(fin)

    u_libs.testflow.setup("Export the VM %s", vm_to_export)
    assert ll_vms.exportVm(
        positive=True,
        vm=vm_to_export,
        storagedomain=sla_config.EXPORT_DOMAIN_NAME
    )


@pytest.fixture(scope="class")
def import_vm(request):
    """
    1) Import VM
    """
    vm_to_import = request.node.cls.vm_to_import
    vm_import_name = request.node.cls.vm_import_name

    def fin():
        """
        1) Remove imported VM
        """
        u_libs.testflow.teardown("Remove the VM %s", vm_import_name)
        ll_vms.removeVm(positive=True, vm=vm_import_name)

    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Import the VM %s from the export domain as %s",
        vm_to_import, vm_import_name
    )
    assert ll_vms.importVm(
        positive=True,
        vm=vm_to_import,
        export_storagedomain=sla_config.EXPORT_DOMAIN_NAME,
        import_storagedomain=sla_config.STORAGE_NAME[0],
        cluster=sla_config.CLUSTER_NAME[0],
        name=vm_import_name
    )


@pytest.fixture(scope="class")
def make_template_from_vm(request):
    """
    1) Make template from VM
    """
    vm_for_template = request.node.cls.vm_for_template
    template_name = request.node.cls.template_name

    def fin():
        """
        1) Remove template
        """
        if ll_templates.check_template_existence(template_name=template_name):
            u_libs.testflow.teardown("Remove the template %s", template_name)
            ll_templates.remove_template(
                positive=True, template=template_name
            )

    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Create the template %s from the VM %s", template_name, vm_for_template
    )
    assert ll_templates.createTemplate(
        positive=True,
        vm=vm_for_template,
        name=template_name,
        cluster=sla_config.CLUSTER_NAME[0],
        storagedomain=sla_config.STORAGE_NAME[0]
    )


@pytest.fixture(scope="class")
def make_vm_from_template(request):
    """
    1) Make VM from template
    """
    template_name = request.node.cls.template_name
    vm_from_template_name = request.node.cls.vm_from_template_name

    def fin():
        """
        1) Remove VM
        """
        u_libs.testflow.teardown("Remove the VM %s", vm_from_template_name)
        ll_vms.removeVm(positive=True, vm=vm_from_template_name)

    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Create the VM %s from the template %s",
        vm_from_template_name, template_name
    )
    assert ll_vms.addVm(
        positive=True,
        cluster=sla_config.CLUSTER_NAME[0],
        name=vm_from_template_name,
        template=template_name
    )


@pytest.fixture(scope="class")
def update_datacenter(request):
    """
    1) Update datacenter
    """
    dcs_to_update = request.node.cls.dcs_to_update

    def fin():
        u_libs.testflow.teardown(
            "Update DC %s with default parameters", sla_config.DC_NAME[0]
        )
        ll_datacenters.update_datacenter(
            positive=True,
            datacenter=dc_name,
            **sla_config.DEFAULT_DC_PARAMETERS
        )
    request.addfinalizer(fin)

    for dc_name, dc_params in dcs_to_update.iteritems():
        u_libs.testflow.setup(
            "Update DC %s with parameters: %s", dc_name, dc_params
        )
        assert ll_datacenters.update_datacenter(
            positive=True, datacenter=dc_name, **dc_params
        )


@pytest.fixture(scope="class")
def update_vms_cpus_to_hosts_cpus(request):
    """
    1) Update VM's CPU's number to be equal to hosts CPU's number
    """
    vms_to_hosts_cpus = request.node.cls.vms_to_hosts_cpus
    double_vms_cpus = getattr(request.node.cls, "double_vms_cpus", False)
    threads_on = getattr(request.node.cls, "threads_on", False)

    for vm_name, host_index in vms_to_hosts_cpus.iteritems():
        host_name = sla_config.HOSTS[host_index]
        host_topology = ll_hosts.get_host_topology(host_name=host_name)
        multiplier = 2 if double_vms_cpus else 1
        vm_cores = host_topology.cores
        if threads_on:
            vm_cores *= host_topology.threads
        vm_params = {
            sla_config.VM_CPU_SOCKET: host_topology.sockets * multiplier,
            sla_config.VM_CPU_CORES: vm_cores
        }
        u_libs.testflow.setup(
            "Update the VM %s with params %s", vm_name, vm_params
        )
        assert ll_vms.updateVm(positive=True, vm=vm_name, **vm_params)


@pytest.fixture(scope="class")
def update_cluster(request, update_cluster_to_default_parameters):
    """
    Update the cluster
    """
    cluster_to_update_params = request.node.cls.cluster_to_update_params

    u_libs.testflow.setup(
        "Update the cluster %s with parameters %s",
        sla_config.CLUSTER_NAME[0], cluster_to_update_params
    )
    assert ll_clusters.updateCluster(
        positive=True,
        cluster=sla_config.CLUSTER_NAME[0],
        **cluster_to_update_params
    )


@pytest.fixture(scope="class")
def configure_hosts_power_management(request):
    """
    1) Add power management to the hosts
    """
    hosts_to_pms = request.node.cls.hosts_to_pms

    def fin():
        """
        1) Remove power management from the hosts
        """
        results = []
        for host_index in hosts_to_pms:
            u_libs.testflow.teardown(
                "Remove PM from the host %s", sla_config.HOSTS[host_index]
            )
            results.append(
                hl_hosts.remove_power_management(
                    host_name=sla_config.HOSTS[host_index]
                )
            )
        assert all(results)
    request.addfinalizer(fin)

    pm_hosts = dict(
        (sla_config.HOSTS[i], sla_config.VDS_HOSTS[i]) for i in hosts_to_pms
    )
    if not sch_helpers.configure_pm_on_hosts(hosts=pm_hosts):
        pytest.skip("Not all hosts have power management")


@pytest.fixture(scope="class")
def stop_host_network(request):
    """
    1) Stop the host network
    2) Wait until the host will have 'Non-Responsive' state
    """
    stop_network_on_host = request.node.cls.stop_network_on_host
    host_name = sla_config.HOSTS[stop_network_on_host]
    host_resource = sla_config.VDS_HOSTS[stop_network_on_host]

    def fin():
        """
        1) Wait until the host will have 'Up' state
        """
        u_libs.testflow.teardown(
            "Wait until the host %s will have 'Up' state",
            host_name
        )
        ll_hosts.wait_for_hosts_states(positive=True, names=host_name)
    request.addfinalizer(fin)

    u_libs.testflow.setup("Stop network service on the host %s", host_name)
    try:
        host_resource.network.if_down(nic=sla_config.MGMT_BRIDGE)
    except socket.timeout as ex:
        logger.warning("Host unreachable, %s", ex)
    u_libs.testflow.teardown(
        "Wait until the host %s will have 'Non-Responsive' state",
        host_name
    )
    assert ll_hosts.wait_for_hosts_states(
        positive=True, names=host_name, states=sla_config.HOST_NONRESPONSIVE
    )


@pytest.fixture(scope="class")
def create_vm_without_disk(request):
    """
    1) Create VM without disk for the future use
    """
    def fin():
        """
        1) Remove VM
        """
        u_libs.testflow.teardown("Remove VM %s", sla_config.VM_WITHOUT_DISK)
        ll_vms.safely_remove_vms(vms=[sla_config.VM_WITHOUT_DISK])
    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Add VM %s to the cluster %s",
        sla_config.VM_WITHOUT_DISK, sla_config.CLUSTER_NAME[0]
    )
    assert ll_vms.addVm(
        positive=True,
        name=sla_config.VM_WITHOUT_DISK,
        cluster=sla_config.CLUSTER_NAME[0],
        template=sla_config.BLANK_TEMPlATE
    )


@pytest.fixture(scope="class")
def attach_host_device(request):
    """
    Attach host device to VM
    """
    pci_device_name = getattr(request.node.cls, "pci_device_name", None)

    if not pci_device_name:
        pci_device = sla_helpers.get_pci_device(host_name=sla_config.HOSTS[0])
        if not pci_device:
            pytest.skip(
                "Can not find PCI device for passthrough on the host %s" %
                sla_config.HOSTS[0]
            )
        pci_device_name = pci_device.get_name()

    def fin():
        """
        Remove host device from VM
        """
        if ll_vms.get_vm_host_devices(vm_name=sla_config.VM_NAME[0]):
            u_libs.testflow.teardown(
                "Detach the host device %s from VM %s",
                pci_device_name, sla_config.VM_NAME[0]
            )
            assert ll_vms.remove_vm_host_device(
                vm_name=sla_config.VM_NAME[0], device_name=pci_device_name
            )
    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Attach the host device %s to VM %s",
        pci_device_name, sla_config.VM_NAME[0]
    )
    assert ll_vms.add_vm_host_device(
        vm_name=sla_config.VM_NAME[0],
        device_name=pci_device_name,
        host_name=sla_config.HOSTS[0]
    )


@pytest.fixture(scope="module")
def migrate_he_vm(request):
    """
    Migrate the HE VM from or to the host
    """
    he_src_host = getattr(request.node.module, "he_src_host", None)
    he_dst_host = getattr(request.node.module, "he_dst_host", None)

    if he_src_host is None and he_dst_host is None:
        return

    if sla_config.PPC_ARCH and (he_src_host == 2 or he_dst_host == 2):
        pytest.skip("The environment does not have enough hosts.")

    he_src_host_name = ""
    if he_src_host is not None:
        he_src_host_name = sla_config.HOSTS[he_src_host]

    he_dst_host_name = ""
    if he_dst_host is not None:
        he_dst_host_name = sla_config.HOSTS[he_dst_host]

    he_vm_host = ll_vms.get_vm_host(vm_name=sla_config.HE_VM)
    for host_name, positive in zip(
        (he_src_host_name, he_dst_host_name), (True, False)
    ):
        if host_name and ll_hosts.is_hosted_engine_configured(
            host_name=host_name
        ):
            if (he_vm_host == host_name) == positive:
                u_libs.testflow.setup("Migrate the HE VM")
                assert ll_vms.migrateVm(
                    positive=True,
                    vm=sla_config.HE_VM,
                    host=he_dst_host_name,
                    force=True
                )
                u_libs.testflow.setup(
                    "Wait %s, until the engine will update all hosts stats",
                    sla_config.UPDATE_SCHEDULER_MEMORY_TIMEOUT
                )
                time.sleep(sla_config.UPDATE_SCHEDULER_MEMORY_TIMEOUT)
                break


@pytest.fixture(scope="class")
def skip_if_not_he_environment():
    """
    Skip the test if the environment does not configure as hosted engine
    """
    if not ll_vms.get_vm_host(vm_name=sla_config.HE_VM):
        pytest.skip("Does not hosted engine environment")


@pytest.fixture(scope="class")
def wait_for_hosts_status_up(request):
    """
    Wait until hosts will have the status equal to 'up'
    """
    hosts_indexes_status_up = request.node.cls.hosts_indexes_status_up
    hosts_names = [sla_config.HOSTS[i] for i in hosts_indexes_status_up]

    def fin():
        u_libs.testflow.teardown(
            "Wait until hosts %s will have status different from 'up'",
            hosts_names
        )
        ll_hosts.wait_for_hosts_states(
            positive=True,
            names=hosts_names,
            states=[
                sla_config.HOST_NONRESPONSIVE,
                sla_config.HOST_CONNECTING,
                sla_config.HOST_REBOOTING
            ]
        )
        u_libs.testflow.teardown(
            "Wait until hosts %s will have status 'up'", hosts_names
        )
        ll_hosts.wait_for_hosts_states(positive=True, names=hosts_names)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def define_hugepages_on_hosts(request):
    """
    Set hugepages of different sizes on hosts
    """
    hosts_to_hugepages = request.node.cls.hosts_to_hugepages

    def fin():
        result = []
        for host_index, hugepages in hosts_to_hugepages.iteritems():
            for hugepage_size in hugepages.iterkeys():
                vds_host = sla_config.VDS_HOSTS[host_index]
                hugepage_file = sla_config.HUGEPAGES_NR_FILE.format(
                    hugepage_size
                )
                if not vds_host.fs.exists(hugepage_file):
                    continue
                u_libs.testflow.teardown(
                    "%s :set %s hugepages of size %skB",
                    sla_config.VDS_HOSTS[host_index],
                    0,
                    hugepage_size
                )
                cmd = [
                    "echo", "0", ">", hugepage_file
                ]
                result.append(not vds_host.run_command(cmd)[0])
                result.append(
                    sla_helpers.wait_for_host_hugepages(
                        host_name=sla_config.HOSTS[host_index],
                        hugepage_size=hugepage_size,
                        expected_hugepages_nr=0
                    )
                )
        assert all(result)
    request.addfinalizer(fin)

    for host_index, hugepages in hosts_to_hugepages.iteritems():
        for hugepage_size, total_size in hugepages.iteritems():
            vds_host = sla_config.VDS_HOSTS[host_index]
            hugepage_file = sla_config.HUGEPAGES_NR_FILE.format(
                hugepage_size
            )
            if not vds_host.fs.exists(hugepage_file):
                pytest.skip(
                    "%s: does not support hugepages of size %s",
                    vds_host, hugepage_size
                )
            hugepages_nr = total_size / (int(hugepage_size) * 1024)
            u_libs.testflow.setup(
                "%s :set %s of hugepages of size %skB",
                vds_host,
                hugepages_nr,
                hugepage_size
            )
            cmd = ["echo", str(hugepages_nr), ">", hugepage_file]
            assert not vds_host.run_command(cmd)[0]
            assert sla_helpers.wait_for_host_hugepages(
                host_name=sla_config.HOSTS[host_index],
                hugepage_size=hugepage_size,
                expected_hugepages_nr=hugepages_nr
            )


@pytest.fixture(scope="class")
def create_equals_numa_nodes_on_vm(request):
    """
    1) Add equals NUMA nodes to the VM
    """
    num_of_vm_numa_nodes = request.node.cls.num_of_vm_numa_nodes

    numa_nodes = sla_helpers.create_number_of_equals_numa_nodes(
        resource=sla_config.VDS_HOSTS[0],
        vm_name=sla_config.VM_NAME[0],
        num_of_numa_nodes=num_of_vm_numa_nodes
    )
    for numa_node in numa_nodes:
        assert ll_vms.add_numa_node_to_vm(
            vm_name=sla_config.VM_NAME[0],
            host_name=sla_config.HOSTS[0],
            **numa_node
        )


@pytest.fixture(scope="class")
def create_custom_numa_nodes_on_vm(request):
    """
    1) Create custom NUMA nodes on the VM
    """
    vm_numa_nodes_params = request.node.cls.vm_numa_nodes_params

    for numa_node in vm_numa_nodes_params:
        assert ll_vms.add_numa_node_to_vm(
            vm_name=sla_config.VM_NAME[0],
            host_name=sla_config.HOSTS[0],
            **numa_node
        )


@pytest.fixture(scope="class")
def remove_all_numa_nodes_from_vm(request):
    def fin():
        """
        1) Remove all NUMA nodes from the VM
        """
        vm_numa_nodes_indexes = [
            vm_numa_node.index for vm_numa_node in ll_vms.get_vm_numa_nodes(
                sla_config.VM_NAME[0]
            )
        ]
        vm_numa_nodes_indexes.sort(reverse=True)
        for numa_node_index in vm_numa_nodes_indexes:
            ll_vms.remove_numa_node_from_vm(
                vm_name=sla_config.VM_NAME[0], numa_node_index=numa_node_index
            )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def skip_numa_tests():
    """
    Skip NUMA tests on the environment that does not have hosts with NUMA nodes
    """
    host_numa_nodes_l = sla_helpers.filter_nodes_without_memory(
        resource=sla_config.VDS_HOSTS[0]
    )
    if len(host_numa_nodes_l) < 2:
        pytest.skip(
            "Number of NUMA nodes with the memory greater "
            "than zero on the host %s less than 2" %
            sla_config.HOSTS[0]
        )


@pytest.fixture(scope="class")
def wait_fence_engine_restart_timeout():
    """
    Wait "DisableFenceAtStartupInSec" seconds to make sure that the engine can
    run fence actions
    """
    arem_initialization_event = ll_events.get_last_event(
        code=sla_config.EVENT_AREM_INITIALIZATION
    )
    if arem_initialization_event.get_id() == "1":
        return

    event_time = arem_initialization_event.get_time().replace(tzinfo=None)
    time_pass = (datetime.now() - event_time).total_seconds()
    if time_pass >= sla_config.FENCE_INITIALIZATION_TIMEOUT:
        return
    else:
        time_to_wait = sla_config.FENCE_INITIALIZATION_TIMEOUT - time_pass
        u_libs.testflow.setup(
            "Wait %ss to be sure that the engine can run fence actions",
            time_to_wait
        )
        time.sleep(int(time_to_wait))
