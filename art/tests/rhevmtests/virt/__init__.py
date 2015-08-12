import art.rhevm_api.utils.inventory as reporter
import config

setup_reporter = None


def setup_module():
    global setup_reporter
    setup_reporter = reporter.Inventory()
    setup_reporter.get_setup_inventory_report(
        print_report=True,
        check_inventory=True,
        rhevm_config_file=config
    )


def teardown_module():
    global setup_reporter
    setup_reporter.get_setup_inventory_report(
        print_report=True,
        check_inventory=True,
        rhevm_config_file=config
    )
    setup_reporter = None
