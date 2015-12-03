"""
This package contains RHEVM tests
"""
import helpers
from rhevmtests import config


def setup_package():
    """ Set unfinished jobs to FINISHED status before run tests """
    helpers.clean_unfinished_jobs_on_engine()
    if config.HOST_ORDER == 'rhevh_first' and not config.HOSTS_RHEVH:
        raise EnvironmentError("This environment doesn't include rhev-h hosts")


def teardown_package():
    """ Check unfinished jobs after all tests """
    helpers.get_unfinished_jobs_list()
