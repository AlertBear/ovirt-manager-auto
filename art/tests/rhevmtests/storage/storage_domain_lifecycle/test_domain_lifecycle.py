import logging
from sys import modules
import config
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
    hosts as hl_hosts,
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    datacenters as ll_dc,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.utils import iptables, storage_api, test_utils

from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as TestCase

from rhevmtests.storage import helpers as storage_helpers
from utilities import utils


logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

__THIS_MODULE = modules[__name__]

CLI_CMD_DF = 'df -H'
DATA_CENTER_TIMEOUT = 60 * 5
ISCSI = config.STORAGE_TYPE_ISCSI
GLUSTER = config.STORAGE_TYPE_GLUSTER
NFS = config.STORAGE_TYPE_NFS


def setup_module():
    """
    Setup the domain related information for all storage domain types
    """
    config.LIFECYCLE_ADDRESS = config.UNUSED_DATA_DOMAIN_ADDRESSES
    config.LIFECYCLE_PATH = config.UNUSED_DATA_DOMAIN_PATHS
    config.GLUSTER_LIFECYCLE_ADDRESS = (
        config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES
    )
    config.GLUSTER_LIFECYCLE_PATH = (
        config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS
    )
    config.LIFECYCLE_LUNS = config.UNUSED_LUNS
    config.LIFECYCLE_LUN_ADDRESS = config.UNUSED_LUN_ADDRESSES
    config.LIFECYCLE_LUN_TARGET = config.UNUSED_LUN_TARGETS


class BaseTestCase(TestCase):
    """
    Implement the common setup for this feature
    """
    __test__ = False
    polarion_test_case = None
    master_domain_ip = None
    engine_ip = None

    @classmethod
    def setup_class(cls):
        """
        Ensures that environment is ready for tests, validating that master
        domain is found and has an IP address, retrieves the IP address of
        the engine and the first host found under the second cluster
        """
        # Select the first non-SPM host, it will be moved to a new
        # DC/Cluster setup
        status, hsm_host = ll_hosts.getAnyNonSPMHost(
            config.HOSTS, cluster_name=config.CLUSTER_NAME
        )
        if not status:
            raise exceptions.HostException(
                "Failed tp retrieve a non-SPM host on cluster '%s'" %
                config.CLUSTER_NAME
            )
        cls.host = hsm_host['hsmHost']
        logger.info("DC name is: '%s'", config.DATA_CENTER_NAME)
        found, master_domain = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        if not found:
            raise exceptions.StorageDomainException(
                "Could not find master storage domain on Data center '%s'" %
                config.DATA_CENTER_NAME
            )
        master_domain = master_domain['masterDomain']
        logger.info("Master domain found : %s", master_domain)

        found, cls.master_domain_ip = ll_sd.getDomainAddress(
            True, master_domain
        )
        if not found:
            raise exceptions.StorageDomainException(
                "Could not find the IP address for the master storage domain "
                "host '%s'" % master_domain
            )
        cls.master_domain_ip = cls.master_domain_ip['address']
        logger.info("Master domain ip found : %s", cls.master_domain_ip)

        cls.engine_ip = utils.getIpAddressByHostName(config.VDC)
        cls.first_host_ip = ll_hosts.getHostIP(cls.host)


