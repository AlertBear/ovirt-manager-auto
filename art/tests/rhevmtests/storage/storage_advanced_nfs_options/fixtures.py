import logging
import pytest
import config

from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
    jobs as ll_jobs,
)
from art.unittest_lib.common import testflow
from art.rhevm_api.utils import test_utils
from concurrent.futures import ThreadPoolExecutor
from art.test_handler import exceptions

logger = logging.getLogger(__name__)
EXPORT = config.EXPORT_TYPE
NFS = config.STORAGE_TYPE_NFS
DC_NAME = config.DATA_CENTER_NAME


@pytest.fixture()
def initializer_class(request, storage):
    """
    Removes all storage domain created during the test
    """
    self = request.node.cls

    def finalizer():
        if self.sds_for_cleanup:
            logger.info("Cleanup - removing storage domains")
            results = list()
            test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
            with ThreadPoolExecutor(
                max_workers=len(self.sds_for_cleanup)
            ) as executor:
                for storage_domain in self.sds_for_cleanup:
                    testflow.teardown(
                        "Removing storage domain %s", storage_domain
                    )
                    if ll_sd.checkIfStorageDomainExist(True, storage_domain):
                        results.append(
                            executor.submit(
                                hl_sd.remove_storage_domain,
                                storage_domain, config.DATA_CENTER_NAME,
                                self.host, engine=config.ENGINE,
                                format_disk=True
                            )
                        )
            for index, result in enumerate(results):
                if result.exception():
                    raise result.exception()
                if not result.result:
                    raise exceptions.HostException(
                        "Remove storage domain %s failed." %
                        self.sds_for_cleanup[index]
                    )
                logger.info(
                    "Remove storage domain %s succeeded",
                    self.sds_for_cleanup[index]
                )
            ll_jobs.wait_for_jobs([config.JOB_REMOVE_DOMAIN])
    request.addfinalizer(finalizer)
    self.sds_for_cleanup = []
    self.host = ll_hosts.get_spm_host(config.HOSTS)
    self.host_ip = ll_hosts.get_host_ip(self.host)
    self.password = config.HOSTS_PW
    self.export_address = config.NFS_DOMAINS_KWARGS[0]['address']
    self.export_path = config.NFS_DOMAINS_KWARGS[0]['path']


@pytest.fixture()
def create_and_remove_sd(request, storage):
    """
    Creates storage domains and removes it and it which will be later imported
    """
    self = request.node.cls

    hl_sd.create_nfs_domain_with_options(
        self.export_domain, EXPORT, self.host, self.export_address,
        self.export_path, datacenter=DC_NAME
    )

    hl_sd.remove_storage_domain(
        self.export_domain, DC_NAME, self.host, engine=config.ENGINE,
    )
    self.sds_for_cleanup.append(self.export_domain)
