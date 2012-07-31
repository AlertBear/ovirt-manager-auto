#!/usr/bin/env python
import threading
import logging
import art.test_handler.settings as settings
from utilities.utils import readConfFile
logger = logging.getLogger('threads')

ACTIONCONF = "conf/actions.conf"
SECTION = 'ACTIONS'

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
     * targets - list of function names
     * params - list of dictionary's (params of targets)
     * async - how run threads (sync or async)
     Return Value: 1) When async is False - return all threads values
                   2) When async is True  - return list of treads
     '''
    actions = readConfFile(ACTIONCONF, SECTION)
    threads = []
    for i in range(len(targets)):
        if not targets[i].lower() in actions:
            raise ParallelException("Can't find %s in %s file" % (targets[i].lower(), ACTIONCONF))
        modules = actions[targets[i].lower()].split('.')
        importPackages = ".".join(modules[:-1])
        funcName = modules[-1]
        if modules[0] == 'utils':
            execCommand  = "from %s import %s" % (importPackages,funcName)
        else:
            execCommand = "from %s.%s import %s" % ( settings.opts['type'],importPackages,funcName)
        exec(execCommand)
        logger.debug("func: %s, params: %s", funcName, params[i])
        t = CreateThread(eval(funcName), **(params[i]))
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


def restartServiceRunRestCommand(vdsName, restCommand, rcmdKwargs={}, service="vdsmd", user='root', password='qum5net'):
    '''
     Description: run in parallel mode restart vdsmd service and any rest api command (given from ods file)
     Author: egerman
     Parameters:
     * vdsName - name of vdsm host
     * restCommand - any function from rest project
     * rcmdKwargs - all params of restCommand function
     * user - user name of vdsm host
     * password - password of vdsm host
     Return Value: True when all threads returned any values, False otherwise.
     '''
    targets = [restCommand, "toggleServiceOnHost"]
    kwargsToggleService = {"positive": True, "host": vdsName, "user" : user, "password" : password, "service" : service, "action" : "restart"}
    paramsList = []
    paramsList.append(rcmdKwargs)
    paramsList.append(kwargsToggleService)
    results = runParallel(targets, paramsList)

    if results.count(True) != len(targets):
        for i in range(len(targets)):
            if not results[i]:
                logging.error("Thread %s returned False value" % targets[i])
            return False
    return True

