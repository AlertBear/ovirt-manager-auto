import logging
from art.rhevm_api.utils.inventory import Inventory
import config

logger = logging.getLogger(__name__)


def teardown_package():
    reporter = Inventory.get_instance()
    reporter.get_setup_inventory_report(
        print_report=True,
        check_inventory=True,
        rhevm_config_file=config
    )
