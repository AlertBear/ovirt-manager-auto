from art.core_api import is_action
from art.core_api.apis_utils import data_st
from art.rhevm_api.utils.test_utils import get_api
import logging
import re

JOBS_API = get_api('job', 'jobs')
LOGGER = logging.getLogger(__name__)
job_statuses = ['STARTED', 'FINISHED', 'FAILED', 'ABORTED', 'UNKNOWN']
step_states = ['VALIDATING', 'EXECUTING', 'FINALIZING']


# noinspection PyUnusedLocal
@is_action()
def check_recent_job(positive, description, last_jobs_num=None,
                     job_status='finished'):
    '''
    Description: Check if in recent jobs exist job with given description
    Author: alukiano
    Parameters:
      * description - search for job with given description
      * last_jobs_num - number of recent jobs you want search in, if None,
        check all exist jobs
      * job_status - to job must be given state
    Return: True if exist job with given description, job and job time
            Else return False, None, None
    '''
    jobs = JOBS_API.get(absLink=False)
    last_job = None
    job_time = None
    last_minute = 0
    last_second = 0
    last_hour = 0
    if last_jobs_num:
        if len(jobs) > int(last_jobs_num):
            jobs = jobs[:int(last_jobs_num)]
    for job in jobs:
        if description in job.get_description() \
           and job.get_status().get_state().lower() == job_status:
            last_time = re.findall(r'\d+:\d+:\d+', str(job.get_start_time()))
            #Check if no newer job with the same description
            if last_time[0].split(":")[0] > last_hour or\
                    (last_time[0].split(":")[0] == last_hour
                     and (last_time[0].split(":")[1] > last_minute
                          or (last_time[0].split(":")[1] == last_minute
                              and last_time[0].split(":")[2] > last_second))):
                last_hour = last_time[0].split(":")[0]
                last_minute = last_time[0].split(":")[1]
                last_second = last_time[0].split(":")[2]
                last_job = job
                job_time = (last_hour, last_minute, last_second)
    if last_job:
        return True, last_job, job_time
    else:
        return False, None, None


@is_action()
def addJob(description, auto_cleared=True):
    '''
    Description: Add new job with given description
    Author: alukiano
    Parameters:
      * description - Name of job
      * auto_cleared - if True, job will automatically removed from tasks,
       after define time(take from database)
       if False, you must remove job from tasks by yourself
    Return: True, if job adding job was success
            False, else
    '''
    if not description:
        LOGGER.warn("No job description")
        return not False
    job_obj = data_st.Job(description=description,
                          auto_cleared=auto_cleared)
    expected_job = data_st.Job(description=description,
                               auto_cleared=auto_cleared)
    status = JOBS_API.create(job_obj, True, expectedEntity=expected_job)[1]
    if not status:
        LOGGER.warn("Adding job failed")
        return False
    return True


@is_action()
def addStep(job_description, step_description,
            step_type, step_state, parent_step_description=None):
    '''
    Description: Add new step to job or step with given description
    Author: alukiano
    Parameters:
      * step_description - Name of step
      * job_description - Name of job to add step
      * type - type of step, one of ['VALIDATING', 'EXECUTING', 'FINALIZING']
      * state - state of step, one of
      ['STARTED', 'FINISHED', 'FAILED', 'ABORTED', 'UNKNOWN']
      * parent_step_description - add sub-step to step with given description
    Return: True, if job adding job was success
            False, else
    '''
    job_obj = None
    parent_step_obj = None
    if not step_description:
        LOGGER.warn("No step description")
        return False
    if not step_type or step_type not in step_states:
        LOGGER.warn("Step type not correct")
        return False
    if not step_state or step_state not in job_statuses:
        LOGGER.warn("Step status not correct")
        return False
    if not job_description:
        LOGGER.warn("Non job description")
        return False
    for status in job_statuses:
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
        LOGGER.warn("No job with given description found")
        return False
    if parent_step_description and not parent_step_obj:
        LOGGER.warn("No parent step with given description")
        return False
    status_obj = data_st.Status(state=step_state)
    step_obj = data_st.Step(description=step_description,
                            job=job_obj,
                            parent_step=parent_step_obj,
                            status=status_obj,
                            type=step_state)
    expected_step = data_st.Step(description=step_description,
                                 job=job_obj,
                                 parent_step=parent_step_obj,
                                 status=status_obj,
                                 type=step_state)
    status = JOBS_API.create(step_obj, True, expectedEntity=expected_step)[1]
    if not status:
        LOGGER.warn("Adding step failed")
        return False
    return True


def step_by_description(job, step_description):
    '''
    Description: Look for step under job with given description
    Author: alukiano
    Parameters:
      * job - under this job looking for step
      * step_description - looking for step with this description
    Return: if step with given description exist, return step object
            else, return None
    '''
    steps = JOBS_API.getElemFromLink(elm=job, link_name='step')
    for step in steps:
        if step_description in step.get_decription():
            return step
    return None


@is_action()
def endJob(job_description, job_status, force=False):
    job_obj = check_recent_job(True,
                               job_description,
                               job_status=job_status)[1]
    if not job_obj:
        LOGGER.warn("Job with given description not exist")
        return False
    status = JOBS_API.syncAction(job_obj, "end", True, force=force)
    if not status:
        LOGGER.warn("Ending of job failed")
    return True