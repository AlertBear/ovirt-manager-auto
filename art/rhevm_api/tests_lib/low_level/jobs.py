import re
from art.core_api.apis_utils import data_st, TimeoutingSampler
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts
import logging

ENUMS = opts['elements_conf']['RHEVM Enums']

JOBS_API = get_api('job', 'jobs')
STEPS_API = get_api('step', 'steps')
logger = logging.getLogger("art.ll_lib.jobs")
TASK_TIMEOUT = 600
JOB_TIMEOUT = 1200
TASK_POLL = 5


def check_recent_job(positive, description, last_jobs_num=None,
                     job_status=ENUMS['job_finished']):
    """
    Description: Check if in recent jobs exist job with given description
    **Author**: alukiano
    **Parameters**:
      * *description* - search for job with given description
      * *last_jobs_num* - number of recent jobs you want search in, if None,
        check all exist jobs
      * *job_status* - to job must be given state
    **Returns**: True if exist job with given description, job and job time
            Else return False, None, None
    """
    jobs = JOBS_API.get(abs_link=False)[:last_jobs_num]
    if not description:
        logger.warn("Description is empty")
        return False, None, None

    job_status = job_status.lower()
    jobs = filter(lambda j: (description in j.get_description() and
                             j.get_status() == job_status), jobs)
    last_job = max(jobs, key=lambda j: j.get_start_time())

    if last_job:
        return True, last_job
    else:
        return False, None


def get_jobs():
    """
    Get a all jobs in the system

    __author__= "ratamir"

    Returns:
        list: List of job objects
    """
    return JOBS_API.get(abs_link=False)


def get_job_object(description, job_status=ENUMS['job_finished']):
    """
    Get the latest job that specified by description and with status

    __author__= "ratamir"

    Args:
        description (str): Search for job with given description
        job_status (str): The status of the requested job

    Returns:
        Job object: Job object if a job with the given description was
        found or None otherwise
    """
    jobs = [job for job in get_jobs() if (
        re.match(description, job.get_description())
        ) and job.get_status() == job_status]
    if jobs:
        return max(jobs, key=lambda j: j.get_start_time())
    return None


def get_job_execution_time(job_object):
    """
    Get the execution time of the job

    __author__= "ratamir"

    Args:
        description (str): Search for job with given description

    Returns:
        float: Execution time of requested job in seconds
    """
    time = (
        job_object.get_last_updated() - job_object.get_start_time()
    ).total_seconds()
    logger.info("JOB '%s' TOOK %s seconds", job_object.get_description(), time)
    return time


def get_active_jobs(job_descriptions=None):
    """
    Check if all/requested jobs have been completed

    __author__ = 'ratamir'
    :param job_descriptions: job descriptions that needs to be sampled
    :type job_descriptions: list
    :return: list of job objects
    :rtype: list
    """
    jobs = JOBS_API.get(abs_link=False)
    # This is a W/A for BZ1248055, due to some GET request to /api/jobs
    # returning 400, just return a list of objects so wait_for_jobs() will
    # continue to call this funcion until the time out
    if jobs is None:
        logger.warning("GET /api/jobs returned 400")
        return [True]

    jobs = filter(
        lambda job: (
            job.get_status() == ENUMS['job_started']
        ), jobs
    )

    if job_descriptions:
        relevant_jobs = []
        for job_description in job_descriptions:
            for job in jobs:
                if re.match(job_description, job.get_description()):
                    relevant_jobs.append(job)
                    break
        jobs = relevant_jobs

    logger.info("Active jobs: %s", [job.get_description() for job in jobs])
    return jobs


def wait_for_jobs(
    job_descriptions=None, timeout=JOB_TIMEOUT, sleep=TASK_POLL,
    exec_time=True
):
    """
    Waits until all/requested jobs in data-center have completed

    __author__ = 'ratamir'
    :param job_descriptions: job descriptions that needs to be sampled
    :type job_descriptions: list
    :param timeout: max seconds to wait
    :type timeout: int
    :param sleep: polling interval
    :type sleep: int
    :param exec_time: Determines if the execution time of the job should be
    logged
    :type exec_time: bool
    :raise: TimeoutExpiredError
    """
    logger.info("Waiting for jobs %s", job_descriptions)
    sampler = TimeoutingSampler(
        timeout, sleep, get_active_jobs, job_descriptions
    )
    for jobs in sampler:
        if not jobs:
            if job_descriptions and exec_time:
                for job_description in job_descriptions:
                    job = get_job_object(job_description)
                    if job:
                        get_job_execution_time(job)
            logger.info("All jobs are gone")
            return


