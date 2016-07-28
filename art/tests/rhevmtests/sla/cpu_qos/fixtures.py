"""
CPU QoS fixtures
"""
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import pytest
import rhevmtests.helpers as rhevm_helpers

logger = conf.logging.getLogger(__name__)


@pytest.fixture(scope="class")
def create_cpu_qoss(request):
    """
    1) Add CPU QoSS to datacenter
    """
    cpu_qoss = request.node.cls.cpu_qoss

    def fin():
        """
        1) Remove CPU QoSS from datacenter
        """
        for cpu_qos_name in cpu_qoss.iterkeys():
            ll_datacenters.delete_qos_from_datacenter(
                datacenter=conf.DC_NAME[0], qos_name=cpu_qos_name
            )
    request.addfinalizer(fin)

    for cpu_qos_name, cpu_qos_value in cpu_qoss.iteritems():
        assert ll_datacenters.add_qos_to_datacenter(
            datacenter=conf.DC_NAME[0],
            qos_name=cpu_qos_name,
            qos_type=conf.QOS_TYPE_CPU,
            cpu_limit=cpu_qos_value
        )


@pytest.fixture(scope="class")
def create_cpu_profile(request):
    """
    1) Add CPU profiles to cluster
    """
    cpu_profiles = request.node.cls.cpu_profiles

    def fin():
        """
        1) Remove CPU profiles from cluster
        """
        for cpu_profile_name in cpu_profiles.iterkeys():
            ll_clusters.remove_cpu_profile(
                cluster_name=conf.CLUSTER_NAME[0],
                cpu_prof_name=cpu_profile_name
            )
    request.addfinalizer(fin)

    for cpu_profile_name, cpu_qos_name in cpu_profiles.iteritems():
        cpu_qos_obj = ll_datacenters.get_qos_from_datacenter(
            datacenter=conf.DC_NAME[0], qos_name=cpu_qos_name
        )
        assert ll_clusters.add_cpu_profile(
            cluster_name=conf.CLUSTER_NAME[0],
            name=cpu_profile_name,
            qos=cpu_qos_obj
        )


@pytest.fixture(scope="class")
def attach_cpu_profiles_to_vms(request):
    """
    1) Attach CPU profiles to VM's
    """
    vms_to_cpu_profiles = request.node.cls.vms_to_cpu_profiles

    def fin():
        """
        1) Attach default CPU profile to VM's
        """
        for vm_name in vms_to_cpu_profiles.iterkeys():
            ll_vms.updateVm(
                positive=True,
                vm=vm_name,
                cpu_profile_id=conf.DEFAULT_CPU_PROFILE_ID_CLUSTER_0
            )
    request.addfinalizer(fin)

    for vm_name, cpu_profile_name in vms_to_cpu_profiles.iteritems():
        cpu_profile_id = ll_clusters.get_cpu_profile_id_by_name(
            cluster_name=conf.CLUSTER_NAME[0],
            cpu_profile_name=cpu_profile_name
        )
        assert ll_vms.updateVm(
            positive=True, vm=vm_name, cpu_profile_id=cpu_profile_id
        )


@pytest.fixture(scope="class")
def create_template_for_cpu_qos_test(request):
    """
    1) Create template from VM
    """
    cpu_profile_id = ll_clusters.get_cpu_profile_id_by_name(
        cluster_name=conf.CLUSTER_NAME[0], cpu_profile_name=conf.CPU_PROFILE_10
    )

    def fin():
        """
        1) Remove template
        """
        ll_templates.removeTemplate(positive=True, template=conf.QOS_TEMPLATE)
    request.addfinalizer(fin)

    assert ll_templates.createTemplate(
        positive=True,
        name=conf.QOS_TEMPLATE,
        vm=conf.QOS_VMS[0],
        cluster=conf.CLUSTER_NAME[0],
        cpu_profile_id=cpu_profile_id

    )


@pytest.fixture(scope="class")
def create_vm_from_template_for_cpu_qos_test(request):
    """
    1) Create VM from template
    """
    def fin():
        """
        1) Remove VM
        """
        ll_vms.removeVm(positive=True, vm=conf.QOS_VM_FROM_TEMPLATE)
    request.addfinalizer(fin)

    assert ll_vms.createVm(
        positive=True,
        vmName=conf.QOS_VM_FROM_TEMPLATE,
        cluster=conf.CLUSTER_NAME[1],
        template=conf.QOS_TEMPLATE
    )


@pytest.fixture(scope="class")
def disable_guest_agent_service(request):
    """
    1) Stop puppet and agent services
    """
    vm_resource = rhevm_helpers.get_host_resource(
        ip=hl_vms.get_vm_ip(conf.QOS_VMS[0]),
        password=conf.VMS_LINUX_PW
    )

    def fin():
        """
        1) Start puppet and agent services
        """
        for service_name in (conf.SERVICE_GUEST_AGENT, conf.SERVICE_PUPPET):
            logger.info("Start %s service", service_name)
            vm_resource.service(name=service_name).start()
    request.addfinalizer(fin)

    for service_name in (conf.SERVICE_GUEST_AGENT, conf.SERVICE_PUPPET):
        logger.info("Stop %s service", service_name)
        vm_resource.service(name=service_name).stop()


@pytest.fixture(scope="class")
def update_vms_cpu(request):
    """
    Update number of VM's CPU's to be equal to number of host CPU's
    """
    update_vms_cpu = request.node.cls.update_vms_cpu

    for vm_name in update_vms_cpu:
        host_cpu = ll_hosts.get_host_processing_units_number(
            host_name=conf.HOSTS[0]
        )
        assert ll_vms.updateVm(positive=True, vm=vm_name, cpu_socket=host_cpu)
