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


class RESTException(Exception):
    '''
    All exceptions specific for the RHEVM REST framework should inherit from
    this.
    '''
    pass

class EntityNotFound(RESTException):
    '''
    Raised when a RHEVM REST framework entity like a Host, DataCenter or Storage
    domain, etc, couldn't be found.
    '''
    pass

class RESTTimeout(RESTException):
    '''
    Raised when some RHEVM REST action timeouts.
    '''
    pass

class RestApiCommandError(Exception):
    '''
    Raised when running commands via RestTestRunnerWrapper
    '''
    def __init__(self, cmd, error):
        self.cmd = cmd
        self.error = error

    def __str__(self):
        return "Error while running command '{0}': {1}".format(self.cmd, self.error)