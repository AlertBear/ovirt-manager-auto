"""
-----------------
Flow cases setup & teardown
-----------------

@author: Nelly Credi
"""

import logging

from .. import config
from .. import help_functions
from art.test_handler.exceptions import SkipTest

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS


def setup_package():
    """
    Setup prerequisites for testing scenario:
    create data center, cluster, host, storage domain, vm & template
    """
    if not config.STORAGE_TYPE == 'nfs':
        logger.info("Storage type is not NFS, skipping tests")
        raise SkipTest
    help_functions.utils.add_dc()
    help_functions.utils.add_cluster()
    help_functions.utils.add_host()
    help_functions.utils.create_sd()
    help_functions.utils.attach_sd()
    help_functions.utils.create_vm()
    help_functions.utils.add_disk_to_vm()
    help_functions.utils.create_template()


def teardown_package():
    """
    Tear down prerequisites for testing host functionality:
    remove data center, cluster, host, storage domain, vm & template
    """
    help_functions.utils.remove_disk_from_vm()
    help_functions.utils.remove_vm()
    help_functions.utils.remove_template()
    help_functions.utils.deactivate_sd()
    help_functions.utils.remove_dc()
    help_functions.utils.remove_sd()
    help_functions.utils.deactivate_host()
    help_functions.utils.remove_host()
    help_functions.utils.remove_cluster()
