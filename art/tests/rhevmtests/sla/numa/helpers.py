"""
Helpers for NUMA test
"""
import logging
import re

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
import config as conf
import rhevmtests.helpers as global_helpers

logger = logging.getLogger(__name__)


def install_numa_package(resource):
    """
    Install numactl package on the resource

    Args:
        resource (VDS): VDS resource

    Raises:
        HostException
    """
    if not resource.package_manager.install(conf.NUMACTL_PACKAGE):
        raise errors.HostException(
            "%s: Failed to install package %s" %
            (resource, conf.NUMACTL_PACKAGE)
        )


def reinstall_numa_package(resource):
    """
    Reinstall numactl package on the resource

    Args:
        resource (VDS): VDS resource

    Raises:
        HostException
    """
    # TODO: W/A for bug https://bugzilla.redhat.com/show_bug.cgi?id=1315184
    out = resource.run_command(command=[conf.NUMACTL, "-H"])[1]
    if not out:
        packager_methods = {
            conf.PACKAGE_MANAGER_INSTALL: resource.package_manager.install,
            conf.PACKAGE_MANAGER_REMOVE: resource.package_manager.remove
        }
        for method_name, packager_method in packager_methods.iteritems():
            if not packager_method(conf.NUMACTL_PACKAGE):
                raise errors.HostException(
                    "%s: Failed to %s package %s" %
                    (resource, method_name, conf.NUMACTL_PACKAGE)
                )


def get_numa_parameters_from_resource(resource):
    """
    Get NUMA parameters from the resource

    Args:
        resource (VDS): VDS resource

    Returns:
        dict: NUMA nodes parameters({node_index: {cpus, memory}})
    """
    reinstall_numa_package(resource=resource)
    param_dict = {}
    logger.info("Get NUMA information from the resource %s", resource)
    rc, out, _ = resource.run_command(command=[conf.NUMACTL, "-H"])
    if rc:
        logger.error("Failed to get numa information from resource")
        return param_dict
    pattern = re.compile(r"node\s(\d+)\s+(\w+):\s+([\d\s]+)\w*$", re.M)
    results = re.findall(pattern, out)
    for result in results:
        node = int(result[0])
        if node not in param_dict:
            param_dict[node] = {}
        if result[1] == conf.NUMA_NODE_CPUS:
            value = [int(v) for v in result[2].split()]
        else:
            value = int(result[2])
        param_dict[node][result[1]] = value
    logger.debug("%s: NUMA parameters: %s", resource, param_dict)
    return param_dict


def get_filtered_numa_parameters_from_resource(resource):
    """
    Get NUMA parameters for the nodes with memory greater than zero

    Args:
        resource (VDS): VDS resource

    Returns:
        dict: Filtered NUMA nodes parameters({node_index: {cpus, memory}})
    """
    h_numa_nodes_params = get_numa_parameters_from_resource(resource=resource)
    return dict(
        (k, v) for k, v in h_numa_nodes_params.iteritems()
        if v[conf.NUMA_NODE_MEMORY] != 0
    )


def get_numa_parameters_from_vm(vm_name):
    """
    Install numactl package on the VM and get VM NUMA parameters

    Args:
        vm_name (str): VM name

    Returns:
        dict: NUMA parameters({node_index: {cpus, memory}})
    """
    params_dict = {}
    vm_resource = global_helpers.get_vm_resource(vm=vm_name)
    if not vm_resource:
        return params_dict
    install_numa_package(resource=vm_resource)
    return get_numa_parameters_from_resource(resource=vm_resource)


def parse_pinning_values(values):
    """
    Return pinning values for lines that include "-" and ","

    Args:
        values (str): Values that include "-" and ","

    Returns:
        list: Pinning values
    """
    pinning_arr = []
    if "," in values:
        values = values.split(",")
        for value in values:
            pinning_arr.extend(parse_pinning_values(value))
    elif "-" in values:
        values = values.split("-")
        pinning_arr.extend(
            range(int(values[0]), int(values[1]) + 1)
        )
    else:
        pinning_arr.append(int(values))
    return pinning_arr


