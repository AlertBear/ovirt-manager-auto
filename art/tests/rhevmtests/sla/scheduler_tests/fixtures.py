"""
Scheduler tests fixtures
"""
from time import sleep

import art.rhevm_api.tests_lib.low_level.affinitylabels as ll_afflabels
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.unittest_lib as u_libs
import pytest
import rhevmtests.sla.config as sla_conf
import rhevmtests.sla.helpers as sla_helpers


@pytest.fixture(scope="class")
def load_hosts_cpu(request):
    """
    1) Load hosts CPU
    """
    hosts_cpu_load = getattr(request.node.cls, "hosts_cpu_load", None)
    if hosts_cpu_load:
        load_to_resources = {}
        for load_value, host_indexes in hosts_cpu_load.iteritems():
            load_to_resources[load_value] = {}
            load_to_resources[load_value][sla_conf.HOST] = []
            load_to_resources[load_value][sla_conf.RESOURCE] = []
            for host_index in host_indexes:
                load_to_resources[load_value][sla_conf.HOST].append(
                    sla_conf.HOSTS[host_index]
                )
                load_to_resources[load_value][sla_conf.RESOURCE].append(
                    sla_conf.VDS_HOSTS[host_index]
                )

        def fin():
            """
            1) Stop CPU load on hosts
            """
            u_libs.testflow.teardown(
                "Release hosts from CPU load: %s", load_to_resources.values()
            )
            sla_helpers.stop_load_on_resources(load_to_resources.values())
        request.addfinalizer(fin)

        u_libs.testflow.setup(
            "Create CPU load on the hosts: %s", load_to_resources
        )
        sla_helpers.start_and_wait_for_cpu_load_on_resources(load_to_resources)


@pytest.fixture(scope="class")
def create_affinity_groups(request):
    """
    1) Add affinity groups
    2) Populate affinity groups by VM's
    """
    affinity_groups = request.node.cls.affinity_groups

    def fin():
        """
        1) Remove affinity groups
        """
        for affinity_group_name in affinity_groups.iterkeys():
            u_libs.testflow.teardown(
                "Remove the affinity group %s", affinity_group_name
            )
            ll_clusters.remove_affinity_group(
                affinity_name=affinity_group_name,
                cluster_name=sla_conf.CLUSTER_NAME[0]
            )
    request.addfinalizer(fin)

    for (
        affinity_group_name, affinity_group_params
    ) in affinity_groups.iteritems():
        vms = affinity_group_params.pop("vms", None)
        u_libs.testflow.setup(
            "Create the affinity group %s", affinity_group_name
        )
        assert ll_clusters.create_affinity_group(
            cluster_name=sla_conf.CLUSTER_NAME[0],
            name=affinity_group_name,
            **affinity_group_params
        )
        if vms:
            u_libs.testflow.setup(
                "Populate the affinity group %s with VM's %s",
                affinity_group_name, vms
            )
            assert ll_clusters.populate_affinity_with_vms(
                affinity_name=affinity_group_name,
                cluster_name=sla_conf.CLUSTER_NAME[0],
                vms=vms
            )


@pytest.fixture(scope="class")
def wait_for_scheduling_memory_update():
    """
    Wait until engine update host scheduling memory
    """
    sleep(sla_conf.UPDATE_SCHEDULER_MEMORY_TIMEOUT)


@pytest.fixture(scope="class")
def create_affinity_labels(request):
    """
    1) Create affinity labels
    """
    affinity_labels = request.node.cls.affinity_labels

    def fin():
        """
        1) Remove affinity labels
        """
        for name in affinity_labels:
            u_libs.testflow.teardown("Delete the affinity label %s", name)
            ll_afflabels.AffinityLabels.delete(name=name)
    request.addfinalizer(fin)

    for name in affinity_labels:
        u_libs.testflow.setup("Create the affinity label %s", name)
        assert ll_afflabels.AffinityLabels.create(name=name)


@pytest.fixture(scope="class")
def assign_affinity_label_to_element(request):
    """
    1) Assign affinity label to elements(VM or host)
    """
    affinity_label_to_element = request.node.cls.affinity_label_to_element

    def fin():
        """
        1) Remove affinity labels from elements(VM or host)
        """
        for label_name, elm_type_d in affinity_label_to_element.iteritems():
            for elm_type, elements in elm_type_d.iteritems():
                for element in elements:
                    if elm_type == "hosts":
                        u_libs.testflow.teardown(
                            "Unassign the affinity label %s from the host %s",
                            label_name, sla_conf.HOSTS[element]
                        )
                        ll_afflabels.AffinityLabels.remove_label_from_host(
                            label_name=label_name,
                            host_name=sla_conf.HOSTS[element]
                        )
                    elif elm_type == "vms":
                        u_libs.testflow.teardown(
                            "Unassign the affinity label %s from the VM %s",
                            label_name, element
                        )
                        ll_afflabels.AffinityLabels.remove_label_from_vm(
                            label_name=label_name, vm_name=element
                        )
    request.addfinalizer(fin)

    for label_name, elm_type_d in affinity_label_to_element.iteritems():
        for elm_type, elements in elm_type_d.iteritems():
            for element in elements:
                if elm_type == "hosts":
                    u_libs.testflow.setup(
                        "Assign the affinity label %s to the host %s",
                        label_name, sla_conf.HOSTS[element]
                    )
                    assert ll_afflabels.AffinityLabels.add_label_to_host(
                        label_name=label_name,
                        host_name=sla_conf.HOSTS[element]
                    )
                elif elm_type == "vms":
                    u_libs.testflow.setup(
                        "Assign the affinity label %s to the VM %s",
                        label_name, element
                    )
                    assert ll_afflabels.AffinityLabels.add_label_to_vm(
                        label_name=label_name, vm_name=element
                    )
