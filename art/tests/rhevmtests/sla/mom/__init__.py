"""
MOM test initialization and teardown
"""

import os
import config
import logging
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
import art.rhevm_api.tests_lib.low_level.storagedomains as storagedomains
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.rhevm_api.tests_lib.low_level.templates as templates
import art.rhevm_api.tests_lib.low_level.hosts as hosts
import art.rhevm_api.tests_lib.low_level.vmpools as pools
import art.test_handler.exceptions as errors

from art.rhevm_api.utils.test_utils import setPersistentNetwork
from art.test_handler.settings import opts

logger = logging.getLogger("MOM")
ENUMS = opts['elements_conf']['RHEVM Enums']
RHEL_TEMPLATE = "rhel_template"

#################################################


def setup_package():
    """
    Prepare environment for MOM test
    """
    if os.environ.get("JENKINS_URL"):
        if not config.GOLDEN_ENV:
            datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                    config.STORAGE_TYPE, config.TEST_NAME)
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
                    os_type=config.OS_TYPE):
                raise errors.VMException("Failed to create vm")
            logger.info("Wait for vm %s ip", config.VM_NAME[0])
            rc, out = vms.waitForIP(config.VM_NAME[0])
            if not rc:
                raise errors.VMException("Vm still not have ip")
            logger.info("Seal vm %s - ip %s", config.VM_NAME[0], out['ip'])
            if not setPersistentNetwork(
                    out['ip'], config.VMS_LINUX_PW
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
            raise errors.VMException("Failed to detach VMs from %s pool" %
                                     config.POOL_NAME)
        logger.info("Remove vms pool %s", config.POOL_NAME)
        if not pools.removeVmPool(True, config.POOL_NAME):
            raise errors.VMException("Failed to remove vms from pool")

        # disable swapping on hosts for faster tests
        for host, pwd in [(config.HOSTS[0], config.HOSTS_PW),
                          (config.HOSTS[1], config.HOSTS_PW)]:
            host_machine = hosts.get_linux_machine_obj(
                host, config.HOSTS_USER, pwd)
            logger.info("Turning off swapping on host %s", host)
            rc, out = host_machine.runCmd(['swapoff', '-a'])
            if not rc:
                raise errors.HostException(
                    "Failed to turn off swap on host %s"
                    ", output - %s" % (host, out))
            if not hosts.set_mom_script(host, config.HOSTS_USER, pwd):
                raise errors.HostException("Failed to set script for mom rpc "
                                           "on host %s" % host)

            logger.info("changing rpc port for mom to 8080 on host %s", host)
            if not hosts.change_mom_rpc_port(
                host, host_user=config.HOSTS_USER, host_pwd=pwd, port=8080
            ):
                raise errors.HostException("Failed to change RPC port "
                                           "for mom on host %s" % host)

        if not storagedomains.waitForStorageDomainStatus(
            True, config.DC_NAME[0], config.STORAGE_NAME[0],
            ENUMS['storage_domain_state_active']
        ):
            raise errors.StorageDomainException(
                "Failed to activate storage domain "
                "after restart of VDSM on hosts")

        host_names = "%s, %s" % (config.HOSTS[0], config.HOSTS[1])
        if not hosts.waitForHostsStates(True, host_names):
            raise errors.HostException("Failed to activate hosts")


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        dc_name = config.DC_NAME[0]
        # turn on swaps on host
        failhost = []
        for host, pwd in [(config.HOSTS[0], config.HOSTS_PW),
                          (config.HOSTS[1], config.HOSTS_PW)]:

            host_machine = hosts.get_linux_machine_obj(
                host, config.HOSTS_USER, pwd)
            rc, out = host_machine.runCmd(['swapon', '-a'])
            logger.info("Swap switched on for host %s", host)
            if not rc:
                failhost.append(host)

        if failhost:
            raise errors.HostException(
                "Failed to turn on swap on host %s" % ' '.join(failhost))

        for host, pwd in [(config.HOSTS[0], config.HOSTS_PW),
                          (config.HOSTS[1], config.HOSTS_PW)]:

            if not hosts.change_mom_rpc_port(host, config.HOSTS_USER, pwd, -1):
                raise errors.HostException("Failed to set mom port for rpc "
                                           "to default")
            logger.info("MOM port for rpc changed to default on host %s", host)
            rc, out = hosts.remove_mom_script(host, config.HOSTS_USER, pwd)
            if not rc:
                raise errors.HostException("Failed to remove script for mom "
                                           "on host %s - output %s" %
                                           (host, out))

        if not storagedomains.waitForStorageDomainStatus(
            True, config.DC_NAME[0], config.STORAGE_NAME[0],
            ENUMS['storage_domain_state_active']
        ):
            raise errors.StorageDomainException(
                "Failed to activate storage domain "
                "after restart of VDSM on hosts")
        logger.info("Remove all exceed vms")
        if not vms.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0], skip=config.VM_NAME
        ):
            raise errors.VMException("Failed to remove vms")
        if not config.GOLDEN_ENV:
            storagedomains.cleanDataCenter(True, dc_name, vdc=config.VDC_HOST,
                                           vdc_password=config.VDC_PASSWORD)
