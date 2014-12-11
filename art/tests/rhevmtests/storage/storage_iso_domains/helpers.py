
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters

import art.rhevm_api.tests_lib.high_level.hosts as hosts
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_sd
import art.test_handler.exceptions as errors
import logging
import config

logger = logging.getLogger(__name__)


def add_storage_domain(datacenter_name, host, **domain):
    """
    Add and attach an storege domain to datacenter_name
    """
    if domain['storage_type'] == config.STORAGE_TYPE_ISCSI:
        if not hl_sd._ISCSIdiscoverAndLogin(host,
                                            domain['lun_address'],
                                            domain['lun_target']):
            return False

    if not ll_sd.addStorageDomain(True, host=host, **domain):
        return False

    if domain['storage_type'] == config.ENUMS['storage_type_local']:
        # local storage domains should be attached and activated after
        # being added
        return ll_sd.is_storage_domain_active(
            datacenter_name, domain['name'])

    status = ll_sd.attachStorageDomain(
        True, datacenter_name, domain['name'], True)

    return status and ll_sd.activateStorageDomain(
        True, datacenter_name, domain['name'])


def build_environment(storage_domains, compatibility_version="3.4",
                      local=False):
    """
    Build an environment
        * compatibility version: str with version
        * domains: list of dictionary with the storage domains parameters
    """
    datacenter_name = config.DATA_CENTER_NAME
    cluster_name = config.CLUSTER_NAME

    if not ll_dc.addDataCenter(True, name=datacenter_name,
                               local=local,
                               version=compatibility_version):
        raise errors.DataCenterException(
            "addDataCenter %s with version %s failed." %
            (datacenter_name, compatibility_version))

    if not ll_clusters.addCluster(True, name=cluster_name,
                                  cpu=config.PARAMETERS['cpu_name'],
                                  data_center=datacenter_name,
                                  version=compatibility_version):
        raise errors.ClusterException(
            "addCluster %s with version %s to datacenter %s failed" %
            (cluster_name, compatibility_version, datacenter_name))

    hosts.add_hosts(
        config.PARAMETERS.as_list('vds'),
        config.PARAMETERS.as_list('vds_password'),
        cluster_name)

    for domain in storage_domains:
        assert add_storage_domain(datacenter_name, config.HOSTS[0], **domain)
