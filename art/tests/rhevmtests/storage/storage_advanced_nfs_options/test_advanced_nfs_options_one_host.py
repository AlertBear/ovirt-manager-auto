import logging
import pytest
import config
import helpers
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler.settings import opts
from art.test_handler.tools import bz, polarion
from art.unittest_lib import attr
from art.unittest_lib.common import testflow
from fixtures import (
    initializer_class, create_and_remove_sd
)
from rhevmtests.storage.fixtures import (
    remove_storage_domain
)

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
EXPORT = config.EXPORT_TYPE
NFS = config.STORAGE_TYPE_NFS
DC_NAME = config.DATA_CENTER_NAME


@pytest.fixture(scope='module', autouse=True)
def detach_export_domain(request):
    """
    Detach export storage domain
    """
    def finalizer():
        testflow.teardown(
            "Attaching and activating storage domain %s",
            config.EXPORT_DOMAIN_NAME
        )
        assert hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME
        ), (
            "Failed to attach and activate export domain %s" %
            config.EXPORT_DOMAIN_NAME
        )
    request.addfinalizer(finalizer)
    import rhevmtests.helpers as rhevm_helpers
    rhevm_helpers.storage_cleanup()
    testflow.setup(
        "Detaching export storage domain %s", config.EXPORT_DOMAIN_NAME
    )
    wait_for_tasks(
        config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
    )
    assert hl_sd.detach_and_deactivate_domain(
        config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME
    ), ("Failed to deactivate and detach export storage domain %s",
        config.EXPORT_DOMAIN_NAME)


@attr(tier=2)
@pytest.mark.usefixtures(
    initializer_class.__name__,
    create_and_remove_sd.__name__,
)
class TestCase4816(helpers.TestCaseNFSOptions):
    """
    Imports existing storage domain with custom advanced NFS options.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    polarion_test_case = "4816"
    export_domain = 'test_%s_export' % polarion_test_case
    iso_domain = 'test_%s_iso' % polarion_test_case
    nfs_version = 'v3'
    nfs_timeout = 60
    nfs_retrans = 1
    export_address = config.NFS_ADDRESSES[0]
    export_path = config.NFS_PATHS[0]

    @polarion("RHEVM3-4816")
    def test_import_existing_export_domain(self):
        """
        Imports existing export storage domain with custom NFS options
        """
        ll_sd.importStorageDomain(
            True, EXPORT, NFS, self.export_address,
            self.export_path, self.host, self.nfs_version, self.nfs_retrans,
            self.nfs_timeout
        )
        result = ll_sd.get_options_of_resource(
            self.host_ip, self.password, self.export_address, self.export_path)
        if result is None:
            self.fail("Resource %s:%s is not mounted on %s!" %
                      (self.export_address, self.export_path, self.host))
        timeo, retrans, nfsvers, sync = result
        result = helpers.verify_nfs_options(
            self.nfs_timeout, self.nfs_retrans, self.nfs_version,
            timeo, retrans, nfsvers
        )
        if result is not None:
            self.fail("NFS option %s not as expected %s, real %s" % result)


@attr(tier=2)
@pytest.mark.usefixtures(
    initializer_class.__name__,
    remove_storage_domain.__name__,
)
@bz({'1373581': {}})
class TestCase4829(helpers.TestCaseNFSOptions):
    """
    Negative test - tests if passed values are correctly validated.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    polarion_test_case = "4829"
    nfs_address = config.NFS_ADDRESSES[0]
    nfs_path = config.NFS_PATHS[0]

    @polarion("RHEVM3-4829")
    def test_create_nfs_storage_with_out_of_range_retransmissions(self):
        """
        Tries to create an NFS storage domain with an out of range
        retransmission number
        """
        self.storage_domain = 'test_%s_oor_retrans' % self.polarion_test_case
        nfs_retrans = 65536 * 2 + 5
        nfs_timeout = 730
        nfs_version = 'v3'
        logger.info("Creating nfs domain %s" % self.storage_domain)
        hl_sd.create_nfs_domain_with_options(
            name=self.storage_domain, sd_type=config.TYPE_DATA, host=self.host,
            address=self.nfs_address, path=self.nfs_path, retrans=nfs_retrans,
            version=nfs_version, timeo=nfs_timeout, positive=False
        )

    @polarion("RHEVM3-4829")
    def test_create_nfs_storage_with_out_of_range_timeout(self):
        """
        Tries to create an NFS storage domain with an out of range
        NFS timeout
        """
        self.storage_domain = 'test_%s_oor_timeout' % self.polarion_test_case
        nfs_retrans = 7
        nfs_timeout = 65536 * 2 + 5
        nfs_version = 'v3'
        logger.info("Creating nfs domain %s" % self.storage_domain)
        hl_sd.create_nfs_domain_with_options(
            self.storage_domain, config.TYPE_DATA, self.host,
            self.nfs_address, self.nfs_path, retrans=nfs_retrans,
            version=nfs_version, timeo=nfs_timeout, positive=False
        )

    @polarion("RHEVM3-4829")
    def test_create_nfs_storage_with_incorrect_nfs_version(self):
        """
        Tries to create an NFS storage domain with a random string
        passed as an NFS version
        """
        self.storage_domain = 'test_%s_incorrect_ver' % self.polarion_test_case
        nfs_retrans = 7
        nfs_timeout = 1000
        nfs_version = 'v7'
        logger.info("Creating nfs domain %s" % self.storage_domain)
        hl_sd.create_nfs_domain_with_options(
            self.storage_domain, config.TYPE_DATA, self.host,
            self.nfs_address, self.nfs_path, retrans=nfs_retrans,
            version=nfs_version, timeo=nfs_timeout, positive=False
        )


