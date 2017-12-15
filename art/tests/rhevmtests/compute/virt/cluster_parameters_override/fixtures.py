#! /usr/bin/python
# -*- coding: utf-8 -*-

import pytest

import config
import rhevmtests.compute.virt.helper as virt_helper
from rhevm_api.utils.test_utils import wait_for_tasks
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    clusters as ll_clusters,
    hosts as ll_hosts,
)
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def set_cpu_model_param(request):
    """
    Set the following cluster cpu parameters:
    cluster_name, cluster_cpu_model, max_host_cpu, min_host_cpu,
    higher_cpu_model, lower_cpu_model,highest_common_cpu_model
    """
    config.CLUSTER_CPU_PARAMS[config.CLUSTER_CPU_NAME] = config.CLUSTER_NAME[0]

    cluster_object = ll_clusters.get_cluster_object(
        config.CLUSTER_CPU_PARAMS[config.CLUSTER_CPU_NAME]
    )
    cluster_hosts_dict = virt_helper.get_cluster_hosts_resources(
        config.CLUSTER_CPU_PARAMS[config.CLUSTER_CPU_NAME]
    )
    cluster_hosts_resources = [h for h in cluster_hosts_dict.itervalues()]

    testflow.setup("Get cluster cpu model")
    config.CLUSTER_CPU_PARAMS[config.CLUSTER_CPU_MODEL] = (
        cluster_object.get_cpu().get_type()
    )

    testflow.setup("Get the max host cpu model of all hosts in the cluster")
    config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU] = (
        config.CPU_MODEL_DENOM.get_maximal_cpu_model(cluster_hosts_resources)
    )

    testflow.setup("Get the min host cpu model of all hosts in the cluster")
    config.CLUSTER_CPU_PARAMS[config.MIN_HOST_CPU] = (
        config.CPU_MODEL_DENOM.get_minimal_cpu_model(cluster_hosts_resources)
    )

    testflow.setup(
        "Get a cpu model which is higher than the max host cpu model in the "
        "cluster"
    )
    config.CLUSTER_CPU_PARAMS[config.HIGER_CPU_MODEL] = (
        config.CPU_MODEL_DENOM.get_relative_cpu_model(
            config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu']
        )
    )

    testflow.setup(
        "Get a cpu model which is lower than the min host cpu model in the "
        "cluster"
    )
    config.CLUSTER_CPU_PARAMS[config.LOWER_CPU_MODEL] = (
        config.CPU_MODEL_DENOM.get_relative_cpu_model(
            cpu_name=config.CLUSTER_CPU_PARAMS[config.CLUSTER_CPU_MODEL],
            higher=False
        )
    )
    testflow.setup("Set the highest commom cpu model")
    config.CLUSTER_CPU_PARAMS[config.HIGHEST_COMMON_CPU_MODEL] = (
        virt_helper.highest_common_cpu_model_host_pair_from_cluster(
            config.CLUSTER_CPU_PARAMS[config.CLUSTER_CPU_NAME]
        )
    )


@pytest.fixture(scope="class")
def check_if_higher_cpu_model_tests_should_run(request):
    """
    Set tests to skip in case the cluster's max host cpu model is the
    highest for it's vendor

    tests:
    1.test_negative_start_vm_with_unsupported_cpu_type
    2.test_edit_vm_update_cpu_type_higher_than_cluster
    """
    testflow.setup(
        "Set tests to skip in case the cluster's max host cpu model is the "
        "highest for it's vendor"
    )
    if not config.CLUSTER_CPU_PARAMS[config.HIGER_CPU_MODEL]:
        pytest.skip("Skipping test, All cpu models are supported")


@pytest.fixture(scope="class")
def check_if_no_high_cpu_host_tests_should_run(request):
    """
    Check if there is a host with cpu model > minimal and skips relevant
    tests if not. Set a flag for new cluster creation if needed

    tests:
    1.test_vm_with_cpu_different_from_cluster
    2.test_run_once_with_cpu_different_from_cluster
    3.test_vmpool_with_cpu__different_from_cluster
    4.test_negative_migrate_vm_with_1_host_supporting_cpu_model
    5.test_migrate_vm_with_custom_cpu_values_2_hosts_supporting
    6.test_edit_vm_update_cpu_type_lower_than_cluster
    7.test_run_once_with_cpu_type_lower_than_cluster
    8.test_vm_with_cpu_type_lower_than_cluster
    """

    cluster_lower = request.cls.cluster_lower
    testflow.setup(
        "Check if there is a host with cpu model > minimal and skips relevant"
        "tests if not. Set a flag for new cluster creation if needed"
    )
    if (
            config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu'] ==
            config.CLUSTER_CPU_PARAMS[config.CLUSTER_CPU_MODEL]
    ):
        if not config.CLUSTER_CPU_PARAMS[config.LOWER_CPU_MODEL]:
            pytest.skip(
                "Skipping test, All hosts have the"
                " minimum cpu model for the vendor"
            )
        else:

            if cluster_lower:
                config.CLUSTER_UPDATED_CPU = (
                    config.CLUSTER_CPU_PARAMS[config.LOWER_CPU_MODEL]['cpu']
                )
    elif (
            (not config.CLUSTER_CPU_PARAMS[config.LOWER_CPU_MODEL]) and
            (not cluster_lower)
    ):
        config.CLUSTER_UPDATED_CPU = (
            config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu']
        )


