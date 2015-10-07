"""
Storage SPM decommission
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_Pool_Metadata_Removal
"""
import config
import logging
import time

from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest

from art.rhevm_api.tests_lib.low_level import clusters as ll_clusters
from art.rhevm_api.tests_lib.low_level import datacenters as ll_datacenters
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_storagedomains
)
from art.rhevm_api.tests_lib.high_level import clusters as hl_clusters
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_storagedomains
)
from art.rhevm_api.utils.log_listener import watch_logs

from multiprocessing import Process, Queue
logger = logging.getLogger(__name__)

TIMEOUT_SD_OPERATION = 300


@attr(tier=2)
class ActivateDeactivate(StorageTest):
    """
    Test for race condition while activating and deactivating storage domains
    in pool
    """

    def setUp(self):
        """
        Select domains to use in the test
        """
        raise NotImplementedError("Implement this setUp in the proper class")

    @polarion("RHEVM3-12462")
    def test_activate_deactivate_storage_domains(self):
        """
        Actions:
        * Deactivate domain1
        * Activate domain1 and at the same time deactivate another domain
        Verify:
        * Both actions should work
        """
        # TODO: Check if there are any tasks running involving this domain
        # before deactivating it, waiting a response from devel
        assert ll_storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.domain1
        )
        ll_storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.domain1, wait=False
        )
        ll_storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.domain2, wait=False
        )
        # Make sure both domains are in the expected state
        assert ll_storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.domain1,
            config.SD_ACTIVE, TIMEOUT_SD_OPERATION
        )
        assert ll_storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.domain2,
            config.SD_MAINTENANCE, TIMEOUT_SD_OPERATION
        )

    def tearDown(self):
        """
        Make sure both domain are active again
        """
        # activateStorageDomain will return True if the domain is already
        # activated
        ll_storagedomains.activateStorageDomain(
            False, config.DATA_CENTER_NAME, self.domain1
        )
        assert ll_storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.domain2
        )


class ActivateDeactivateSameStorageType(ActivateDeactivate):
    """
    Test with both storage domains from the same type (file/block)
    """
    __test__ = True

    def setUp(self):
        """
        Select storage domains for test
        """
        self.domains = ll_storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.domain1, self.domain2 = self.domains[0:2]


class ActivateDeactivateMixedStorageTypes(ActivateDeactivate):
    """
    Test with storage domains from different types (file and block)
    """
    __test__ = True

    def setUp(self):
        """
        Select storage domains for test
        """
        self.domain1 = ll_storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        if self.storage in config.BLOCK_TYPES:
            domain2_storage_type = config.STORAGE_TYPE_NFS
        else:
            domain2_storage_type = config.STORAGE_TYPE_ISCSI
        self.domain2 = ll_storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, domain2_storage_type
        )[0]


