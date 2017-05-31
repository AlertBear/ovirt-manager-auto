"""
External Tasks test module
"""
import logging
import pytest

import art.rhevm_api.tests_lib.low_level.jobs as job_api
from art.test_handler.exceptions import JobException
from art.test_handler.settings import opts
from art.test_handler.tools import polarion
from art.unittest_lib import (
    attr, testflow,
    CoreSystemTest as TestBase
)

import config


enums = opts["elements_conf"]["RHEVM Enums"]
logger = logging.getLogger(__name__)


@attr(tier=2)
class JobTestTemplate(TestBase):
    """
    Template class for jobs related tests.
    """
    needs_job_finalizer = True
    job_negative = False

    started_state = enums["job_started"]
    finished_state = enums["job_finished"]

    job_description = config.job_description
    empty_job_description = str()

    @classmethod
    def add_job(cls):
        return job_api.add_job(job_description=cls.job_description)

    @classmethod
    def end_job(cls):
        if not job_api.end_job(
            cls.job_description,
            cls.started_state,
            cls.finished_state
        ):
            raise JobException("Failed to end a job.")
        return True

    def check_job(self):
        return job_api.check_recent_job(
            description=self.job_description,
            job_status=self.started_state
        )[0]

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Ending a job.")
            try:
                assert cls.end_job()
            except ValueError:
                logger.info("Nested call. It's ok.")

        if cls.needs_job_finalizer:
            request.addfinalizer(finalize)

        testflow.setup("Adding a job.")
        assert (not cls.add_job() if cls.job_negative else cls.add_job())


class StepTestTemplate(JobTestTemplate):
    """
    Template class for steps related tests.
    """
    step_negative = False

    step_description = config.step_description
    step_type = enums["step_validating"]
    bad_step_type = "bad_step_type"

    @classmethod
    def add_step(cls):
        return job_api.add_step(
            job_description=cls.job_description,
            step_description=cls.step_description,
            step_type=cls.step_type,
            step_state=cls.finished_state
        )

    def get_job_object(self):
        _, job_object = job_api.check_recent_job(
            description=self.job_description,
            job_status=self.started_state
        )
        return job_object

    def check_step(self):
        return job_api.step_by_description(
            self.get_job_object(),
            self.step_description
        )

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(StepTestTemplate, cls).setup_class(request)

        testflow.setup("Adding a step.")
        assert (not cls.add_step() if cls.step_negative else cls.add_step())


class SubStepTemplate(StepTestTemplate):
    """
    Template class for sub steps related tests.
    """
    sub_step_negative = False
    sub_step_description = config.sub_step_description
    sub_step_type = enums["step_executing"]
    step_type = sub_step_type

    @classmethod
    def add_sub_step(cls):
        return job_api.add_step(
            job_description=cls.job_description,
            step_description=cls.sub_step_description,
            step_type=cls.sub_step_type,
            step_state=cls.finished_state,
            parent_step_description=cls.step_description
        )

    def check_sub_step(self):
        job_object = self.get_job_object()
        child_step_object = job_api.step_by_description(
            job_object,
            self.sub_step_description
        )
        parent_step_object = job_api.step_by_description(
            job_object,
            self.step_description
        )
        return (
            child_step_object.get_parent_step().get_id() ==
            parent_step_object.get_id()
        )

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(SubStepTemplate, cls).setup_class(request)

        testflow.setup("Adding a sub step.")
        assert (
            not cls.add_sub_step() if cls.sub_step_negative
            else cls.add_sub_step()
        )


class TestAddJobWithCorrectDescription(JobTestTemplate):
    @polarion("RHEVM3-7154")
    def test_add_job_with_correct_description(self):
        """
        Adding a job with correct description
        """
        testflow.step(
            "Checking if adding a job with correct description will succeed."
        )
        assert self.check_job()


class TestAddJobWithEmptyDescription(JobTestTemplate):
    job_negative = True
    job_description = str()

    @polarion("RHEVM3-7165")
    def test_add_job_with_empty_description(self):
        """
        Adding job with empty description
        """
        testflow.step(
            "Checking if adding job with empty description will fail."
        )
        assert not self.check_job()


class TestAddStepWithCorrectParameters(StepTestTemplate):
    @polarion("RHEVM3-7159")
    def test_add_step_with_correct_parameters(self):
        """
        Adding step with correct parameters
        """
        testflow.step(
            "Checking if adding a step with correct parameters will succeed."
        )
        assert self.check_step()


class TestAddStepWithIncorrectType(StepTestTemplate):
    step_negative = True
    step_type = StepTestTemplate.bad_step_type

    @polarion("RHEVM3-7166")
    def test_add_step_with_incorrect_type(self):
        """
        Adding step with incorrect type
        """
        testflow.step(
            "Checking if adding a step with incorrect type will fail."
        )
        assert not self.check_step()


class TestAddSubStepWithCorrectParameters(SubStepTemplate):
    @polarion("RHEVM3-7162")
    def test_add_sub_step_with_correct_parameters(self):
        """
        Add sub step with correct description
        """
        testflow.step(
            "Checking if adding a sub step with "
            "correct parameters will succeed."
        )
        assert self.check_sub_step()


class TestEndJobWithCorrectDescription(JobTestTemplate):
    needs_job_finalizer = False

    @polarion("RHEVM3-7158")
    def test_end_job_with_correct_description(self):
        """
        Ending job with correct description
        """
        testflow.step("Ending a job with correct description.")
        assert self.end_job()


class TestEndStepWithCorrectDescription(StepTestTemplate):
    def end_step(self):
        return job_api.end_step(
            job_description=self.job_description,
            job_status=self.started_state,
            step_description=self.step_description,
            end_status=True
        )

    @polarion("RHEVM3-7155")
    def test_end_step_with_correct_description(self):
        """
        Ending a step with correct description
        """
        testflow.step("Ending a step with correct description.")
        assert self.end_step()
