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
import abc
import logging
import inspect
from collections import namedtuple
from utilities.utils import generateShortGuid
from art.core_api.apis_exceptions import APITimeout, EntityNotFound
import art.test_handler.settings as settings

# TODO: move default values to conf spec
DS_PATH = settings.opts.get('data_struct_mod')
DS_VALIDATE = DS_PATH

__import__(DS_PATH)
__import__(DS_VALIDATE)
data_st = sys.modules[DS_PATH]
data_st_validate = sys.modules[DS_VALIDATE]
parse = data_st.parseString

DEF_TIMEOUT = 900  # default timeout
DEF_SLEEP = 10  # default sleep
NEGATIVE_CODES = [400, 409, 500]
NEGATIVE_CODES_CREATE = NEGATIVE_CODES + [404]
HEADERS = 'headers'
CORRELATION_ID = 'Correlation-Id'
MAX_CORRELATION_ID_LENGTH = 50
logger = logging.getLogger('api_utils')

api_error = namedtuple('api_error', 'reason status detail')


def getDS(ds_name):
    if hasattr(data_st, ds_name):
        return getattr(data_st, ds_name)
    return None


class APIUtil(object):
    '''
    Basic class for API functionality
    '''
    __metaclass__ = abc.ABCMeta
    __api_methods = ['create', 'update', 'delete', 'syncAction']

    def __init__(self, element, collection, **kwargs):
        self.opts = kwargs['opts'] if 'opts' in kwargs else settings.opts
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

    @abc.abstractmethod
    def login(self):
        return

    # FIXME: when we will move to python 2.7: to use @abc.abstractclassmethod
    @classmethod
    @abc.abstractmethod
    def logout(cls):
        return

    @property
    def logger(self):
        return logging.getLogger(self.collection_name)

    def getCorrelationId(self):
        '''
        Description: builds unique correlation id
        Parameters: None
        Return: correlation id
        '''
        # backward compatibility
        if CORRELATION_ID in self.opts[HEADERS]:
            return self.opts[HEADERS][CORRELATION_ID]

        funcs_names_stack = [func[3] for func in inspect.stack()]
        api_func_name = filter(lambda func: func in self.__api_methods,
                               funcs_names_stack)[0]
        test_func_name = funcs_names_stack[funcs_names_stack.index(
            api_func_name) + 1]

        correlation_id = "_".join(
            [generateShortGuid(), test_func_name,
             api_func_name])[:MAX_CORRELATION_ID_LENGTH]

        return correlation_id

    def getReqMatrixParams(self, current=None):
        '''
        Description: build dict of matrix parameters for request
        Parameters:
           * current - boolean current value (True/False)
        Return: dict of parameters: correlation_id, current
        '''
        add_params = dict(correlation_id=self.getCorrelationId())
        if current is not None:
            add_params['current'] = current
        return add_params

    def makeAction(self, async, expiry, **params):
        '''
        Description: build action (post body for actions urls)
        Author: edolinin
        Parameters:
           * async - type of action (synchronic or not)
           * expiry - action axpiration time
        Return: action
        '''

        action = data_st.Action()
        action.async = str(async).lower()
        action.grace_period = data_st.GracePeriod()
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
        if objs:
            for obj in objs:
                propVal = getattr(obj, prop)
                if propVal == name_val:
                    return obj

        raise EntityNotFound("Entity '{0}' not found".format(name_val))

    def waitForQuery(self, query, event_id=None, timeout=DEF_TIMEOUT,
                     sleep=DEF_SLEEP, href=None):
        '''
        Waits until the query `xpath` on doc specified by `link` is evaluates
        as True.

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
        sampler.func_args = query, [200, 201], href, event_id

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
        except APITimeout:
            logger.error("(%s) return incorrect status after timeout"
                         % self.func.__name__)
            return False
