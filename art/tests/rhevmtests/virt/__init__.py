import logging
from art.rhevm_api.utils.inventory import Inventory
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import config
import helper

logger = logging.getLogger(__name__)


def setup_package():
    """
    1. Stop all VMs
    2. Update all VMs to default parameters
    3. Remove all redundant VMs
    """
    logger.info("VIRT cleanup")
    skip_vms = config.VM_NAME + [config.HE_VM]
    helper.remove_all_pools_from_cluster(config.CLUSTER_NAME[0])
    none_ge_vms_in_cluster = helper.get_all_vm_in_cluster(
        cluster_name=config.CLUSTER_NAME[0],
        skip=skip_vms
    )
    logger.info("Stop GE VMs")
    ll_vms.stop_vms_safely(config.VM_NAME)
    logger.info("Remove none GE VMs")
    if none_ge_vms_in_cluster:
        ll_vms.stop_vms_safely(none_ge_vms_in_cluster)
        for vm in none_ge_vms_in_cluster:
            ll_vms.updateVm(positive=True, vm=vm, protected=False)
    hl_vms.remove_all_vms_from_cluster(config.CLUSTER_NAME[0], skip=skip_vms)
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
