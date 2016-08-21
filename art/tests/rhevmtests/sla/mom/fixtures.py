"""
MOM Test Fixtures
"""
import logging

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import helpers
import pytest
from art.test_handler import find_test_file

logger = logging.getLogger(__name__)


@pytest.fixture(scope="class")
def update_vms_for_ksm_test():
    """
    1) Update VM's for KSM tests
    """
    host_mem = ll_hosts.get_host_free_memory(conf.HOSTS[0])
    for vm_name in conf.MOM_VMS:
        vm_memory = int(
            round(host_mem * 2 / conf.NUMBER_OF_VMS / conf.GB) * conf.GB
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=vm_name,
            placement_host=conf.HOSTS[0],
            placement_affinity=conf.VM_USER_MIGRATABLE,
            memory=vm_memory,
            memory_guaranteed=vm_memory
        )


@pytest.fixture(scope="class")
def update_cluster_for_ksm_test():
    """
    1) Update cluster for KSM test
    """
    assert ll_clusters.updateCluster(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        ksm_enabled=True,
        ballooning_enabled=False,
        mem_ovrcmt_prc=conf.CLUSTER_OVERCOMMITMENT_DESKTOP
    )


@pytest.fixture(scope="class")
def stop_memory_allocation(request):
    """
    1) Stop memory allocation on the host
    """
    def fin():
        memory_allocation_pid = conf.VDS_HOSTS[0].run_command(
            command=["pgrep", "-f", conf.HOST_ALLOC_PATH]
        )[1].strip()
        if memory_allocation_pid:
            conf.VDS_HOSTS[0].run_command(
                command=["kill", "-9", memory_allocation_pid]
            )
    request.addfinalizer(fin)


@pytest.fixture(scope="module")
def prepare_env_for_ballooning_test(request):
    """
    1) Update cluster parameters
    2) Change MOM pressure threshold to 0.40 on resources
    3) Restart VDSM on the host
    4) Copy memory allocation script on the host
    """
    def fin():
        """
        1) Update balloon policy to the old value
        2) Restart VDSM on the host
        3) Delete memory allocation script from the host
        """
        helpers.change_mom_pressure_percentage(
            resource=conf.VDS_HOSTS[0],
            pressure_threshold=conf.DEFVAR_PRESSURE_THRESHOLD_020
        )
        hl_hosts.restart_vdsm_and_wait_for_activation(
            hosts_resource=[conf.VDS_HOSTS[0]],
            dc_name=conf.DC_NAME[0],
            storage_domain_name=conf.STORAGE_NAME[0]
        )
        if conf.VDS_HOSTS[0].fs.exists(path=conf.HOST_ALLOC_PATH):
            logger.info(
                "Remove memory allocation script from the host %s",
                conf.HOSTS[0]
            )
            conf.VDS_HOSTS[0].fs.remove(path=conf.HOST_ALLOC_PATH)
    request.addfinalizer(fin)

    assert ll_clusters.updateCluster(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        ksm_enabled=False,
        ballooning_enabled=True,
        mem_ovrcmt_prc=conf.CLUSTER_OVERCOMMITMENT_DESKTOP
    )
    assert helpers.change_mom_pressure_percentage(
        resource=conf.VDS_HOSTS[0],
        pressure_threshold=conf.DEFVAR_PRESSURE_THRESHOLD_040
    )
    assert hl_hosts.restart_vdsm_and_wait_for_activation(
        hosts_resource=[conf.VDS_HOSTS[0]],
        dc_name=conf.DC_NAME[0],
        storage_domain_name=conf.STORAGE_NAME[0]
    )
    logger.info(
        "Copy memory allocation script to the host %s directory %s",
        conf.HOSTS[0], conf.HOST_ALLOC_PATH
    )
    conf.VDS_HOSTS[0].copy_to(
        resource=conf.ENGINE_HOST,
        src=find_test_file(conf.ALLOC_SCRIPT_LOCAL),
        dst=conf.HOST_ALLOC_PATH
    )
