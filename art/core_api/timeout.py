#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
# Authors: Avi Tal <atal@redhat.com>
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

import signal
import time
import logging


logger = logging.getLogger(__name__)


class TimeoutExpiredError(Exception):
    message = 'Timed Out'

    def __init__(self, *value):
        self.value = value

    def __str__(self):
        return "%s: %s" % (self.message, repr(self.value))


def timeout(seconds, error_message='signal alarm timeout validation'):
    '''
    Author: atal
    Timeout decorator use to enforce timeout on a fucntion via signal alaram.
    A very important notes:
        1. Never use this decortor other than in main thread.
        2. Support only unix systems.
        3. Nested time decorator will raise RuntimeError
    make sure you handle FunctionTimeoutError exception well
    >>> @timeout(5, 'failed due to timeout')
    >>> foo():
    >>>     import time
    >>>     time.sleep(10)
    >>> foo()
    TimeoutExpiredError
    '''
    def decorator(func):
        def _is_sigalrm_exists():
            return signal.getsignal(signal.SIGALRM) is not signal.SIG_DFL

        def _timeout_handler(signum, frame):
            raise TimeoutExpiredError(error_message)

        def new_f(*args, **kwargs):
            if _is_sigalrm_exists():
                raise RuntimeError('SIGALRM was already activated.')
            old = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.signal(signal.SIGALRM, old)
            signal.alarm(0)
            return result
        new_f.func_name = func.func_name
        return new_f
    return decorator


class TimeoutingSampler(object):
    '''
    Samples the function output.

    This is a generator object that at first yields the output of function
    `func`. After the yield, it either raises instance of `timeout_exc_cls` or
    sleeps `sleep` seconds.

    Yielding the output allows you to handle every value as you wish.

    Feel free to set the instance variables.

    Author: jhenner
    '''

    def __init__(self, timeout, sleep, func, *func_args, **func_kwargs):
        '''
        See the doc for TimeoutingSampler.
        '''

        self.timeout = timeout
        ''' Timeout in seconds. '''
        self.sleep = sleep
        ''' Sleep interval seconds. '''

        self.func = func
        ''' A function to sample. '''
        self.func_args = func_args
        ''' Args for func. '''
        self.func_kwargs = func_kwargs
        ''' Kwargs for func. '''

        self.start_time = None
        ''' Time of starting the sampling. '''
        self.last_sample_time = None
        ''' Time of last sample. '''

        self.timeout_exc_cls = TimeoutExpiredError
        ''' Class of exception to be raised.  '''
        self.timeout_exc_args = (self.timeout,)
        ''' An args for __init__ of the timeout exception. '''
        self.timeout_exc_kwargs = {}
        ''' A kwargs for __init__ of the timeout exception. '''

    def __iter__(self):
        if self.start_time is None:
            self.start_time = time.time()
        while True:
            self.last_sample_time = time.time()
            yield self.func(*self.func_args, **self.func_kwargs)
            if self.timeout < (time.time() - self.start_time):
                raise self.timeout_exc_cls(*self.timeout_exc_args,
                                           **self.timeout_exc_kwargs)
            time.sleep(self.sleep)

    def waitForFuncStatus(self, result):
        '''
        Description: Get function and run it for given time until success or
                     timeout. (using __iter__ function)
        **Author**: myakove
        **Parameters**:
            * *result* - Expected result from func (True or False), for
                         positive/negative tests
        Example (calling updateNic function)::
        sample = TimeoutingSampler(timeout=60, sleep=1,
                                   func=updateNic, positive=True,
                                   vm=config.VM_NAME[0], nic=nic_name,
                                   plugged='true')
                if not sample.waitForFuncStatus(result=True):
                    raise NetworkException("Couldn't update NIC to be plugged")
        '''

        try:
            for res in self:
                if result == res:
                    return True
        except self.timeout_exc_cls:
            logger.error(
                "(%s) return incorrect status after timeout",
                self.func.__name__,
            )
            return False
