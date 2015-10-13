"""
This package contains RHEVM tests
"""
import helpers


def setup_package():
    """ Set unfinished jobs to FINISHED status before run tests """
    helpers.clean_unfinished_jobs_on_engine()


def teardown_package():
    """ Check unfinished jobs after all tests """
    helpers.get_unfinished_jobs_list()
