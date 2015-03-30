from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains as h_sd
from art.rhevm_api.tests_lib.low_level import storagedomains, templates, vms
from art.test_handler.settings import opts
from art.rhevm_api.utils.test_utils import get_api
import art.rhevm_api.utils.test_utils as utils
import logging
from rhevmtests.system.guest_tools.linux_guest_agent import config

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
    storagedomains.importStorageDomain(
        True, type='export',
        storage_type='nfs',
        address=config.EXPORT_DOMAIN_ADDRESS,
        host=config.HOSTS[0],
        path=config.EXPORT_DOMAIN_PATH,
        clean_export_domain_metadata=True)
    h_sd.attach_and_activate_domain(config.DC_NAME[0],
                                    config.EXPORT_STORAGE_DOMAIN)
    for os, template in config.TEMPLATES.iteritems():
        vm_name = 'vm_%s' % template['name']
        assert templates.import_template(
            True, template=template['name'],
            source_storage_domain=config.EXPORT_STORAGE_DOMAIN,
            destination_storage_domain=config.STORAGE_DOMAIN,
            cluster=config.CLUSTER_NAME[0], name=template['name'])
        assert vms.createVm(True, vm_name, vm_name,
                            cluster=config.CLUSTER_NAME[0],
                            template=template['name'],
                            network=config.MGMT_BRIDGE)
        assert vms.startVm(True, vm_name,
                           wait_for_status=ENUMS['vm_state_up'])
        mac = vms.getVmMacAddress(True, vm=vm_name, nic='nic1')
        assert mac[0], "vm %s MAC was not found." % vm_name
        mac = mac[1].get('macAddress', None)
        LOGGER.info("Mac adress is %s", mac)

        guest_ip = utils.convertMacToIpAddress(
            True, mac, subnetClassB=config.SUBNET_CLASS)
        assert guest_ip[0], "MacToIp was not corretly converted."
        config.TEMPLATES[os]['ip'] = guest_ip[1].get('ip', None)
        config.TEMPLATES[os]['vm_name'] = vm_name
        config.TEMPLATES[os]['vm_id'] = VM_API.find(vm_name).id


def teardown_package():
    for os, template in config.TEMPLATES.iteritems():
        vms.removeVm(True, vm='vm_%s' % template['name'], stopVM='true')
        templates.removeTemplate(True, template['name'])

    h_sd.detach_and_deactivate_domain(
        config.DC_NAME[0],
        config.EXPORT_STORAGE_DOMAIN,
    )
    h_sd.remove_storage_domain(
        config.EXPORT_STORAGE_DOMAIN,
        config.DC_NAME[0], config.HOSTS[0],
    )

    if not config.GOLDEN_ENV:
        datacenters.clean_datacenter(True, config.DC_NAME[0])
