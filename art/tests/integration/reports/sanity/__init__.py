import logging

LOGGER = logging.getLogger(__name__)


def setup_package():
    LOGGER.info("Setup Module")


def teardown_package():
    LOGGER.debug("Teardown Module")
