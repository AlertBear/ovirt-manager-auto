"""
Init for sla tests package
"""
import logging

import config
from art.rhevm_api.tests_lib.high_level import vms as hl_vms
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from rhevmtests import networking
import pytest

logger = logging.getLogger(__name__)


@networking.ignore_exception
def sla_cleanup():
    """
    1. Stop all VMs
    2. Update all VMs to default parameters
    3. Remove all redundant VMs
    """
    logger.info("SLA cleanup")
    ll_vms.stop_vms_safely(ll_vms.VM_API.get(abs_link=False))
    logger.info("Remove all exceed vms")
    hl_vms.remove_all_vms_from_cluster(
        config.CLUSTER_NAME[0], skip=config.VM_NAME
    )
    for vm in config.VM_NAME:
        logger.info("Update VM %s to default parameters ")
        if not ll_vms.updateVm(
            positive=True, vm=vm, **config.DEFAULT_VM_PARAMETERS
        ):
            logger.error("Failed to update VM %s to default Parameters" % vm)


def teardown_package():
    """
    Run package teardown
    """
    pytest.config.hook.pytest_rhv_teardown(team="sla")


def setup_package():
    """
    Run package setup
    """
    pytest.config.hook.pytest_rhv_setup(team="sla")
