"""
High-level functions above data-center
"""

import logging

import art.rhevm_api.tests_lib.high_level.clusters as hl_clusters
import art.rhevm_api.tests_lib.high_level.hosts as hosts
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_sd
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.clusters as clusters
import art.rhevm_api.tests_lib.low_level.datacenters as datacenters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.test_handler.exceptions as errors
from art.rhevm_api.resources import Host  # This import is not good here
from art.rhevm_api.utils.cpumodel import CpuModelDenominator, CpuModelError
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler.settings import opts


logger = logging.getLogger("art.hl_lib.dcs")
ENUMS = opts['elements_conf']['RHEVM Enums']
SPM_TIMEOUT = 300
SPM_SLEEP = 5
FIND_SDS_TIMEOUT = 10
SD_STATUS_OK_TIMEOUT = 120


def build_setup(config, storage, storage_type, basename="testname",
                local=False):
    """
    Description: Creates a setup based on what's specified in the config
    Parameters:
        * config - dict containing setup specification ([PARAMETERS] section)
        * storage - dict containing storage specification ([{storage}] section)
        * storage_type - type of storage to use (NFS, ISCSI, FCP, LOCALFS)
        * basename - baseword for naming objects in setup
    Returns names of created storage domains
    """
    hl_mac_pool.update_default_mac_pool()
    datacenter_name = config.get('dc_name', '%s_DC_1' % basename)
    cluster_name = config.get('cluster_name', '%s_Cluster_1' % basename)
    config['dc_name'] = datacenter_name
    config['cluster_name'] = cluster_name
    version = config.get('compatibility_version')

    if not datacenters.addDataCenter(
            positive=True, name=datacenter_name, local=local, version=version
    ):
        raise errors.DataCenterException(
            "Add DataCenter %s version %s failed." %
            (datacenter_name, version)
        )
    logger.info("Datacenter %s was created successfully", datacenter_name)

    if not clusters.addCluster(
            positive=True, name=cluster_name, cpu=config['cpu_name'],
            data_center=datacenter_name, version=version
    ):
        raise errors.ClusterException(
            "Add Cluster %s with cpu_type %s and version %s "
            "to datacenter %s failed" %
            (cluster_name, config['cpu_name'], version, datacenter_name)
        )
    logger.info("Cluster %s was created successfully", cluster_name)

    hosts.add_hosts(config.as_list('vds'), config.as_list('vds_password'),
                    cluster_name)

    # Align cluster cpu compatibility to fit all hosts
    hosts_obj = [Host.get(h) for h in config.as_list('vds')]
    cpu_den = CpuModelDenominator()
    try:
        cpu_info = cpu_den.get_common_cpu_model(
            hosts_obj, version=version,
        )
    except CpuModelError as ex:
        logger.error("Can not determine the best cpu_model: %s", ex)
    else:
        logger.info("Cpu info %s for cluster: %s", cpu_info, cluster_name)
        if not clusters.updateCluster(True, cluster_name, cpu=cpu_info['cpu']):
            logger.error(
                "Can not update cluster cpu_model to: %s", cpu_info['cpu'],
            )

    return hl_sd.create_storages(
        storage, storage_type, config.as_list('vds')[0], datacenter_name)


def get_spm_host(positive, datacenter):
    """
    Description: get spm host name
    :param datacenter name
    :type datacenter: str
    :returns name of spm host
    :rtype: str
    """

    is_spm_exists, spm_host = ll_hosts.getHost(positive, datacenter, True)

    if not is_spm_exists:
        logger.error("No SPM found in data center %s, storage", datacenter)
        return None

    return ll_hosts.HOST_API.find(spm_host['hostName'])


