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
import abc
import logging
from collections import namedtuple

from utilities.utils import generateShortGuid
from timeout import TimeoutingSampler as _TimeoutingSampler
from art.core_api.apis_exceptions import APITimeout, EntityNotFound
import art.test_handler.settings as settings

DS_PATH = settings.ART_CONFIG.get('RUN').get('data_struct_mod')
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
POSITIVE_CODES = [200, 201]
POSITIVE_CODES_CREATE = POSITIVE_CODES + [202]
HEADERS = 'headers'
CORRELATION_ID = 'Correlation-Id'
MAX_CORRELATION_ID_LENGTH = 50
logger = logging.getLogger('api_utils')
flow_logger = logging.getLogger('art.flow')  # CI logger

api_error = namedtuple('api_error', 'reason status detail')


class ApiOperation(object):
    '''
    Description: Class to represent the API Operations (like Enum)
    Author: khakimi
    '''
    create = 'create'
    update = 'update'
    delete = 'delete'
    syncAction = 'syncAction'


def getDS(ds_name):
    if hasattr(data_st, ds_name):
        return getattr(data_st, ds_name)
    return None


class APIUtil(object):
    '''
    Basic class for API functionality
    '''
    __metaclass__ = abc.ABCMeta
    __api_methods = [ApiOperation.create, ApiOperation.update,
                     ApiOperation.delete, ApiOperation.syncAction]

    def __init__(self, element, collection, **kwargs):
        self.opts = kwargs.get('opts') or settings.ART_CONFIG
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
    def extract_attribute(self, response, attr):
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

    def getCorrelationId(self, api_operation=None):
        '''
        Description: builds unique correlation id
        Parameters:
            * api_operation - the api operation performed
        Return: correlation id
        '''
        # backward compatibility
        if CORRELATION_ID in self.opts[HEADERS]:
            return self.opts[HEADERS][CORRELATION_ID]

        if api_operation is None:
            api_operation = 'unknown_api'
        correlation_id = "_".join(
            [
                self.collection_name,
                api_operation,
                generateShortGuid()
            ]
        )[:MAX_CORRELATION_ID_LENGTH]

        return correlation_id

    def getReqMatrixParams(self, current=None, api_operation=None):
        '''
        Description: build dict of matrix parameters for request
        Parameters:
           * current - boolean current value (True/False)
           * api_operation - the api operation performed
        Return: dict of parameters: correlation_id, current
        '''
        add_params = dict(correlation_id=self.getCorrelationId(api_operation))
        if current is not None:
            add_params['current'] = current
        return add_params

    def makeAction(self, async, action_expiry, **params):
        # FIXME: This async parametr will not be friend with py3.5
        '''
        Description: build action (post body for actions urls)
        Author: edolinin
        Parameters:
           * async - type of action (synchronic or not)
           * action_expiry - action axpiration timeout
        Return: action
        '''

        action = data_st.Action()
        action.async = str(async).lower()
        action.grace_period = data_st.GracePeriod()
        action.grace_period.expiry = action_expiry
        action.grace_period.absolute = 'false'
        for p in params:
            setattr(action, p, params[p])
        return action

    def getElemFromElemColl(
        self, elm, name_val, collection_name=None, elm_name=None,
        prop='name', all_content=False
    ):
        '''
        Description: get element from element's collection
        Parameters:
           * elm - element object
           * collection_name - collection name
           * elm_name - element name
           * name_val - name of element to look for
           * all_content - Get object with all-content
        Return: element obj or None if not found
        '''
        if all_content:
            self.api.headers['All-content'] = True

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

        MSG = ('Waiting for query `%s` and event_id %s up to %d seconds,'
               'sampling every %d second.')
        self.logger.info(MSG % (query, event_id, timeout, sleep))
        sampler = TimeoutingSampler(timeout, sleep, self.query)
        TIMEOUT_MSG_TMPL = ("Timeout when waiting for query '{0}' on '{1}'"
                            .format(query, self.collection_name))
        sampler.timeout_exc_args = TIMEOUT_MSG_TMPL.format(query, event_id),
        sampler.func_args = query, [200, 201], href, event_id

        try:
            for sampleOk in sampler:
                if sampleOk:
                    return True
        except APITimeout:
            self.logger.error(TIMEOUT_MSG_TMPL)
            return False

    def print_error_msg(self, operation, status=None, reason=None,
                        detail=None, trace=None, positive=True):
        """
        Description: print detailed error message.
        :param operation: the operation which failed (create/update...)
        :type operation: str
        :param status: status code (400...)
        :type status: str
        :param reason: error reason (Bad Request...)
        :type reason: str
        :param detail: error details
        :type detail: str
        :param trace: stack trace
        :type trace: str
        :param positive: True if it is Not as expected otherwise False
        :type positive: bool
        """
        error_msg = []
        positive_msg = '{0} as expected:\n'.format(' NOT' if positive else '')
        error_msg.append('Failed to {0} element'.format(operation))
        error_msg.append(positive_msg)
        error_msg.append('\tStatus: {0}\n'.format(status) if status else '')
        error_msg.append('\tReason: {0}\n'.format(reason) if reason else '')
        error_msg.append('\tDetail: {0}\n'.format(detail) if detail else '')
        error_msg.append('\tTrace: {0}\n'.format(trace) if trace else '')

        if positive:
            logger.error(''.join(error_msg))
            flow_logger.error(''.join(error_msg))  # CI logger
        else:
            logger.warn(''.join(error_msg))


class TimeoutingSampler(_TimeoutingSampler):

    def __init__(self, *args, **kwargs):
        super(TimeoutingSampler, self).__init__(*args, **kwargs)
        self.timeout_exc_cls = APITimeout
