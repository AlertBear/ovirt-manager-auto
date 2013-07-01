import logging
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_d

LOGGER = logging.getLogger(__name__)


def setup_package():
    """ creates datacenter, adds hosts, clusters, 2 storages according to
        config file
    """
    import config

    luns = config.PARAMETERS.as_list('lun')
    domain_address = config.PARAMETERS.as_list('data_domain_address')
    config.PARAMETERS['lun'] = list()
    config.PARAMETERS['data_domain_address'] = list()
    LOGGER.info("Preparing datacenter %s with hosts %s",
                config.DATA_CENTER_NAME, config.VDC)
    build_setup(config=config.PARAMETERS, storage=config.PARAMETERS,
                storage_type=config.DATA_CENTER_TYPE,
                basename=config.BASENAME)

    config.PARAMETERS['lun'] = luns
    config.PARAMETERS['data_domain_address'] = domain_address

    sd_args1 = {
        'name' : config.ST_NAME,
        'type' : config.ENUMS['storage_dom_type_data'],
        'storage_type' : config.DATA_CENTER_TYPE,
        'host' : config.VDS[0],
    }

    if config.DATA_CENTER_TYPE == 'nfs':
        sd_args1['address'] = config.ADDRESS[0]
        sd_args1['path'] = config.PATH[0]
    elif config.DATA_CENTER_TYPE == 'iscsi':
        sd_args1['lun'] = config.LUN[0]
        sd_args1['lun_address'] = config.LUN_ADDRESS[0]
        sd_args1['lun_target'] = config.LUN_TARGET[0]
        sd_args1['lun_port'] = config.LUN_PORT

    LOGGER.info('Creating first domain with parameters: %s', sd_args1)
    ll_st_d.addStorageDomain(True, **sd_args1)

    sd_args2 = sd_args1
    sd_args2['name'] = config.ST_NAME_2

    if config.DATA_CENTER_TYPE == 'nfs':
        sd_args2['address'] = config.ADDRESS[1]
        sd_args2['path'] = config.PATH[1]
    elif config.DATA_CENTER_TYPE == 'iscsi':
        sd_args2['lun'] = config.LUN[1]
        sd_args2['lun_address'] = config.LUN_ADDRESS[1]
        sd_args2['lun_target'] = config.LUN_TARGET[1]

    LOGGER.info('Creating second domain with parameters: %s', sd_args2)

    ll_st_d.addStorageDomain(True, **sd_args2)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    import config
    ll_st_d.cleanDataCenter(True, config.DATA_CENTER_NAME,
                            vdc=config.VDC, vdc_password=config.VDC_PASSWORD)
