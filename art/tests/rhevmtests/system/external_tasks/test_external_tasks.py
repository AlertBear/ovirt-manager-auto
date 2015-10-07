"""
External Tasks test

"""
from art.unittest_lib import CoreSystemTest as TestCase
from nose.tools import istest
from art.unittest_lib import attr
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.test_handler.exceptions as errors
from art.rhevm_api.utils.test_utils import get_api
import art.rhevm_api.tests_lib.low_level.jobs as job_api
from art.test_handler.settings import opts
from rhevmtests.system.external_tasks import config
import logging

JOB_API = get_api('job', 'jobs')
ENUMS = opts['elements_conf']['RHEVM Enums']
logger = logging.getLogger(__name__)

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
        status = job_api.check_recent_job(
            True, description=description,
            job_status=ENUMS['job_started'])[0]
        return status


@attr(tier=2)
class AddJobWithCorrectDescription(AddingJob):
    """
    Adding job with correct description
    """
    __test__ = True

    @polarion("RHEVM3-7154")
    @istest
    def add_job_with_correct_description(self):
        '''
        Adding job with correct description
        '''
        self.assertTrue(self._add_job(config.EXTERNAL_JOB_DESCRIPTION))
        logger.info("Job was created")

    @classmethod
    def teardown_class(cls):
        '''
        End job with given description
        '''
        logger.info("Attempting to end job %s",
                    config.EXTERNAL_JOB_DESCRIPTION)
        if not job_api.end_job(
                config.EXTERNAL_JOB_DESCRIPTION,
                ENUMS['job_started'],
                ENUMS['job_finished']
        ):
            raise errors.JobException("Ending job was failed")


@attr(tier=2)
class AddJobWithEmptyDescription(AddingJob):
    """
    Adding job with empty description
    """
    __test__ = True

    @polarion("RHEVM3-7165")
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
        if not job_api.add_job(
            job_description=config.EXTERNAL_JOB_DESCRIPTION
        ):
            logger.error("Adding job failed")

    def _add_step(self, step_type):
        '''
        Adding step
        '''
        logger.info("Attempting to add step")
        if not job_api.add_step(
                job_description=config.EXTERNAL_JOB_DESCRIPTION,
                step_description=config.EXTERNAL_STEP_DESCRIPTION,
                step_type=step_type,
                step_state=ENUMS['job_finished']
        ):
            logger.error("Adding step failed")
        job_obj = job_api.check_recent_job(
            True, config.EXTERNAL_JOB_DESCRIPTION,
            job_status=ENUMS['job_started'])[1]
        logger.info("Checking if step with description %s "
                    "appear under job with description %s",
                    config.EXTERNAL_STEP_DESCRIPTION,
                    config.EXTERNAL_JOB_DESCRIPTION)
        status = job_api.step_by_description(job_obj,
                                             config.EXTERNAL_STEP_DESCRIPTION)
        return status

    @classmethod
    def teardown_class(cls):
        '''
        End job with given description
        '''
        logger.info("Attempting to end job %s",
                    config.EXTERNAL_JOB_DESCRIPTION)
        if not job_api.end_job(config.EXTERNAL_JOB_DESCRIPTION,
                               ENUMS['job_started'],
                               ENUMS['job_finished']):
            raise errors.JobException("Ending job was failed")


@attr(tier=2)
class AddStepWithCorrectParameters(AddingStep):
    """
    Adding step with correct parameters
    """
    __test__ = True

    @polarion("RHEVM3-7159")
    @istest
    def add_step_with_correct_parameters(self):
        '''
        Adding step with correct parameters under given job
        '''
        self.assertTrue(self._add_step(ENUMS['step_validating']))
        logger.info("Step exist")


@attr(tier=2)
class AddStepWithIncorrectType(AddingStep):
    """
    Adding step with incorrect type
    """
    __test__ = True

    @polarion("RHEVM3-7166")
    @istest
    def add_step_with_incorrect_type(self):
        '''
        Adding step with incorrect type under given job
        '''
        self.assertFalse(self._add_step('some_string'))
        logger.info("Step adding was failed")


