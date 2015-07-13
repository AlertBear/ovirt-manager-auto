"""
Helper for multiple_queues_nics
"""
import logging
import re

logger = logging.getLogger("Multiple_Queues_Nics_Helper")


def check_queues_from_qemu(vm, host_obj, num_queues):
    """
    Get numbers of queues from qemu process by VM name

    :param vm: VM name
    :type vm: str
    :param host_obj: resource.VDS host object
    :type host_obj: object
    :param num_queues: Number of queues to check
    :type num_queues: int
    :return: True/False
    :rtype: bool
    """
    cmd = ["pgrep", "-a", "qemu-kvm"]
    host_exec = host_obj.executor()
    rc, out, error = host_exec.run_cmd(cmd)
    if rc:
        logger.error("Failed to run %s. ERR: %s", cmd, error)
        return False

    running_vms = re.findall(r'\d+ .*qemu-kvm.*', out)
    for run_vm in running_vms:
        if re.findall(r'-name %s' % vm, run_vm):
            qemu_queues = re.findall(r'fds=[\d\d:]+', out)
            if not qemu_queues:
                if num_queues == 0:
                    return True

                logger.error("Queues not found in qemu")
                return False

            for queue in qemu_queues:
                striped_queue = queue.strip("fds=")
                queues_found = len(striped_queue.split(":"))
                if num_queues != queues_found:
                    logger.error(
                        "%s queues found in qemu, didn't match the expected "
                        "%s queues", queues_found, num_queues
                    )
                    return False
            return True
    logger.error("%s not found on host", vm)
    return False
