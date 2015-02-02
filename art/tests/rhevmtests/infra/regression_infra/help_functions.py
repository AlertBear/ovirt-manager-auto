"""
-----------------
Helper functions for setup & teardown
-----------------

@author: Nelly Credi
"""

import config
import logging

from art.rhevm_api.tests_lib.low_level import (hosts,
                                               datacenters,
                                               clusters,
                                               storagedomains,
                                               vms,
                                               templates)
from art.test_handler.exceptions import (DataCenterException,
                                         ClusterException,
                                         HostException,
                                         StorageDomainException,
                                         VMException,
                                         TemplateException)
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.utils.test_utils import wait_for_tasks

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS


class utils(object):

    reverse_env_list = []

    @staticmethod
    def add_dc():
        logger.info('Add data center')
        status = datacenters.addDataCenter(
            positive=True, name=config.DATA_CENTER_1_NAME,
            local=False, version=config.COMP_VERSION)
        utils.reverse_env_list.append(utils.remove_dc)
        if not status:
            raise DataCenterException('Failed to add data center')

    @staticmethod
    def add_cluster():
        logger.info('Add cluster')
        status = clusters.addCluster(
            positive=True, name=config.CLUSTER_1_NAME, cpu=config.CPU_NAME,
            data_center=config.DATA_CENTER_1_NAME,
            version=config.COMP_VERSION, on_error='migrate')
        utils.reverse_env_list.append(utils.remove_cluster)
        if not status:
            raise ClusterException('Failed to add cluster')

    @staticmethod
    def add_host():
        logger.info('Add host')
        status = hosts.addHost(
            positive=True, name=config.HOST_NAME, wait=True, reboot=False,
            root_password=config.HOSTS_PW, cluster=config.CLUSTER_1_NAME,
            vdcPort=config.VDC_PORT)
        utils.reverse_env_list.append(utils.remove_host)
        if not status:
            raise HostException('Failed to add host')
        utils.reverse_env_list.append(utils.deactivate_host)

    @staticmethod
    def create_sd():
        logger.info('Create storage domain')
        status = storagedomains.addStorageDomain(
            positive=True, name=config.STORAGE_DOMAIN_NAME,
            type=ENUMS['storage_dom_type_data'],
            storage_type=ENUMS['storage_type_nfs'],
            address=config.DATA_DOMAIN_ADDRESS,
            host=config.HOST_NAME, path=config.DATA_DOMAIN_PATH)
        utils.reverse_env_list.remove(utils.remove_dc)
        utils.reverse_env_list.append(utils.remove_sd)
        utils.reverse_env_list.append(utils.remove_dc)
        if not status:
            raise StorageDomainException('Failed to add storage domain')
        utils.reverse_env_list.append(utils.deactivate_sd)

    @staticmethod
    def attach_sd():
        logger.info('Attach storage domain')
        status = storagedomains.attachStorageDomain(
            positive=True, datacenter=config.DATA_CENTER_1_NAME,
            storagedomain=config.STORAGE_DOMAIN_NAME)
        if not status:
            raise StorageDomainException('Failed to attach storage domain')

    @staticmethod
    def create_vm():
        logger.info('Create vm')
        status = vms.addVm(positive=True, name=config.VM_NAME,
                           cluster=config.CLUSTER_1_NAME)
        utils.reverse_env_list.append(utils.remove_vm)
        if not status:
            raise VMException('Failed to add VM')

    @staticmethod
    def add_disk_to_vm():
        logger.info('Add disk to vm')
        status = vms.addDisk(positive=True, vm=config.VM_NAME, size=2147483648,
                             storagedomain=config.STORAGE_DOMAIN_NAME,
                             type=ENUMS['disk_type_system'],
                             format=ENUMS['format_cow'],
                             interface=ENUMS['interface_ide'])
        utils.reverse_env_list.append(utils.remove_disk_from_vm)
        if not status:
            raise VMException('Failed to add disk to VM')

    @staticmethod
    def create_template():
        logger.info('Create template')
        status = templates.createTemplate(
            positive=True, vm=config.VM_NAME, name=config.TEMPLATE_NAME,
            cluster=config.CLUSTER_1_NAME)
        utils.reverse_env_list.append(utils.remove_template)
        if not status:
            raise TemplateException('Failed to create template')

    @staticmethod
    def remove_disk_from_vm():
        logger.info('Remove disk from vm')
        status = vms.removeDisk(positive=True, vm=config.VM_NAME,
                                disk=config.VM_NAME + '_Disk1')
        if not status:
            raise VMException('Failed to remove disk from VM')

    @staticmethod
    def remove_vm():
        logger.info('Remove vm')
        status = vms.removeVm(positive=True, vm=config.VM_NAME)
        if not status:
            raise VMException('Failed to remove VM')

    @staticmethod
    def remove_template():
        logger.info('Remove template')
        status = templates.removeTemplate(positive=True,
                                          template=config.TEMPLATE_NAME)
        if not status:
            raise TemplateException('Failed to remove template')

    @staticmethod
    def deactivate_sd():
        logger.info('Wait for tasks to finish ...')
        wait_for_tasks(
            config.VDC_HOST,
            config.VDC_ROOT_PASSWORD,
            config.DATA_CENTER_1_NAME,
        )
        logger.info('Deactivate storage domain')
        status = storagedomains.deactivateStorageDomain(
            positive=True, datacenter=config.DATA_CENTER_1_NAME,
            storagedomain=config.STORAGE_DOMAIN_NAME)
        if not status:
            raise StorageDomainException('Failed to deactivate SD')

    @staticmethod
    def remove_dc():
        logger.info('Remove data center')
        status = datacenters.removeDataCenter(
            positive=True, datacenter=config.DATA_CENTER_1_NAME)
        if not status:
            raise DataCenterException('Failed to remove data center')

    @staticmethod
    def remove_sd():
        logger.info('Remove storage domain')
        status = storagedomains.removeStorageDomain(
            positive=True, storagedomain=config.STORAGE_DOMAIN_NAME,
            host=config.HOST_NAME, format='true')
        if not status:
            raise StorageDomainException('Failed to remove SD')

    @staticmethod
    def deactivate_host():
        logger.info('Deactivate host')
        status = hosts.deactivateHost(positive=True, host=config.HOST_NAME)
        if not status:
            raise HostException('Failed to deactivate host')

    @staticmethod
    def remove_host():
        logger.info('Remove host')
        status = hosts.removeHost(positive=True, host=config.HOST_NAME)
        if not status:
            raise HostException('Failed to remove host')

    @staticmethod
    def remove_cluster():
        logger.info('Remove cluster')
        status = clusters.removeCluster(positive=True,
                                        cluster=config.CLUSTER_1_NAME)
        if not status:
            raise ClusterException('Failed to remove cluster')

    @staticmethod
    def clean_environment():
        logger.info('cleaning environment')
        while utils.reverse_env_list:
            component_to_clean = utils.reverse_env_list.pop()
            try:
                component_to_clean()
            except EntityNotFound:
                logger.info('Failed to perform operation ' +
                            component_to_clean.__name__ +
                            ' - EntityNotFound exception caught')
