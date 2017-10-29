#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2010 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

'''
Jobs support.
Author: jhenner
'''

import copy
from Queue import Queue, Empty, Full
from threading import Thread, current_thread, Event as tEvent
import logging
import sys
from time import time as _time

from art.core_api.timeout import TimeoutExpiredError


class Event(object):
    """
    Nice class that is providing events mechanism for Python.
    """
    def __init__(self):
        self.handlers = set()

    def handle(self, handler):
        """Attach new event handler."""
        self.handlers.add(handler)
        return self

    def unhandle(self, handler):
        """Detach existing event handler."""
        try:
            self.handlers.remove(handler)
        except ValueError:
            raise ValueError("The subscriber does not handle this event!")
        return self

    def invoke(self, *args, **kwargs):
        """Invoke existing event handlers."""
        for handler in self.handlers:
            if handler is not None:
                handler(*args, **kwargs)

    def getHandlersAmount(self):
        """Return amount of handlers."""
        return len(self.handlers)

    __iadd__ = handle
    __isub__ = unhandle
    __call__ = invoke
    __len__ = getHandlersAmount


class ReturnableEvent(Event):
    """
    Support for event which returns output.
    """
    def invoke(self, *args, **kwargs):
        """Invoke first existing event handler and return its output."""
        for handler in self.handlers:
            if handler is not None:
                return handler(*args, **kwargs)

    __call__ = invoke


class QueueWithTimeout(Queue):
    """
    In addition to Queue's functionality, it allows to specify a timeout when
    waiting for jobs to finish.
    """

    def join(self, timeout=None):
        """
        Works the same as Queue.join() except when given a timeout in which
        case an exception is raised if the jobs don't finish after the
        specified timeout.
        """
        if not timeout:
            Queue.join(self)

        else:
            self.all_tasks_done.acquire()
            try:
                endtime = _time() + timeout
                while self.unfinished_tasks:
                    remaining = endtime - _time()
                    if remaining <= 0.0:
                        msg = "%s seconds expired" % timeout
                        raise TimeoutExpiredError(msg)
                    self.all_tasks_done.wait(remaining)
            finally:
                self.all_tasks_done.release()


class Job(object):
    '''
    A unit of work.

    Any job can be in states:
     * 'INITED'   - The job has not yet been started.
     * 'RUNNING'  - Job is being processed.
     * 'FINISHED' - Job finished either with success or with exception.

    Every job has method `run` which can be redefined to the actual job
    code, or some callable can be passed as a `target` param.

    When the job is in 'FINISHED' state, the return value is available as
    `result`.

    Author: jhenner
    '''
    def __init__(self, target=None, args=(), kwargs={}):
        '''
        Params:
         * target - A callable that will be called as a content of the job.
         * args   - Args for the `target`.
         * kwargs - Kwargs for the `target`.
        '''
        self.result = None
        self.exception = None
        self.target = target if target else self.run
        self.args = args
        self.kwargs = kwargs

        self.running_event = Event()
        ''' Triggered when job starts. Called as running_event(). '''

        self.exception_event = Event()
        '''
        Triggered when exception occurs. Called as exception_event(exc).
        '''

        self.finished_event = Event()
        '''
        Triggered when job finished (or exception caught). Called as
        finished_event(sys.exc_info()).
        '''

        self.state = 'INITED'

    def start(self):
        '''
        Starts the job.
        Author: jhenner
        '''
        self.state = 'RUNNING'
        self.running_event()
        try:
            self.result = self.target(*self.args, **self.kwargs)
        except Exception:
            self.exception_caught(sys.exc_info())
        finally:
            self.state = 'FINISHED'
            self.finished_event()

    def run(self):
        '''
        Redefine that to specify what the job should do.
        Author: jhenner
        '''
        pass

    def exception_caught(self, exc_info):
        ''' Called when some Exception propagate out from `self.target`.'''
        self.exception = exc_info[1]
        logging.exception(exc_info[1])
        self.exception_event(exc_info)

    def __str__(self):
        result = self.result if self.state == 'FINISHED' else '?'
        return (
            'Job(%s, %s, %s) = %s\t%s' % (
                self.target, self.args, self.kwargs, result, self.state
            )
        )


