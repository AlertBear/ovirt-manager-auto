import logging
from automation_unittests.test_runner_setup_teardown.verify_results \
    import VerifyTeardownResults

logger = logging.getLogger(__name__)


def setup_package():
    logger.info('************** setup package **************')


def teardown_package():
    logger.info('************** teardown package **************')
    VerifyTeardownResults.increase_teardown_counter()