def wait_for_step_to_start(
    job_object, step_description, timeout=JOB_TIMEOUT, sleep=TASK_POLL,
):
    """
    Waits until all/requested jobs in data-center have completed

    Author: ratamir

    Arguments:
        job_object (Object): job object that hold the step
        step_description (str): Looking for step with this description
        timeout (int): max seconds to wait
        sleep (int): polling interval

    Raises:
        TimeoutExpiredError: in case the step hasn't started in the timeout
            period
    """
    logger.info("Waiting for step %s to start", step_description)
    sampler = TimeoutingSampler(
        timeout, sleep, step_by_description, job_object, step_description
    )
    for step in sampler:
        if step:
            return


def add_job(job_description, auto_cleared=True):
    '''
    Description: Add new job with given description
    **Author**: alukiano
    **Parameters**:
      * *description* - Name of job
      * *auto_cleared* - if True, job will automatically removed from tasks,
       after define time(take from database)
       if False, you must remove job from tasks by yourself
    **Returns**: True, if job adding job was success
            False, else
    '''
    job_obj = data_st.Job(description=job_description,
                          auto_cleared=auto_cleared)
    if not JOBS_API.create(job_obj, True)[1]:
        return False
    return True


def add_step(
        job_description, step_description,
        step_type, step_state,
        parent_step_description=None
):
    """
    Description: Add new step to job or step with given description
    Arguments:
        step_description (str): Name of step
        job_description (str): Name of job to add step
        step_type (obj): type of step, one of
            ['VALIDATING', 'EXECUTING', 'FINALIZING']
        step_state (obj): state of step, one of
            ['STARTED', 'FINISHED', 'FAILED', 'ABORTED', 'UNKNOWN']
        parent_step_description (str): add sub-step to step
            with given description
    Returns:
        bool: True, if job adding job was success, else False
    """
    job_obj = None
    parent_step_obj = None
    for status in [
            ENUMS['job_started'], ENUMS['job_finished'],
            ENUMS['job_failed'], ENUMS['job_aborted'],
            ENUMS['job_unknown']
    ]:
        _, job_obj = check_recent_job(
            True,
            job_description,
            job_status=status
        )
        if job_obj:
            if parent_step_description:
                parent_step_obj = step_by_description(
                    job_obj,
                    parent_step_description
                )
                if parent_step_obj:
                    break
            else:
                break
    if not job_obj:
        logger.error("No job with given description found")
        return False
    if parent_step_description and not parent_step_obj:
        logger.error("No parent step with given description found")
        return False
    steps_obj = STEPS_API.getElemFromLink(job_obj, get_href=True)
    step_obj = data_st.Step(
        description=step_description,
        job=job_obj,
        parent_step=parent_step_obj,
        status=step_state,
        type_=step_type.lower()
    )
    if not STEPS_API.create(step_obj, True, collection=steps_obj)[1]:
        return False
    return True


def step_by_description(job, step_description):
    """
    Description: Look for step under job with given description
    **Author**: alukiano
    **Parameters**:
      * *job* - under this job looking for step
      * *step_description* - looking for step with this description
    **Returns**: if step with given description exist, return step object
            else, return None
    """
    steps_obj = STEPS_API.getElemFromLink(job, link_name='steps', attr='step',
                                          get_href=False)
    if not steps_obj:
        warn_msg = 'No step with description %s under job with description %s'
        logger.warning(warn_msg, step_description, job.get_description())
    for step in steps_obj:
        if step_description in step.get_description():
            return step
    return None


def end_job(job_description, job_status, end_status):
    """
    Description:
        End job with given description
    Parameters:
        job_description (str): description of job you want to end
        job_status (str): status of job you want to end
        end_status (str):  end job with specific status. One of
            ['STARTED', 'FINISHED', 'FAILED', 'ABORTED', 'UNKNOWN']
    Returns:
        bool: True, if ending job succeeds, False otherwise
    """
    _, job_object = check_recent_job(
        True,
        job_description,
        job_status=job_status
    )
    if not job_object:
        logger.warn("Job with given description not exist")
        return False
    if not JOBS_API.syncAction(
        job_object,
        "end",
        True,
        status=end_status
    ):
        return False
    return True


def end_step(job_description, job_status, step_description, end_status):
    """
    Description: End step with given description
    **Author**: alukiano
    **Parameters**:
      * *job_description* - step under job with given description
      * *job_status* - step under job with given status
      * *step_description* - end step with given description
      * *end_status* - end step with specific status False or True
    **Returns**: True, if ending job success,else False
    """
    job_obj = check_recent_job(True,
                               job_description,
                               job_status=job_status)[1]
    if not job_obj:
        logger.warn("Job with given description not exist")
        return False
    step_obj = step_by_description(job_obj, step_description)
    if not STEPS_API.syncAction(
            step_obj, "end", True,  succeeded=end_status
    ):
        return False
    return True
