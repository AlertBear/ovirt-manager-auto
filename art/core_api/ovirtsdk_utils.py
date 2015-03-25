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

import time
import logging
from art.core_api import validator, measure_time
from art.core_api.apis_utils import data_st, NEGATIVE_CODES, DEF_TIMEOUT, \
    DEF_SLEEP, ApiOperation
from art.core_api.apis_exceptions import EntityNotFound
from art.core_api.apis_exceptions import APIException, APILoginError
from ovirtsdk import api as sdkApi
from ovirtsdk.xml import params as sdk_params
from ovirtsdk.infrastructure.errors import RequestError, DisconnectedError
from art.core_api.apis_utils import APIUtil

logger = logging.getLogger(__name__)

PROPERTIES_MAP = {
    'type_': 'type',
}


def print_connection_method(kwargs):
    '''
    print the connection method
    :param kwargs: all method arguments
    :type kwargs: dict
    '''
    conn_cmd = ["{0}={1}, ".format(k, v) for k, v in kwargs.iteritems()]
    logger.info("Connect: sdkApi.API({0})".format("".join(conn_cmd)))


class SdkUtil(APIUtil):
    '''
    Implements SDK APIs methods
    '''
    _sdkInit = None

    def __init__(self, element, collection):
        super(SdkUtil, self).__init__(element, collection)
        self.login()

    def login(self):
        """
        Description: login to python sdk.
        Author: imeerovi
        Parameters:
        Returns:
        """
        if not self._sdkInit:
            user_with_domain = '{0}@{1}'.format(self.opts['user'],
                                                self.opts['user_domain'])
            kwargs = dict()
            kwargs.update(
                url=self.opts['uri'],
                username=user_with_domain,
                password=self.opts['password'],
                persistent_auth=self.opts['persistent_auth'],
                session_timeout=self.opts['session_timeout'],
                renew_session=True,
                filter=self.opts['filter'],
            )
            if self.opts['secure']:
                kwargs.update(
                    key_file=self.opts['ssl_key_file'],
                    cert_file=self.opts['ssl_cert_file'],
                    ca_file=self.opts['ssl_ca_file'],
                    )
            else:
                kwargs.update(insecure=True)

            print_connection_method(kwargs)
            try:
                self.api = sdkApi.API(**kwargs)
            except (RequestError, DisconnectedError) as e:
                raise APILoginError(e)

            self.__class__._sdkInit = self.api

        else:
            self.api = self._sdkInit

    @classmethod
    def logout(cls):
        """
        Description: logout from python sdk.
        Author: imeerovi
        Parameters:
        Returns:
        """
        if cls._sdkInit:
            try:
                cls._sdkInit.disconnect()
            except Exception as e:
                raise APIException(e, 'logout from python sdk failed')
            cls._sdkInit = None

    def get(self, collection=None, **kwargs):
        '''
        Description: get collection by its name
        Author: edolinin
        Parameters:
           * collection - collection name to get
        Return: parsed GET response
        '''

        href = kwargs.pop('href', None)
        if href is not None:
            if href == '':
                return self.api
            else:
                # TODO - remove this work-around when solving problem of
                # same returned objects in all engines
                return href

        if not collection:
            collection = self.collection_name

        self.logger.debug("GET request content is --  collection:%s",
                          collection)

        results = None
        try:
            results = self.__getCollection(collection).list()
        except AttributeError as exc:
            raise EntityNotFound("Can't get collection '{0}': {1}".
                                 format(collection, exc))

        return results

    def create(self, entity, positive, expectedEntity=None, incrementBy=1,
               async=False, collection=None, current=None, compare=True,
               **kwargs):
        '''
        Description: creates a new element
        Author: edolinin
        Parameters:
           * entity - entity for post body
           * positive - if positive or negative verification should be done
           * expectedEntity - if there are some expected entity different from
                              entity
           * incrementBy - increment by number of elements
           * async -sycnh or asynch request
           * compare - True by default and run compareElements,
                       otherwise compareElements doesn't run
        Return: POST response (None on parse error.),
                status (True if POST test succeeded, False otherwise.)
        '''

        entity = self._translate_params(entity)

        if not collection:
            collection = self.__getCollection(self.collection_name)

        try:
            self.logger.debug("CREATE api content is --  "
                              "collection:%s element:%s ",
                              self.collection_name,
                              validator.dump_entity(entity, self.element_name))
        except Exception:
            pass

        response = None
        try:
            with measure_time('POST'):
                response = collection.add(
                    entity,
                    **self.getReqMatrixParams(
                        current,
                        api_operation=ApiOperation.create)
                )

            if not async:
                self.find(response.id, 'id', collection=collection.list())

            self.logger.info("New entity was added successfully")
            expEntity = entity if not expectedEntity else expectedEntity
            if compare and not validator.compareElements(
                    expEntity, response, self.logger, self.element_name):
                return response, False

        except RequestError as e:
            self.print_error_msg(ApiOperation.create, e.status, e.reason,
                                 e.detail, positive=positive)
            if positive:
                return None, False

        return response, True

    def __set_property(self, entity, property_name, property_value):
        '''
        Set property for sdk object
        '''
        property_name = PROPERTIES_MAP.get(property_name, property_name)
        self.logger.debug("Setting %s.%s property to '%s'",
                          entity.__class__.__name__,
                          property_name,
                          property_value)
        getattr(entity, 'set_' + property_name)(property_value)

    def _translate_params(self, entity):
        """
        Translates data_st.Entity to ovirtsdk.xml.params.Entity
        Parameters:
         * entity - instance data_st.Entity
        Return: instance of ovirtsdk.xml.params.Entity
        """
        if isinstance(entity, data_st.GeneratedsSuper):
            entity_name = validator.getClassName(entity.__class__.__name__)
            self.logger.debug("Translation data_st.%s to ovirtsdk.%s",
                              entity_name, entity.__class__.__name__)
            new_entity = getattr(sdk_params, entity_name)()
        elif isinstance(entity, sdk_params.GeneratedsSuper):
            entity_name = entity.__class__.__name__
            self.logger.debug("%s is already instance of ovirtsdk.%s",
                              entity_name, entity_name)
            new_entity = entity
        else:
            # in this case here is no reason to translate it
            return entity

        for attr, value in entity.__dict__.iteritems():
            if value is not None:
                if isinstance(value, data_st.GeneratedsSuper):
                    self.logger.debug("%s is instance of data_st.%s, "
                                      "translate to ovirtsdk.%s", attr,
                                      entity_name, entity_name)
                    value = self._translate_params(value)
                elif isinstance(value, list):
                    self.logger.debug("%s is list, going over items", attr)
                    self._translate_list(value)
                try:
                    self.__set_property(new_entity, attr, value)
                except AttributeError:
                    self.logger.warn("Attribute doesn't exist %s", attr)
        return new_entity

    def _translate_list(self, list_):
        """
        Translates list of data_st.Entity to list ovirtsdk.xml.params.Entity.
        NOTE: It is done in the place.
        """
        for i in xrange(len(list_)):
            value = list_[i]
            if isinstance(value, list):
                self._translate_list(value)
            elif isinstance(value, (data_st.GeneratedsSuper,
                                    sdk_params.GeneratedsSuper)):
                list_[i] = self._translate_params(value)

    def update(self, origEntity, newEntity, positive,
               expected_neg_status=NEGATIVE_CODES, current=None, compare=True):
        '''
        Description: update an element
        Author: edolinin
        Parameters:
           * origEntity - original entity
           * newEntity - entity for post body
           * positive - if positive or negative verification should be done
           * expected_neg_status - list of expected statuses for negative
                                   request
           * compare - True by default and run compareElements,
                       otherwise compareElements doesn't run
        Return: PUT response, True if PUT test succeeded, False otherwise
        '''
        response = None
        newEntity = self._translate_params(newEntity)
        for attr in newEntity.__dict__.keys():
            try:
                attrVal = newEntity.__dict__[attr]
                if attrVal is not None:
                    self.__set_property(origEntity, attr, attrVal)
            except AttributeError:
                self.logger.warn("Attribute doesn't exist %s", attr)

        dumpedEntity = None
        try:
            dumpedEntity = validator.dump_entity(newEntity, self.element_name)
        except Exception:
            pass

        self.logger.debug("UPDATE api content is --  "
                          "collection :%s element:%s ", self.collection_name,
                          dumpedEntity)

        try:
            matrix_params = self.getReqMatrixParams(
                current, api_operation=ApiOperation.update)
            with measure_time('PUT'):
                response = origEntity.update(**matrix_params)
            self.logger.info(self.element_name + " was updated")
        except RequestError as e:
            self.print_error_msg(ApiOperation.update, e.status, e.reason,
                                 e.detail, positive=positive)
            if positive or not validator.compareResponseCode(
                    e.status, expected_neg_status, self.logger):
                return None, False
            return None, True
        compare_elements = True if not compare else (
            validator.compareElements(newEntity, response,
                                      self.logger, self.element_name))
        if (positive and compare_elements) or (
                not positive and expected_neg_status not in NEGATIVE_CODES):
            return response, True

        return None, False

    def delete(self, entity, positive, body=None, **kwargs):
        '''
        Description: delete an element
        Author: edolinin
        Parameters:
           * entity - entity to delete
           * positive - if positive or negative verification should be done
        Return: status (True if DELETE test succeeded, False otherwise)
        '''

        try:
            self.logger.debug("DELETE entity: {0}".format(entity.get_id()))
            correlation_id = self.getCorrelationId(ApiOperation.delete)
            if body:
                with measure_time('DELETE'):
                    entity.delete(self._translate_params(body),
                                  correlation_id=correlation_id)
            else:
                with measure_time('DELETE'):
                    entity.delete(correlation_id=correlation_id)
        except RequestError as e:
            self.print_error_msg(ApiOperation.delete, e.status, e.reason,
                                 e.detail, positive=positive)
            if positive:
                return False

        return True

    def query(self, constraint, exp_status=None, href=None, event_id=None,
              **params):
        '''
        Description: run search query
        Author: edolinin
        Parameters:
           * constraint - query for search
        Return: query results
        '''
        collection = href
        if not href:
            collection = self.collection_name

        search = None
        collection = self.__getCollection(collection)

        if event_id is not None:
            params['from_event_id'] = event_id

        MSG = ("SEARCH content is -- collection:%s "
               "query:%s params :%s")
        self.logger.debug(MSG, self.collection_name, constraint, params)
        with measure_time('GET'):
            search = collection.list(constraint, **params)

        self.logger.debug("Response for QUERY request is: %s ", search)

        return search

    def find(self, val, attribute='name', absLink=True, collection=None):
        '''
        Description: find entity by name
        Author: edolinin
        Parameters:
           * val - name of entity to look for
           * attribute - attribute name for searching
           * absLink - absolute link or just a  suffix
        Return: found entity or exception EntityNotFound
        '''

        if not collection:
            collection = self.__getCollection(self.collection_name).list()

        results = None
        try:
            if attribute == 'name':
                results = filter(lambda r: r.get_name() == val, collection)[0]
            if attribute == 'id':
                results = filter(lambda r: r.get_id() == val, collection)[0]
        except Exception:
            raise EntityNotFound("Entity %s not found  for collection '%s'."
                                 % (val, self.collection_name))

        return results

    def __getCollection(self, collection_name):
        '''
        Returns sdk collection object
        '''
        return getattr(self.api, collection_name)

    def getElemFromLink(
            self, elm, link_name=None, attr=None, get_href=False,
            all_content=False
    ):
        """
        Get collection (link_name or self.collection_name) of objects
        from requested element (elm)

        :param elm: Object from which the collection will be retrieved
        :type elm: object
        :param link_name: collection to be retrieved from the elm object
        :type link_name: str
        :param attr: Parameter is only used by rest api
        :type attr: Not in use
        :param get_href:  If True, get the api URL of the object
        :type get_href: bool
        :param all_content: If True, retrieved object should be with all
        content
        :type all_content: bool
        :return: Collection object or None if not found
        :rtype: object or None
        """
        if not link_name:
            link_name = self.collection_name

        if get_href:
            # equivalent to elm.link_name
            return getattr(elm, link_name)
        else:
            if all_content:
                return getattr(elm, link_name).list(all_content=all_content)
            return getattr(elm, link_name).list()

    def syncAction(self, entity, action, positive, async=False, **params):
        '''
        Description: run synchronic action
        Author: edolinin
        Parameters:
           * entity - target entity
           * action - desired action
           * positive - if positive or negative verification should be done
           * asynch - synch or asynch action
        Return: status (True if Action test succeeded, False otherwise)
        '''

        entity = self._translate_params(entity)

        act = self._translate_params(self.makeAction(async, 10, **params))

        try:
            self.logger.info("Running action %s on %s",
                             validator.dump_entity(act, 'action'),
                             entity)
        except Exception:
            pass

        try:
            correlation_id = self.getCorrelationId(ApiOperation.syncAction)
            with measure_time('POST'):
                act = getattr(entity, action)(act,
                                              correlation_id=correlation_id)
        except RequestError as e:
            self.print_error_msg(ApiOperation.syncAction, e.status, e.reason,
                                 e.detail, positive=positive)
            if positive:
                return False
            else:
                return True
        else:
            if not positive:
                errorMsg = "Succeeded to run an action '%s' for negative test"
                self.logger.error(errorMsg, action)
                return False

        return validator.compareAsyncActionStatus(async, act.status.state,
                                                  self.logger)

    def waitForElemStatus(self, elm, status, timeout=DEF_TIMEOUT,
                          ignoreFinalStates=False, collection=None):
        '''
        Description: Wait till the sdk element (the Host, VM) gets the desired
        status or till timeout.

        Author: edolinin
        Parameters:
            * elm - sdk element to probe for a status
            * status - a string represents status to wait for. it could be
                       multiple statuses as a string with space delimiter
                       Example: "active maintenance inactive"
            * timeout - maximum time to continue status probing
        Return: status (True if element get the desired status,
                False otherwise)
        '''

        handleTimeout = 0
        while handleTimeout <= timeout:

            elm = self.find(elm.name, collection=collection)

            elemStat = None
            if hasattr(elm, 'snapshot_status'):
                elemStat = elm.snapshot_status.lower()
            elif hasattr(elm, 'status'):
                elemStat = elm.status.state.lower()
            else:
                self.logger.error("Element %s doesn't have attribute status",
                                  self.element_name)
                return False

            try:
                self.logger.info("Element %s Waiting for the status %s",
                                 validator.dump_entity(elm, self.element_name),
                                 status)
            except Exception:
                pass

            if not hasattr(elm, 'status'):
                self.logger.error("Element %s doesn't have attribute status",
                                  self.element_name)
                return False

            if elemStat in status.lower().split():
                self.logger.info("%s status is '%s'", self.element_name,
                                 elemStat)
                return True
            elif elemStat.find("fail") != -1 and not ignoreFinalStates:
                self.logger.error("%s status is '%s'", self.element_name,
                                  elemStat)
                return False
            elif elemStat == 'up' and not ignoreFinalStates:
                self.logger.error("%s status is '%s'", self.element_name,
                                  elemStat)
                return False
            else:
                self.logger.debug("Waiting for status '%s', currently "
                                  "status is '%s' ", status, elemStat)
                time.sleep(DEF_SLEEP)
                handleTimeout = handleTimeout + DEF_SLEEP
                continue

        self.logger.error("Interrupt because of timeout. %s status is '%s'.",
                          self.element_name, elemStat)
        return False


APIUtil.register(SdkUtil)
