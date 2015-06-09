import config
import helpers
import logging

from art.unittest_lib import attr

from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_st
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)
ENUMS = helpers.ENUMS
NFS = config.STORAGE_TYPE_NFS


@attr(tier=1)
class TestCase232975(helpers.TestCaseNFSOptions):
    """
    Imports existing storage domain with custom advanced NFS options.

    https://tcms.engineering.redhat.com/case/232975/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    tcms_plan_id = '5849'
    tcms_test_case = '232975'
    export_domain = 'test_%s_export' % tcms_test_case
    iso_domain = 'test_%s_iso' % tcms_test_case
    datacenter = config.DATA_CENTER_NAME
    nfs_version = 'v3'
    nfs_timeout = 60
    nfs_retrans = 1
    export_address = config.NFS_ADDRESSES[0]
    export_path = config.NFS_PATHS[0]

    def setUp(self):
        """ Creates storage domains which will be later imported

        Don't change to setup_class, as in case setup_class fails,
        teardown_class wouldn't be called (and all later tests will fail)!
        """
        sd_type = ENUMS['storage_dom_type_export']

        hl_st.create_nfs_domain_with_options(
            self.export_domain, sd_type, self.host, self.export_address,
            self.export_path, datacenter=self.datacenter)

        hl_st.remove_storage_domain(
            self.export_domain, self.datacenter, self.host, False, config.VDC,
            config.VDC_PASSWORD)
        self.sds_for_cleanup.append(self.export_domain)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_import_existing_export_domain(self):
        """ Imports existing export storage domain with custom NFS options
        """
        sd_type = ENUMS['storage_dom_type_export']
        ll_st.importStorageDomain(
            True, sd_type, NFS, self.export_address,
            self.export_path, self.host, self.nfs_version, self.nfs_retrans,
            self.nfs_timeout)
        result = ll_st.get_options_of_resource(
            self.host_ip, self.password, self.export_address, self.export_path)
        if result is None:
            self.fail("Resource %s:%s is not mounted on %s!" % (
                self.export_address, self.export_path, self.host))
        timeo, retrans, nfsvers, sync = result
        result = helpers.verify_nfs_options(
            self.nfs_timeout, self.nfs_retrans, self.nfs_version,
            timeo, retrans, nfsvers)
        if result is not None:
            self.fail("NFS option %s not as expected %s, real %s" % result)


@attr(tier=1)
class TestCase148670(helpers.TestCaseNFSOptions):
    """
    Negative test - tests if passed values are correctly validated.

    https://tcms.engineering.redhat.com/case/148670/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    tcms_plan_id = '5849'
    tcms_test_case = '148670'
    nfs_address = config.NFS_ADDRESSES[0]
    nfs_path = config.NFS_PATHS[0]

    def setUp(self):
        self.name = None

    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_nfs_storage_with_out_of_range_retransmissions(self):
        """ Tries to create an NFS storage domain with an out of range
        retransmission number
        """
        self.name = 'test_%s_oor_retrans' % self.tcms_test_case
        nfs_retrans = 65536 * 2 + 5
        nfs_timeout = 730
        nfs_version = 'v3'
        logger.info("Creating nfs domain %s" % self.name)
        hl_st.create_nfs_domain_with_options(
            self.name, ENUMS['storage_dom_type_data'], self.host,
            self.nfs_address, self.nfs_path, retrans=nfs_retrans,
            version=nfs_version, timeo=nfs_timeout, positive=False)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_nfs_storage_with_out_of_range_timeout(self):
        """ Tries to create an NFS storage domain with an out of range
        NFS timeout
        """
        self.name = 'test_%s_oor_timeout' % self.tcms_test_case
        nfs_retrans = 7
        nfs_timeout = 65536 * 2 + 5
        nfs_version = 'v3'
        logger.info("Creating nfs domain %s" % self.name)
        hl_st.create_nfs_domain_with_options(
            self.name, ENUMS['storage_dom_type_data'], self.host,
            self.nfs_address, self.nfs_path, retrans=nfs_retrans,
            version=nfs_version, timeo=nfs_timeout, positive=False)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_nfs_storage_with_incorrect_nfs_version(self):
        """ Tries to create an NFS storage domain with a random string
        passed as an NFS version
        """
        self.name = 'test_%s_incorrect_ver' % self.tcms_test_case
        nfs_retrans = 7
        nfs_timeout = 1000
        nfs_version = 'v7'
        logger.info("Creating nfs domain %s" % self.name)
        hl_st.create_nfs_domain_with_options(
            self.name, ENUMS['storage_dom_type_data'], self.host,
            self.nfs_address, self.nfs_path, retrans=nfs_retrans,
            version=nfs_version, timeo=nfs_timeout, positive=False)

    def tearDown(self):
        storage_domains = helpers.STORAGE_DOMAIN_API.get(absLink=False)
        if self.name in [x.name for x in storage_domains]:
            hl_st.remove_storage_domain(
                self.name, None, self.host, True, config.VDC,
                config.VDC_PASSWORD)


