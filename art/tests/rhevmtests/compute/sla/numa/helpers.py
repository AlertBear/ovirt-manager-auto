"""
Helpers for NUMA test
"""
import logging
import re

import config as conf
import rhevmtests.helpers as global_helpers
import rhevmtests.compute.sla.helpers as sla_helpers

logger = logging.getLogger(__name__)


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
    sla_helpers.install_numa_package(resource=vm_resource)
    return sla_helpers.get_numa_parameters_from_resource(resource=vm_resource)


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
    h_numa_nodes_params = sla_helpers.filter_nodes_without_memory(
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