def get_clusters_connected_to_datacenter(dc_id):
    """
    Description: get list of clusters connected to datacenter
    :param dc_id datacenter id
    :type dc_id: str
    :returns list of clusters names
    :rtype: list
    """

    all_clusters = clusters.util.get(absLink=False)
    clusters_connected_to_dc = [
        cluster for cluster in all_clusters
        if cluster.get_data_center() is not None
    ]
    return filter(
        lambda x: x.get_data_center().get_id() == dc_id,
        clusters_connected_to_dc
    )


def clean_datacenter(
        positive,
        datacenter,
        db_name=ll_sd.RHEVM_UTILS_ENUMS['RHEVM_DB_NAME'],
        db_user=ll_sd.RHEVM_UTILS_ENUMS['RHEVM_DB_USER'],
        formatIsoStorage='false',
        formatExpStorage='false',
        vdc=None,
        vdc_password=None,
        hosted_engine_vm=None,
        hosted_engine_sd=None,
):
    """
    Description: Remove data center: all clusters. vms, templates floating
                 disks, storage domains and hosts
    :param datacenter name
    :type datacenter: str
    :param db_name: engine database name
    :type db_name: str
    :param db_user: name of engine db user
    :type db_user: str
    :param formatIsoStorage - when removing should we format it
    :type formatIsoStorage: bool
    :param formatExpStorage - when removing should we format it
    :type formatExpStorage: bool
    :param vdc engine machine ip
    :type vdc; str
    :param vdc_password
    :type vdc_password: str
    :param hosted_engine_vm: the vm name of hosted engine
    :type hosted_engine_vm: str
    :param hosted_engine_sd: the sd name of hosted engine
    :type hosted_engine_sd: str
    :returns: True if relevant operations within this function pass,
    False otherwise
    :rtype: bool
    """
    status = True
    hosted_engine = False
    dc_obj = datacenters.get_data_center(datacenter)

    hosts_to_remove = []
    clusters_to_remove = get_clusters_connected_to_datacenter(dc_obj.get_id())

    for cluster_obj in clusters_to_remove:
        cluster_name = cluster_obj.get_name()
        cl_vms = hl_vms.get_vms_objects_from_cluster(cluster_name)
        cl_vms_names = [cl.get_name() for cl in cl_vms]
        if hosted_engine_vm in cl_vms_names:
            cl_vms_names.remove(hosted_engine_vm)
            hosted_cl_name = cluster_name
            hosted_engine = True
        ll_vms.safely_remove_vms(cl_vms_names)
        hl_clusters.remove_templates_connected_cluster(cluster_name)
        hosts_to_remove.extend(
            hl_clusters.get_hosts_connected_to_cluster(cluster_obj.get_id())
        )

    sds = ll_sd.getDCStorages(datacenter, False)

    if hosted_engine:
        _, master_domain = ll_sd.findMasterStorageDomain(True, datacenter)
        hosted_host = ll_vms.get_vm_host(hosted_engine_vm)
        logger.info("This is hosted Engine cleanup(leave the following):")
        logger.info("  Datacenter: %s", datacenter)
        logger.info("  Cluster: %s", hosted_cl_name)
        logger.info("  Host: %s", hosted_host)
        logger.info("  Hosted Engine SD: %s", hosted_engine_sd)
        logger.info("  Master SD: %s", master_domain['masterDomain'])
        logger.info("  VM: %s", hosted_engine_vm)
        # Set spm priority to default (Medium)
        ll_hosts.setSPMPriority(
            positive=True, hostName=hosted_host, spmPriority=5
        )
        ll_hosts.select_host_as_spm(
            positive=True, host=hosted_host, data_center=datacenter
        )

        hosts_to_remove = [
            h for h in hosts_to_remove if h.get_name() != hosted_host
        ]
        clusters_to_remove = [
            cl for cl in clusters_to_remove if cl.get_name() != hosted_cl_name
        ]
        sds = [
            sd for sd in sds
            if sd.get_name() != hosted_engine_sd and not sd.get_master()
        ]

    spm_host_obj = get_spm_host(positive, datacenter)
    if sds:
        for sd in sds:
            logger.info(
                "Remove floating disks from storage domain: %s", sd.get_name()
            )
            ll_sd.remove_floating_disks(sd)

        dc_name = dc_obj.get_name()
        if vdc and vdc_password:
            wait_for_tasks(
                vdc=vdc,
                vdc_password=vdc_password,
                datacenter=dc_name,
                db_name=db_name,
                db_user=db_user
            )

        logger.info("Deactivate and detach non-master storage domains")
        for sd in sds:
            if not sd.get_master():
                sd_name = sd.get_name()
                logger.info("Detach and deactivate %s", sd_name)
                if not hl_sd.detach_and_deactivate_domain(
                    dc_name, sd_name
                ):
                    raise errors.StorageDomainException(
                        "Failed to deactivate storage domain %s" % sd_name
                    )

        if vdc and vdc_password:
            wait_for_tasks(
                vdc=vdc,
                vdc_password=vdc_password,
                datacenter=dc_name,
                db_name=db_name,
                db_user=db_user
            )

        if not hosted_engine:
            logger.info("Deactivate master storage domain")
            status = ll_sd.deactivate_master_storage_domain(
                positive, datacenter
            )

            if vdc and vdc_password:
                wait_for_tasks(
                    vdc=vdc,
                    vdc_password=vdc_password,
                    datacenter=dc_name,
                    db_name=db_name,
                    db_user=db_user
                )
    if not hosted_engine:
        logger.info("Remove data center")
        if not datacenters.remove_datacenter(positive, datacenter):
            logger.error("Remove data center %s failed", datacenter)
            status = False

    if sds and spm_host_obj:
        logger.info("Remove storage domains")
        status = ll_sd.remove_storage_domains(
            sds, spm_host_obj.get_name(),
            formatExpStorage,
            formatIsoStorage
        )

    logger.info("Remove hosts")
    for host in hosts_to_remove:
        logger.info("Put host %s to maintenance & remove it", host.get_name())
        if not ll_hosts.removeHost(True, host.get_name(), deactivate=True):
            logger.error("Failed to remove %s", host.get_name())

    logger.info("Remove cluster")
    for cluster_obj in clusters_to_remove:
        cluster_name = cluster_obj.get_name()
        if not clusters.removeCluster(positive, cluster_name):
            logger.error("Remove cluster %s Failed", cluster_name)
            status = False
    return status