@attr(tier=0)
class TestCase148641(helpers.TestCaseNFSOptions):
    """
    Creates NFS data storage domain without specifying advanced NFS options and
    checks that the default values were used. Also checks that the NFS versions
    used is the highest possible.

    https://tcms.engineering.redhat.com/case/148641/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    tcms_plan_id = '5849'
    tcms_test_case = '148641'

    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_nfs_storage_with_default_options(self):
        """ Creates storage domains with default options and checks if they are
        correct.
        """
        version = 'v3'  # TODO: fix it! it should depend on the host os version
        self.name = 'test_%s' % self.tcms_test_case
        storage = helpers.NFSStorage(
            name=self.name, address=config.NFS_ADDRESSES[0],
            path=config.NFS_PATHS[0], timeout_to_set=None,
            retrans_to_set=None, vers_to_set=None,
            expected_timeout=helpers.DEFAULT_NFS_TIMEOUT,
            expected_retrans=helpers.DEFAULT_NFS_RETRANS,
            expected_vers=version
        )
        wait_for_jobs()
        self.create_nfs_domain_and_verify_options([storage])
        self.sds_for_cleanup.append(self.name)


@attr(tier=1)
class TestCase153290(helpers.TestCaseNFSOptions):
    """
    Creates ISO and export storage domains with custom advanced NFS options
    and verifies they were really used.

    https://tcms.engineering.redhat.com/case/153290/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    tcms_plan_id = '5849'
    tcms_test_case = '153290'
    nfs_retrans = 7
    nfs_timeout = 740
    nfs_version = 'v3'

    def _create_and_check(self, sd_type, suffix, idx):
        """ Creates NFS storage domain of specified type. Suffix - suffix of
        domain name.
        """
        self.name = 'test_%s_%s' % (self.tcms_test_case, suffix)
        storage = helpers.NFSStorage(
            name=self.name, sd_type=sd_type, address=config.NFS_ADDRESSES[idx],
            path=config.NFS_PATHS[idx], timeout_to_set=self.nfs_timeout,
            retrans_to_set=self.nfs_retrans, vers_to_set=self.nfs_version,
            expected_timeout=self.nfs_timeout,
            expected_retrans=self.nfs_retrans, expected_vers=self.nfs_version)
        self.create_nfs_domain_and_verify_options([storage])
        self.sds_for_cleanup.append(self.name)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_change_nfs_options_export(self):
        """ Creates export storage domain with advanced NFS options and checks
        that they were really used.
        """
        self._create_and_check(ENUMS['storage_dom_type_export'], 'export', 0)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_change_nfs_options_iso(self):
        """ Creates ISO storage domain with advanced NFS options and checks
        that they were really used.
        """
        self._create_and_check(ENUMS['storage_dom_type_iso'], 'iso', 1)


@attr(tier=1)
class TestCase153368(helpers.TestCaseNFSOptions):
    """
    Creates multiple storage domains with different custom advanced NFS options
    and checks that all of them have the correct values.

    https://tcms.engineering.redhat.com/case/153368/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    tcms_plan_id = '5849'
    tcms_test_case = '153368'

    @tcms(tcms_plan_id, tcms_test_case)
    def test_multiple_storage_domains(self):
        """
        creates multiple storage domains with different advanced NFS options
        and checks they are correct
        """
        self.name_prefix = 'test_%s_' % self.tcms_test_case
        nfs_resources = []
        for i in range(len(config.NFS_ADDRESSES)):
            if i:
                timeout, retrans = 100 * i + 650, 6 + i
                exp_timeout, exp_retrans = 100 * i + 650, 6 + i
            else:
                timeout, retrans = None, None
                exp_timeout = helpers.DEFAULT_NFS_TIMEOUT
                exp_retrans = helpers.DEFAULT_NFS_RETRANS
            name = self.name_prefix + str(i)
            self.sds_for_cleanup.append(name)
            kwargs = {"name": name,
                      "address": config.NFS_ADDRESSES[i],
                      "path": config.NFS_PATHS[i], "timeout_to_set": timeout,
                      "retrans_to_set": retrans, "vers_to_set": 'v3',
                      "expected_timeout": exp_timeout,
                      "expected_retrans": exp_retrans, "expected_vers": 'v3'}
            nfs_resources.append(helpers.NFSStorage(**kwargs))

        self.create_nfs_domain_and_verify_options(nfs_resources)


@attr(tier=1)
class TestCase166534(helpers.TestCaseNFSOptions):
    """
    Test steps:
    * creates an export NFS storage domain with custom advanced NFS options
      and attaches it to a storage domain
    * checks that it is mounted with options specified by the user
    * detaches and removes this storage domain
    * import the removed storage domain without specifying advanced NFS options
    * checks that this time the storage domain was mounted with default options

    https://tcms.engineering.redhat.com/case/166534/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    tcms_plan_id = '5849'
    tcms_test_case = '166534'
    nfs_retrans = 7
    nfs_timeout = 760
    nfs_version = 'v3'

    @tcms(tcms_plan_id, tcms_test_case)
    def test_import_storage_domain_created_with_nfs_options(self):
        """ Checks that importing storage domain which was created with custom
        advanced NFS options by default use default NFS options, not the ones
        defined when creating the storage domain.
        """
        self.name = 'test_%s_create' % self.tcms_test_case
        address = config.NFS_ADDRESSES[0]
        path = config.NFS_PATHS[0]
        datacenter = config.DATA_CENTER_NAME
        sd_type = ENUMS['storage_dom_type_export']

        storage = helpers.NFSStorage(
            name=self.name, address=address, path=path,
            timeout_to_set=self.nfs_timeout, retrans_to_set=self.nfs_retrans,
            vers_to_set=self.nfs_version, expected_timeout=self.nfs_timeout,
            expected_retrans=self.nfs_retrans, expected_vers=self.nfs_version,
            sd_type=ENUMS['storage_dom_type_export'])
        self.create_nfs_domain_and_verify_options([storage])
        self.sds_for_cleanup.append(self.name)

        hl_st.remove_storage_domain(
            self.name, datacenter, self.host, False, config.VDC,
            config.VDC_PASSWORD)

        logger.info("Importing storage domain")
        ll_st.importStorageDomain(
            True, sd_type, NFS, address, path, self.host)
        logger.info("Attaching storage domain")
        ll_st.attachStorageDomain(True, datacenter, self.name)

        logger.info("Getting mount options")
        options = ll_st.get_options_of_resource(
            self.host_ip, self.password, address, path)
        if options is None:
            self.fail("Storage domain is not mounted!")
        (timeo, retrans, vers, sync) = options
        logger.info("Verifying mount options")
        result = helpers.verify_nfs_options(
            helpers.DEFAULT_NFS_TIMEOUT, helpers.DEFAULT_NFS_RETRANS, 'v3',
            timeo, retrans, vers)
        if result is not None:
            self.fail("Wrong NFS option %s, expected: %s, real: %s" % result)
        logger.info("Test passed")


