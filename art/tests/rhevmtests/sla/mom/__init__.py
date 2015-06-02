"""
MOM test initialization and teardown
"""


import config
import logging
import art.test_handler.exceptions as errors
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import templates
import art.rhevm_api.tests_lib.low_level.vmpools as pools
from art.rhevm_api.tests_lib.high_level import datacenters
import art.rhevm_api.tests_lib.high_level.hosts as h_hosts
from art.rhevm_api.utils.test_utils import setPersistentNetwork

logger = logging.getLogger("MOM")
RHEL_TEMPLATE = "rhel_template"
NUM_OF_HOSTS = 2
BALLOON_FILE = "/etc/vdsm/mom.d/02-balloon.policy"

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
        "Replace %s in %s on %s ", exists_value, correct_value, BALLOON_FILE
    )
    if not resource.executor().run_cmd(
        ["sed", "-i", "s/%s/%s/" % (exists_value, correct_value), BALLOON_FILE]
    ):
        message = (
            "Failed to replace %s in %s on %s " %
            (exists_value, correct_value, BALLOON_FILE)
        )
        if teardown:
            logger.error(message)
        else:
            raise errors.ResourceError(message)


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
    rc, out, err = host_resource.executor().run_cmd([command, "-a"])
    if rc:
        message = (
            "Failed to run %s on %s, due to %s" % (command, host_resource, err)
        )
        if teardown:
            logger.error(message)
        else:
            raise errors.HostException(message)


def setup_package():
    """
    Prepare environment for MOM test
    """

    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config.PARAMETERS, config.PARAMETERS,
            config.STORAGE_TYPE, config.TEST_NAME
        )
        logger.info("Create vm %s to use as template", config.VM_NAME[0])
        if not vms.createVm(
                positive=True, vmName=config.VM_NAME[0],
                vmDescription="RHEL VM",
                cluster=config.CLUSTER_NAME[0],
                storageDomainName=config.STORAGE_NAME[0],
                size=6 * config.GB, nic=config.NIC_NAME[0],
                memory=2 * config.GB,
                network=config.MGMT_BRIDGE,
                installation=True, image=config.COBBLER_PROFILE,
                user=config.VMS_LINUX_USER, password=config.VMS_LINUX_PW,
                os_type=config.OS_TYPE
        ):
            raise errors.VMException("Failed to create vm")

        logger.info("Wait for vm %s ip", config.VM_NAME[0])
        rc, out = vms.waitForIP(config.VM_NAME[0])
        if not rc:
            raise errors.VMException("Vm still not have ip")
        logger.info("Seal vm %s - ip %s", config.VM_NAME[0], out["ip"])
        if not setPersistentNetwork(
                out["ip"], config.VMS_LINUX_PW
        ):
            raise errors.VMException("Failed to set persistent network")
        logger.info("Stop vm %s", config.VM_NAME[0])
        if not vms.stopVm(True, config.VM_NAME[0]):
            raise errors.VMException("Failed to stop vm")
        logger.info("Create template from vm %s", config.VM_NAME[0])
        if not templates.createTemplate(
                True, name=RHEL_TEMPLATE, vm=config.VM_NAME[0]
        ):
            raise errors.TemplateException(
                "Failed to create template for pool"
            )
        rhel_template = RHEL_TEMPLATE
    else:
        rhel_template = config.TEMPLATE_NAME[0]

    # create VMs for KSM and balloon
    logger.info("Create vms pool %s", config.POOL_NAME)
    if not pools.addVmPool(
            True, name=config.POOL_NAME, size=config.VM_NUM,
            cluster=config.CLUSTER_NAME[0],
            template=rhel_template,
            description="%s pool" % config.POOL_NAME
    ):
        raise errors.VMException(
            "Failed creation of pool for %s" % config.POOL_NAME
        )
    # detach VMs from pool to be editable
    logger.info("Detach vms from vms pool %s", config.POOL_NAME)
    if not pools.detachVms(True, config.POOL_NAME):
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
    h_hosts.restart_vdsm_and_wait_for_activation(
        config.VDS_HOSTS[:2], config.DC_NAME[0], config.STORAGE_NAME[0]
    )


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
    if not config.GOLDEN_ENV:
        datacenters.clean_datacenter(
            True, config.DC_NAME[0], vdc=config.VDC_HOST,
            vdc_password=config.VDC_ROOT_PASSWORD
        )
