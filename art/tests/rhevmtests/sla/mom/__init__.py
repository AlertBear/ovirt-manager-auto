"""
MOM test initialization and teardown
"""


import config
import logging
import art.test_handler.exceptions as errors
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level import vmpools as hl_pools
import art.rhevm_api.tests_lib.low_level.vmpools as pools
import art.rhevm_api.tests_lib.high_level.hosts as h_hosts

logger = logging.getLogger("MOM")


#################################################


def change_mom_pressure_percentage(resource, teardown=False):
    """
    change_mom_pressure_percentage in order to test deflation and inflation
    faster

    :param resource: host resource
    :type resource: host resource
    :param teardown: True if run from teardown, False otherwise
    :type teardown: bool
    :raise: ResourceError
    """

    dpt0_20 = "(defvar pressure_threshold 0.20)"
    dpt0_40 = "(defvar pressure_threshold 0.40)"
    exists_value = dpt0_40 if teardown else dpt0_20
    correct_value = dpt0_20 if teardown else dpt0_40
    logger.info(
        "Replace %s in %s on %s ", exists_value, correct_value,
        config.BALLOON_FILE
    )
    rc, _, _ = resource.run_command(
        ["sed", "-i", "s/%s/%s/" % (exists_value, correct_value),
         config.BALLOON_FILE]
    )
    if rc and not teardown:
        return False


def change_swapping(host_resource, teardown=False):
    """
    disable/enable swap

    :param host_resource: host resource
    :type host_resource: host resource
    :param teardown: True if run from teardown, False otherwise
    :type teardown: bool
    :raise: HostException
    """
    command = "swapon" if teardown else "swapoff"
    logger.info("Running %s on host %s", command, host_resource)
    rc, _, _ = host_resource.run_command([command, "-a"])
    if rc and not teardown:
        return False


def setup_package():
    """
    Prepare environment for MOM test
    """

    # create VMs for KSM and balloon
    logger.info("Create vms pool %s", config.POOL_NAME)
    if not pools.addVmPool(
        True, name=config.POOL_NAME, size=config.VM_NUM,
        cluster=config.CLUSTER_NAME[0],
        template=config.TEMPLATE_NAME[0],
        description="%s pool" % config.POOL_NAME
    ):
        raise errors.VMException(
            "Failed creation of pool for %s" % config.POOL_NAME
        )
    # detach VMs from pool to be editable
    logger.info("Detach vms from vms pool %s", config.POOL_NAME)
    if not hl_pools.detach_vms_from_pool(config.POOL_NAME):
        raise errors.VMException(
            "Failed to detach VMs from %s pool" % config.POOL_NAME
        )
    logger.info("Remove vms pool %s", config.POOL_NAME)
    if not pools.removeVmPool(True, config.POOL_NAME):
        raise errors.VMException("Failed to remove vms from pool")

    # disable swapping on hosts and change mom pressure for faster tests
    for host_resource in config.VDS_HOSTS[:2]:
        change_mom_pressure_percentage(host_resource)
        change_swapping(host_resource)


def teardown_package():
    """
    Cleans the environment
    """

    logger.info("Teardown...")
    for host_resource in config.VDS_HOSTS[:2]:
        change_mom_pressure_percentage(host_resource, True)
        change_swapping(host_resource, True)
    try:
        h_hosts.restart_vdsm_and_wait_for_activation(
            config.VDS_HOSTS[:2], config.DC_NAME[0], config.STORAGE_NAME[0]
        )
    except errors.HostException as e:
        logger.error("Failed to restart vdsm service, %s", e)
    except errors.StorageDomainException as e:
        logger.error("Failed to activate storage domain, %s", e)

    logger.info("Remove all exceed vms")
    if not vms.remove_all_vms_from_cluster(
        config.CLUSTER_NAME[0], skip=config.VM_NAME
    ):
        raise errors.VMException("Failed to remove vms")