def ensure_data_center_and_sd_are_active(
    datacenter, exclude_states=[ENUMS['storage_domain_state_maintenance']]
):
    """
    Wait for the Data center to become active, for an SPM host selection and
    for all storage domains to become active

    :param datacenter: Datacenter Name
    :type datacenter: str
    :param exclude_states: List of storage domains statuses that can be ignored
    :type exclude_states: list
    """
    logger.info("Wait for the Data center to become active")
    if not datacenters.waitForDataCenterState(datacenter):
        raise errors.DataCenterException(
            "The Data center was not up within 3 minutes, aborting test"
        )

    if not ll_hosts.waitForSPM(
        datacenter, SPM_TIMEOUT, SPM_SLEEP
    ):
        raise errors.StorageDomainException(
            "SPM host was not elected within 5 minutes, aborting test"
        )
    for sd in ll_sd.getDCStorages(datacenter, False):
        if sd.get_status() in exclude_states:
            continue
        logger.info(
            "Waiting up to %s seconds for sd %s to be active",
            SD_STATUS_OK_TIMEOUT, sd.get_name()
        )
        if not ll_sd.waitForStorageDomainStatus(
            True, datacenter, sd.get_name(),
            ENUMS['storage_domain_state_active'], SD_STATUS_OK_TIMEOUT, 1
        ):
            raise errors.StorageDomainException(
                "NFS domain '%s' has not reached %s state after %s seconds" %
                (
                    sd.get_name(), ENUMS['storage_domain_state_active'],
                    SD_STATUS_OK_TIMEOUT
                )
            )
