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

import base64
import cgi
import httplib
import logging
import re
import ssl
from contextlib import contextmanager
from multiprocessing import Manager

from art.core_api.apis_exceptions import APIException

logger = logging.getLogger('http')


class HTTPProxy(object):
    """
    Establish connection with the REST API and run REST methods
    """

    def __init__(self, opts):
        self.opts = opts
        self.cookie = None
        self.last_active_user = None
        self.type = opts['RUN']['media_type']
        self.process_manager = Manager()
        self.headers = self.process_manager.dict(
            self.opts.get('HTTP_HEADERS', {})
        )

    @contextmanager
    def create_connection(self):
        """
        Create new HTTP or HTTPS connection.
        """
        conn = None
        try:
            # Create HTTPS Connection
            if self.opts['REST_CONNECTION']['scheme'] == 'https':
                context = None
                # https://www.python.org/dev/peps/pep-0476/
                if hasattr(ssl, "_create_unverified_context"):
                    context = ssl._create_unverified_context()
                conn = httplib.HTTPSConnection(
                    self.opts['REST_CONNECTION']['host'],
                    self.opts['REST_CONNECTION']['port'],
                    context=context
                )
            else:  # Create HTTP Connection
                conn = httplib.HTTPConnection(
                    self.opts['REST_CONNECTION']['host'],
                    self.opts['REST_CONNECTION']['port']
                )

            yield conn
        finally:
            if conn:
                conn.close()

    def connect(self):
        """
        Run the HEAD request for connection establishing
        and set cookie if available
        """
        response = self.__do_request(
            "HEAD", self.opts['REST_CONNECTION']['uri'],
            get_header='Set-Cookie', repeat=False
        )
        self.cookie = response['Set-Cookie']
        self.last_active_user = self.__get_user()

    def __do_request(
        self, method, url, body=None, get_header=None, repeat=True
    ):
        """
        Run HTTP request

        Args:
            method (str): Request method(GET, POST, PUT, DELETE)
            url (str): Request url
            body (str): Request body
            get_header (str): Name of the header to return with the response
            repeat (bool): Repeat request in case of authorization error
        """
        with self.create_connection() as conn:
            headers = dict(self.basic_headers())

            if body:
                headers['Content-type'] = self.type

            # run http request
            conn.request(method, url, body, headers=headers)
            # get response
            resp = conn.getresponse()

            charset = encoding_from_headers(resp) or 'utf-8'

            resp_body = resp.read().decode(charset)
            # W/A lxml issue with unicode strings having declarations
            resp_body = re.sub(r'^\s*<\?xml\s+.*?\?>', '', resp_body)

            ret = {'status': resp.status, 'body': resp_body}

            if headers.get('Authorization', None):
                self.cookie = resp.getheader('Set-Cookie')
                self.last_active_user = self.__get_user()

            if resp.status == 401 and self.cookie:
                if repeat:  # Update cookie and send request again
                    self.connect()
                    return self.__do_request(
                        method=method,
                        url=url,
                        body=body,
                        get_header=get_header,
                        repeat=False
                    )

            if resp.status >= 300:
                ret['reason'] = resp.reason

            if get_header:
                ret[get_header] = resp.getheader(get_header)

            return ret

    def GET(self, url):
        '''
        GET HTTP request
        '''
        return self.__do_request("GET", url)

    def POST(self, url, body):
        '''
        POST HTTP request
        '''
        return self.__do_request("POST", url, body)

    def PUT(self, url, body):
        '''
        PUT HTTP request
        '''
        return self.__do_request("PUT", url, body)

    def DELETE(self, url, body=None):
        '''
        DELETE HTTP request
        '''
        return self.__do_request("DELETE", url, body)

    def basic_auth(self):
        '''
        Build authentication header
        '''
        user = '%s' % self.opts['REST_CONNECTION']['user']
        if self.opts['REST_CONNECTION']['user_domain']:
            user += '@%s' % self.opts['REST_CONNECTION']['user_domain']
        credentials = base64.encodestring(
            '%s:%s' % (user, self.opts['REST_CONNECTION']['password'])
        )[:-1]
        return "Basic %s" % credentials.replace('\n', '')

    def basic_headers(self):
        '''
        Build request headers
        '''
        if self.headers:
            headers = self.process_manager.dict(self.headers)
        else:
            headers = self.process_manager.dict()

        if (
                self.opts['REST_CONNECTION']['user'] and
                self.opts['REST_CONNECTION']['password']
        ):
            if self.cookie and self.last_active_user == self.__get_user():
                headers['Cookie'] = self.cookie
            else:
                headers['Authorization'] = self.basic_auth()

            if self.headers:
                headers.update(self.opts['HTTP_HEADERS'])

        return headers

    def __parse_link(self, s, links):
        '''
        Build links matrix
        Parameters:
        * s - link from response header
        * links - links dictionary
        '''
        url = s[s.find('<')+1:s.find('>')]
        s = s[s.find(';')+1:]
        rel = s[s.find('rel=')+4:]
        if rel.find(';') != -1:
            rel = rel[:s.find(';')]
        links[rel] = url
        return links

    def __get_user(self):
        '''
        Return user@domain who is currenlty specified in opts.
        '''
        return '{0}@{1}'.format(
            self.opts['REST_CONNECTION']['user'],
            self.opts['REST_CONNECTION']['user_domain'],
        )

    def HEAD_for_links(self):
        '''
        Build links matrix from HEAD request
        '''
        if self.opts['RUN'].get('standalone'):
            return {}

        response = self.__do_request(
            "HEAD", self.opts['REST_CONNECTION']['uri'], get_header='link',
        )
        links = {}
        if response['status'] >= 300:
            MSG = "Bad HTTP response status: {0}, {1}"
            raise APIException(MSG.format(response['status'],
                                          response['reason']))
        for s in response['link'].split(','):
            self.__parse_link(s, links)
        links['capabilities'] = (
            '%scapabilities' % self.opts['REST_CONNECTION']['uri']
        )
        return links


def encoding_from_headers(response):
    content_type = response.getheader('Content-Type')

    if not content_type:
        return None

    content_type, params = cgi.parse_header(content_type)
    if 'charset' in params:
        return params['charset'].strip("'\"")
    else:
        return None
