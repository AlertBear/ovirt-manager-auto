import logging

logger = logging.getLogger("upgradeSanity")


def setup_module():
    """
    Prepare environment
    """
    import config as cfg
    if not cfg.installed_matches_current_version():
        logger.info("SETUP in source version")


def teardown_module():
    """
    Cleans the environment
    """
    import config as cfg
    if cfg.installed_matches_current_version():
        logger.info("TEARDOWN in destination version")
