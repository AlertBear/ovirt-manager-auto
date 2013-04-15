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

import httplib
import base64
import re
import cgi
import copy
from art.core_api.apis_exceptions import APIException
from socket import error as SocketError

import logging
logger=logging.getLogger('http')


class HTTPProxy():
    '''
    Establish connection with rest api and run rest methods
    '''

    def __init__(self, opts):
        self.opts = opts
        self.cookie = None
        self.last_active_user = None
        self.type = opts['media_type']
        self.connections_pool = []
        self.headers = self.opts['headers']

        self.default_conn = self.add_connection()


    def __del__(self):
        '''
        Close the http connections
        '''
        for conn in self.connections_pool:
            conn.close()


    def add_connection(self):
        '''
        Create a connection and pull it to the pool
        '''
        if self.opts['scheme'] == 'https':
            conn = httplib.HTTPSConnection(self.opts['host'], self.opts['port'])
        else:
            conn = httplib.HTTPConnection(self.opts['host'], self.opts['port'])

        self.connections_pool.append(conn)

        return conn


    def connect(self, conn=None):
        '''
        Run the HEAD request for connection establishing
        and set cookie if available
        Parameters:
        * conn - connection to work with (if not provided - default is used)
        '''

        if not conn:
            conn = self.default_conn

        response = self.__do_request("HEAD", self.opts['uri'],
                        get_header='Set-Cookie', conn=conn)
        self.cookie = response['Set-Cookie']
        self.last_active_user = self.__get_user()


    def __do_request(self, method, url, body=None, get_header=None, conn=None):
        '''
        Run HTTP request
        Parameters:
        * method - request method
        * url - request url
        * body - request body
        * get_header - name of the header to return with the response
        * conn - connection to work with (if not provided - default is used)
        '''

        if not conn:
            conn = self.default_conn

        try:
            headers = self.basic_headers()


            if body:
                headers['Content-type'] = self.type

            # run http request
            conn.request(method, url, body, headers = headers)
            # get response
            resp = conn.getresponse()

            charset = encoding_from_headers(resp) or 'utf-8'

            resp_body = resp.read().decode(charset)
            #Workaround lxml issue with unicode strings having declarations
            resp_body = re.sub(r'^\s*<\?xml\s+.*?\?>', '', resp_body)

            ret = { 'status' : resp.status, 'body' : resp_body }

            if headers.get('Authorization', None):
                self.cookie = resp.getheader('Set-Cookie')
                self.last_active_user = self.__get_user()

            if resp.status == 401 and self.cookie:
                self.cookie = None
                raise httplib.CannotSendRequest

            if resp.status >= 300:
                ret['reason'] = resp.reason

            if get_header:
                ret[get_header] = resp.getheader(get_header)

            return ret

        except (httplib.CannotSendRequest, httplib.BadStatusLine):
            add_conn = self.add_connection()
            self.connect(add_conn)

            return self.__do_request(method, url, body=body,
                        get_header=get_header, conn=add_conn)

        except SocketError:
            logger.exception("Socket connection problem for " + url)
            raise


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
        user = '%s' % self.opts['user']
        if self.opts['user_domain']:
            user += '@%s' % self.opts['user_domain']
        credentials = base64.encodestring('%s:%s' \
                %  (user, self.opts['password']))[:-1]
        return "Basic %s" % credentials


    def basic_headers(self):
        '''
        Build request headers
        '''
        headers = copy.deepcopy(self.headers)

        if self.opts['user'] and self.opts['password']:
            if self.cookie and self.last_active_user == self.__get_user():
                headers['Cookie'] = self.cookie
            else:
                headers['Authorization'] = self.basic_auth()

            headers.update(self.opts['headers'])

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
        return '%s@%s' % (self.opts['user'], self.opts['user_domain'])


    def HEAD_for_links(self):
        '''
        Build links matrix from HEAD request
        '''

        if self.opts.get('standalone', True):
            return {}

        response = self.__do_request("HEAD", self.opts['uri'], get_header='link')
        links = {}
        if response['status'] >= 300:
            MSG = "Bad HTTP response status: {0}, {1}"
            raise APIException(MSG.format(response['status'],
                                          response['reason']))
        for s in response['link'].split(','):
            self.__parse_link(s, links)
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
