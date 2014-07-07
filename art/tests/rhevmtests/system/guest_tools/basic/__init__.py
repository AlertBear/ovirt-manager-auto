"""
Please be aware all your tests must be able to loaded by nose.loader.TestLoader
automatically. If you need something what is not visible for TestLoader first
of all ask yourself 'Why?'. Only in case you are convienced there is reason
to do that, just let me know (lbednar@redhat.com), I have workaround.

NOTE: test identifier for this example is
 tests_file = unittest://tests/unittest_template:example

Purpose of this doc string is also description of test suite.
"""

# Import module from rhevm_api
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
import art.rhevm_api.tests_lib.low_level.storagedomains as storagedomains
from rhevmtests.system import config


def setup_package():
    # import MUST be in the function, cannot be on module level. That's
    # because of __init__.py is loaded first and then ART_CONFIG is set.
    # Here put your set-up action for whole bunch of tests
    datacenters.build_setup(
        config.PARAMETERS, config.PARAMETERS,
        config.STORAGE_TYPE, config.TEST_NAME)
    storagedomains.importStorageDomain(True, type='iso',
                                       storage_type='nfs',
                                       address=config.ISO_DOMAIN_ADDRESS,
                                       host=config.VDS,
                                       path=config.ISO_DOMAIN_PATH)
    storagedomains.importStorageDomain(
        True, type='export',
        storage_type='nfs',
        address=config.EXPORT_DOMAIN_ADDRESS,
        host=config.VDS,
        path=config.EXPORT_DOMAIN_PATH)
    storagedomains.attachStorageDomain(True, config.DC_NAME,
                                       config.EXPORT_STORAGE_DOMAIN)
    storagedomains.attachStorageDomain(True, config.DC_NAME,
                                       config.ISO_STORAGE_DOMAIN)
    storagedomains.activateStorageDomain(True, config.DC_NAME,
                                         config.EXPORT_STORAGE_DOMAIN)
    storagedomains.activateStorageDomain(True, config.DC_NAME,
                                         config.ISO_STORAGE_DOMAIN)


def teardown_package():
    # Here put your tear-down action for whole bunch of tests
    storagedomains.deactivateStorageDomain(
        True, datacenter=config.DC_NAME,
        storagedomain=config.ISO_STORAGE_DOMAIN)
    storagedomains.deactivateStorageDomain(
        True, datacenter=config.DC_NAME,
        storagedomain=config.EXPORT_STORAGE_DOMAIN)
    storagedomains.detachStorageDomain(
        True, datacenter=config.DC_NAME,
        storagedomain=config.EXPORT_STORAGE_DOMAIN)
    storagedomains.detachStorageDomain(
        True, datacenter=config.DC_NAME,
        storagedomain=config.ISO_STORAGE_DOMAIN)
    storagedomains.removeStorageDomain(
        True, storagedomain=config.EXPORT_STORAGE_DOMAIN,
        host=config.VDS, format='False')
    storagedomains.removeStorageDomain(
        True, storagedomain=config.ISO_STORAGE_DOMAIN,
        host=config.VDS, format='False')
    cleanDataCenter(True, config.DC_NAME)