def _create_sd(sd_type, host):
    """
    Helper function for creating two storage domains
    Return: False if not all the storage domains were created,
            True otherwise
    """
    sd_args = {
        'type': config.TYPE_DATA,
        'storage_type': sd_type,
        'host': host,
    }
    sd_args['name'] = "%s_%s" % (sd_type, config.TESTNAME)
    if sd_type == ISCSI:
        sd_args['lun'] = config.LIFECYCLE_LUNS[0]
        sd_args['lun_address'] = config.LIFECYCLE_LUN_ADDRESS[0]
        sd_args['lun_target'] = config.LIFECYCLE_LUN_TARGET[0]
        sd_args['lun_port'] = config.LUN_PORT
        sd_args['override_luns'] = True
    elif sd_type == NFS:
        sd_args['address'] = config.LIFECYCLE_ADDRESS[0]
        sd_args['path'] = config.LIFECYCLE_PATH[0]
    elif sd_type == GLUSTER:
        sd_args['address'] = config.GLUSTER_LIFECYCLE_ADDRESS[0]
        sd_args['path'] = config.GLUSTER_LIFECYCLE_PATH[0]
        sd_args['vfs_type'] = ENUMS['vfs_type_glusterfs']

    logger.info("Creating storage domain with parameters: %s", sd_args)
    status = ll_sd.addStorageDomain(True, **sd_args)
    if not status:
        return None
    return sd_args['name']


