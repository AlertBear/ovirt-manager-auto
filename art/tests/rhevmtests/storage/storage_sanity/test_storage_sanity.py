import config
import logging
import rhevmtests.storage.helpers as storage_helpers
from art.core_api import apis_exceptions
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler import exceptions
from art.unittest_lib import StorageTest as TestCase, attr
from art.rhevm_api.tests_lib.high_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_domains
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level.hosts import (
    getSPMHost, waitForSPM, select_host_as_spm, getAnyNonSPMHost,
)
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

SPM_TIMEOUT = 600
SPM_SLEEP = 5
MIN_UNUSED_LUNS = 2
ISCSI = config.STORAGE_TYPE_ISCSI
ENUMS = config.ENUMS


def setup_module():
    """
    Creates datacenter, adds hosts, clusters, and storage domains depending
    on config file
    """
    storage_helpers.storage_cleanup()


@attr(tier=1)
class TestCase11591(TestCase):
    """
    storage sanity test, create and extend a Data domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = (ISCSI in opts['storages'])
    storages = set([ISCSI])
    polarion_test_case = '11591'

    def setUp(self):
        """
        Creates a storage domain
        """
        if not waitForSPM(config.DATA_CENTER_NAME, SPM_TIMEOUT, SPM_SLEEP):
            raise exceptions.HostException("SPM is not set on the current "
                                           "Data center")
        self.spm_host = getSPMHost(config.HOSTS)

        self.assertTrue(len(config.UNUSED_LUNS) >= MIN_UNUSED_LUNS,
                        "There are less than %s unused LUNs, aborting test"
                        % MIN_UNUSED_LUNS)
        self.sd_name = "{0}_{1}".format(self.polarion_test_case,
                                        "iSCSI_Domain")
        logger.info("The unused LUNs found are: '%s'", config.UNUSED_LUNS)
        status_attach_and_activate = storagedomains.addISCSIDataDomain(
            self.spm_host, self.sd_name,
            config.DATA_CENTER_NAME, config.UNUSED_LUNS["lun_list"][0],
            config.UNUSED_LUNS["lun_addresses"][0],
            config.UNUSED_LUNS["lun_targets"][0], override_luns=True
        )
        self.assertTrue(status_attach_and_activate,
                        "The domain was not added and activated "
                        "successfully")
        wait_for_jobs([ENUMS['job_activate_storage_domain']])
        assert ll_st_domains.wait_for_storage_domain_available_size(
            config.DATA_CENTER_NAME, self.sd_name,
        )
        self.domain_size = ll_st_domains.get_total_size(self.sd_name)
        logger.info("Total size for domain '%s' is '%s'", self.sd_name,
                    self.domain_size)

    def tearDown(self):
        """
        Removes storage domain created with setUp
        """
        logger.info("Waiting for tasks before deactivating/removing the "
                    "storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        logger.info("Removing Storage domain '%s'", self.sd_name)
        self.assertTrue(ll_st_domains.removeStorageDomains(True, self.sd_name,
                                                           self.spm_host),
                        "Failed to remove domain '%s'" % self.sd_name)
        wait_for_jobs([ENUMS['job_remove_storage_domain']])

    @polarion("RHEVM3-11591")
    def test_create_and_extend_storage_domain(self):
        """
        Creates and extends a storage domain
        """
        extend_lun = {
            "lun_list": [config.UNUSED_LUNS["lun_list"][1]],
            "lun_addresses": [config.UNUSED_LUNS["lun_addresses"][1]],
            "lun_targets": [config.UNUSED_LUNS["lun_targets"][1]],
            "override_luns": True
        }
        logger.info("Extending storage domain %s", self.sd_name)
        storagedomains.extend_storage_domain(self.sd_name, self.storage,
                                             self.spm_host, **extend_lun)
        ll_st_domains.wait_for_change_total_size(self.sd_name,
                                                 self.domain_size)
        extended_sd_size = ll_st_domains.get_total_size(self.sd_name)
        logger.info("Total size for domain '%s' is '%s'", self.sd_name,
                    extended_sd_size)
        self.assertTrue(extended_sd_size > self.domain_size,
                        "The extended storage domain size hasn't increased")


@attr(tier=2)
class TestCase11592(TestCase):
    """
    Storage sanity test, changing domain status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11592'
    sd_name = None

    def setUp(self):
        """
        Creates a storage domain
        """
        if not waitForSPM(config.DATA_CENTER_NAME, SPM_TIMEOUT, SPM_SLEEP):
            raise exceptions.HostException("SPM is not set on the current "
                                           "Data center")
        self.spm_host = getSPMHost(config.HOSTS)

        if self.storage in config.BLOCK_TYPES:
            if not len(config.UNUSED_LUNS) >= 1:
                raise exceptions.StorageDomainException(
                    "There are no unused LUNs, aborting test"
                )
            self.sd_name = "{0}_{1}".format(self.polarion_test_case,
                                            "iSCSI_Domain")
            status_attach_and_activate = storagedomains.addISCSIDataDomain(
                self.spm_host,
                self.sd_name,
                config.DATA_CENTER_NAME,
                config.UNUSED_LUNS["lun_list"][0],
                config.UNUSED_LUNS["lun_addresses"][0],
                config.UNUSED_LUNS["lun_targets"][0],
                override_luns=True
            )
            if not status_attach_and_activate:
                raise exceptions.StorageDomainException(
                    "Creating iSCSI domain '%s' failed" % self.sd_name
                )
        elif self.storage == config.STORAGE_TYPE_NFS:
            self.sd_name = "{0}_{1}".format(self.polarion_test_case,
                                            "NFS_Domain")
            self.nfs_address = config.UNUSED_DATA_DOMAIN_ADDRESSES[0]
            self.nfs_path = config.UNUSED_DATA_DOMAIN_PATHS[0]
            status = storagedomains.addNFSDomain(
                host=self.spm_host,
                storage=self.sd_name,
                data_center=config.DATA_CENTER_NAME,
                address=self.nfs_address,
                path=self.nfs_path,
                format=True
            )
            if not status:
                raise exceptions.StorageDomainException(
                    "Creating NFS domain '%s' failed" % self.sd_name
                )
        elif self.storage == config.STORAGE_TYPE_GLUSTER:
            self.sd_name = "{0}_{1}".format(self.polarion_test_case,
                                            "Gluster_Domain")
            self.gluster_address = \
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0]
            self.gluster_path = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0]
            status = storagedomains.addGlusterDomain(
                host=self.spm_host,
                name=self.sd_name,
                data_center=config.DATA_CENTER_NAME,
                address=self.gluster_address,
                path=self.gluster_path,
                vfs_type=config.ENUMS['vfs_type_glusterfs']
            )
            if not status:
                raise exceptions.StorageDomainException(
                    "Creating Gluster domain '%s' failed" % self.sd_name
                )
        wait_for_jobs([ENUMS['job_activate_storage_domain']])

    def tearDown(self):
        """
        Removes storage domain created with setUp
        """
        if self.sd_name is not None:
            logger.info("Waiting for tasks before deactivating/removing the "
                        "storage domain")
            wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                           config.DATA_CENTER_NAME)
            logger.info("Removing Storage domain '%s'", self.sd_name)
            try:
                status = ll_st_domains.removeStorageDomains(True, self.sd_name,
                                                            self.spm_host)
                if not status:
                    raise exceptions.StorageDomainException(
                        "Failed to remove domain '%s'" % self.sd_name
                    )
            except apis_exceptions.EntityNotFound:
                logger.info("Storage domain '%s' wasn't added successfully, "
                            "nothing to remove", self.sd_name)

    @polarion("RHEVM3-11592")
    def test_change_domain_status_test(self):
        """
        Test checks if attaching/detaching storage domains works properly,
        including ensuring that it is impossible to detach an active domain
        """
        logger.info("Attempt to detach an active domain - this should fail")
        self.assertTrue(
            ll_st_domains.detachStorageDomain(
                False, config.DATA_CENTER_NAME, self.sd_name
            ),
            "Detaching non-master active domain '%s' worked" % self.sd_name
        )

        logger.info("Waiting for tasks before deactivating the storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        logger.info("De-activate non-master data domain")
        self.assertTrue(
            ll_st_domains.deactivateStorageDomain(
                True, config.DATA_CENTER_NAME, self.sd_name
            ),
            "De-activating non-master domain '%s' failed" % self.sd_name
        )

        logger.info("Re-activate non-master data domain")
        self.assertTrue(
            ll_st_domains.activateStorageDomain(
                True, config.DATA_CENTER_NAME, self.sd_name
            ),
            "Activating non-master data domain '%s' failed" % self.sd_name
        )

        logger.info("Waiting for tasks before deactivating the storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        logger.info("Deactivating non-master data domain")
        self.assertTrue(
            ll_st_domains.deactivateStorageDomain(
                True, config.DATA_CENTER_NAME, self.sd_name
            ),
            "De-activating non-master domain '%s' failed" % self.sd_name
        )

        logger.info("Detaching non-master data domain")
        self.assertTrue(
            ll_st_domains.detachStorageDomain(
                True, config.DATA_CENTER_NAME, self.sd_name
            ),
            "Detaching non-master domain '%s' failed" % self.sd_name
        )

        # In local DC, once a domain is detached it is removed completely
        # so it cannot be reattached - only run this part of the test
        # for non-local DCs
        if not config.LOCAL:
            logger.info("Attaching non-master data domain")
            self.assertTrue(
                ll_st_domains.attachStorageDomain(
                    True, config.DATA_CENTER_NAME, self.sd_name
                ),
                "Attaching non-master data domain '%s' failed" % self.sd_name
            )

            logger.info("Activating non-master data domain")
            self.assertTrue(
                ll_st_domains.activateStorageDomain(
                    True, config.DATA_CENTER_NAME, self.sd_name
                ),
                "Activating non-master data domain '%s' failed" % self.sd_name
            )


@attr(tier=2)
class TestCase11593(TestCase):
    """
    storage sanity test, changing master domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11593'

    @polarion("RHEVM3-11593")
    def test_change_master_domain_test(self):
        """ test checks if changing master domain works correctly
        """
        found, master_domain = ll_st_domains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        self.assertTrue(found, "Master domain not found!")

        old_master_domain_name = master_domain['masterDomain']

        logger.info("Deactivating master domain")
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        self.assertTrue(
            ll_st_domains.deactivateStorageDomain(
                True, config.DATA_CENTER_NAME, old_master_domain_name),
            "Cannot deactivate master domain")

        logger.info("Finding new master domain")
        found, new_master = ll_st_domains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        logger.info("New master: %s" % new_master)
        self.assertTrue(found, "New master domain not found")

        logger.info("Activating old master domain")
        self.assertTrue(
            ll_st_domains.activateStorageDomain(
                True, config.DATA_CENTER_NAME, old_master_domain_name),
            "Cannot activate old master domain")


@attr(tier=1)
class TestCase5830(TestCase):
    """
    Polarion Test Case 5830 - Manually Re-assign SPM
    """
    __test__ = True
    polarion_test_case = '5830'
    original_spm_host = None

    def setUp(self):
        logger.info("Waiting for SPM host to be elected on current Data "
                    "center")
        if not waitForSPM(config.DATA_CENTER_NAME, SPM_TIMEOUT, SPM_SLEEP):
            raise exceptions.HostException("SPM is not set on the current "
                                           "Data center")

        logger.info("Getting current SPM host and HSM host")
        self.original_spm_host = getSPMHost(config.HOSTS)
        self.hsm_host = getAnyNonSPMHost(
            config.HOSTS, config.HOST_UP
        )[1]['hsmHost']
        if not self.original_spm_host:
            raise exceptions.HostException("Current SPM host could not be "
                                           "retrieved")
        if not self.hsm_host:
            raise exceptions.HostException("Did not find HSM host")
        logger.info("Found SPM host: '%s', HSM host: '%s",
                    self.original_spm_host, self.hsm_host)

    def tearDown(self):
        if self.original_spm_host:
            logger.info("Waiting for SPM host to be elected")
            if not waitForSPM(config.DATA_CENTER_NAME, SPM_TIMEOUT, SPM_SLEEP):
                raise exceptions.HostException("SPM is not set on the current "
                                               "Data center")
            logger.info("Setting the original SPM host '%s' back as SPM",
                        self.original_spm_host)
            wait_for_tasks(
                config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
            )
            if not select_host_as_spm(True, self.original_spm_host,
                                      config.DATA_CENTER_NAME):
                raise exceptions.HostException("Did not successfully revert "
                                               "the SPM to host '%s'" %
                                               self.original_spm_host)

    @polarion("RHEVM3-5830")
    def test_reassign_spm(self):
        """
        Assign first HSM host to be the SPM
        """
        self.new_spm_host = self.hsm_host
        logger.info("Selecting HSM host '%s' as SPM", self.new_spm_host)
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        self.assertTrue(select_host_as_spm(True, self.new_spm_host,
                                           config.DATA_CENTER_NAME),
                        "Unable to set host '%s' as SPM" % self.new_spm_host)
