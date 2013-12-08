from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st
from art.rhevm_api.tests_lib.low_level.storagedomains import createDatacenter
from art.rhevm_api.tests_lib.low_level import general


def setup_module():

    import config as cfg
    if not cfg.installed_matches_current_version():
        createDatacenter(True, hosts=cfg.HOSTS[0], cpuName=cfg.CPU_NAME,
                         username=cfg.HOSTS_USER, password=cfg.HOSTS_PW,
                         datacenter=cfg.DC_NAME, storage_type=cfg.STORAGE_TYPE,
                         cluster=cfg.CLUSTER_NAME, version=cfg.VERSION,
                         dataStorageDomains=cfg.DATA_PATHS[0],
                         address=cfg.DATA_ADDRESSES[0],
                         sdNameSuffix=cfg.SD_SUFFIX)


def teardown_module():

    import config as cfg
    if cfg.installed_matches_current_version():
        ll_st.cleanDataCenter(True, cfg.DC_NAME, vdc=cfg.VDC,
                              vdc_password=cfg.VDC_PASSWORD)
