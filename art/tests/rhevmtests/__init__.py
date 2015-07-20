"""
This package contains RHEVM tests
"""
import logging
import art.rhevm_api.tests_lib.low_level.jobs as ll_jobs
import helpers

logger = logging.getLogger(__name__)


def setup_package():
    """ Set unfinished jobs to FINISHED status before run tests """
    helpers.clean_unfinished_jobs_on_engine(ll_jobs.get_active_jobs())


def teardown_package():
    """ Check unfinished jobs after all tests """
    helpers.get_unfinished_jobs_list()
