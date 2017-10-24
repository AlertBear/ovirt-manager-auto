"""
Helpers file for the watchdog test
"""
import logging

import art.rhevm_api.tests_lib.low_level.general as ll_general
import config as conf
import rhevmtests.helpers as helpers

logger = logging.getLogger(__name__)


@ll_general.generate_logs()
def kill_watchdog_on_vm(vm_name):
    """
    Kill the watchdog process on the VM

    Args:
        vm_name (str): VM name

    Returns:
        bool: True, if kill watchdog process action succeeds, otherwise False
    """
    vm_resource = helpers.get_vm_resource(vm=vm_name)
    cmd = ["pkill", "-9", "watchdog"]
    if vm_resource.run_command(command=cmd)[0]:
        return False
    return True


@ll_general.generate_logs()
def detect_watchdog_on_vm(positive, vm_name):
    """
    Detect watchdog device 6300esb on the VM

    Args:
        positive (bool): Positive or negative behaviour
        vm_name (str): VM name

    Returns:
        bool: True, if the VM has watchdog device and positive=True or
            if the VM does not have watchdog device and positive=False,
            otherwise False
    """
    vm_resource = helpers.get_vm_resource(vm=vm_name, start_vm=False)
    get_dev_package = (
        conf.LSHW_PACKAGE if conf.PPC_ARCH else conf.LSPCI_PACKAGE
    )
    if conf.PPC_ARCH:
        if not vm_resource.package_manager.install(get_dev_package):
            return False

    cmd = [get_dev_package, "|", "grep", "-i", conf.WATCHDOG_MODEL[1:]]
    status = vm_resource.run_command(command=cmd)[0]
    return bool(status) != positive


def install_watchdog_on_vm(vm_name):
    """
    Install and enable watchdog service

    Args:
        vm_name (str): VM name

    Returns:
        bool: True, if enable and start of watchdog service succeed,
            otherwise False
    """
    vm_resource = helpers.get_vm_resource(vm=vm_name, start_vm=False)

    if not vm_resource.package_manager.install(conf.WATCHDOG_PACKAGE):
        return False

    logger.info(
        "%s: update watchdog configuration file %s",
        vm_resource, conf.WATCHDOG_CONFIG_FILE
    )
    cmd = [
        "sed",
        "-i",
        "s/#watchdog-device/watchdog-device/",
        conf.WATCHDOG_CONFIG_FILE
    ]
    if vm_resource.run_command(command=cmd)[0]:
        return False

    watchdog_service = vm_resource.service("watchdog")
    if not watchdog_service.is_enabled():
        logger.info("%s: enable watchdog service", vm_resource)
        if not watchdog_service.enable():
            logger.error(
                "%s: failed to enable watchdog service", vm_resource
            )
            return False

    logger.info("%s: restart watchdog service", vm_resource)
    if not watchdog_service.restart():
        logger.error("%s: failed to restart watchdog service")
        return False

    return True
