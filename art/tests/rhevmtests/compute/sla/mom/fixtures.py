"""
MOM Test Fixtures
"""
import logging

import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import helpers
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
            memory_guaranteed=vm_memory,
            max_memory=vm_memory + conf.GB
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
    1) Change MOM pressure threshold to 0.60 on resources
    2) Restart VDSM on the host
    3) Copy memory allocation script on the host
    4) Enable ballooning for the host
    """
    def fin():
        """
        1) Disable ballooning for the host
        2) Update balloon policy to the old value
        3) Restart VDSM on the host
        4) Delete memory allocation script from the host
        """
        results = []
        u_libs.testflow.teardown(
            "Disable ballooning for the host %s", conf.HOSTS[0]
        )
        results.append(helpers.enable_host_ballooning())
        u_libs.testflow.teardown(
            "Change ballooning pressure threshold to %s",
            conf.DEFVAR_PRESSURE_THRESHOLD_020
        )
        results.append(
            helpers.change_mom_pressure_percentage(
                resource=conf.VDS_HOSTS[0],
                pressure_threshold=conf.DEFVAR_PRESSURE_THRESHOLD_020
            )
        )
        if conf.VDS_HOSTS[0].fs.exists(path=conf.HOST_ALLOC_PATH):
            u_libs.testflow.teardown(
                "Remove memory allocation script from the host %s",
                conf.HOSTS[0]
            )
            results.append(
                conf.VDS_HOSTS[0].fs.remove(path=conf.HOST_ALLOC_PATH)
            )
        assert all(results)
    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Change ballooning pressure threshold to %s",
        conf.DEFVAR_PRESSURE_THRESHOLD_040
    )
    assert helpers.change_mom_pressure_percentage(
        resource=conf.VDS_HOSTS[0],
        pressure_threshold=conf.DEFVAR_PRESSURE_THRESHOLD_040
    )
    u_libs.testflow.setup(
        "Copy memory allocation script to the host %s directory %s",
        conf.HOSTS[0], conf.HOST_ALLOC_PATH
    )
    conf.SLAVE_HOST.fs.transfer(
        path_src=find_test_file(conf.ALLOC_SCRIPT_LOCAL),
        target_host=conf.VDS_HOSTS[0],
        path_dst=conf.HOST_ALLOC_PATH
    )
    u_libs.testflow.setup("Enable ballooning for the host %s", conf.HOSTS[0])
    assert helpers.enable_host_ballooning()