@attr(tier=2)
@pytest.mark.usefixtures(initializer_class.__name__,)
class TestCase4826(helpers.TestCaseNFSOptions):
    """
    Creates NFS data storage domain without specifying advanced NFS options and
    checks that the default values were used. Also checks that the NFS versions
    used is the highest possible.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    polarion_test_case = '4826'

    @polarion("RHEVM3-4826")
    def test_create_nfs_storage_with_default_options(self):
        """
        Creates storage domains with default options and checks if they are
        correct.
        """
        version = 'v3'  # TODO: fix this, should depend on the host OS version
        self.storage_domain = 'test_%s' % self.polarion_test_case
        storage = helpers.NFSStorage(
            name=self.storage_domain, address=config.NFS_ADDRESSES[0],
            path=config.NFS_PATHS[0], timeout_to_set=None,
            retrans_to_set=None, vers_to_set=None,
            expected_timeout=helpers.DEFAULT_NFS_TIMEOUT,
            expected_retrans=helpers.DEFAULT_NFS_RETRANS,
            expected_vers=version
        )
        self.create_nfs_domain_and_verify_options([storage])
        self.sds_for_cleanup.append(self.storage_domain)


@attr(tier=2)
@pytest.mark.usefixtures(
    detach_export_domain.__name__,
    initializer_class.__name__,
)
class TestCase4830(helpers.TestCaseNFSOptions):
    """
    Creates ISO and export storage domains with custom advanced NFS options
    and verifies they were really used.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    polarion_test_case = '4830'
    nfs_retrans = 7
    nfs_timeout = 600
    nfs_version = 'v3'

    def _create_and_check(self, sd_type, suffix, idx):
        """
        Creates NFS storage domain of specified type. Suffix - suffix of
        domain name.
        """
        self.storage_domain = 'test_%s_%s' % (self.polarion_test_case, suffix)
        storage = helpers.NFSStorage(
            name=self.storage_domain, sd_type=sd_type,
            address=config.NFS_ADDRESSES[idx], path=config.NFS_PATHS[idx],
            timeout_to_set=self.nfs_timeout, retrans_to_set=self.nfs_retrans,
            vers_to_set=self.nfs_version, expected_timeout=self.nfs_timeout,
            expected_retrans=self.nfs_retrans, expected_vers=self.nfs_version
        )
        self.sds_for_cleanup.append(self.storage_domain)
        self.create_nfs_domain_and_verify_options([storage])

    @polarion("RHEVM3-4830")
    def test_create_change_nfs_options_export(self):
        """
        Creates export storage domain with advanced NFS options and checks
        that they were really used.
        """
        self._create_and_check(EXPORT, 'export', 0)

    @polarion("RHEVM3-4830")
    def test_create_change_nfs_options_iso(self):
        """
        Creates ISO storage domain with advanced NFS options and checks
        that they were really used.
        """
        self._create_and_check(ENUMS['storage_dom_type_iso'], 'iso', 1)


