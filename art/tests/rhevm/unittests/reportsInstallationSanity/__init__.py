import logging

LOGGER = logging.getLogger(__name__)


def setup_module():
    LOGGER.info("Setup Module")


def teardown_module():
    LOGGER.debug("Teardown Module")
