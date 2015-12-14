"""
DataCenter Networks feature test
"""
from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter
from rhevmtests.system.power_management import config

from art.test_handler.exceptions import DataCenterException, HostException,\
    ClusterException, StorageDomainException
from art.rhevm_api.tests_lib.low_level.datacenters import addDataCenter
import logging
from art.rhevm_api.tests_lib.low_level.clusters import addCluster
from art.rhevm_api.tests_lib.low_level.hosts import addHost
from art.rhevm_api.tests_lib.high_level import storagedomains

########################################################

logger = logging.getLogger("Power Management")


def setup_package():
    """
    Prepare environment
    """
    if not config.GOLDEN_ENV:
        logger.info("Creating data center with 2 clusters and 3 hosts")
        if not addDataCenter(True, name=config.DC_NAME[0],
                             storage_type=config.STORAGE_TYPE,
                             version=config.COMP_VERSION):
            raise DataCenterException("cannot add data center: %s" %
                                      config.DC_NAME[0])
        for cluster_name in [config.CLUSTER_NAME[0], config.CLUSTER_NAME[1]]:
                if not addCluster(True, name=cluster_name, cpu=config.CPU_NAME,
                                  data_center=config.DC_NAME[0],
                                  version=config.COMP_VERSION):
                    raise ClusterException(
                        "cannot add cluster: %s" % cluster_name
                    )
        for host_name in [config.HOSTS[0], config.HOSTS[1]]:
            if not addHost(True, name=host_name,
                           root_password=config.HOSTS_PW, address=host_name,
                           cluster=config.CLUSTER_NAME[0]):
                raise HostException("cannot add host: %s" % host_name)
        if not addHost(
            True,
            name=config.HOSTS[2],
            root_password=config.HOSTS_PW,
            address=config.HOSTS[2],
            cluster=config.CLUSTER_NAME[1]
        ):
            raise HostException("cannot add host: %s" % config.HOSTS[2])
        if not storagedomains.create_storages(config.STORAGE,
                                              type_=config.STORAGE_TYPE,
                                              host=config.HOSTS[1],
                                              datacenter=config.DC_NAME[0]):
            raise StorageDomainException(
                "Cannot create %s storage for data center: %s"
                % (config.STORAGE_TYPE, config.DC_NAME[0]))


def teardown_package():
    """
    Cleans environment
    """
    if not config.GOLDEN_ENV:
        if not clean_datacenter(
                True, config.DC_NAME[0],
                vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD):
            raise DataCenterException("Cannot clean and remove DC: %s"
                                      % config.DC_NAME[0])
