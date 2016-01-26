"""
init for system tests package
"""
from art.rhevm_api.utils.inventory import Inventory
from rhevmtests.system import config


def teardown_package():
    reporter = Inventory.get_instance()
    reporter.get_setup_inventory_report(
        print_report=True,
        check_inventory=True,
        rhevm_config_file=config
    )
