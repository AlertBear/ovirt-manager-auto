import logging

from art.rhevm_api.tests_lib.high_level import (
    datacenters, storagedomains as h_sd
)
from art.rhevm_api.tests_lib.low_level import storagedomains, vms
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts
from rhevmtests.system.guest_tools.linux_guest_agent import config, common


ENUMS = opts['elements_conf']['RHEVM Enums']
LOGGER = logging.getLogger(__name__)
VM_API = get_api('vm', 'vms')


def setup_package():
    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config.PARAMETERS,
            config.PARAMETERS,
            config.STORAGE_TYPE,
            config.TEST_NAME,
        )
        # FIXME: change it to import of glance
        storagedomains.importStorageDomain(
            True, type='export',
            storage_type='nfs',
            address=config.EXPORT_DOMAIN_ADDRESS,
            host=config.HOSTS[0],
            path=config.EXPORT_DOMAIN_PATH,
            clean_export_domain_metadata=True
        )
        h_sd.attach_and_activate_domain(
            config.DC_NAME[0], config.EXPORT_STORAGE_DOMAIN
        )
    for image in sorted(config.TEST_IMAGES):
        config.TEST_IMAGES[image]['image'] = common.import_image(image)
        assert vms.createVm(
            positive=True,
            vmName=image,
            vmDescription=image,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE,
            nic=config.NIC_NAME,
            nicType=config.NIC_TYPE_E1000,
        )
        config.TEST_IMAGES[image]['id'] = VM_API.find(image).id


def teardown_package():
    if not config.GOLDEN_ENV:
        h_sd.detach_and_deactivate_domain(
            config.DC_NAME[0],
            config.EXPORT_STORAGE_DOMAIN,
        )
        h_sd.remove_storage_domain(
            config.EXPORT_STORAGE_DOMAIN,
            config.DC_NAME[0], config.HOSTS[0],
        )
        datacenters.clean_datacenter(True, config.DC_NAME[0])