@pytest.fixture(scope="class")
def check_if_no_several_hosts_with_high_cpu_tests_should_run(request):
    """
    Set tests to skip in case there's no more than 1 host with max host
    cpu model

    tests:
    1.test_migrate_vm_with_custom_cpu_values_2_hosts_supporting
    """

    testflow.setup(
        "Set tests to skip in case there's no two hosts with model"
        " higher than minimal "
    )
    if not config.CPU_MODEL_DENOM.get_relative_cpu_model(
        cpu_name=(
            config.CLUSTER_CPU_PARAMS[config.HIGHEST_COMMON_CPU_MODEL]['cpu']
        ),
        higher=False
    ):
        pytest.skip(
            "Skipping test, need more than one host with same"
            " cpu model higher than cluster"
        )


@pytest.fixture(scope="class")
def check_if_no_different_hosts_tests_should_run(request):
    """
    Set tests to skip in case that all hosts in the cluster have the
    same cpu type

    tests:
    1.test_pin_vm_with_custom_cpu_to_host
    """

    testflow.setup(
        "Set tests to skip in case that all hosts in the cluster have the same"
        " cpu type but not necessarily the same as the cluster"
    )
    if (
            config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu'] ==
            config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu']
    ):
        pytest.skip(
            "Skipping test, need at least 2 hosts in the cluster "
            "with different cpu model"
        )


@pytest.fixture()
def revert_ge_vm_to_default_values(request):
    """
    Sets 1st GE vm back to default values and stops it if needed
    after test case.
    """
    def fin():
        """
        Sets 1st GE vm back to default values and stops it if needed after
        test case.
        """
        result = list()
        testflow.teardown("Stopping VM: %s", config.VM_NAME[0])
        result.append(ll_vms.stop_vms_safely([config.VM_NAME[0]]))
        testflow.teardown(
            "set VM %s custom cpu model value to None", config.VM_NAME[0]
        )
        result.append(
            ll_vms.updateVm(
                True,
                config.VM_NAME[0],
                custom_cpu_model='',
                placement_affinity=config.VM_MIGRATABLE,
                placement_host=config.VM_ANY_HOST,
                cpu_socket=1,
                memory=config.GB,
                max_memory=4 * config.GB,
                ballooning=True
            )
        )
        if len(ll_vms.get_vm_nics_obj(config.VM_NAME[0])) == 2:
            result.append(
                ll_vms.removeNic(
                    True, config.VM_NAME[0], config.NIC_NAME[1]
                )
            )
        if len(ll_vms.get_disk_attachments(config.VM_NAME[0])) == 2:
            result.append(
                ll_vms.removeDisk(
                    positive=True,
                    vm=config.VM_NAME[0],
                    disk=config.ADDITIONAL_DISK
                )
            )
        assert all(result)
    request.addfinalizer(fin)


@pytest.fixture()
def deactivate_redundant_hosts(request):
    """
    Checks if there are more than 1 hosts in the cluster with max available cpu
    model and deactivates all but one if there is.
    """
    host_with_cpu_model = virt_helper.get_hosts_by_cpu_model(
        cpu_model_name=config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu'],
        cluster=config.CLUSTER_CPU_PARAMS[config.CLUSTER_CPU_NAME]
    )

    def fin():
        """
        Bring deactivated hosts back up
        """
        if len(host_with_cpu_model) > 1:
            for host in host_with_cpu_model[1:]:
                testflow.setup("Activate host: %s", host)
                assert ll_hosts.activate_host(True, host)
    request.addfinalizer(fin)
    testflow.setup(
        "Check if there are more than 1 hosts with cpu model: %s in cluster: "
        "%s", config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu'],
        config.CLUSTER_CPU_PARAMS[config.CLUSTER_CPU_NAME]
    )
    if len(host_with_cpu_model) > 1:
        for host in host_with_cpu_model[1:]:
            testflow.setup("Deactivate host: %s", host)
            assert ll_hosts.deactivate_host(True, host)
    wait_for_tasks(
        engine=config.ENGINE,
        datacenter=config.DC_NAME[0],
        timeout=600
    )
