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
import re
import threading
import time
from contextlib import contextmanager

import art.core_api.apis_utils as api_utils
from art.core_api import http, template_parser, validator, measure_time
from art.core_api.apis_exceptions import EntityNotFound, APIException,\
    APILoginError, MoreThanOneEntitiesFound
from art.test_handler import settings
from lxml import etree


class RespKey(object):
    '''
    Description: Class to represent the Responds Keys (like Enum)
    Author: khakimi
    '''
    status = 'status'
    reason = 'reason'
    body = 'body'
    trace = 'trace'


class RestUtil(api_utils.APIUtil):

    xsd = None
    xsd_schema_errors = []
    _restInit = None
    context_lock = threading.Lock()

    '''
    Implements REST APIs methods
    '''
    def __init__(self, element, collection, **kwargs):
        super(RestUtil, self).__init__(element, collection, **kwargs)
        self.entry_point = self.opts['REST_CONNECTION'].get(
            'entry_point'
        )
        self.standalone = self.opts['RUN'].get('standalone')
        self.login()

    def login(self):
        """
        Description: login to rest api.
        Author: imeerovi
        Parameters:
        Returns:
        """
        if RestUtil._restInit and not self.standalone:
            self.api = RestUtil._restInit
        else:
            self.api = http.HTTPProxy(self.opts)
            if self.opts['REST_CONNECTION']['persistent_auth']:
                self.api.headers['Prefer'] = 'persistent-auth'
            self.api.headers['Session-TTL'] = self.opts['REST_CONNECTION'].get(
                'session_timeout'
            )
            self.api.headers['Filter'] = str(
                self.opts['REST_CONNECTION']['filter']
            )

            if not self.standalone:
                try:
                    self.api.connect()
                except APIException as e:
                    raise APILoginError(e)

        try:
            self.links = self.api.HEAD_for_links()
        except APIException as ex:
            raise APIException(
                "Failed to Build links matrix from HEAD request. "
                "Exception: %s" % ex
            )
        else:
            if RestUtil._restInit is None:
                RestUtil._restInit = self.api

        # load xsd schema file
        if self.xsd is None:
            xsd_schema = etree.parse(settings.ART_CONFIG['RUN']['api_xsd'])
            self.xsd = etree.XMLSchema(xsd_schema)

        self.max_collection = settings.ART_CONFIG['RUN']['max_collection']

    @classmethod
    def logout(cls):
        """
        Description: logout from rest api.
        Author: imeerovi
        Parameters:
        Returns: True if logout succeeded or False otherwise
        """
        RestUtil._restInit = None

    @contextmanager
    def correlationIdContext(self, api_operation):
        """
        Description: context management for getting correlation id
        Author: imeerovi
        Parameters:
            * api_operation - the api operation performed
        Returns: correlation-id
        """
        with self.__class__.context_lock:
            try:
                self.api.headers['Correlation-Id'] = super(
                    RestUtil, self).getCorrelationId(api_operation)
                self.logger.info("Using Correlation-Id: %s",
                                 self.api.headers['Correlation-Id'])
                yield
            finally:
                self.logger.debug("Cleaning Correlation-Id: %s",
                                  self.api.headers['Correlation-Id'])
                self.api.headers.pop('Correlation-Id')

    def validateResponseViaXSD(self, href, ret):
        '''
        Validate xml response against xsd schema
        Author: jvorcak
        Parameters:
           * href - url of the request
           * ret - reponse object containing the body
        '''
        if ret[RespKey.body]:
            try:
                doc = etree.fromstring(ret[RespKey.body])
                self.xsd.assertValid(doc)
            except etree.DocumentInvalid as err:
                error_obj = (href, ret, err)
                self.xsd_schema_errors.append(error_obj)
            except etree.XMLSyntaxError as err:
                self.logger.error('Failed parsing response for XSD validations'
                                  'error: %s. body: %s' %
                                  (err, ret[RespKey.body]))

    @staticmethod
    def build_url(href, **additional_params):
        """
        Build URL with additional parameters

        Args:
            href (str): Initial URL for request

        Keyword Args:
            current (bool): Current flag
            deploy_hosted_engine (bool): Deploy hosted engine flag
            undeploy_hosted_engine (bool): Undeploy hosted engine flag

        Returns:
            str: URL with additional parameters
        """
        url = href
        for k, v in additional_params.iteritems():
            if v:
                url = "%s?%s" % (url, k)
        return url

    def get(
            self, href=None, elm=None, custom_headers=None, abs_link=True,
            list_only=False, no_parse=False, validate=True
    ):
        """
        Implements GET method and verify the response
        (codes 200,201)

        __author__: edolinin

        Args:
           href (str): url for get request
           custom_headers (dict): custom header which will be added to API
                                  call.
                                  Ex.: {'Accept': 'application/x-virt-viewer'}
           elm (str): element name
           abs_link (bool): if href url is absolute url (True) or just a suffix
           list_only (bool): True to list the element and return body, False -
                             otherwise.
           no_parse (bool): whether to parse the answer or not, False to parse,
                            not to parse - True.
           validate (bool): True - validate, otherwise - False.

        Returns:
           str: parsed GET response
        """
        if href is None:
            href = self.collection_name

        if not abs_link:
            if href:
                href = self.links.get(href)
            else:
                href = self.opts['REST_CONNECTION']['uri']

        if not elm:
            elm = self.element_name

        if custom_headers:
            for header in custom_headers.keys():
                self.api.headers[header] = custom_headers[header]

        self.logger.debug("GET request content is --  url:%(uri)s ",
                          {'uri': href})
        ret = self.api.GET(href)

        if not validator.compareResponseCode(
            ret[RespKey.status], api_utils.POSITIVE_CODES, self.logger
        ):
            return None

        if validate:
            self.validateResponseViaXSD(href, ret)

        self.logger.debug("Response body for GET request is: %s ",
                          ret[RespKey.body])

        if no_parse:
            return ret[RespKey.body]

        parsed_resp = None
        try:
            parsed_resp = api_utils.parse(ret[RespKey.body], silence=True)
        except etree.XMLSyntaxError:
            self.logger.error("Cant parse xml response")
            return None

        if hasattr(parsed_resp, elm):
            return getattr(parsed_resp, elm)
        else:
            if list_only:
                self.logger.error("Element '{0}' not found at {1} \
                ".format(elm, ret[RespKey.body]))
            return parsed_resp

    def parse_detail(self, ret):
        '''
        Description: parsing the error details from ret
        Author: Kobi Hakimi
        Parameter:
            * ret - the string to parse from it the error details
        Return: the error details which we got it as xml node skip the
                last 2 chars '</'
        '''
        try:
            return ret[RespKey.body].split('detail>')[1][:-2]
        except IndexError:
            self.logger.error("Details was not found on body")
            return None

    def responseCodesMatch(self, positive, operation, expected_pos_status,
                           expected_neg_status, ret):
        '''
        Description: print error in case its not positive status and compare
                     the current status with expected positive and negative
                     response codes
        Author: Kobi Hakimi
        Parameter:
            * positive - if positive or negative verification should be done
            * operation - describe from which operation this method called
            * expected_pos_status - LIST OF expected positive status
            * expected_neg_status - LIST OF expected negative status
            * ret - the return value of rest command.
        Return: True if the expected status and the actual status match
                otherwise return False
        '''
        if ret[RespKey.status] not in expected_pos_status:
            reason = ret[RespKey.reason] if(RespKey.reason in
                                            ret.keys()) else None
            self.print_error_msg(operation, ret[RespKey.status], reason,
                                 self.parse_detail(ret), positive=positive)
        expected_statuses = (
            expected_pos_status if positive else expected_neg_status)

        return validator.compareResponseCode(ret[RespKey.status],
                                             expected_statuses, self.logger)

    def create(self, entity, positive, **kwargs):
        """
        Create POST request and verify the response

        Args:
            entity (DS object): Entity for POST body
            positive (bool): Positive on negative behaviour

        Keyword Args:
            expected_pos_status (list): Expected positive statuses
            expected_neg_status (list): Expected negative statuses
            expected_entity (DS object): Expected entity
            async (bool): Sync or async request
            collection (str): Collection name
            coll_elm_name (str): Collection element name
            compare (bool): Enable compareElements
            operations (list): Operations to concatenate to the url
            current (bool): Current flag
            deploy_hosted_engine (bool): Deploy hosted engine flag
            validate (bool): Validate the new element exist after creation

        Returns:
            tuple: POST response and status
        """
        expected_pos_status = kwargs.get(
            "expected_pos_status", api_utils.POSITIVE_CODES_CREATE
        )
        expected_neg_status = kwargs.get(
            "expected_neg_status", api_utils.NEGATIVE_CODES_CREATE
        )
        async = kwargs.get("async", False)
        compare = kwargs.get("compare", True)

        href = kwargs.get("collection")
        if not href:
            href = self.links[self.collection_name]

        if self.max_collection is not None:
            href = "{0};max={1}".format(href, self.max_collection)

        coll_elm_name = kwargs.get("coll_elm_name")
        if not coll_elm_name:
            coll_elm_name = self.element_name

        entity = validator.dump_entity(entity, coll_elm_name)

        post_url = self.build_url(
            href=href,
            current=kwargs.get("current"),
            deploy_hosted_engine=kwargs.get("deploy_hosted_engine")
        )

        operations = kwargs.get("operations")
        if operations:
            post_url += ";" + ";".join(operations)

        self.logger.debug(
            "CREATE request content is --  url:%(uri)s body:%(body)s ",
            {'uri': post_url, 'body': entity}
        )

        # TODO: fix this nasty nested with when we will move to python 2.7
        with self.correlationIdContext(api_utils.ApiOperation.create):
            with measure_time("POST"):
                ret = self.api.POST(post_url, entity)

        if not self.responseCodesMatch(
            positive, api_utils.ApiOperation.create, expected_pos_status,
            expected_neg_status, ret
        ):
            return None, False

        validate = kwargs.get("validate", self.opts["RUN"]["validate"])
        if not validate:
            return None, True

        collection = self.get(href, list_only=True, elm=coll_elm_name)

        self.logger.debug(
            "Response body for CREATE request is: %s ", ret[RespKey.body]
        )

        if positive:
            if ret[RespKey.body]:
                self.logger.info("New entity was added")
                actual_entity = validator.dump_entity(
                    api_utils.parse(ret[RespKey.body], silence=True),
                    self.element_name
                )

                expected_entity = kwargs.get("expected_entity")
                expected_entity = entity if not expected_entity else (
                    validator.dump_entity(expected_entity, self.element_name)
                )

                if compare and not validator.compareElements(
                    api_utils.parse(expected_entity, silence=True),
                    api_utils.parse(actual_entity, silence=True),
                    self.logger,
                    self.element_name
                ):
                    return None, False

                if not async:
                    self.find(
                        api_utils.parse(actual_entity, silence=True).id, "id",
                        collection=collection, abs_link=False
                    )
            else:
                return ret[RespKey.body], True
        self.validateResponseViaXSD(href, ret)
        return api_utils.parse(ret[RespKey.body], silence=True), True

    def update(
        self, origEntity, newEntity, positive,
        expected_pos_status=api_utils.POSITIVE_CODES,
        expected_neg_status=api_utils.NEGATIVE_CODES,
        current=None, compare=True
    ):
        '''
        Description: implements PUT method and verify the response
        Author: edolinin
        Parameters:
           * origEntity - original entity
           * newEntity - entity for post body
           * positive - if positive or negative verification should be done
           * expected_pos_status - list of expected statuses for positive
                                   request
           * expected_neg_status - list of expected statuses for negative
                                   request
           * compare - True by default and run compareElements,
                       otherwise compareElements doesn't run
        Return: PUT response, status (True if PUT test succeeded,
                                      False otherwise)
        '''

        entity = validator.dump_entity(newEntity, self.element_name)

        put_url = self.build_url(href=origEntity.href, current=current)
        self.logger.debug(
            "PUT request content is --  url:%(uri)s body:%(body)s ",
            {'uri': put_url, 'body': entity})

        # TODO: fix this nasty nested with when we will move to python 2.7
        with self.correlationIdContext(api_utils.ApiOperation.update):
            with measure_time('PUT'):
                ret = self.api.PUT(put_url, entity)

        if not self.responseCodesMatch(
            positive, api_utils.ApiOperation.update, expected_pos_status,
            expected_neg_status, ret
        ):
            return None, False

        if not self.opts['RUN']['validate']:
            return None, True

        self.logger.debug("Response body for PUT request is: %s ",
                          ret[RespKey.body])

        if positive:
            self.logger.info(self.element_name + " was updated")

            if compare and not validator.compareElements(
                api_utils.parse(entity, silence=True),
                api_utils.parse(ret[RespKey.body], silence=True),
                self.logger, self.element_name
            ):
                return None, False

        self.validateResponseViaXSD(origEntity.href, ret)
        return api_utils.parse(ret[RespKey.body], silence=True), True

    def delete(self, entity, positive,
               expected_pos_status=[200, 202, 204],
               expected_neg_status=api_utils.NEGATIVE_CODES,
               operations=[]):
        '''
        Implements DELETE method and verify the reponse

        :param entity: Entity to delete
        :type entity: object
        :param positive: If positive or negative verification should be done
        :type positive: bool
        :param expected_pos_status: Expected statuses for positive request
        :type expected_pos_status: list of int
        :param expected_neg_status: Expected statuses for negative request
        :type expected_neg_status: list of int
        :param operations: Operations to concatenate to the href
        :type operations: list of strings
        :return: If the request status is same as expected
        :rtype: bool
        '''
        href = entity.href
        if operations:
            href += ';' + ';'.join(operations)
        with self.correlationIdContext(api_utils.ApiOperation.delete):
            self.logger.debug("DELETE request content is --  url:%(uri)s",
                              {'uri': href})
            with measure_time('DELETE'):
                ret = self.api.DELETE(href)

        if not self.responseCodesMatch(
            positive, api_utils.ApiOperation.delete,
            expected_pos_status, expected_neg_status, ret
        ):
            return False

        if not self.opts['RUN']['validate']:
            return True

        self.logger.debug("Response body for DELETE request is: %s ",
                          ret[RespKey.body])

        self.validateResponseViaXSD(href, ret)
        return True

    def find(
        self, val, attribute='name', abs_link=True, collection=None,
        all_content=False, **kwargs
    ):
        """
        Find entity by name

        Args:
            val (str): name of entity to look for
            attribute (str): attribute name for searching
            abs_link (bool): absolute link or just a suffix
            collection (str): Collection name
            all_content (bool): All content header
            kwargs (dict): additional search attribute=val pairs (the attribute
                can be a chain attribute such as 'attr_x.attr_y')

        Returns:
            Entity: Found entity

        Raises:
            EntityNotFound: If entity not found
        """
        href = self.collection_name
        if all_content:
            self.api.headers['All-content'] = all_content

        if abs_link:
            href = self.links[self.collection_name]

        if self.max_collection is not None:
            href = '{0};max={1}'.format(href, self.max_collection)

        if not collection:
            collection = self.get(href, list_only=True)

        if not collection:
            raise EntityNotFound("Empty collection %s" % href)

        results = filter(lambda r: getattr(r, attribute) == val, collection)
        for attr, value in kwargs.iteritems():
            results = filter(
                lambda r: reduce(getattr, attr.split('.'), r) == value,
                results
            )

        if not results:
            raise EntityNotFound(
                "Entity %s not found on url '%s'." % (val, href)
            )
        if len(results) > 1:
            raise MoreThanOneEntitiesFound(
                "The entity %s occurs %d times on url '%s'." %
                (val, len(results), href)
            )
        return results[0]

    def query(
        self, constraint, expected_status=None, href=None,
        event_id=None, all_content=False, **params
    ):
        """
        Run search query

        Args:
            constraint (str): Query for search
            expected_status (list): Expected statuses for positive request
            href (str): Base href for search
            event_id (str): Event id
            all_content (bool): All content header
            params (dict): Extra keys to send to query

        Returns:
            list: Query results

        Examples:
            NET_API.query(constraint=conf.MGMT_BRIDGE, datacenter=conf.DC_0)
        """
        expected_status = (
            expected_status if expected_status else api_utils.POSITIVE_CODES
        )
        if not href:
            href = self.links["%s/search" % self.collection_name]

        search_params = list()
        if self.collection_name == "events":
            before_search, after_search = href.split('?')
            search_params.append(before_search)

        for p, val in params.iteritems():
            search_params.append("{0}={1}".format(p, val))

        if self.collection_name == "events":
            href = "{0}?{1}".format(";".join(search_params), after_search)

        elif search_params:
            href = "{0}&{1}".format(href, "&".join(search_params))

        query_template = template_parser.URITemplate(href)
        query_href = query_template.sub({"query": constraint})
        query_href = query_href.replace(" ", "%20")
        if event_id:
            query_href = query_template.sub(
                {"query": constraint, "event_id": event_id}
            )
        else:
            query_href = query_href.replace("from=", '')

        self.logger.debug(
            "SEARCH request content is --  url:%(uri)s" % {'uri': query_href})

        if all_content:
            self.api.headers['All-content'] = all_content

        try:
            with measure_time('GET'):
                ret = self.api.GET(query_href)
        finally:
            if all_content:
                self.api.headers.pop('All-content')

        self.logger.debug(
            "Response body for QUERY request is: %s " % ret[RespKey.body]
        )
        if not validator.compareResponseCode(
            ret[RespKey.status], expected_status, self.logger
        ):
            return None

        self.validateResponseViaXSD(href, ret)

        return getattr(
            api_utils.parse(ret[RespKey.body], silence=True), self.element_name
        )

    def syncAction(self, entity, action, positive, **kwargs):
        """
        Run synchronic action

        Args:
            entity (DS object): Target entity
            action (str): Action to run
            positive (bool): Positive or negative behaviour

        Keyword Args:
            async (bool): Sync or async action
            positive_async_stat (list): Async expected positive statuses
            positive_sync_stat (list): Sync expected positive statuses
            negative_stat (list): Expected negative statuses
            deploy_hosted_engine (bool): Deploy hosted engine flag
            undeploy_hosted_engine (bool): Undeploy hosted engine flag

        Returns:
            str: POST response
        """
        expected_async_pos_status = kwargs.pop(
            "positive_async_stat", [200, 202]
        )
        expected_sync_pos_status = kwargs.pop(
            "positive_sync_stat", api_utils.POSITIVE_CODES
        )
        expected_neg_status = kwargs.pop(
            "negative_stat", api_utils.NEGATIVE_CODES
        )
        async = kwargs.pop("async", False)

        action_href = filter(
            lambda x: x.get_rel() == action, entity.actions.get_link()
        )[0].get_href()
        if re.search("^/{0}/.*".format(self.entry_point), action_href) is None:
            action_href = "/{0}{1}".format(self.entry_point, action_href)

        action_href = self.build_url(
            href=action_href,
            deploy_hosted_engine=kwargs.get("deploy_hosted_engine"),
            undeploy_hosted_engine=kwargs.get("undeploy_hosted_engine")
        )

        operations = kwargs.pop("operations", [])
        if operations:
            action_href += ";" + ";".join(operations)

        action_body = validator.dump_entity(
            self.makeAction(async, 10, **kwargs), "action"
        )

        self.logger.debug(
            "Action request content is --  url:%(uri)s body:%(body)s",
            {"uri": action_href, "body": action_body}
        )

        # TODO: fix this nasty nested with when we will move to python 2.7
        with self.correlationIdContext(api_utils.ApiOperation.syncAction):
            with measure_time("POST"):
                ret = self.api.POST(action_href, action_body)

        positive_stat = (
            expected_async_pos_status if async else expected_sync_pos_status
        )
        if not self.responseCodesMatch(
            positive, api_utils.ApiOperation.syncAction, positive_stat,
            expected_neg_status, ret
        ):
            return None

        if not self.opts["RUN"]["validate"]:
            return ret[RespKey.body]

        self.logger.debug(
            "Response body for action request is: %s", ret[RespKey.body]
        )
        try:
            resp_action = api_utils.parse(ret[RespKey.body], silence=True)
        except etree.XMLSyntaxError:
            self.logger.error("Cant parse xml response")
            return None

        if positive:
            if resp_action and not validator.compareAsyncActionStatus(
                async, resp_action.status, self.logger
            ):
                return None

        else:
            return api_utils.api_error(
                reason=ret[RespKey.reason],
                status=ret[RespKey.status],
                detail=self.parse_detail(ret)
            )

        self.validateResponseViaXSD(action_href, ret)
        valid = validator.compareActionLink(
            entity.actions, action, self.logger
        )

        return ret[RespKey.body] if valid else None

    def extract_attribute(self, response, attr):
        '''
        Extract the attribute from POST response
        :param response: POST response string
        :type response: str
        :param attr: the name of the attribute to extract
        :type attr: str
        :return: list of attribute values
        :rtype: list
        '''
        if response and attr:
            pat = '<{0}>(.*)</{0}>'.format(attr)
            return [str(x) for x in re.findall(pat, response)]
        return None

    def getElemFromLink(self, elm, link_name=None, attr=None, get_href=False,
                        all_content=False):
        """
        Get collection or specific object if attr is passed (link_name or
        self.collection_name) of objects
        from requested element (elm)

        :param elm: Object from which the collection will be retrieved
        :type elm: object
        :param link_name: collection to be retrieved from the elm object
        :type link_name: str
        :param attr: attribute to get (usually name of desired collection)
        :type attr: str
        :param get_href: If True, get the api URL of the object
        :type get_href: bool
        :param all_content: If True, retrieved object should be with all
        content
        :type all_content: bool
        :return: Collection object or None if not found
        :rtype: object or None
        """
        if not link_name:
            link_name = self.collection_name

        if not attr:
            attr = self.element_name

        no_results = None if get_href else []

        if all_content:
            self.api.headers['All-content'] = all_content

        try:
            for link in elm.get_link():
                if link.get_rel() == link_name:
                    if get_href:
                        return link.get_href()

                    link_content = self.get(link.get_href())
                    if not link_content:
                        return no_results

                    if isinstance(link_content, list):
                        return link_content
                    elif isinstance(link_content, api_utils.data_st.Fault):
                        raise EntityNotFound(
                            "Obtained Fault object for %s element and "
                            "link_name %s link with response: %s"
                            % (elm, link_name, link_content.get_detail())
                        )
                    else:
                        return getattr(link_content, 'get_' + attr)()
        finally:
            # Sets up the default 'all_content' header
            if all_content:
                self.api.headers.pop('All-content')
        return no_results

    def waitForElemStatus(
        self, restElement, status, timeout=api_utils.DEF_TIMEOUT,
        ignoreFinalStates=False, collection=None
    ):
        '''
        Description: Wait till the rest element (the Host, VM) gets the desired
        status or till timeout.

        Author: edolinin
        Parameters:
            * restElement - rest element to probe for a status
            * status - a string represents status to wait for. it could be
                       multiple statuses as a string with space delimiter
                       Example: "active maintenance inactive"
            * timeout - maximum time to continue status probing
        Return: status (True if element get the desired status,
                        False otherwise)
        '''

        handleTimeout = 0
        while handleTimeout <= timeout:
            restElement = self.get(restElement.href)

            elemStat = None
            if hasattr(restElement, 'snapshot_status'):
                elemStat = restElement.snapshot_status.lower()
            elif hasattr(restElement, 'status'):
                elemStat = restElement.status.lower()
            else:
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
                self.logger.debug(
                    "Waiting for status '%s' currently status is '%s' ",
                    status, elemStat)
                time.sleep(api_utils.DEF_SLEEP)
                handleTimeout = handleTimeout + api_utils.DEF_SLEEP
                continue

        self.logger.error(
            "Interrupt because of timeout. %s status is '%s'.",
            self.element_name, elemStat
        )
        return False

    def get_headers(self):
        """
        Retrieve headers dict.

        Returns:
            dict: dictionary with headers names and values.
        """
        return self.api.headers

    def set_header(self, header, value):
        """
        Set header.

        Args:
            header (str): header name (example: 'Content-Type', 'Filter', etc.)
            value (str): header value which will be set for chosen header.

        """
        if value is None:
            if header in self.api.headers.keys():
                self.api.headers.pop(header)
        else:
            self.api.headers[header] = value


api_utils.APIUtil.register(RestUtil)