@attr(tier=4)
class TestCase11598(BaseTestCase):
    """
    * Block connection from engine to host.
    * Wait until host goes to non-responsive.
    * Unblock connection.
    * Check that the host is UP again.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11598'

    @polarion("RHEVM3-11598")
    def test_disconnect_engine_from_host(self):
        """
        Block connection from one engine to host.
        Wait until host goes to non-responsive.
        Unblock connection.
        Check that the host is UP again.
        """
        assert iptables.block_and_wait(
            self.engine_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.first_host_ip, self.host, config.HOST_NONRESPONSIVE
        )

        assert iptables.unblock_and_wait(
            self.engine_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.first_host_ip, self.host
        )

    @classmethod
    def teardown_class(cls):
        """
        Unblock all connections that were blocked during the test
        """
        def check_dc_and_host_state():
            """ Checks whether DC and host used are available"""
            return (
                ll_dc.waitForDataCenterState(
                    config.DATA_CENTER_NAME, timeout=DATA_CENTER_TIMEOUT
                ) and ll_hosts.isHostUp(True, cls.host)
            )

        if not check_dc_and_host_state():
            logger.info("Unblocking connections, something went wrong")
            try:
                storage_api.unblockOutgoingConnection(
                    cls.engine_ip, config.HOSTS_USER, config.HOSTS_PW,
                    cls.first_host_ip
                )
            except exceptions.NetworkException, msg:
                logging.info("Connection already unblocked. Reason: %s", msg)

        if not check_dc_and_host_state():
            cls.test_failed = True
            logger.error(
                "Could not successfully restore the Data center state and "
                "host within the timeout period"
            )

        cls.teardown_exception()


@attr(tier=2)
class TestCase11784(TestCase):
    """
    Create storage domains from all types and attache them to datacenter
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Multiple_Storage_Domains_General
    """
    __test__ = True
    polarion_test_case = '11784'

    def setUp(self):
        """
        Sets up storage parameters
        """
        status, hsm_host = ll_hosts.getAnyNonSPMHost(
            config.HOSTS, cluster_name=config.CLUSTER_NAME
        )
        if not status:
            raise exceptions.HostException(
                "Failed tp retrieve a non-SPM host on cluster '%s'" %
                config.CLUSTER_NAME
            )
        self.host = hsm_host['hsmHost']
        logger.info("Creating storage domains")
        self.sd_name = _create_sd(self.storage, self.host)

    @polarion("RHEVM3-11784")
    def test_add_another_storage_domain_test(self):
        """
        Check that both storage domains were automatically activated
        after attaching them
        """
        self.assertTrue(
            ll_sd.attachStorageDomain(
                True, config.DATA_CENTER_NAME, self.sd_name
            ), "Failed to attach SD %s" % self.sd_name
        )
        self.assertTrue(
            ll_sd.is_storage_domain_active(
                config.DATA_CENTER_NAME, self.sd_name
            )
        )

    def tearDown(self):
        """
        Removes storage domains created for this test
        """
        logger.info(
            "Waiting for tasks before deactivating/removing the storage domain"
        )
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        logger.info("Removing storage domain")
        if not ll_sd.removeStorageDomains(True, self.sd_name, self.host):
            TestCase.test_failed = True
            logger.error(
                "Failed to remove storage domains '%s'", self.sd_name
            )
        TestCase.teardown_exception()


@attr(tier=2)
class TestUpgrade(TestCase):
    """
    Base class for upgrade testing
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Storage_Domain_Live_Upgrade
    """
    __test__ = False
    dc_name = None
    cluster_name = None
    sd_name_pattern = None
    storage_type = None
    dc_version = None
    dc_upgraded_version = None
    storage_format = None
    upgraded_storage_format = None
    cluster_version = config.COMPATIBILITY_VERSION
    host = None
    vm_name = None
    domain_kw = None
    polarion_test_case = '11743'

    def setUp(self):
        """
        Prepares Data center without storage
        """
        status, hsm_host = ll_hosts.getAnyNonSPMHost(
            config.HOSTS, cluster_name=config.CLUSTER_NAME
        )
        if not status:
            raise exceptions.HostException(
                "Failed tp retrieve a non-SPM host on cluster '%s'" %
                config.CLUSTER_NAME
            )
        self.host = hsm_host['hsmHost']
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        if self.storage == NFS:
            self.sd_path = config.LIFECYCLE_PATH[0]
            self.sd_address = config.LIFECYCLE_ADDRESS[0]
        elif self.storage == GLUSTER:
            self.sd_path = config.GLUSTER_LIFECYCLE_PATH[0]
            self.sd_address = config.GLUSTER_LIFECYCLE_ADDRESS[0]
        else:
            self.sd_lun = config.LIFECYCLE_LUNS[0]
            self.sd_lun_address = config.LIFECYCLE_LUN_ADDRESS[0]
            self.sd_lun_target = config.LIFECYCLE_LUN_TARGET[0]

        self.host_ip = ll_hosts.getHostIP(self.host)

        logger.info(
            "Retrieve the first host from the 2nd cluster (in original Data "
            "center)"
        )
        if not ll_dc.addDataCenter(
            True, name=self.dc_name, local=False,
            version=self.dc_version
        ):
            raise exceptions.DataCenterException(
                "Failed to create Data center '%s'" % self.dc_name
            )

        if not ll_clusters.addCluster(
            True, name=self.cluster_name, cpu=config.CPU_NAME,
            data_center=self.dc_name, version=self.cluster_version
        ):
            raise exceptions.ClusterException(
                "Failed to create Cluster '%s'" % self.cluster_name
            )

        logger.info("Move the host into the newly created cluster")
        if not hl_hosts.move_host_to_another_cluster(
            self.host, self.cluster_name
        ):
            raise exceptions.ClusterException(
                "Could not move host '%s' into cluster '%s'" % (
                    self.host, self.cluster_name
                )
            )

    def tearDown(self):
        """
        Remove Data Center, cluster, storage domains and migrates hosts to a
        temporary cluster
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error(
                "Failed to power off and remove vm %s", self.vm_name
            )
            TestCase.test_failed = True

        status = hl_dc.clean_datacenter(
            True, self.dc_name, formatExpStorage='true', vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )
        if not status:
            TestCase.test_failed = True
            logger.error(
                "Failed to clean Data center '%s'", self.dc_name
            )

        logger.info(
            "Re-add the moved host back into its original cluster/data center"
        )
        if not ll_hosts.addHost(
            True, self.host, address=self.host_ip, wait=True, reboot=False,
            cluster=config.CLUSTER_NAME, root_password=config.VDC_ROOT_PASSWORD
        ):
            self.test_failed = True
            logger.error(
                "Could not add host '%s' back into cluster '%s'",
                self.host, config.CLUSTER_NAME
            )

        TestCase.teardown_exception()

    @polarion("RHEVM3-11743")
    def test_data_center_upgrade(self):
        """
        Changes DC version while installing a VM
        """
        create_vm_args = config.create_vm_args.copy()
        create_vm_args['vmName'] = self.vm_name
        create_vm_args['vmDescription'] = self.vm_name
        create_vm_args['cluster'] = self.cluster_name
        create_vm_args['clone_from_template'] = False
        create_vm_args['storageDomainName'] = (
            self.sd_name_pattern % self.storage
        )
        assert storage_helpers.create_vm_or_clone(**create_vm_args)

        logger.info(
            "Upgrading Data Center %s from version %s to version %s ",
            self.dc_name, self.dc_version, self.dc_upgraded_version
        )
        ll_dc.update_datacenter(
            True, datacenter=self.dc_name, version=self.dc_upgraded_version
        )
        sds = ll_sd.getDCStorages(self.dc_name, get_href=False)
        for sd_obj in sds:
            was_upgraded = ll_sd.checkStorageFormatVersion(
                True, sd_obj.name, self.upgraded_storage_format
            )
            logger.info(
                "Checking that %s was upgraded: %s", sd_obj.name, was_upgraded
            )
            self.assertTrue(was_upgraded)


