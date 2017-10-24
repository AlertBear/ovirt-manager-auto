"""
Helpers file for sla sanity test
"""
import logging
import re

import art.test_handler.exceptions as errors
import rhevmtests.compute.sla.config as conf

logger = logging.getLogger(__name__)


def adapt_vcpu_pinning_to_cli(vcpu_pinning):
    """
    Adapt the VCPU pinning format to the CLI

    Args:
        vcpu_pinning (list): VCPU pinning list

    Returns:
        list: Adapted to the CLI VCPU pinning
    """
    if conf.ART_CONFIG['RUN']["engine"] == "cli":
        cli_vcpu_pinning = []
        for pinning in vcpu_pinning:
            for key, value in pinning.iteritems():
                cli_value = value.replace(",", "\,")
                pinning[key] = cli_value
            cli_vcpu_pinning.append(pinning)
        return cli_vcpu_pinning
    return vcpu_pinning


def get_vcpu_pinning_info_from_host(host_resource, vm_name, vcpu):
    """
    Get the VM VCPU pinning info from the host

    Args:
        host_resource (VDS): Host resource
        vm_name (str): VM name
        vcpu (int): VCPU index

    Returns:
        tuple: Host CPU index, pinning affinity

    Raises:
        HostException
    """
    rc, out, err = host_resource.executor().run_cmd(
        ["virsh", "-r", "list", "|grep", vm_name]
    )
    if rc:
        raise errors.HostException(
            "Can't read 'virsh -r list' on %s, err: %s" % (host_resource, err)
        )
    vm_id = out.split()[0]
    logger.info("VM pid is %s", vm_id)
    rc, out, err = host_resource.executor().run_cmd(
        ["virsh", "-r", "vcpuinfo", vm_id]
    )
    if rc:
        raise errors.HostException(
            "Can't read 'virsh -r vcpuinfo %s' on %s" % (vm_id, host_resource)
        )
    regex = r"VCPU:\s+%s\s+CPU:\s+(\d+)" % str(vcpu)
    running = re.search(regex, out).group(1)
    regex = r"VCPU:\s+%s[\w\W]+?CPU Affinity:\s+([-y]+)" % str(vcpu)
    affinity = re.search(regex, out).group(1)
    logger.info(
        "VCPU %s of VM %s pinned to physical CPU %s, and has affinity %s",
        vcpu, vm_name, running, affinity
    )
    return running, affinity


def get_vm_qemu_argument_from_host(host_resource, vm_name, qemu_arg_name):
    """
    Get the VM QEMU argument value from the host

    Args:
        host_resource (VDS): Host resource
        vm_name (str): VM name
        qemu_arg_name (str): QEMU argument name

    Returns:
        str: QEMU argument value

    Raises:
        HostException
    """
    rc, out, err = host_resource.executor().run_cmd(
        ["ps", "-F", "-C", "qemu-kvm", "|grep", vm_name]
    )
    if rc:
        raise errors.HostException(
            "Can't read 'ps' on %s, err: %s" % (host_resource, err)
        )
    regex = r"[\w\W]+ -%s ([\w]+) [\w\W]+" % qemu_arg_name
    res = re.search(regex, out).group(1)
    return res