@attr(tier=2)
@pytest.mark.usefixtures(initializer_class.__name__,)
class TestCase4822(helpers.TestCaseNFSOptions):
    """
    Creates multiple storage domains with different custom advanced NFS options
    and checks that all of them have the correct values.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    polarion_test_case = '4822'

    @polarion("RHEVM3-4822")
    def test_multiple_storage_domains(self):
        """
        creates multiple storage domains with different advanced NFS options
        and checks they are correct
        """
        self.name_prefix = 'test_%s_' % self.polarion_test_case
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


@attr(tier=2)
@pytest.mark.usefixtures(
    detach_export_domain.__name__,
    initializer_class.__name__,
)
class TestCase4821(helpers.TestCaseNFSOptions):
    """
    Test steps:
    * creates an export NFS storage domain with custom advanced NFS options
      and attaches it to a storage domain
    * checks that it is mounted with options specified by the user
    * detaches and removes this storage domain
    * import the removed storage domain without specifying advanced NFS options
    * checks that this time the storage domain was mounted with default options

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    polarion_test_case = '4821'
    nfs_retrans = 7
    nfs_timeout = 760
    nfs_version = 'v3'

    @polarion("RHEVM3-4821")
    def test_import_storage_domain_created_with_nfs_options(self):
        """
        Checks that importing storage domain which was created with custom
        advanced NFS options by default use default NFS options, not the ones
        defined when creating the storage domain.
        """
        self.name = 'test_%s_create' % self.polarion_test_case
        address = config.NFS_ADDRESSES[0]
        path = config.NFS_PATHS[0]

        storage = helpers.NFSStorage(
            name=self.name, address=address, path=path,
            timeout_to_set=self.nfs_timeout, retrans_to_set=self.nfs_retrans,
            vers_to_set=self.nfs_version, expected_timeout=self.nfs_timeout,
            expected_retrans=self.nfs_retrans, expected_vers=self.nfs_version,
            sd_type=EXPORT
        )
        self.create_nfs_domain_and_verify_options([storage])
        self.sds_for_cleanup.append(self.name)

        hl_sd.remove_storage_domain(
            self.name, DC_NAME, self.host, False, config.VDC,
            config.VDC_PASSWORD
        )

        logger.info("Importing storage domain")
        ll_sd.importStorageDomain(
            True, EXPORT, NFS, address, path, self.host
        )
        logger.info("Attaching storage domain")
        ll_sd.attachStorageDomain(True, DC_NAME, self.name)

        logger.info("Getting mount options")
        options = ll_sd.get_options_of_resource(
            self.host_ip, self.password, address, path)
        if options is None:
            self.fail("Storage domain is not mounted!")
        (timeo, retrans, vers, sync) = options
        logger.info("Verifying mount options")
        result = helpers.verify_nfs_options(
            helpers.DEFAULT_NFS_TIMEOUT, helpers.DEFAULT_NFS_RETRANS, 'v3',
            timeo, retrans, vers
        )
        if result is not None:
            self.fail("Wrong NFS option %s, expected: %s, real: %s" % result)
        logger.info("Test passed")