class TestUpgradeNFS(TestUpgrade):
    """
    Building NFS data center
    """
    storage_type = NFS
    domain_kw = 'data_domain_address'

    def setUp(self):
        """
        Create NFS storage domains for upgrade tests
        """
        super(TestUpgradeNFS, self).setUp()
        self.sd_name = self.sd_name_pattern % self.storage
        logger.info("Adding NFS storage domains needed for tests")
        logger.info("Address: %s, Path: %s", self.sd_address, self.sd_path)
        if not hl_sd.addNFSDomain(
            self.host, self.sd_name, self.dc_name,
            self.sd_address, self.sd_path, storage_format=self.storage_format
        ):
            raise exceptions.StorageDomainException(
                "Failed to create NFS Storage domain '%s'" % self.sd_name
            )
        logger.info(
            "NFS storage domain %s was created successfully", self.sd_name
        )


class TestUpgradeISCSI(TestUpgrade):
    """
    Building iSCSI data center
    """
    storage_type = ISCSI
    domain_kw = 'lun'

    def setUp(self):
        """
        Create iSCSI storage domains for upgrade tests
        """
        super(TestUpgradeISCSI, self).setUp()
        self.sd_name = self.sd_name_pattern % self.storage
        logger.info("Adding iSCSI storage domains needed for tests")
        if not hl_sd.addISCSIDataDomain(
            self.host, self.sd_name, self.dc_name, self.sd_lun,
            self.sd_lun_address, self.sd_lun_target,
            storage_format=self.storage_format, override_luns=True
        ):
            raise exceptions.StorageDomainException(
                "Failed to create iSCSI Storage domain '%s'" % self.sd_name
            )
        logger.info(
            "iSCSI storage domains %s were created successfully", self.sd_name
        )


class TestUpgradeLocal(TestUpgrade):
    """
    Building local data center
    """
    storage_type = config.STORAGE_TYPE_LOCAL

    @classmethod
    def setup_class(cls):
        """ Local file storage setup """
        raise NotImplementedError("Local test hasn't been implemented yet")
        # uncomment it when you implement localfs tests
        # super(TestUpgradeLocal, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """ Local file storage teardown """
        raise NotImplementedError("Local test hasn't been implemented yet")
        # uncomment it when you implement localfs tests
        # super(TestUpgradeLocal, cls).teardown_class()


