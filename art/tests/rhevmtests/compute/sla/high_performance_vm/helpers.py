"""
High Performance VM helpers method
"""
import re

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.compute.sla.helpers as sla_helpers
import rhevmtests.compute.sla.high_performance_vm.config as conf
from art.unittest_lib import testflow

logger = conf.logging.getLogger(__name__)


def get_io_and_emulator_cpu_pinning(vm_name):
    """
    Get IO and emulator threads CPU pinning

    Args:
        vm_name(str): VM name

    Returns:
        dict: mapping between IO or emulator threads files to list with
            CPU pinning
    """
    vm_host = ll_vms.get_vm_host(vm_name=vm_name)
    host_resource = conf.VDS_HOSTS[conf.HOSTS.index(vm_host)]
    vm_pid = host_resource.get_vm_process_pid(vm_name=vm_name)

    # Get emulator and IO threads status files
    threads_status_files = {}
    for thread_name in (conf.THREAD_QEMU, conf.THREAD_IO):
        command = [
            "grep", "-H", thread_name, "/proc/{0}/task/*/status".format(vm_pid)
        ]
        rc, out, _ = host_resource.run_command(command=command)
        if rc:
            return False
        threads_status_files[thread_name] = re.findall(
            r"/proc/\d+/task/\d+/status", out
        )

    # Get CPU pinning for emulator and IO threads
    threads_pinning = {}
    for thread_name, threads_files in threads_status_files.iteritems():
        for thread_file in threads_files:
            command = ["grep", "Cpus_allowed_list:", thread_file]
            rc, out, _ = host_resource.run_command(command=command)
            pinning = out.split(":")[-1].strip()
            threads_pinning[thread_file] = sla_helpers.parse_pinning_values(
                values=pinning
            )
    logger.debug("IO and emulator threads pinning: %s", threads_pinning)
    return threads_pinning


def verify_io_and_emulator_cpu_pinning(
    vm_name, numa_node=None, host_resource=None
):
    """
    Verify IO and emulator threads CPU pinning

    Args:
        vm_name (str): VM name
        numa_node (NumaNode): If specified, will check auto-pinning to two
            first CPU's of NUMA node
        host_resource (VDS): If specified, will check auto-pinning to all CPU's
            of host

    Returns:
        bool: True, if pinning is correct, otherwise False
    """
    threads_pinning = get_io_and_emulator_cpu_pinning(vm_name=vm_name)

    expected_cpus = []
    # In case of pinning to all host CPU's(the same as no pinning)
    if host_resource:
        expected_cpus = ll_sla.get_list_of_online_cpus_on_resource(
            resource=host_resource
        )
        expected_cpus.sort()
    # In case of pinning to first two CPU's of the specific NUMA node
    elif numa_node:
        expected_cpus = ll_hosts.get_numa_node_cpus(numa_node_obj=numa_node)
        expected_cpus.sort()
        expected_cpus = expected_cpus[:2]

    testflow.step(
        "Verify that IO and emulator threads pinned to CPU's %s", expected_cpus
    )
    for thread_pinning in threads_pinning.itervalues():
        thread_pinning.sort()
        if thread_pinning != expected_cpus:
            return False
    return True
