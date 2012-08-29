#!/usr/bin/env python
# FIXME: generally this should be rewrited. or replaced by utilities.jobs module
import threading
import logging
import art.test_handler.settings as settings
from utilities.utils import readConfFile
logger = logging.getLogger('threads')

class ParallelException(Exception):
    pass


class ThreadSafeDict(dict):
    def __init__(self, *args, **kwargs):
        super(ThreadSafeDict, self).__init__(*args, **kwargs)
        self._lock = threading.Lock()

    def __enter__(self):
        self._lock.acquire()

    def __exit__(self, type, value, traceback):
        self._lock.release()


class CreateThread(threading.Thread):
    '''
     Description: create thread class
     Author: egerman
     '''
    retValue = None
    def __init__(self, target, **kwargs):
        '''
        Parameters:
        *target - function name as string
        **kwargs - params of target
        '''
        self._target = target
        self._kwargs = kwargs
        threading.Thread.__init__(self)

    def run(self):
        self.retValue = self._target(**(self._kwargs))

def runParallel(targets, params, async=False):
    '''
     Description: run functions in parallel mode
     Author: egerman
     Parameters:
     * targets - list of functions
     * params - list of dictionary's (params of targets)
     * async - how run threads (sync or async)
     Return Value: 1) When async is False - return all threads values
                   2) When async is True  - return list of treads
     '''
    threads = []
    for i in range(len(targets)):
        t = CreateThread(targets[i], **(params[i]))
        t.start()
        logger.info("Thread %s started", funcName)
        threads.append(t)

    if async:
        return threads

    for t in threads:
        t.join()

    results = []
    for t in threads:
        results.append(t.retValue)

    return results


