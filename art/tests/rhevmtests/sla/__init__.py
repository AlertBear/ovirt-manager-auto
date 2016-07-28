"""
Init for sla tests package
"""
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.utils.inventory import Inventory
from rhevmtests.sla import config
from rhevmtests import networking
import logging

logger = logging.getLogger(__name__)


@networking.ignore_exception
def sla_cleanup():
    """
    1. Stop all VMs
    2. Update all VMs to default parameters
    3. Remove all redundant VMs
    """
    logger.info("SLA cleanup")
    ll_vms.stop_vms_safely(ll_vms.VM_API.get(absLink=False))
    logger.info("Remove all exceed vms")
    ll_vms.remove_all_vms_from_cluster(
        config.CLUSTER_NAME[0], skip=config.VM_NAME
    )
    for vm in config.VM_NAME:
        logger.info("Update VM %s to default parameters ")
        if not ll_vms.updateVm(
            positive=True, vm=vm, **config.DEFAULT_VM_PARAMETERS
        ):
            logger.error("Failed to update VM %s to default Parameters" % vm)


def teardown_package():
    reporter = Inventory.get_instance()
    reporter.get_setup_inventory_report(
        print_report=True,
        check_inventory=True,
        rhevm_config_file=config
    )