@attr(tier=2)
class UpgradeBaseClass(StorageTest):
    """
    Test behaviour of an upgraded data center
    """
    data_center_name = "spm_decommission_data_center"
    cluster_name = "spm_decommission_cluster"

    domain_1 = "domain1_spm_decommission"
    domain_2 = "domain2_spm_decommission"

    def setUp(self):
        """
        Create a data center and attach hosts
        """
        ll_datacenters.addDataCenter(
            True, name=self.data_center_name, storage_type=self.storage,
            version=config.DC_ORIGIN_VERSION
        )
        ll_clusters.addCluster(
            True, name=self.cluster_name, cpu=config.CPU_NAME,
            data_center=self.data_center_name, version=config.COMP_VERSION
        )
        host_list = hl_clusters.get_hosts_connected_to_cluster(
            ll_clusters.get_cluster_object(config.CLUSTER_NAME).get_id()
        )
        self.host_1, self.host_2 = (
            host_list[0].get_name(), host_list[1].get_name()
        )
        hl_hosts.switch_host_to_cluster(self.host_1, self.cluster_name)
        hl_hosts.switch_host_to_cluster(self.host_2, self.cluster_name)

    def add_first_storage_domain(self):
        """
        Add and activate the first storage domain
        """
        logger.info("Adding storage domain %s", self.domain_1)
        assert ll_storagedomains.addStorageDomain(
            True, name=self.domain_1, host=self.host_1,
            **self.domain1_parameters
        )
        assert hl_storagedomains.attach_and_activate_domain(
            self.data_center_name, self.domain_1
        )

    def search_regex_after_activating_second_domains(self, regex):
        """
        Perform a regex search in the hosts' vdsm log after activating
        the second domain
        """
        def f(q, host):
            """
            Perform a regex search in host and updates the queue object q
            with the result
            """
            try:
                found_regex = False
                host_ip = ll_hosts.getHostIP(host)
                found_regex, cmd_rc = watch_logs(
                    config.VDSM_LOG, regex, ip_for_files=host_ip,
                    username=config.HOSTS_USER, password=config.HOSTS_PW,
                    time_out=60
                )
            finally:
                q.put((found_regex, host))

        def assert_found(q):
            found, host = q.get()
            self.assertTrue(
                found, "Search %s failed returned no results on host %s" %
                (regex, host)
            )

        logger.info(
            "Attaching and activating domain %s and looking for expression "
            "%s on hosts %s and %s on vdsm logs", self.domain_2, regex,
            self.host_1, self.host_2
        )
        q = Queue()
        process_host_1 = Process(target=f, args=(q, self.host_1))
        process_host_2 = Process(target=f, args=(q, self.host_2))
        process_host_1.start()
        process_host_2.start()
        time.sleep(2)
        assert hl_storagedomains.attach_and_activate_domain(
            self.data_center_name, self.domain_2
        )
        assert_found(q)
        assert_found(q)

    @polarion("RHEVM3-12463")
    def test_backward_compatibility(self):
        """
        Actions:
        * Create a storage domain, activate it
        * Create a second storage domain and activate it
        Verify:
        * Engine sends RefreshStoragePool to vdsm when creating the
        second domain and when activating it
        """
        self.add_first_storage_domain()
        assert ll_storagedomains.addStorageDomain(
            True, name=self.domain_2, host=self.host_1,
            **self.domain2_parameters
        )
        self.search_regex_after_activating_second_domains("refreshStoragePool")

    @polarion("RHEVM3-12461")
    def test_upgrade_data_center(self):
        """
        Actions:
        * Create a storage domain and activate it in the DC
        * Upgrade the DC and cluster to 3.5
        * Create a second storage domain
        Verify:
        * When creating and activating the second storage domain, engine should
        send ConnectStoragePool with the domainsMap attribute in it which
        includes all the pools domains and their statuses to vdsm instead of
        RefreshStoragePool
        """
        # regex example
        # connectStoragePool(spUUID=u'5cdf77ac-170f-481f-a85c-52773adea750',
        # ..., domainsMap={u'1ccdf894-8c35-4b5d-9d9f-0f454202a59b': u'active',
        # u'1329e3fc-66c0-412f-bd41-a229a49e957c': u'active'}
        self.add_first_storage_domain()
        logger.info(
            "Uprading data center %s to version %s", self.data_center_name,
            config.DC_UPGRADE_VERSION
        )
        assert ll_datacenters.updateDataCenter(
            True, self.data_center_name, version=config.DC_UPGRADE_VERSION
        )
        assert ll_storagedomains.addStorageDomain(
            True, name=self.domain_2, host=self.host_1,
            **self.domain2_parameters
        )
        domain_1_id = ll_storagedomains.getStorageDomainObj(
            self.domain_1
        ).get_id()
        domain_2_id = ll_storagedomains.getStorageDomainObj(
            self.domain_2
        ).get_id()

        # It appears that the order of the domains map is random,
        # so attempt both possible combinations
        domains_regex = "u'%s': u'\w+', u'%s': u'\w+'"
        option_1 = domains_regex % (domain_2_id, domain_1_id)
        option_2 = domains_regex % (domain_1_id, domain_2_id)
        regex = "connectStoragePool.*domainsMap={(%s|%s)}" % (
            option_1, option_2
        )
        self.search_regex_after_activating_second_domains(regex)

    def tearDown(self):
        """
        Remove the created data center
        """
        sds = ll_storagedomains.getDCStorages(self.data_center_name, False)
        for sd in sds:
            if not sd.get_master():
                hl_storagedomains.detach_and_deactivate_domain(
                    self.data_center_name, sd.get_name()
                )
        status, master = ll_storagedomains.findMasterStorageDomain(
            True, self.data_center_name
        )
        if status:
            ll_storagedomains.deactivate_master_storage_domain(
                True, self.data_center_name
            )
        ll_datacenters.removeDataCenter(True, self.data_center_name)
        ll_storagedomains.remove_storage_domains(sds, self.host_1)
        hl_hosts.switch_host_to_cluster(self.host_1, config.CLUSTER_NAME)
        hl_hosts.switch_host_to_cluster(self.host_2, config.CLUSTER_NAME)
        ll_clusters.removeCluster(True, self.cluster_name)


class UpgradeSameStorageType(UpgradeBaseClass):
    """
    Test with both storage domains from the same type (file/block)
    """
    __test__ = True

    def setUp(self):
        """
        Get storage domains parameters
        """
        self.domain1_parameters = config.STORAGE_DOMAINS_KWARGS[
            self.storage
        ][0]
        self.domain2_parameters = config.STORAGE_DOMAINS_KWARGS[
            self.storage
        ][1]
        super(UpgradeSameStorageType, self).setUp()


class UpgradeMixedStorageTypes(UpgradeBaseClass):
    """
    Test with storage domains from different types (file and block)
    """
    __test__ = True

    def setUp(self):
        """
        Get storage domains parameters
        """
        self.domain1_parameters = config.STORAGE_DOMAINS_KWARGS[
            self.storage
        ][0]

        if self.storage in config.BLOCK_TYPES:
            self.domain2_parameters = config.STORAGE_DOMAINS_KWARGS[
                config.STORAGE_TYPE_NFS
            ][1]
        else:
            self.domain2_parameters = config.STORAGE_DOMAINS_KWARGS[
                config.STORAGE_TYPE_ISCSI
            ][1]
        super(UpgradeMixedStorageTypes, self).setUp()
