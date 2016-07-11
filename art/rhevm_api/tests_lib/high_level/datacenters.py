"""
High-level functions above data-center
"""

import logging


import art.rhevm_api.tests_lib.low_level.clusters as clusters
import art.rhevm_api.tests_lib.low_level.datacenters as datacenters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.hosts as hosts
import art.rhevm_api.tests_lib.high_level.storagedomains as storagedomains
import art.rhevm_api.tests_lib.high_level.clusters as hl_clusters
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
from art.rhevm_api.tests_lib.low_level.disks import (
    getStorageDomainDisks,
    deleteDisk,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
from art.rhevm_api.utils.cpumodel import CpuModelDenominator, CpuModelError
from art.rhevm_api.resources import Host  # This import is not good here
import art.test_handler.exceptions as errors
from art.test_handler.settings import opts
from art.rhevm_api.utils.test_utils import wait_for_tasks


LOGGER = logging.getLogger("art.hl_lib.dcs")
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
    LOGGER.info("Datacenter %s was created successfully", datacenter_name)

    if not clusters.addCluster(
            positive=True, name=cluster_name, cpu=config['cpu_name'],
            data_center=datacenter_name, version=version
    ):
        raise errors.ClusterException(
            "Add Cluster %s with cpu_type %s and version %s "
            "to datacenter %s failed" %
            (cluster_name, config['cpu_name'], version, datacenter_name)
        )
    LOGGER.info("Cluster %s was created successfully", cluster_name)

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
        LOGGER.error("Can not determine the best cpu_model: %s", ex)
    else:
        LOGGER.info("Cpu info %s for cluster: %s", cpu_info, cluster_name)
        if not clusters.updateCluster(True, cluster_name, cpu=cpu_info['cpu']):
            LOGGER.error(
                "Can not update cluster cpu_model to: %s", cpu_info['cpu'],
            )

    return storagedomains.create_storages(
        storage, storage_type, config.as_list('vds')[0], datacenter_name)


def clean_all_disks_from_dc(datacenter, exception_list=None):
    """
    Description: Removes all disks in DC's storage domain. If exception_list
    is given, the disks names in that list will remain in the setup
    Author: ratamir
    Parameters:
    * datacenter - data center name
    * exception_list - List of disks names that should remain in the setup
    """
    sdObjList = ll_storagedomains.getDCStorages(datacenter, False)

    for storage_domain in sdObjList:
        LOGGER.info('Find any floating disks in storage domain %s',
                    storage_domain.get_name())
        floating_disks = getStorageDomainDisks(storage_domain.get_name(),
                                               False)
        if floating_disks:
            floating_disks_list = [disk.get_id() for disk in
                                   floating_disks if
                                   (disk.get_alias() not in exception_list)]
            for disk in floating_disks_list:
                LOGGER.info('Removing floating disk %s', disk)
                if not deleteDisk(True, alias=disk, async=False, disk_id=disk):
                    return False
            LOGGER.info('Ensuring all disks are removed')
            wait_for_jobs()
            LOGGER.info('All floating disks removed successfully')
        else:
            LOGGER.info('No floating disks found in storage domain %s',
                        storage_domain.get_name())


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
        LOGGER.error("No SPM found in data center %s, storage", datacenter)
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
        db_name=ll_storagedomains.RHEVM_UTILS_ENUMS['RHEVM_DB_NAME'],
        db_user=ll_storagedomains.RHEVM_UTILS_ENUMS['RHEVM_DB_USER'],
        formatIsoStorage='false',
        formatExpStorage='false',
        vdc=None,
        vdc_password=None
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
    :returns: True if relevant operations within this function pass,
    False otherwise
    :rtype: bool
    """
    status = True
    dc_obj = datacenters.util.find(datacenter)

    spm_host_obj = get_spm_host(positive, datacenter)
    hosts_to_remove = []

    clusters_to_remove = get_clusters_connected_to_datacenter(dc_obj.get_id())

    for cluster_obj in clusters_to_remove:
        hl_clusters.remove_vms_and_templates_from_cluster(
            cluster_obj.get_name()
        )
        hosts_to_remove += (
            hl_clusters.get_hosts_connected_to_cluster(cluster_obj.get_id())
        )

    sds = ll_storagedomains.getDCStorages(datacenter, False)

    if sds:
        for sd in sds:
            LOGGER.info(
                "Remove floating disks from storage domain: %s",
                sd.get_name()
            )
            ll_storagedomains.remove_floating_disks(sd)

        if vdc and vdc_password:
            wait_for_tasks(
                vdc=vdc,
                vdc_password=vdc_password,
                datacenter=dc_obj.get_name(),
                db_name=db_name,
                db_user=db_user
            )

        LOGGER.info("Deactivate and detach non-master storage domains")
        for sd in sds:
            if not sd.get_master():
                LOGGER.info("Detach and deactivate %s", sd.get_name())
                if not storagedomains.detach_and_deactivate_domain(
                    dc_obj.get_name(), sd.get_name()
                ):
                    raise errors.StorageDomainException(
                        "Failed to deactivate storage domain %s" %
                        sd.get_name()
                    )

        if vdc and vdc_password:
            wait_for_tasks(
                vdc=vdc,
                vdc_password=vdc_password,
                datacenter=dc_obj.get_name(),
                db_name=db_name,
                db_user=db_user
            )

        LOGGER.info("Deactivate master storage domain")
        status = ll_storagedomains.deactivate_master_storage_domain(
            positive, datacenter
        )

        if vdc and vdc_password:
            wait_for_tasks(
                vdc=vdc,
                vdc_password=vdc_password,
                datacenter=dc_obj.get_name(),
                db_name=db_name,
                db_user=db_user
            )

    LOGGER.info("Remove data center")
    if not datacenters.remove_datacenter(positive, datacenter):
        LOGGER.error("Remove data center %s failed", datacenter)
        status = False

    if sds and spm_host_obj:
        LOGGER.info("Remove storage domains")
        status = ll_storagedomains.remove_storage_domains(
            sds, spm_host_obj.get_name(),
            formatExpStorage,
            formatIsoStorage
        )

    LOGGER.info("Remove hosts")
    for host in hosts_to_remove:
        LOGGER.info("Put %s to maintenance & remove it", host.get_name())
        if not ll_hosts.removeHost(True, host.get_name(), deactivate=True):
            LOGGER.error("Failed to remove %s", host.get_name())

    LOGGER.info("Remove cluster")
    for cluster_obj in clusters_to_remove:
        if not clusters.removeCluster(positive, cluster_obj.get_name()):
            LOGGER.error(
                "Remove cluster %s Failed",
                cluster_obj.get_name()
            )
            status = False

    return status


def ensure_data_center_and_sd_are_active(datacenter):
    """
    Wait for the Data center to become active, for an SPM host selection and
    for all storage domains to become active

    ** This is a workaround for bug:
    https://bugzilla.redhat.com/show_bug.cgi?id=1300075
    where storage domains are coming up in Unknown state after engine restart

    :param datacenter: Datacenter Name
    :type datacenter: str
    """
    LOGGER.info("Wait for the Data center to become active")
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
    for sd in ll_storagedomains.getDCStorages(datacenter, False):
        LOGGER.info(
            "Waiting up to %s seconds for sd %s to be active",
            SD_STATUS_OK_TIMEOUT, sd.get_name()
        )
        if not ll_storagedomains.waitForStorageDomainStatus(
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
