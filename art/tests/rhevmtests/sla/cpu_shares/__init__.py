"""
CPU SHARE test
"""
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
from rhevmtests.sla import config
logger = config.logging.getLogger(__name__)


def setup_package():
    """
    Update 4 vms to a specific core on a specific host
    """
    for vm_name in config.VM_NAME[:4]:
        logger.info("Update VM %s cpu pinning", vm_name)
        if not ll_vms.updateVm(
            True, vm_name,
            placement_affinity=config.VM_PINNED,
            placement_host=config.HOSTS[0],
            vcpu_pinning=([{"0": "0"}])
        ):
            raise errors.VMException(
                "Failed to update VM %s cpu pinning" % vm_name
            )


def teardown_package():
    """
    Remove cpu pinning and cpu shares from vms
    """
    for vm_name in config.VM_NAME[:4]:
        logger.info("Remove CPU pinning from VM %s" % vm_name)
        if not ll_vms.updateVm(
            True, vm_name,
            placement_affinity=config.VM_MIGRATABLE,
            placement_host=config.VM_ANY_HOST,
            vcpu_pinning=[],
            cpu_shares=0,
        ):
            logger.error(
                "Failed to remove host pinning from VM %s", vm_name
            )
