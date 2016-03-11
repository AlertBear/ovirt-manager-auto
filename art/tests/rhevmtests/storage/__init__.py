from rhevmtests.storage import config
from art.rhevm_api.utils.inventory import Inventory


def assign_storgage_params(targets, keywords, *args):
    for i, target in enumerate(targets):
        for j, key in enumerate(keywords):
            target[key] = args[j][i]


def setup_package():
    config.FIRST_HOST = config.HOSTS[0]
    assign_storgage_params(
        config.NFS_DOMAINS_KWARGS,
        ('address', 'path'),
        config.UNUSED_DATA_DOMAIN_ADDRESSES,
        config.UNUSED_DATA_DOMAIN_PATHS,
    )
    assign_storgage_params(
        config.ISCSI_DOMAINS_KWARGS,
        ('lun_address', 'lun_target', 'lun'),
        config.UNUSED_LUN_ADDRESSES,
        config.UNUSED_LUN_TARGETS,
        config.UNUSED_LUNS,
    )
    assign_storgage_params(
        config.GLUSTER_DOMAINS_KWARGS,
        ('address', 'path'),
        config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES,
        config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS,
    )
    assign_storgage_params(
        config.FC_DOMAINS_KWARGS,
        ('fc_lun',),
        config.UNUSED_FC_LUNS,
    )


def teardown_package():
    reporter = Inventory.get_instance()
    reporter.get_setup_inventory_report(
        print_report=True,
        check_inventory=True,
        rhevm_config_file=config
    )
