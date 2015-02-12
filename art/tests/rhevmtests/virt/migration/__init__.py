#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt - Migration test initialization
"""

import os
import logging
from rhevmtests.networking import network_cleanup
from rhevmtests.networking import config as netconf
import art.test_handler.exceptions as errors
from art.test_handler.exceptions import NetworkException
from rhevmtests.virt.migration.helper import set_host_status
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.datacenters as dc_api
import art.rhevm_api.tests_lib.low_level.clusters as cluster_api
import art.rhevm_api.tests_lib.high_level.datacenters as high_dc_api
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from rhevmtests.virt import config
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level import vms as hl_vm

logger = logging.getLogger("Virt_Network_Migration_Init")

# ################################################

NUM_OF_VMS = 5


def migration_job_create_vm(vm_name):
    """
    Create VM
    :param vm_name: VM name
    :type vm_name: str
    """
    if not vm_api.createVm(
        positive=True, vmName=vm_name, vmDescription=config.VM_DESCRIPTION,
        cluster=config.CLUSTER_NAME[0],
        storageDomainName=config.STORAGE_NAME[0], size=config.DISK_SIZE,
        nic='nic1', network=config.MGMT_BRIDGE,
        installation=config.INSTALLATION, image=config.COBBLER_PROFILE,
        user=config.VMS_LINUX_USER, password=config.VMS_LINUX_PW,
        os_type='RHEL6x64', useAgent=True
    ):
        raise errors.VMException("Failed to create VM: %s" % vm_name)


def setup_package():
    """
    Prepare environment for Migration Test
    """
    if os.environ.get("JENKINS_URL"):
        if not config.GOLDEN_ENV:
            logger.info("Building setup...")
            if not high_dc_api.build_setup(
                config.PARAMETERS, config.PARAMETERS, config.STORAGE_TYPE,
                config.TEST_NAME
            ):
                raise errors.DataCenterException("Setup environment failed")
            logger.info(
                "Add additional cluster %s to datacenter %s",
                config.CLUSTER_NAME[1], config.DC_NAME[0]
            )
            if not cluster_api.addCluster(
                True, name=config.CLUSTER_NAME[1], version=config.COMP_VERSION,
                data_center=config.DC_NAME[0], cpu=config.CPU_NAME
            ):
                raise errors.ClusterException("Cluster creation failed")
        logger.info(
            "Create additional datacenter %s", config.ADDITIONAL_DC_NAME
        )
        if not dc_api.addDataCenter(
            True, name=config.ADDITIONAL_DC_NAME, local=True,
            version=config.COMP_VERSION
        ):
            raise errors.DataCenterException("Datacenter creation failed")
        logger.info(
            "Add cluster to datacenter %s", config.ADDITIONAL_DC_NAME
        )
        if not cluster_api.addCluster(
            True, name=config.ADDITIONAL_CL_NAME,
            version=config.COMP_VERSION, data_center=config.ADDITIONAL_DC_NAME,
            cpu=config.CPU_NAME
        ):
            raise errors.ClusterException("Cluster creation failed")
        if not config.GOLDEN_ENV:
            # Temporary update clusters to memory over commitment of 0%
            # Need to be removed once ART default will be 0%
            for cluster_name in [
                config.CLUSTER_NAME[0], config.CLUSTER_NAME[1],
                config.ADDITIONAL_CL_NAME
            ]:
                logger.info(
                    "Update cluster %s to mem_ovrcmt_prc=0", cluster_name
                )
                if not cluster_api.updateCluster(
                        True, cluster_name, mem_ovrcmt_prc=0
                ):
                    raise errors.VMException(
                        "Failed to update cluster %s to mem_ovrcmt_prc=0" %
                        cluster_name
                    )
            logger.info('Create vms: %s', config.VM_NAMES[:5])
            for vm_name in config.VM_NAMES[:5]:
                migration_job_create_vm(vm_name)

            logger.info("Stop all vms")
            if not vm_api.stopVms(','.join(config.VM_NAMES[:5])):
                raise errors.VMException("Failed to stop vms")

        if config.GOLDEN_ENV:
            network_cleanup()
            logger.info(
                "Running on golden env, starting VM %s on host %s",
                config.VM_NAME[0], config.HOSTS[0]
            )

            if not hl_vm.start_vm_on_specific_host(
                vm=config.VM_NAME[0], host=config.HOSTS[0]
            ):
                raise NetworkException(
                    "Cannot start VM %s on host %s" %
                    (config.VM_NAME[0], config.HOSTS[0])
                )
            if not vms.waitForVMState(vm=config.VM_NAME[0]):
                raise NetworkException(
                    "VM %s did not come up" % config.VM_NAME[0]
                )
            logger.info(
                "Set all but 2 hosts in the Cluster %s to the maintenance "
                "state", config.CLUSTER_NAME[0]
            )
            set_host_status()

        logger.info("Disabling firewall on the Hosts")
        for host in config.VDS_HOSTS:
            if not host.service(netconf.FIREWALL_SRV).stop():
                raise NetworkException("Cannot stop Firewall service")


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        logging.info(
            "Remove cluster %s from datacenter %s", config.ADDITIONAL_CL_NAME,
            config.ADDITIONAL_DC_NAME
        )
        if not cluster_api.removeCluster(
            True, config.ADDITIONAL_CL_NAME
        ):
            logger.error("Failed to remove %s", config.ADDITIONAL_CL_NAME)
        logging.info(
            "Remove additional datacenter %s", config.ADDITIONAL_DC_NAME
        )
        if not dc_api.removeDataCenter(True, config.ADDITIONAL_DC_NAME):
            logger.error(
                "Failed to remove datacenter %s" % config.ADDITIONAL_DC_NAME
            )
        if not config.GOLDEN_ENV:
            logging.info(
                "Remove additional cluster %s from datacenter %s",
                config.CLUSTER_NAME[1], config.DC_NAME[0]
            )
            if not cluster_api.removeCluster(True, config.CLUSTER_NAME[1]):
                raise errors.ClusterException("Failed to remove cluster")

            if not cleanDataCenter(
                True, config.DC_NAME[0], vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
            ):
                raise errors.DataCenterException("Clean up environment failed")

        if config.GOLDEN_ENV:
            logger.info("Enabling firewall on the Hosts")
            for host in config.VDS_HOSTS:
                if not host.service(netconf.FIREWALL_SRV).start():
                    logger.error("Cannot start Firewall service")

            logger.info(
                "Running on golden env, stopping VM %s", config.VM_NAME[0]
            )
            if not vms.stopVm(True, vm=config.VM_NAME[0]):
                logger.error(
                    "Failed to stop VM: %s", config.VM_NAME[0]
                )
            logger.info("Set inactive hosts to the active state")
            set_host_status(activate=True)