@attr(tier=1)
class TestCase166616(helpers.TestCaseNFSOptions):
    """
    Test checks that removing and destroying NFS storage domain with custom
    advanced NFS options work correctly and that adding again storage domain
    created with advanced NFS options doesn't preserve these options.

    https://tcms.engineering.redhat.com/case/166616/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = (NFS in opts['storages'])
    tcms_plan_id = '5849'
    tcms_test_case = '166616'
    nfs_retrans = 7
    nfs_timeout = 770
    nfs_version = 'v3'

    @tcms(tcms_plan_id, tcms_test_case)
    def test_remove_and_add_again_storage_domain_with_nfs_options(self):
        """ Test steps:
        * creates storage domain with custom advanced options
        * removes it from dc without formatting the disk
        * creates the same storage domain again
        * destroys it
        * creates once again with default advanced options
        """
        address = config.NFS_ADDRESSES[0]
        path = config.NFS_PATHS[0]
        datacenter = config.DATA_CENTER_NAME
        self.name = 'test_%s_custom' % self.tcms_test_case
        self.sds_for_cleanup.append(self.name)

        logger.info("Creating first time with custom options")
        storage = helpers.NFSStorage(
            name=self.name, address=address, path=path,
            timeout_to_set=self.nfs_timeout, retrans_to_set=self.nfs_retrans,
            vers_to_set=self.nfs_version, expected_timeout=self.nfs_timeout,
            expected_retrans=self.nfs_retrans, expected_vers=self.nfs_version,
            sd_type=ENUMS['storage_dom_type_export'])
        self.create_nfs_domain_and_verify_options([storage])

        logger.info("Removing created storage domain")
        hl_st.remove_storage_domain(
            self.name, datacenter, self.host, False, config.VDC,
            config.VDC_PASSWORD)

        logger.info("Creating second time with custom options")
        storage = helpers.NFSStorage(
            name=self.name, address=address, path=path,
            timeout_to_set=self.nfs_timeout, retrans_to_set=self.nfs_retrans,
            vers_to_set=self.nfs_version, expected_timeout=self.nfs_timeout,
            expected_retrans=self.nfs_retrans, expected_vers=self.nfs_version,
            sd_type=ENUMS['storage_dom_type_export'])
        self.create_nfs_domain_and_verify_options([storage])

        logger.info("Destroying storage domain")
        hl_st.remove_storage_domain(
            self.name, datacenter, self.host, True, config.VDC,
            config.VDC_PASSWORD)

        logger.info("Creating third time with default options")
        self.name = 'test_%s_default' % self.tcms_test_case
        storage = helpers.NFSStorage(
            name=self.name, address=address, path=path, timeout_to_set=None,
            retrans_to_set=None, vers_to_set=None,
            expected_timeout=helpers.DEFAULT_NFS_TIMEOUT,
            expected_retrans=helpers.DEFAULT_NFS_RETRANS, expected_vers='v3',
            sd_type=ENUMS['storage_dom_type_export'])
        self.sds_for_cleanup.append(self.name)
        self.create_nfs_domain_and_verify_options([storage])
