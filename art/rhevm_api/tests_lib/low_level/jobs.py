import re
from art.core_api import is_action
from art.core_api.apis_utils import data_st, TimeoutingSampler
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts
import logging

ENUMS = opts['elements_conf']['RHEVM Enums']

JOBS_API = get_api('job', 'jobs')
STEPS_API = get_api('step', 'steps')
LOGGER = logging.getLogger(__name__)
TASK_TIMEOUT = 600
JOB_TIMEOUT = 1200
TASK_POLL = 5


@is_action()
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
    jobs = JOBS_API.get(absLink=False)[:last_jobs_num]
    if not description:
        LOGGER.warn("Description is empty")
        return False, None, None

    job_status = job_status.lower()
    jobs = filter(lambda j: (description in j.get_description() and
                             j.get_status().get_state().lower() == job_status),
                  jobs)
    last_job = max(jobs, key=lambda j: j.get_start_time())

    if last_job:
        return True, last_job
    else:
        return False, None


@is_action()
def get_active_jobs(job_descriptions=None):
    """
    Check if all/requested jobs have been completed

    __author__ = 'ratamir'
    :param job_descriptions: job descriptions that needs to be sampled
    :type job_descriptions: list
    :return: list of job objects
    :rtype: list
    """
    jobs = JOBS_API.get(absLink=False)
    # This is a W/A for BZ1248055, due to some GET request to /api/jobs
    # returning 400, just return a list of objects so wait_for_jobs() will
    # continue to call this funcion until the time out
    if jobs is None:
        LOGGER.warning("GET /api/jobs returned 400")
        return [True]

    jobs = filter(
        lambda job: (
            job.get_status().get_state() == ENUMS['job_started']
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

    LOGGER.info("Active jobs: %s", [job.get_description() for job in jobs])
    return jobs


@is_action("waitForJobs")
def wait_for_jobs(job_descriptions=None, timeout=JOB_TIMEOUT, sleep=TASK_POLL):
    """
    Waits until all/requested jobs in data-center have completed

    __author__ = 'ratamir'
    :param job_descriptions: job descriptions that needs to be sampled
    :type job_descriptions: list
    :param timeout: max seconds to wait
    :type timeout: int
    :param sleep: polling interval
    :type sleep: int
    :raise: TimeoutExpiredError
    """
    LOGGER.info("Waiting for jobs %s", job_descriptions)
    sampler = TimeoutingSampler(
        timeout, sleep, get_active_jobs, job_descriptions
    )
    for jobs in sampler:
        if not jobs:
            LOGGER.info("All jobs are gone")
            return


@is_action()
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


@is_action()
def add_step(job_description, step_description,
             step_type, step_state, parent_step_description=None):
    """
    Description: Add new step to job or step with given description
    **Author**: alukiano
    **Parameters**:
      * *step_description* - Name of step
      * *job_description* - Name of job to add step
      * *step_type* - type of step, one of
        ['VALIDATING', 'EXECUTING', 'FINALIZING']
      * *step_state* - state of step, one of
        ['STARTED', 'FINISHED', 'FAILED', 'ABORTED', 'UNKNOWN']
      * *parent_step_description* - add sub-step to step with given description
    **Returns**: True, if job adding job was success, else False
    """
    job_obj = None
    parent_step_obj = None
    for status in [ENUMS['job_started'], ENUMS['job_finished'],
                   ENUMS['job_failed'], ENUMS['job_aborted'],
                   ENUMS['job_unknown']]:
        job_obj = check_recent_job(True, job_description, job_status=status)[1]
        if job_obj:
            if parent_step_description:
                parent_step_obj = step_by_description(job_obj,
                                                      parent_step_description)
                if parent_step_obj:
                    break
            else:
                break
    if not job_obj:
        LOGGER.error("No job with given description found")
        return False
    if parent_step_description and not parent_step_obj:
        LOGGER.error("No parent step with given description found")
        return False
    steps_obj = STEPS_API.getElemFromLink(job_obj, get_href=True)
    status_obj = data_st.Status(state=step_state)
    step_obj = data_st.Step(description=step_description,
                            job=job_obj,
                            parent_step=parent_step_obj,
                            status=status_obj,
                            type_=step_type.lower())
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
        LOGGER.warn(warn_msg, step_description, job.get_description())
    for step in steps_obj:
        if step_description in step.get_description():
            return step
    return None


@is_action()
def end_job(job_description, job_status, end_status):
    """
    Description: End job with given description
    **Author**: alukiano
    **Parameters**:
      * *job_description* - description of job, that you want to end
      * *job_status* - status of job, that you want to end
      * *end_status* - end job with specific status
        ['STARTED', 'FINISHED', 'FAILED', 'ABORTED', 'UNKNOWN']
    **Returns**: True, if ending job success
            False, else
    """
    status_obj = data_st.Status(state=end_status)
    job_obj = check_recent_job(True,
                               job_description,
                               job_status=job_status)[1]
    if not job_obj:
        LOGGER.warn("Job with given description not exist")
        return False
    if not JOBS_API.syncAction(job_obj, "end", True, status=status_obj):
        return False
    return True


@is_action()
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
        LOGGER.warn("Job with given description not exist")
        return False
    step_obj = step_by_description(job_obj, step_description)
    if not STEPS_API.syncAction(
            step_obj, "end", True,  succeeded=end_status
    ):
        return False
    return True


@is_action()
def clear_job(job_description, job_status):
    job_obj = check_recent_job(True, job_description, job_status=job_status)[1]
    if not job_obj:
        LOGGER.warn("Job with given description not exist")
        return False
    status = JOBS_API.syncAction(job_obj, "clear", True)
    if not status:
        LOGGER.warn("Clearing of job failed")
    return True
