"""
External Tasks test

"""
from art.unittest_lib import BaseTestCase as TestCase
from nose.tools import istest
from art.test_handler.tools import tcms
import art.test_handler.exceptions as errors
from art.rhevm_api.utils.test_utils import get_api
import art.rhevm_api.tests_lib.low_level.jobs as job_api
import config
import logging

JOB_API = get_api('job', 'jobs')

logger = logging.getLogger(__package__ + __name__)

########################################################################
#                             Test Cases                               #
########################################################################


class AddingJob(TestCase):
    __test__ = False

    def _add_job(self, description):
        '''
        Adding job with given description
        '''
        logger.info("Attempting to add job")
        if not job_api.add_job(job_description=description):
            logger.error("Adding job failed")
        status = job_api.check_recent_job(True,
                                          description=description,
                                          job_status=
                                          job_api.JOB_STATUSES[0])[0]
        return status


class AddJobWithCorrectDescription(AddingJob):
    """
    Adding job with correct description
    """
    __test__ = True

    @tcms('9767', '282631')
    @istest
    def add_job_with_correct_description(self):
        '''
        Adding job with correct description
        '''
        self.assertTrue(self._add_job(config.job_description))
        logger.info("Job was created")

    @classmethod
    def teardown_class(cls):
        '''
        End job with given description
        '''
        logger.info("Attempting to end job %s", config.job_description)
        if not job_api.end_job(config.job_description,
                               job_api.JOB_STATUSES[0],
                               job_api.JOB_STATUSES[1]):
            raise errors.JobException("Ending job was failed")


class AddJobWithEmptyDescription(AddingJob):
    """
    Adding job with empty description
    """
    __test__ = True

    @tcms('9767', '282632')
    @istest
    def add_job_with_empty_description(self):
        '''
        Adding job with empty description
        '''
        self.assertFalse(self._add_job(''))
        logger.info("Job creation was failed")


class AddingStep(TestCase):
    """
    Adding step
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        '''
        Adding job for adding step
        '''
        logger.info("Attempting to add job")
        if not job_api.add_job(job_description=config.job_description):
            logger.error("Adding job failed")

    def _add_step(self, step_type):
        '''
        Adding step
        '''
        logger.info("Attempting to add step")
        if not job_api.add_step(job_description=config.job_description,
                                step_description=config.step_description,
                                step_type=step_type,
                                step_state=job_api.JOB_STATUSES[1]):
            logger.error("Adding step failed")
        job_obj = job_api.check_recent_job(True,
                                           config.job_description,
                                           job_status=
                                           job_api.JOB_STATUSES[0])[1]
        logger.info("Checking if step with description %s "
                    "appear under job with description %s",
                    config.step_description, config.job_description)
        status = job_api.step_by_description(job_obj, config.step_description)
        return status

    @classmethod
    def teardown_class(cls):
        '''
        End job with given description
        '''
        logger.info("Attempting to end job %s", config.job_description)
        if not job_api.end_job(config.job_description,
                               job_api.JOB_STATUSES[0],
                               job_api.JOB_STATUSES[1]):
            raise errors.JobException("Ending job was failed")


class AddStepWithCorrectParameters(AddingStep):
    """
    Adding step with correct parameters
    """
    __test__ = True

    @tcms('9767', '289362')
    @istest
    def add_step_with_correct_parameters(self):
        '''
        Adding step with correct parameters under given job
        '''
        self.assertTrue(self._add_step(job_api.STEP_TYPES[0]))
        logger.info("Step exist")


class AddStepWithIncorrectType(AddingStep):
    """
    Adding step with incorrect type
    """
    __test__ = True

    @tcms('9767', '308838')
    @istest
    def add_step_with_incorrect_type(self):
        '''
        Adding step with incorrect type under given job
        '''
        self.assertFalse(self._add_step('some_string'))
        logger.info("Step adding was failed")


class AddSubStepWithCorrectParameters(TestCase):
    """
    Add sub step with correct description
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Add job and step under job
        '''
        logger.info("Attempting to add job")
        if not job_api.add_job(job_description=config.job_description):
            logger.error("Adding job failed")
        if not job_api.add_step(job_description=config.job_description,
                                step_description=config.step_description,
                                step_type=job_api.STEP_TYPES[1],
                                step_state=job_api.JOB_STATUSES[1]):
            logger.error("Adding step failed")

    @tcms('9767', '289237')
    @istest
    def add_sub_step_with_correct_parameters(self):
        '''
        Add sub step with correct description
        '''
        logger.info("Attempting to add sub step")
        if not job_api.add_step(job_description=config.job_description,
                                step_description=config.sub_step_description,
                                step_type=job_api.STEP_TYPES[1],
                                step_state=job_api.JOB_STATUSES[1],
                                parent_step_description=
                                config.step_description):
            logger.error("Adding sub step failed")
        job_obj = job_api.check_recent_job(True,
                                           config.job_description,
                                           job_status=
                                           job_api.JOB_STATUSES[0])[1]
        logger.info("Checking if step with description %s "
                    "appear under step with description %s",
                    config.sub_step_description, config.step_description)
        step_obj = job_api.step_by_description(job_obj,
                                               config.sub_step_description)
        parent_step_obj = job_api.step_by_description(job_obj,
                                                      config.step_description)
        status = step_obj.get_parent_step().get_id() ==\
            parent_step_obj.get_id()
        self.assertTrue(status)
        logger.info("Step exist")

    @classmethod
    def teardown_class(cls):
        '''
        End job with given description
        '''
        logger.info("Attempting to end job %s", config.job_description)
        if not job_api.end_job(config.job_description,
                               job_api.JOB_STATUSES[0],
                               job_api.JOB_STATUSES[1]):
            raise errors.JobException("Ending job was failed")


class EndJobWithCorrectDescription(TestCase):
    """
    Ending job with correct description
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Add job with correct description
        '''
        logger.info("Attempting to add job")
        if not job_api.add_job(job_description=config.job_description):
            logger.error("Adding job failed")

    @tcms('9767', '289545')
    @istest
    def end_job_with_correct_description(self):
        '''
        Ending job with correct description
        '''
        logger.info("Attempting to end job %s", config.job_description)
        status = job_api.end_job(config.job_description,
                                 job_api.JOB_STATUSES[0],
                                 job_api.JOB_STATUSES[1])
        self.assertTrue(status)
        logger.info("Ending job %s success", config.job_description)


class EndStepWithCorrectDescription(TestCase):
    """
    Ending step with correct description
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Add job and step under job
        '''
        logger.info("Attempting to add job")
        if not job_api.add_job(job_description=config.job_description):
            logger.error("Adding job failed")
        logger.info("Adding job success")
        if not job_api.add_step(job_description=config.job_description,
                                step_description=config.step_description,
                                step_type=job_api.STEP_TYPES[1],
                                step_state=job_api.JOB_STATUSES[1]):
            logger.error("Adding step to job was failed")

    @tcms('9767', '308836')
    @istest
    def end_step_with_correct_description(self):
        '''
        Ending step with correct description
        '''
        logger.info("Attempting to end step %s", config.step_description)
        status = job_api.end_step(config.job_description,
                                  job_api.JOB_STATUSES[0],
                                  config.step_description,
                                  True)
        self.assertTrue(status)
        logger.info("Ending step %s success", config.step_description)

    @classmethod
    def teardown_class(cls):
        '''
        End job with given description
        '''
        logger.info("Attempting to end job %s", config.job_description)
        if not job_api.end_job(config.job_description,
                               job_api.JOB_STATUSES[0],
                               job_api.JOB_STATUSES[1]):
            raise errors.JobException("Ending job was failed")