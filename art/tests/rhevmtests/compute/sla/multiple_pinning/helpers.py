"""
Multiple pinning helper
"""
import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.unittest_lib as u_libs
import config as conf


def get_the_same_cpus_from_resources():
    """
    Get intersection of online CPU's on all resources

    Returns:
        int: Index of CPU that exist on all resources
    """
    cpu_list = ll_sla.get_list_of_online_cpus_on_resource(
        resource=conf.VDS_HOSTS[0]
    )
    for resource in conf.VDS_HOSTS[:2]:
        cpu_list = set(cpu_list).intersection(
            ll_sla.get_list_of_online_cpus_on_resource(resource=resource)
        )
    if not cpu_list:
        pytest.skip(
            "Hosts %s do not have the same online CPU" % conf.VDS_HOSTS[:2]
        )
    return cpu_list.pop()


def change_host_cluster(cluster_name):
    """
    1) Deactivate the host
    2) Change the host cluster
    3) Activate the host

    Args:
        cluster_name (str): Cluster name

    Returns:
        bool: True, if all actions succeed, otherwise False
    """
    if not ll_hosts.deactivate_host(
        positive=True, host=conf.HOSTS[0], host_resource=conf.VDS_HOSTS[0]
    ):
        return False

    u_libs.testflow.setup(
        "Change the host %s cluster to %s", conf.HOSTS[0], cluster_name
    )
    if not ll_hosts.update_host(
        positive=True, host=conf.HOSTS[0], cluster=cluster_name
    ):
        return False

    if not ll_hosts.activate_host(
        positive=True, host=conf.HOSTS[0], host_resource=conf.VDS_HOSTS[0]
    ):
        return False
    return True
