import logging

logger = logging.getLogger(__name__)


def setup_package():
    logger.info('************** setup package **************')
    raise Exception


def teardown_package():
    logger.info('************** teardown package **************')