class JobsSet(object):
    '''
    Creates a job Queue and spawns one or more worker threads taking the jobs
    from the queue.

    Author: jhenner
    '''
    def __init__(self, num_worker_threads=None, queue_size=0):
        self.num_worker_threads = num_worker_threads
        self.__queue = QueueWithTimeout(queue_size)
        self.threads = list()
        self.__all_done = tEvent()
        self.__any_done = tEvent()

    @property
    def allDone(self):
        '''
        True if all Jobs have been finished.
        Author: jhenner
        '''
        return self.__all_done.is_set()

    def waitUntilAllDone(self, time=None):
        '''
        Blocks until all_done is True.
        Author: jhenner
        '''
        self.__all_done.wait(time)
        logging.debug("waitUntilAllDone release")

    def waitUntilAnyDone(self, time=None):
        return self.__any_done.wait(time)

    def fillQueue(self, job):
        newJobs = []
        try:
            while True:
                newJob = copy.copy(job)
                self.addJobs((newJob,), False)
                newJobs.append(newJob)
        except Full:
            pass
        return newJobs

    def addJobs(self, jobs, block=True):
        '''
        Add jobs to this JobsSet.
        Author: jhenner
        '''
        for job in jobs:
            self.__queue.put(job, block)
            job.finished_event += self.__jobDoneHandler
            job.finished_event += self.__any_done.set

    def start(self):
        ''' Spawn the workers in their threads. '''
        if not self.num_worker_threads or self.num_worker_threads < 1:
            self.num_worker_threads = self.__queue.unfinished_tasks
        self.__all_done.clear()

        # Create the threads and spawn the workers.
        for _ in range(self.num_worker_threads):
            t = WorkerThread(self.__queue, 'JobsSet')
            self.threads += t,
            # Allow python exit even that this thread haven't finished yet.
            t.daemon = True
            t.start()

    def __stopWorkers(self):
        logging.debug("Stopping %d workers.", len(self.threads))
        for thread in self.threads:
            logging.debug(
                "Stopping %s. Actual state: %s", thread, thread.state
            )
            thread.stop()
            logging.debug("Worker %s state: %s", thread, thread.state)
        return

    def join(self, timeout=None):
        '''
        Wait for all jobs done, then quit the workers and join their threads.
        Author: jhenner
        '''
        logging.debug("Joining queue.")
        self.__queue.join(timeout)
        self.__stopWorkers()
        for t in self.threads:
            logging.debug("Joining thread %s.", t)
            t.join()

    def __jobDoneHandler(self):
        '''
        Emits `all_done` if everything done.
        Author: jhenner
        '''
        self.__queue.task_done()
        if 0 == self.__queue.unfinished_tasks:
            logging.debug('JobsSet %s All tasks finished.', self)
            self.__all_done.set()
        else:
            logging.debug(
                'JobsSet %s still waiting for %d jobs.',
                self, self.__queue.unfinished_tasks
            )


class Worker(object):
    '''
    Takes Jobs from queue and executes it.

    Any job can be in states:
     * 'RUNNING' - Worker is working (processing the jobs in queue).
     * 'STOPPED' - Worker was stopped and will not process further jobs until
                   started again.
     * 'STOPPING' - Worker will stop after current job finishes.

    Author: jhenner
    '''

    SUICIDE_JOB = Job()

    def __init__(self, queue, state_poll_intrv=.2):
        '''
        Parameters:
         * queue - A queue to get the Jobs from.
         * state_poll_intrv - Seconds how often to poll for status change
                              caused by stop().
        Author: jhenner
        '''
        self.queue = queue
        self.state = None
        self.state_poll_intrv = state_poll_intrv

    def stop(self):
        '''
        Wait for the current workers Job to finish and stop the worker then.
        Author: jhenner
        '''
        self.state = 'STOPPING'

    def __iterjobs(self):
        while self.state == 'RUNNING':
            try:
                job = self.queue.get(timeout=self.state_poll_intrv)
            except Empty:
                # Right now, task queue is still empty, but we need to timeout
                # the self.queue.get in order to not wait infinitely.
                # We need to check the self.state sometimes.
                continue
            yield job

    def run(self):
        '''
        Keeps taking jobs from the queue and calls start() on each of them
        until WorkersDeath is raised. All derivatives of Exception are caught
        and reported.

        Can be stopped either by sending a SUICIDE_JOB, or with a stop()
        method.

        Author: jhenner
        '''
        self.state = 'RUNNING'
        for job in self.__iterjobs():
            if job is self.SUICIDE_JOB:
                logging.debug(
                    'Worker in thread %s stopped.', current_thread()
                )
                break
            try:
                job.start()
            except Exception:
                pass
        self.state = 'STOPPED'


class WorkerThread(Worker, Thread):
    '''
    Python's threading implementation of the Worker.

    See: Worker.
    '''
    def __init__(self, queue, name):
        Worker.__init__(self, queue)
        Thread.__init__(self, name=name)


def main():
    class Writer(Job):
        def __init__(self, name):
            self.name = name
            super(Writer, self).__init__()

        def run(self):
            N = 50
            for i in range(N):
                for j in xrange(100):
                    for k in xrange(100):
                        pass
                print '%s [%s%s]' % (self, "=" * i, " " * (N-i))
            return 'Finished fine.'

        def __str__(self):
            return 'Writer %d is %s' % (id(self), self.state)

    logging.basicConfig(level=logging.DEBUG)

    print 'Start.'

    js = JobsSet(3)
    jobs = [Writer(i) for i in range(13)]
    js.addJobs(jobs)
    js.start()
    while not js.allDone:
        js.waitUntilAllDone(1)
        print
        print '\n'.join(str(j) for j in jobs)
        print
    js.join()
    print 'Success.'


if __name__ == '__main__':
    main()