@attr(tier=2)
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
        if not job_api.add_job(
                job_description=config.EXTERNAL_JOB_DESCRIPTION
        ):
            logger.error("Adding job failed")
        if not job_api.add_step(
                job_description=config.EXTERNAL_JOB_DESCRIPTION,
                step_description=config.EXTERNAL_STEP_DESCRIPTION,
                step_type=ENUMS['step_executing'],
                step_state=ENUMS['job_finished']
        ):
            logger.error("Adding step failed")

    @polarion("RHEVM3-7162")
    @istest
    def add_sub_step_with_correct_parameters(self):
        '''
        Add sub step with correct description
        '''
        step_description = config.EXTERNAL_STEP_DESCRIPTION
        logger.info("Attempting to add sub step")
        if not job_api.add_step(
                job_description=config.EXTERNAL_JOB_DESCRIPTION,
                step_description=config.EXTERNAL_SUB_STEP_DESCRIPTION,
                step_type=ENUMS['step_executing'],
                step_state=ENUMS['job_finished'],
                parent_step_description=step_description
        ):
            logger.error("Adding sub step failed")
        job_obj = job_api.check_recent_job(
            True, config.EXTERNAL_JOB_DESCRIPTION,
            job_status=ENUMS['job_started'])[1]
        logger.info("Checking if step with description %s "
                    "appear under step with description %s",
                    config.EXTERNAL_SUB_STEP_DESCRIPTION, step_description)
        step_obj = job_api.step_by_description(
            job_obj, config.EXTERNAL_SUB_STEP_DESCRIPTION)
        parent_step_obj = job_api.step_by_description(job_obj,
                                                      step_description)
        status = (step_obj.get_parent_step().get_id() ==
                  parent_step_obj.get_id())
        self.assertTrue(status)
        logger.info("Step exist")

    @classmethod
    def teardown_class(cls):
        '''
        End job with given description
        '''
        logger.info("Attempting to end job %s",
                    config.EXTERNAL_JOB_DESCRIPTION)
        if not job_api.end_job(config.EXTERNAL_JOB_DESCRIPTION,
                               ENUMS['job_started'],
                               ENUMS['job_finished']):
            raise errors.JobException("Ending job was failed")


@attr(tier=2)
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
        if not job_api.add_job(
                job_description=config.EXTERNAL_JOB_DESCRIPTION
        ):
            logger.error("Adding job failed")

    @polarion("RHEVM3-7158")
    @istest
    def end_job_with_correct_description(self):
        '''
        Ending job with correct description
        '''
        logger.info("Attempting to end job %s",
                    config.EXTERNAL_JOB_DESCRIPTION)
        status = job_api.end_job(config.EXTERNAL_JOB_DESCRIPTION,
                                 ENUMS['job_started'],
                                 ENUMS['job_finished'])
        self.assertTrue(status)
        logger.info("Ending job %s success", config.EXTERNAL_JOB_DESCRIPTION)


@attr(tier=2)
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
        if not job_api.add_job(
                job_description=config.EXTERNAL_JOB_DESCRIPTION
        ):
            logger.error("Adding job failed")
        logger.info("Adding job success")
        if not job_api.add_step(
            job_description=config.EXTERNAL_JOB_DESCRIPTION,
            step_description=config.EXTERNAL_STEP_DESCRIPTION,
            step_type=ENUMS['step_executing'],
            step_state=ENUMS['job_finished']
        ):
            logger.error("Adding step to job was failed")

    @polarion("RHEVM3-7155")
    @istest
    def end_step_with_correct_description(self):
        '''
        Ending step with correct description
        '''
        logger.info("Attempting to end step %s",
                    config.EXTERNAL_STEP_DESCRIPTION)
        status = job_api.end_step(config.EXTERNAL_JOB_DESCRIPTION,
                                  ENUMS['job_started'],
                                  config.EXTERNAL_STEP_DESCRIPTION, True)
        self.assertTrue(status)
        logger.info("Ending step %s success", config.EXTERNAL_STEP_DESCRIPTION)

    @classmethod
    def teardown_class(cls):
        '''
        End job with given description
        '''
        logger.info("Attempting to end job %s",
                    config.EXTERNAL_JOB_DESCRIPTION)
        if not job_api.end_job(config.EXTERNAL_JOB_DESCRIPTION,
                               ENUMS['job_started'],
                               ENUMS['job_finished']):
            raise errors.JobException("Ending job was failed")
