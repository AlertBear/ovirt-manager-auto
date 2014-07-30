"""
This class creates and configures the required test environment
"""
from art.rhevm_api.tests_lib.high_level import datacenters
from rhevmtests.storage.storage_disk_image_format import config


def setup_module():
    """
    Creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config=config.PARAMETERS, storage=config.PARAMETERS,
            storage_type=config.STORAGE_TYPE, basename=config.TESTNAME,
        )


def teardown_module():
    """
    Removes created datacenter, storages etc.
    """
    if not config.GOLDEN_ENV:
        datacenters.clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_ROOT_PASSWORD,
        )