def get_vm_numa_pinning(resource, vm_name, pinning_type):
    """
    Get VM CPU and memory NUMA pinning information from the host

    Args:
        resource (VDS): VDS resource
        vm_name (str): VM name
        pinning_type (str): Pinning type(CPU or memory)

    Returns:
        dict: VM pinning information
    """
    pinning_dict = {}
    logger.info("Get vm %s pid from host %s", vm_name, resource.fqdn)
    vm_pid = resource.get_vm_process_pid(vm_name)
    if not vm_pid:
        logger.error("Failed to get vm %s pid", vm_name)
        return pinning_dict
    cmd = [
        "cat", "/proc/%s/task/*/status" % vm_pid, "|", "grep", pinning_type
    ]
    logger.info(
        "Get VM %s pinning information from the host %s", vm_name, resource
    )
    rc, out, _ = resource.run_command(command=cmd)
    if rc:
        return pinning_dict
    proc_pattern = re.compile(
        r"{0}:\s+([\d\-,]*)$".format(pinning_type), re.M
    )
    results = re.findall(proc_pattern, out)
    for proc_index, result in enumerate(results):
        pinning_dict[proc_index] = parse_pinning_values(result)
    logger.debug("VM %s pinning information: %s", vm_name, pinning_dict)
    return pinning_dict


def get_numa_mode_from_vm_process(resource, vm_name, numa_mode):
    """
    Get VM NUMA mode from the host

    Args:
        resource (VDS): VDS resource
        vm_name (str): VM name
        numa_mode (str): Expected NUMA mode of the VM

    Returns:
        bool: True, if the VM NUMA mode equal to the expected NUMA mode,
            otherwise False
    """
    logger.info("Get vm %s pid", vm_name)
    vm_pid = resource.get_vm_process_pid(vm_name)
    if not vm_pid:
        logger.error("Failed to get vm %s pid", vm_name)
        return False
    cmd = ["grep", numa_mode, "/proc/%s/numa_maps" % vm_pid]
    rc, out, _ = resource.run_command(command=cmd)
    return bool(not rc and out)


def create_number_of_equals_numa_nodes(resource, vm_name, num_of_numa_nodes):
    """
    Create the number of equals NUMA nodes for the future use

    Args:
        resource (VDS): VDS resource
        vm_name (str): VM name
        num_of_numa_nodes (int): Number of NUMA nodes to create

    Returns:
        list: NUMA nodes definitions
    """
    numa_nodes = []
    h_numa_nodes_indexes = get_filtered_numa_parameters_from_resource(
        resource=resource
    ).keys()
    v_numa_node_memory = ll_vms.get_vm_memory(
        vm_name
    ) / num_of_numa_nodes / conf.MB
    v_numa_node_cores = (
        ll_vms.get_vm_cores(vm_name=vm_name) *
        ll_vms.get_vm_sockets(vm_name=vm_name) /
        num_of_numa_nodes
    )
    for index in range(num_of_numa_nodes):
        cores = range(
            index * v_numa_node_cores, (index + 1) * v_numa_node_cores
        )
        numa_node = {
            "index": index,
            "memory": v_numa_node_memory,
            "cores": cores,
            "pin_list": [h_numa_nodes_indexes[index]]
        }
        numa_nodes.append(numa_node)
    return numa_nodes


def is_numa_cpu_pinning_correct(
    h_numa_nodes_params, vm_pinning, num_of_vm_numa_nodes
):
    """
    Check if NUMA CPU pinning of the VM is correct

    Args:
        h_numa_nodes_params (dict): Host NUMA parameters
        vm_pinning (dict): VM NUMA pinning parameters
        num_of_vm_numa_nodes (int): Number of VM NUMA nodes

    Returns:
        bool: True, if VM NUMA CPU pinning is correct, otherwise False
    """
    for pinning in h_numa_nodes_params.values()[:num_of_vm_numa_nodes]:
        with_pinning = sum(
            x == pinning[conf.NUMA_NODE_CPUS] for x in vm_pinning.values()
        )
        if with_pinning != conf.CORES_MULTIPLIER:
            return False
    return True


def is_numa_memory_pining_correct_under_strict_mode(
    h_numa_nodes_params, vm_pinning, num_of_vm_numa_nodes
):
    """
    Check if NUMA memory pinning of the VM correct under strict mode

    Args:
        h_numa_nodes_params (dict): Host NUMA parameters
        vm_pinning (dict): VM NUMA pinning parameters
        num_of_vm_numa_nodes (int): Number of VM NUMA nodes

    Returns:
        bool: True, if VM NUMA memory pinning is correct, otherwise False
    """
    for pinning in h_numa_nodes_params.keys()[:num_of_vm_numa_nodes]:
        with_pinning = sum(
            x == [pinning] for x in vm_pinning.values()
        )
        if with_pinning != conf.CORES_MULTIPLIER:
            return False
    return True


def is_numa_memory_pining_correct(h_numa_nodes_params, vm_pinning):
    """
    Check if NUMA memory pinning of the VM correct
    under preferred and interleave mode

    Args:
        h_numa_nodes_params (dict): Host NUMA parameters
        vm_pinning (dict): VM NUMA pinning parameters

    Returns:
        bool: True, if VM NUMA memory pinning is correct, otherwise False
    """
    for pinning in vm_pinning.values():
        if pinning != h_numa_nodes_params.keys():
            return False
    return True


