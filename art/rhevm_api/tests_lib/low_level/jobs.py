from art.core_api import is_action
from art.core_api.apis_utils import data_st
from art.rhevm_api.utils.test_utils import get_api
import logging
import time

JOBS_API = get_api('job', 'jobs')
STEPS_API = get_api('step', 'steps')
LOGGER = logging.getLogger(__name__)
JOB_STATUSES = ['STARTED', 'FINISHED', 'FAILED', 'ABORTED', 'UNKNOWN']
STEP_TYPES = ['VALIDATING', 'EXECUTING', 'FINALIZING']


# noinspection PyUnusedLocal
@is_action()
def check_recent_job(positive, description, last_jobs_num=None,
                     job_status='finished'):
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
    jobs = JOBS_API.get(absLink=False)
    last_job = None
    job_time = None
    if not description:
        LOGGER.warn("Description is empty")
        return False, None, None
    if last_jobs_num:
        last_jobs_num = int(last_jobs_num)
        if len(jobs) > last_jobs_num:
            jobs = jobs[:last_jobs_num]
    for job in jobs:
        status = job.get_status().get_state().lower()
        if (description in job.get_description()
                and status == job_status.lower()):
            last_time = str(job.get_start_time()).split(".")[0].split("T")[1]
            last_time_obj = time.strptime(last_time, "%H:%M:%S")
            # Check if no newer job with the same description
            if last_time_obj > job_time:
                last_job = job
                job_time = last_time_obj
    if last_job:
        return True, last_job, (job_time.tm_hour,
                                job_time.tm_min,
                                job_time.tm_sec)
    else:
        return False, None, None


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
    for status in JOB_STATUSES:
        job_obj = check_recent_job(True,
                                   job_description,
                                   job_status=status)[1]
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
    steps_obj = JOBS_API.getElemFromLink(job_obj, link_name='steps',
                                         get_href=True)
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
    steps_obj = JOBS_API.get(job.get_link()[0].get_href()).get_step()
    if not steps_obj:
        LOGGER.warn("No step with description %s"
                    " under job with description %s",
                    step_description, job.get_description())
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
    if not STEPS_API.syncAction(step_obj, "end", True,  succeeded=end_status):
        return False
    return True

# @is_action()
# def clear_job(job_description, job_status):
#     job_obj = check_recent_job(True,
#                                job_description,
#                                job_status=job_status)[1]
#     if not job_obj:
#         LOGGER.warn("Job with given description not exist")
#         return False
#     status = JOBS_API.syncAction(job_obj, "clear", True)
#     if not status:
#         LOGGER.warn("Clearing of job failed")
#     return True
