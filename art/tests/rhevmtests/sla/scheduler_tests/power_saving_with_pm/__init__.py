"""
Scheduler - Power Saving with Power Management test initialization
"""
import time
import logging
import rhevmtests.sla.config as conf
from art.unittest_lib import SkipTest
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.datacenters as hl_dcs

logger = logging.getLogger(__name__)

#################################################


def setup_package():
    """
    Prepare environment for Power Saving with Power Management Test
    """
    if not conf.GOLDEN_ENV:
        logger.info("Building setup...")
        if not hl_dcs.build_setup(
            conf.PARAMETERS, conf.PARAMETERS,
            conf.STORAGE_TYPE, conf.TEST_NAME
        ):
            raise errors.DataCenterException("Setup environment failed")
        logger.info("Create three new vms")
        for vm in conf.VM_NAME[:3]:
            if not ll_vms.createVm(
                positive=True, vmName=vm, vmDescription="Test VM",
                cluster=conf.CLUSTER_NAME[0],
                storageDomainName=conf.STORAGE_NAME[0], size=conf.GB,
                nic=conf.NIC_NAME[0], network=conf.MGMT_BRIDGE
            ):
                raise errors.VMException("Cannot create %s" % vm)
    logger.info("Select host %s as SPM", conf.HOSTS[0])
    if not ll_hosts.checkHostSpmStatus(True, conf.HOSTS[0]):
        if not ll_hosts.select_host_as_spm(
            True, conf.HOSTS[0], conf.DC_NAME[0]
        ):
            raise errors.DataCenterException(
                "Selecting host as SPM failed"
            )
    hosts_resource = dict(zip(conf.HOSTS[:3], conf.VDS_HOSTS[:3]))
    for host_name, host_resource in hosts_resource.iteritems():
        host_fqdn = host_resource.fqdn
        host_pm = conf.pm_mapping.get(host_fqdn)
        if host_pm is None:
            raise SkipTest(
                "Host %s with fqdn %s does not have power management" %
                (host_name, host_fqdn)
            )

        agent_option = {
            "slot": host_pm[conf.PM_SLOT]
        } if conf.PM_SLOT in host_pm else None
        agent = {
            "agent_type": host_pm.get(conf.PM_TYPE),
            "agent_address": host_pm.get(conf.PM_ADDRESS),
            "agent_username": host_pm.get(conf.PM_USERNAME),
            "agent_password": host_pm.get(conf.PM_PASSWORD),
            "concurrent": False,
            "order": 1,
            "options": agent_option
        }

        if not hl_hosts.add_power_management(
            host_name=host_name,
            pm_automatic=True,
            pm_agents=[agent]
        ):
            raise errors.HostException("Can not update host %s" % host_name)


def teardown_package():
    """
    Cleans the environment
    """
    for host_name in conf.HOSTS[:3]:
        logger.info("Check if host %s has state down", host_name)
        host_status = ll_hosts.getHostState(host_name) == conf.HOST_DOWN
        if host_status:
            logger.info(
                "Wait %d seconds between fence operations",
                conf.FENCE_TIMEOUT
            )
            time.sleep(conf.FENCE_TIMEOUT)
            logger.info("Start host %s", host_name)
            if not ll_hosts.fenceHost(True, host_name, 'start'):
                logger.error("Failed to start host %s", host_name)
        hl_hosts.remove_power_management(host_name=host_name)
    logger.info("Free all host CPU's from loading")
    ll_sla.stop_cpu_loading_on_resources(conf.VDS_HOSTS[:3])
    if not conf.GOLDEN_ENV:
        logger.info("Clean environment")
        if not hl_dcs.clean_datacenter(
            positive=True,
            datacenter=conf.DC_NAME[0],
            vdc=conf.VDC_HOST,
            vdc_password=conf.VDC_ROOT_PASSWORD
        ):
            logger.error("Clean up environment failed")