def is_numa_pinning_correct(pinning_type, numa_mode, num_of_vm_numa_nodes):
    """
    Check if VM NUMA CPU or memory pinning is correct

    Args:
        pinning_type (str): Pinning type(CPU_PINNING_TYPE, MEMORY_PINNING_TYPE)
        numa_mode (str): VM NUMA mode
        num_of_vm_numa_nodes (int): Number of VM NUMA nodes

    Returns:
        bool: True, if VM NUMA pinning is correct, otherwise False
    """
    h_numa_nodes_params = get_filtered_numa_parameters_from_resource(
        resource=conf.VDS_HOSTS[0]
    )
    vm_pinning = get_vm_numa_pinning(
        resource=conf.VDS_HOSTS[0],
        vm_name=conf.VM_NAME[0],
        pinning_type=pinning_type
    )
    if pinning_type == conf.CPU_PINNING_TYPE:
        return is_numa_cpu_pinning_correct(
            h_numa_nodes_params=h_numa_nodes_params,
            vm_pinning=vm_pinning,
            num_of_vm_numa_nodes=num_of_vm_numa_nodes
        )
    elif pinning_type == conf.MEMORY_PINNING_TYPE:
        if numa_mode == conf.STRICT_MODE:
            return is_numa_memory_pining_correct_under_strict_mode(
                h_numa_nodes_params=h_numa_nodes_params,
                vm_pinning=vm_pinning,
                num_of_vm_numa_nodes=num_of_vm_numa_nodes
            )
        else:
            return is_numa_memory_pining_correct(
                h_numa_nodes_params=h_numa_nodes_params,
                vm_pinning=vm_pinning
            )
    return False


def is_vm_has_correct_number_of_numa_nodes(expected_number_of_vm_numa_nodes):
    """
    Check if VM has correct number of NUMA nodes

    Args:
        expected_number_of_vm_numa_nodes (int): Expected number of the
            VM NUMA nodes

    Returns:
        bool: True, if expected number of NUMA nodes equal to real one,
            otherwise False
    """
    vm_numa_params = get_numa_parameters_from_vm(
        vm_name=conf.VM_NAME[0]
    )
    logger.info(
        "Check if VM %s has %d numa nodes",
        conf.VM_NAME[0], expected_number_of_vm_numa_nodes
    )
    return len(vm_numa_params.keys()) == expected_number_of_vm_numa_nodes


def is_vm_numa_nodes_have_correct_values(
    value_type, expected_numa_params
):
    """
    Check VM NUMA nodes parameters on guest OS

    Args:
        value_type (str): Value type(CPU, memory)
        expected_numa_params (list): Expected values

    Returns:
        bool: True, if expected values equal to real one, otherwise False
    """
    vm_numa_params = get_numa_parameters_from_vm(
        vm_name=conf.VM_NAME[0]
    )
    for vm_numa_index, vm_numa_param in vm_numa_params.iteritems():
        exp_value = expected_numa_params[
            vm_numa_index
        ][conf.VM_NUMA_PARAMS[value_type]]
        vm_value = vm_numa_param[value_type]
        logger.info(
            "Check if %s on the VM NUMA node %s is approximately equal to %s",
            conf.VM_NUMA_PARAMS[value_type], vm_numa_index, exp_value
        )
        if value_type == conf.NUMA_NODE_MEMORY:
            if (
                vm_value < exp_value - conf.MEMORY_ERROR or
                vm_value > exp_value + conf.MEMORY_ERROR
            ):
                return False
        else:
            if exp_value != vm_value:
                return False
    return True


def get_pci_devices_numa_node_from_resource(resource):
    """
    Get mapping between PCI devices and NUMA nodes

    Args:
        resource (VDS): Host resource

    Returns:
        dict: Mapping between PCI devices and NUMA nodes
    """
    out = resource.run_command(
        ["tail", "-n", "1", "/sys/bus/pci/devices/*/numa_node"]
    )[1]
    pci_devices = {}
    pci_device_name = ""
    for line in out.splitlines():
        if line:
            if "pci" in line:
                pci_device_name = line.split("/")[-2]
                pci_device_name = pci_device_name.replace(
                    ":", "_"
                ).replace(".", "_")
                pci_device_name = "pci_{0}".format(pci_device_name)
            elif pci_device_name:
                pci_devices[pci_device_name] = int(line)
    return pci_devices