class TestUpgradePosix(TestUpgrade):
    """
    Building posixfs data center
    """
    storage_type = config.STORAGE_TYPE_POSIX

    @classmethod
    def setup_class(cls):
        """ POSIX file storage setup """
        raise NotImplementedError("Posix test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        # super(TestUpgradePosix, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """ POSIX file storage teardown """
        raise NotImplementedError("Posix test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        # super(TestUpgradePosix, cls).teardown_class()


class TestUpgradeGluster(TestUpgrade):
    """
    Building glusterfs data center
    """
    storage_type = GLUSTER

    def setUp(self):
        """
        Create NFS storage domains for upgrade tests
        """
        super(TestUpgradeGluster, self).setUp()
        self.sd_name = self.sd_name_pattern % self.storage
        logger.info("Adding Gluster storage domains needed for tests")
        logger.info("Address: %s, Path: %s", self.sd_address, self.sd_path)
        if not hl_sd.addGlusterDomain(
            self.host, self.sd_name, self.dc_name,
            self.sd_address, self.sd_path,
            vfs_type=config.ENUMS['vfs_type_glusterfs']
        ):
            raise exceptions.StorageDomainException(
                "Failed to create Gluster Storage domain '%s'" % self.sd_name
            )
        logger.info(
            "Gluster storage domain %s was created successfully", self.sd_name
        )


class TestUpgradeFCP(TestUpgrade):
    """
    Building FCP data center
    """
    storage_type = config.STORAGE_TYPE_FCP

    @classmethod
    def setup_class(cls):
        """ Fiber Channel file storage setup """
        raise NotImplementedError("FCP test hasn't been implemented yet")
        # uncomment it when you implement fcp tests
        # super(TestUpgradeFCP, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """ Fiber Channel file storage setup """
        raise NotImplementedError("FCP test hasn't been implemented yet")
        # uncomment it when you implement fcp tests
        # super(TestUpgradeFCP, cls).teardown_class()


# dict to map storage type to storage class to use
TYPE_TO_CLASS = {
    NFS: TestUpgradeNFS,
    ISCSI: TestUpgradeISCSI,
    config.STORAGE_TYPE_LOCAL: TestUpgradeLocal,
    config.STORAGE_TYPE_FCP: TestUpgradeFCP,
    config.STORAGE_TYPE_POSIX: TestUpgradePosix,
    GLUSTER: TestUpgradeGluster,
}

storage_v3_format = ENUMS['storage_format_version_v3']
for storage_type in config.STORAGE_SELECTOR:
    logger.debug("Generating TestUpgrade for storage type %s", storage_type)
    if storage_type == GLUSTER:
        # TODO: Implement TestUpgradeGluster (3.3 and up)
        continue
    for dc_version in config.DC_VERSIONS:
        dc_version_name = dc_version.replace('.', '')
        for dc_upgrade_version in config.DC_UPGRADE_VERSIONS:
            if dc_version == dc_upgrade_version:
                continue
            dc_upgrade_version_name = dc_upgrade_version.replace('.', '')
            storage_format = None
            if storage_type == ISCSI:
                storage_format = ENUMS['storage_format_version_v2']
            elif storage_type == NFS:
                storage_format = ENUMS['storage_format_version_v1']
            elif storage_type == GLUSTER:
                storage_format = ENUMS['storage_format_version_v1']

            name_pattern = (
                storage_type, dc_version_name, dc_upgrade_version_name
            )
            class_name = "TestUpgrade%s%s%s" % name_pattern
            doc = (
                "Test case upgrades %s Data Center from %s to %s" %
                name_pattern
            )
            class_attrs = {
                '__doc__': doc,
                '__test__': True,
                'dc_name': 'dc_%s_upgrade_%s_%s' % name_pattern,
                'cluster_name': 'cluster_%s_upgrade_%s_%s' % name_pattern,
                'sd_name_pattern': "sd_%s_%%s_%s_%s" % name_pattern,
                'dc_version': dc_version,
                'dc_upgraded_version': dc_upgrade_version,
                'storage_format': storage_format,
                'upgraded_storage_format': storage_v3_format,
                'storages': set([storage_type]),
            }
            new_class = type(
                class_name, (TYPE_TO_CLASS[storage_type],), class_attrs
            )
            setattr(__THIS_MODULE, class_name, new_class)
    delattr(__THIS_MODULE, 'new_class')
