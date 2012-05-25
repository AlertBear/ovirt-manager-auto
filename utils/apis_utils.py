#!/usr/bin/env python

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

import sys
import time
from apis_exceptions import APITimeout, APICommandError, EntityNotFound
from time import strftime
import settings
import abc
import logging
from utils.data_structures import Action, GracePeriod

XSD_PATH = settings.opts['api_xsd']
DS_PATH = settings.opts['data_struct_mod']
__import__(DS_PATH)
data_st = sys.modules[DS_PATH]
parse = data_st.parseString

DEF_TIMEOUT = 900 # default timeout
DEF_SLEEP = 10 # default sleep

def getDS(ds_name):
    return getattr(data_st, ds_name)

class APIUtil(object):
    '''
    Basic class for API functionality
    '''
    __metaclass__ = abc.ABCMeta

    def __init__(self, element, collection, **kwargs):
        self.opts = settings.opts
        self.element_name = element
        self.collection_name = collection
     
    @abc.abstractmethod
    def create(self, entity, positive, **kwargs):
        return

    @abc.abstractmethod
    def update(self, hrefAll, href, entity, positive, **kwargs):
        return

    @abc.abstractmethod
    def delete(self, entity, positive, **kwargs):
        return

    @abc.abstractmethod
    def find(self, name, **kwargs):
        return

    @abc.abstractmethod
    def get(self, href, **kwargs):
        return

    @abc.abstractmethod
    def query(self, href, constraint, **kwargs):
        return

    @abc.abstractmethod
    def syncAction(self, entity, action, positive, **kwargs):
        return

    @abc.abstractmethod
    def waitForElemStatus(self, elm, status, **kwargs):
        return

    @abc.abstractmethod
    def getElemFromLink(self, elm, link_name, **kwagrs):
        return

    @property
    def logger(self):
        return logging.getLogger(self.collection_name)
    

    def makeAction(self, async, expiry, **params):
        '''
        Description: build action (post body for actions urls)
        Author: edolinin
        Parameters:
           * async - type of action (synchronic or not)
           * expiry - action axpiration time
        Return: action
        '''

        action = Action()
        action.async = str(async).lower()
        action.grace_period = GracePeriod()
        action.grace_period.expiry = expiry
        action.grace_period.absolute = 'false'
        for p in params:
            setattr(action, p, params[p])
        return action
    

    def getElemFromElemColl(self, elm, name_val, collection_name=None,
                                    elm_name=None, prop='name'):
        '''
        Description: get element from element's collection
        Parameters:
           * elm - element object
           * collection_name - collection name
           * elm_name - element name
           * name_val - name of element to loof for
        Return: element obj or None if not found
        '''
        if not collection_name:
            collection_name = self.collection_name

        if not elm_name:
            elm_name = self.element_name
            
        # get element's collection from element link
        objs = self.getElemFromLink(elm, collection_name, attr=elm_name)
        # get element by name
        for obj in objs:
            propVal = getattr(obj, prop)
            if propVal == name_val:
                return obj

        raise EntityNotFound("Entity '{0}' not found".format(name_val))


    def waitForQuery(self, query, event_id=None, timeout=DEF_TIMEOUT, sleep=DEF_SLEEP):
        '''
        Waits until the query `xpath` on doc specified by `link` is evaluates as
        True.

        Parameters:
            * query - query to wait for.
            * event_id - event id.
            * timeout - Maximal number of seconds to wait.
            * sleep - A sampling period.
        Author: jhenner
        '''

        MSG = 'Waiting for query `%s` and event_id %s up to %d seconds, sampling every %d second.'
        self.logger.info(MSG % (query, event_id, timeout, sleep))
        sampler = TimeoutingSampler(timeout, sleep, self.query)
        TIMEOUT_MSG_TMPL = "Timeout when waiting for query '{0}' on '{1}'"\
                                        .format(query, self.collection_name)
        sampler.timeout_exc_args = TIMEOUT_MSG_TMPL.format(query, event_id),
        sampler.func_args = query, [200, 201], None, event_id

        try:
            for sampleOk in sampler:
                if sampleOk:
                    return True
        except APITimeout:
            self.logger.error(TIMEOUT_MSG_TMPL)
            return False


class TimeoutingSampler(object):
    '''
    Samples the function output.

    This is a generator object that at first yields the output of function `func`.
    After the yield, it either raises instance of `timeout_exc_cls` or sleeps
    `sleep` seconds.

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

        self.timeout_exc_cls = APITimeout
        ''' Class of exception to be raised.  '''
        self.timeout_exc_args = ()
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
                raise self.timeout_exc_cls(
                        *self.timeout_exc_args,
                        **self.timeout_exc_kwargs)
            time.sleep(self.sleep)


class TestRunnerWrapper():
    '''
    Runs APIs functions not from run.py and without settings.conf.
    Required settings options are defined in constructor.

    Usage Example:
        from utils.restutils import TestRunnerWrapper
        wrapper = TestRunnerWrapper('10.35.113.80')
        try:
            status = wrapper.runCommand('rest.datacenters.addDataCenter','true',name='test',storage_type='NFS',version='2.2')
        except APICommandError:
            ...

    Author: edolinin
    '''

    def __init__(self, ip, **kwargs):
        '''
        Defines settings configuration required to run REST APIs functions
        Parameters:
        * ip - vdc ip
        * kwargs - dictionary with settings configurations, keys names are
        the same as in settings.conf, if omitted - defaults are set
        '''

        from utils.settings import opts
        import logging

        opts['host'] = ip

        opts['scheme'] = kwargs.get('scheme', 'https')
        opts['port'] = kwargs.get('port', '8443')
        opts['entry_point'] = kwargs.get('entry_point', 'api')
        opts['user'] = kwargs.get('user', 'vdcadmin')
        opts['user_domain'] = kwargs.get('user_domain', 'qa.lab.tlv.redhat.com')
        opts['password'] = kwargs.get('password', '123456')
        opts['type'] = kwargs.get('type', 'rest')
        opts['debug'] = kwargs.get('debug', 'DEBUG')
        opts['log'] = kwargs.get('log', "/var/tmp/%sTests%s.log" % (opts['type'], strftime('%Y%m%d_%H%M%S')))
        opts['urisuffix'] = ''
        opts['uri'] = '%(scheme)s://%(host)s:%(port)s/%(entry_point)s%(urisuffix)s/' \
            % opts

        opts['in_parallel'] = kwargs.get('in_parallel', [])
        opts['parallel_run'] = True if opts['in_parallel'] else False
        opts['standalone'] = kwargs.get('standalone', False)

        self.logger = logging.getLogger(__name__)
        print "Log file is initialized at {0}".format(opts['log'])


    @classmethod
    def runCommand(cls, action, *args, **kwargs):
        '''
        Runs REST APIs functions

        Parameters:
        * action - full path of the action which should be run
        * args - list of function's non-keyword arguments
        * kwargs - dictionary with function's keyword arguments

        Exceptions: raises APICommandError in case of error

        '''

        actionModulesNames = action.split(".")
        funcPackage = ".".join(actionModulesNames[:-1])
        funcName = actionModulesNames[-1]

        exec("from " + funcPackage + " import " + funcName)

        params = ''
        for arg in args:
            params = "{0},{1!r}".format(params, arg)

        for paramName, paramVal in kwargs.items():
            params = "{0},{1}={2!r}".format(params, paramName, paramVal)
        cmd = funcName + "(" + params.strip(' ,') + ")"

        try:
            return eval(cmd)
        except Exception as e:
            raise APICommandError(cmd, e)
