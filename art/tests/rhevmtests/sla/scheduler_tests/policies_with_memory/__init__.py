"""
Scheduler - scheduler policies with memory test initialization
"""
import logging
import config as conf
from art.rhevm_api.utils import test_utils
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd

logger = logging.getLogger(__name__)


def update_configuration_constants(host_name=None):
    """
    Update configuration file constants depend on host memory

    :param host_name: host name
    :type host_name: str
    """
    if host_name is None:
        host_name = conf.HOSTS[0]
    half_host_memory = ll_hosts.get_host_memory(host_name) / 2
    conf.DEFAULT_PS_PARAMS[
        conf.MIN_FREE_MEMORY
    ] = (half_host_memory + 2 * conf.GB) / conf.MB
    conf.DEFAULT_PS_PARAMS[
        conf.MAX_FREE_MEMORY
    ] = (half_host_memory - 2 * conf.GB) / conf.MB
    conf.DEFAULT_ED_PARAMS[
        conf.MAX_FREE_MEMORY
    ] = (half_host_memory - 2 * conf.GB) / conf.MB
    overutilized_memory = (
        half_host_memory + 3 * conf.GB - half_host_memory % conf.MB
    )
    normalutilized_memory = (
        half_host_memory - conf.GB - half_host_memory % conf.MB
    )
    for normalutilized_vm, overutilized_vm in zip(
        conf.LOAD_NORMALUTILIZED_VMS, conf.LOAD_OVERUTILIZED_VMS
    ):
        conf.LOAD_MEMORY_VMS.update(
            {
                normalutilized_vm: {
                    conf.MEMORY: normalutilized_memory,
                    conf.MEMORY_GUARANTEED: normalutilized_memory
                },
                overutilized_vm: {
                    conf.MEMORY: overutilized_memory,
                    conf.MEMORY_GUARANTEED: overutilized_memory
                }
            }
        )


def setup_package():
    """
    1) Change LowUtilizationForEvenlyDistribute engine-config parameter
    2) Wait until storage domains will be active after engine restart
    3) Create memory load vms
    """
    logger.info(
        "Change engine-config parameter %s to %s",
        conf.ENGINE_CONFIG_LOW_UTILIZATION,
        conf.DEFAULT_PS_PARAMS[conf.LOW_UTILIZATION]
    )
    cmd = [
        "{0}={1}".format(
            conf.ENGINE_CONFIG_LOW_UTILIZATION,
            conf.DEFAULT_PS_PARAMS[conf.LOW_UTILIZATION]
        )
    ]
    if not test_utils.set_engine_properties(conf.ENGINE, cmd):
        raise errors.UnkownConfigurationException(
            "Failed to set %s option to %s" %
            (
                conf.ENGINE_CONFIG_LOW_UTILIZATION,
                conf.DEFAULT_PS_PARAMS[conf.LOW_UTILIZATION]
            )
        )
    if not ll_sd.waitForStorageDomainStatus(
        positive=True,
        dataCenterName=conf.DC_NAME[0],
        storageDomainName=conf.STORAGE_NAME[0],
        expectedStatus=conf.SD_ACTIVE
    ):
        raise errors.StorageDomainException(
            "Storage domain %s not active" % conf.STORAGE_NAME[0]
        )
    logger.info(
        "Update cluster %s overcommitment to %d",
        conf.CLUSTER_NAME[0], conf.CLUSTER_OVERCOMMITMENT_NONE
    )
    if not ll_clusters.updateCluster(
        positive=True, cluster=conf.CLUSTER_NAME[0],
        mem_ovrcmt_prc=conf.CLUSTER_OVERCOMMITMENT_NONE
    ):
        raise errors.ClusterException(
            "Failed to update cluster %s" % conf.CLUSTER_NAME[0]
        )
    # Assume that all hosts have minimum 8Gb and equal amount of memory
    update_configuration_constants()
    for vm_name, vm_params in conf.LOAD_MEMORY_VMS.iteritems():
        logger.info("Create vm %s with parameters: %s", vm_name, vm_params)
        if not ll_vms.createVm(
            positive=True, vmName=vm_name, vmDescription="",
            cluster=conf.CLUSTER_NAME[0],
            storageDomainName=conf.STORAGE_NAME[0], size=conf.GB,
            nic=conf.NIC_NAME[0], network=conf.MGMT_BRIDGE,
            **vm_params
        ):
            raise errors.VMException("Failed to create vm %s" % vm_name)


def teardown_package():
    """
    Remove memory load vms
    """
    if not ll_vms.safely_remove_vms(conf.LOAD_MEMORY_VMS.keys()):
        logger.error("Failed to remove vms: %s", conf.LOAD_MEMORY_VMS.keys())
    logger.info(
        "Update cluster %s overcommitment to %d",
        conf.CLUSTER_NAME[0], conf.CLUSTER_OVERCOMMITMENT_DESKTOP
    )
    if not ll_clusters.updateCluster(
        positive=True, cluster=conf.CLUSTER_NAME[0],
        mem_ovrcmt_prc=conf.CLUSTER_OVERCOMMITMENT_DESKTOP
    ):
        logger.error("Failed to update cluster %s" % conf.CLUSTER_NAME[0])
    engine_default_value = 0
    logger.info(
        "Change engine-config parameter %s to %s",
        conf.ENGINE_CONFIG_LOW_UTILIZATION, engine_default_value
    )
    cmd = [
        "{0}={1}".format(
            conf.ENGINE_CONFIG_LOW_UTILIZATION, engine_default_value
        )
    ]
    if not test_utils.set_engine_properties(conf.ENGINE, cmd):
        raise errors.UnkownConfigurationException(
            "Failed to set %s option to %s" %
            (conf.ENGINE_CONFIG_LOW_UTILIZATION, engine_default_value)
        )
