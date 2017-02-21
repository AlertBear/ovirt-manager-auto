"""
CPU QoS fixtures
"""
import pytest

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf


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
        ll_templates.remove_template(positive=True, template=conf.QOS_TEMPLATE)
    request.addfinalizer(fin)

    assert ll_templates.createTemplate(
        positive=True,
        name=conf.QOS_TEMPLATE,
        vm=conf.VM_WITHOUT_DISK,
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
