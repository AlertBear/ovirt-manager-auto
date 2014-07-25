"""
MOM test initialization and teardown
"""

import os
import logging
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
import art.rhevm_api.tests_lib.low_level.storagedomains as storagedomains
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.rhevm_api.tests_lib.low_level.templates as templates
import art.rhevm_api.tests_lib.low_level.vmpools as pools
import art.rhevm_api.tests_lib.low_level.hosts as hosts
import art.test_handler.exceptions as errors

from art.rhevm_api.utils.test_utils import setPersistentNetwork
from art.test_handler.settings import opts
from utilities import machine

logger = logging.getLogger("MOM")
ENUMS = opts['elements_conf']['RHEVM Enums']
RHEL_TEMPLATE = "rhel_template"
IMPORT_TIMEOUT = 7200

#################################################


def setup_package():
    """
    Prepare environment for MOM test
    """
    if os.environ.get("JENKINS_URL"):
        import config
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TEST_NAME)

        if not storagedomains.importStorageDomain(
                True, type=ENUMS['storage_dom_type_export'],
                storage_type=ENUMS['storage_type_nfs'],
                host=config.HOSTS[0], address=config.MOM_EXPORT_ADDRESS,
                path=config.MOM_EXPORT_PATH):
            raise errors.StorageDomainException("Failed to import "
                                                "storage domain")

        if not storagedomains.attachStorageDomain(
                True, datacenter=config.DC_NAME[0],
                storagedomain=config.MOM_EXPORT_DOMAIN):
            raise errors.StorageDomainException(
                "Failed to attach export storage domain")

        if not storagedomains.activateStorageDomain(
                True, datacenter=config.DC_NAME[0],
                storagedomain=config.MOM_EXPORT_DOMAIN):
            raise errors.StorageDomainException(
                "Failed to activate export storage domain")

        if not storagedomains.waitForStorageDomainStatus(
                True, config.DC_NAME[0], config.MOM_EXPORT_DOMAIN,
                ENUMS['storage_domain_state_active']):
            raise errors.StorageDomainException(
                "Failed to activate export storage domain")

        for vm in [config.RHEL, config.W7, config.W2K]:
            if not vms.importVm(True, vm,
                                export_storagedomain=config.MOM_EXPORT_DOMAIN,
                                import_storagedomain=config.STORAGE_NAME[0],
                                cluster=config.CLUSTER_NAME[0], async=True):
                raise errors.VMException("Failed to import vm %s" % vm)

        if not vms.waitForVMState(config.RHEL,
                                  state=ENUMS['vm_state_down'],
                                  timeout=IMPORT_TIMEOUT):
            raise errors.VMException("Failed to import vm %s" % config.RHEL)

        if not vms.startVm(True, config.RHEL):
            raise errors.VMException("Failed to start vm %s" % config.RHEL)

        if not vms.waitForIP(config.RHEL):
            raise errors.VMException("guest-agent failed on %s" % config.RHEL)
        # update tools
        vm_machine = vms.get_vm_machine(
            config.RHEL, config.VMS_LINUX_USER, config.VMS_LINUX_PW)
        rc = vm_machine.yum('rhevm-guest-agent-common', 'update', timeout=120,
                            conn_timeout=120)
        if rc:
            logger.info("Guest agent updated on %s", config.RHEL)
        else:
            logger.warning("Guest agent not updated on %s continuing "
                           "with old GA, output", config.RHEL)

        status, ip = vms.waitForIP(config.RHEL, timeout=7200, sleep=10)
        if not status:
            raise errors.VMException(
                "Failed to obtain vm %s machine" % config.RHEL)
        if not setPersistentNetwork(ip['ip'], config.VMS_LINUX_PW):
            raise errors.VMException("Failed to set persistent network")

        if not vms.stopVm(True, config.RHEL):
            raise errors.VMException("Failed to stop VM %s" % config.RHEL)

        if not templates.createTemplate(True, name=RHEL_TEMPLATE,
                                        vm=config.RHEL):
            raise errors.TemplateException("Failed to create "
                                           "template for pool")

        # create VMs for KSM and balloon
        for name, vm_num, in [
                ("ksm", config.KSM_VM_NUM),
                ("balloon", config.BALLOON_VM_NUM)]:
            if not pools.addVmPool(
                    True, name=name, size=vm_num,
                    cluster=config.CLUSTER_NAME[0],
                    template=RHEL_TEMPLATE, description="%s pool" % name):
                raise errors.VMException("Failed creation of pool for %s" %
                                         name)
            # detach VMs from pool to be editable
            if not pools.detachVms(True, name):
                raise errors.VMException("Failed to detach VMs from %s pool" %
                                         name)

        for vm_name in [config.W7, config.W2K]:
            if not vms.waitForVMState(vm_name, state=ENUMS['vm_state_down']):
                raise errors.VMException("Failed to import vm %s" % vm_name)

        # safely detach export storage domain
        if not storagedomains.deactivateStorageDomain(
                True, config.DC_NAME[0], config.MOM_EXPORT_DOMAIN):
            raise errors.StorageDomainException(
                "Failed to deactivate export domain")
        if not storagedomains.detachStorageDomain(
                True, config.DC_NAME[0], config.MOM_EXPORT_DOMAIN):
            raise errors.StorageDomainException("Failed to detach "
                                                "export domain")

        # disable swapping on hosts for faster tests
        for host, pwd in [(config.HOSTS[0], config.HOSTS_PW[0]),
                          (config.HOSTS[1], config.HOSTS_PW[1])]:
            host_machine = machine.Machine(host, 'root',
                                           pwd).util(machine.LINUX)
            logger.info("Turning off swapping on host %s", host)
            rc, out = host_machine.runCmd(['swapoff', '-a'])
            if not rc:
                raise errors.HostException(
                    "Failed to turn off swap on host %s"
                    ", output - %s" % (host, out))
            if not hosts.set_mom_script(host, 'root', pwd):
                raise errors.HostException("Failed to set script for mom rpc "
                                           "on host %s" % host)

            logger.info("changing rpc port for mom to 8080 on host %s", host)
            if not hosts.change_mom_rpc_port(
                    host, host_user='root', host_pwd=pwd, port=8080):
                raise errors.HostException("Failed to change RPC port "
                                           "for mom on host %s" % host)

        if not storagedomains.waitForStorageDomainStatus(
                True, config.DC_NAME[0], config.STORAGE_NAME[0],
                ENUMS['storage_domain_state_active']):
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
        import config
        logger.info("Teardown...")
        dc_name = config.DC_NAME[0]
        # turn on swaps on host
        failhost = []
        for host, pwd in [(config.HOSTS[0], config.HOSTS_PW[0]),
                          (config.HOSTS[1], config.HOSTS_PW[1])]:

            host_machine = machine.Machine(host,
                                           'root', pwd).util(machine.LINUX)
            rc, out = host_machine.runCmd(['swapon', '-a'])
            logger.info("Swap switched on for host %s", host)
            if not rc:
                failhost.append(host)

        if failhost:
            raise errors.HostException(
                "Failed to turn on swap on host %s" % ' '.join(failhost))

        for host, pwd in [(config.HOSTS[0], config.HOSTS_PW[0]),
                          (config.HOSTS[1], config.HOSTS_PW[1])]:

            if not hosts.change_mom_rpc_port(host, 'root', pwd, -1):
                raise errors.HostException("Failed to set mom port for rpc "
                                           "to default")
            logger.info("MOM port for rpc changed to default on host %s", host)
            rc, out = hosts.remove_mom_script(host, 'root', pwd)
            if not rc:
                raise errors.HostException("Failed to remove script for mom "
                                           "on host %s - output %s" %
                                           (host, out))

        if not storagedomains.waitForStorageDomainStatus(
                True, config.DC_NAME[0], config.STORAGE_NAME[0],
                ENUMS['storage_domain_state_active']):
            raise errors.StorageDomainException(
                "Failed to activate storage domain "
                "after restart of VDSM on hosts")

        storagedomains.cleanDataCenter(True, dc_name, vdc=config.VDC_HOST,
                                       vdc_password=config.VDC_PASSWORD)