@attr(tier=2)
@pytest.mark.usefixtures(initializer_class.__name__,)
@bz({'1373581': {}})
class TestCase4815(helpers.TestCaseNFSOptions):
    """
    Ensure that incorrect and conflicting parameters for creating a storage
    domain are blocked

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    sd_name = 'storage_domain_%s'

    polarion_test_case = '4815'

    sds_params = list()
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'vers=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'nfsvers=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'protocol_version=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'vfs_type=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'retrans=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'timeo=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 'A',
        'nfs_timeout': 10,
        'mount_options': None,
    })

    @polarion("RHEVM3-4815")
    def test_create_sd_with_defined_values(self):
        """
        test check if bad and conflict parameters for creating storage
        domain are blocked
        """
        for index, sd_params in enumerate(self.sds_params):
            logger.info(
                "creating storage domain with values: "
                "retrans = %s, timeout = %d, vers = %s, mount_optiones = %s",
                sd_params['nfs_retrans'], sd_params['nfs_timeout'],
                sd_params['nfs_version'], sd_params['mount_options']
            )
            storage_domain_name = self.sd_name % index

            storage = ll_sd.NFSStorage(
                name=storage_domain_name,
                address=config.NFS_ADDRESSES[0],
                path=config.NFS_PATHS[0],
                timeout_to_set=sd_params['nfs_timeout'],
                retrans_to_set=sd_params['nfs_retrans'],
                mount_options_to_set=sd_params['mount_options'],
                vers_to_set=sd_params['nfs_version'],
                expected_timeout=sd_params['nfs_timeout'],
                expected_retrans=sd_params['nfs_retrans'],
                expected_vers=sd_params['nfs_version'],
                sd_type=config.TYPE_DATA
            )
            self.sds_for_cleanup.append(storage_domain_name)

            logger.info(
                "Attempt to create domain %s with wrong params ", storage.name
            )
            hl_sd.create_nfs_domain_with_options(
                name=storage.name, sd_type=storage.sd_type,
                host=self.host, address=storage.address,
                path=storage.path, version=storage.vers_to_set,
                retrans=storage.retrans_to_set, timeo=storage.timeout_to_set,
                mount_options=storage.mount_options_to_set,
                datacenter=config.DATA_CENTER_NAME, positive=False
            )
            self.sds_for_cleanup.remove(storage_domain_name)


@attr(tier=2)
@pytest.mark.usefixtures(initializer_class.__name__,)
class TestCase4817(helpers.TestCaseNFSOptions):
    """
    Test check if creating storage domains with defined values is working
    properly

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '4817'
    nfs_retrans = 5
    nfs_timeout = 10
    nfs_version = 'v3'
    mount_option = 'sync'

    @polarion("RHEVM3-4817")
    def test_create_sd_with_defined_values(self):
        """
        Check if creating an NFS storage domain with predefined values works
        """
        address = config.NFS_ADDRESSES[0]
        path = config.NFS_PATHS[0]
        self.name = 'test_%s_custom' % self.polarion_test_case
        self.sds_for_cleanup.append(self.name)

        logger.info("Creating NFS domain with custom options")
        storage = helpers.NFSStorage(
            name=self.name,
            address=address,
            path=path,
            timeout_to_set=self.nfs_timeout,
            retrans_to_set=self.nfs_retrans,
            mount_options_to_set=self.mount_option,
            vers_to_set=self.nfs_version,
            expected_timeout=self.nfs_timeout,
            expected_retrans=self.nfs_retrans,
            expected_vers=self.nfs_version,
            expected_mount_options=self.mount_option,
            sd_type=config.TYPE_DATA
        )
        self.create_nfs_domain_and_verify_options([storage])
        self.sds_for_cleanup.append(self.name)


@attr(tier=2)
@pytest.mark.usefixtures(
    detach_export_domain.__name__,
    initializer_class.__name__,
)
class TestCase4818(helpers.TestCaseNFSOptions):
    """
    Test checks that removing and destroying NFS storage domain with custom
    advanced NFS options work correctly and that adding again storage domain
    created with advanced NFS options doesn't preserve these options.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    polarion_test_case = '4818'
    nfs_retrans = 7
    nfs_timeout = 770
    nfs_version = 'v3'

    @polarion("RHEVM3-4818")
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
        self.name = 'test_%s_custom' % self.polarion_test_case
        self.sds_for_cleanup.append(self.name)

        logger.info("Creating first time with custom options")
        storage = helpers.NFSStorage(
            name=self.name, address=address, path=path,
            timeout_to_set=self.nfs_timeout, retrans_to_set=self.nfs_retrans,
            vers_to_set=self.nfs_version, expected_timeout=self.nfs_timeout,
            expected_retrans=self.nfs_retrans, expected_vers=self.nfs_version,
            sd_type=EXPORT
        )
        self.create_nfs_domain_and_verify_options([storage])

        logger.info("Removing created storage domain")
        hl_sd.remove_storage_domain(
            self.name, DC_NAME, self.host, False, config.VDC,
            config.VDC_PASSWORD
        )

        logger.info("Creating second time with custom options")
        storage = helpers.NFSStorage(
            name=self.name, address=address, path=path,
            timeout_to_set=self.nfs_timeout, retrans_to_set=self.nfs_retrans,
            vers_to_set=self.nfs_version, expected_timeout=self.nfs_timeout,
            expected_retrans=self.nfs_retrans, expected_vers=self.nfs_version,
            sd_type=EXPORT
        )
        self.create_nfs_domain_and_verify_options([storage])

        logger.info("Destroying storage domain")
        hl_sd.remove_storage_domain(
            self.name, DC_NAME, self.host, True, config.VDC,
            config.VDC_PASSWORD
        )

        logger.info("Creating third time with default options")
        self.name = 'test_%s_default' % self.polarion_test_case
        storage = helpers.NFSStorage(
            name=self.name, address=address, path=path, timeout_to_set=None,
            retrans_to_set=None, vers_to_set=None,
            expected_timeout=helpers.DEFAULT_NFS_TIMEOUT,
            expected_retrans=helpers.DEFAULT_NFS_RETRANS, expected_vers='v3',
            sd_type=EXPORT
        )
        self.sds_for_cleanup.append(self.name)
        self.create_nfs_domain_and_verify_options([storage])
