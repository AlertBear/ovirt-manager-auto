from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sds
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level import disks as ll_disks
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sds
from rhevmtests.system.wgt import config


def setup_package():
    ll_sds.attachStorageDomain(
        True, config.DC_NAME[0], config.ISO_DOMAIN_NAME
    )
    ll_sds.activateStorageDomain(
        True, config.DC_NAME[0], config.ISO_DOMAIN_NAME
    )


def teardown_package():
    for vm in ll_vms.get_vms_from_cluster(config.CLUSTER_NAME[0]):
        if vm.capitalize().startswith("Win"):
            ll_vms.removeVm(positive=True, vm=vm, stopVM=True)

    for disk in ll_disks.get_all_disks():
        if disk.get_alias().capitalize().startswith("Win"):
            ll_disks.deleteDisk(True, disk.get_alias())

    hl_sds.detach_and_deactivate_domain(
        datacenter=config.DC_NAME[0],
        domain=config.ISO_DOMAIN_NAME,
    )
