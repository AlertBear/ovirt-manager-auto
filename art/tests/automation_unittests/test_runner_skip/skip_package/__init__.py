
import logging

logger = logging.getLogger(__name__)


def setup_package():
    """
    Nothing for setup
    """
    logger.info('*********** setup package ***********')
    raise Exception('Raise exception in package setup')


def teardown_package():
    """
    Nothing for teardown
    """
    logger.info('*********** teardown package ***********')