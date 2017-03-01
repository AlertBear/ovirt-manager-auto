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


class APIException(Exception):
    '''
    All exceptions specific for the framework should inherit from this.
    '''
    pass


class APILoginError(APIException):
    '''
    Raised when API login failed
    '''
    pass


class EntityNotFound(APIException):
    '''
    Raised when a RHEVM REST framework entity like a Host, DataCenter or
    Storage domain, etc, couldn't be found.
    '''
    pass


class MoreThanOneEntitiesFound(APIException):
    '''
    Raised when more than one RHEVM REST framework entities like a Host,
    DataCenter or Storage domain, etc were found.
    '''
    pass


class APITimeout(APIException):
    '''
    Raised when some action timeouts.
    '''
    pass


class EngineTypeError(APIException):
    '''
    Raised when action doesn't support provided api engine
    '''
    pass


class APICommandError(Exception):
    '''
    Raised when running commands via RestTestRunnerWrapper
    '''
    def __init__(self, cmd, error):
        self.cmd = cmd
        self.error = error

    def __str__(self):
        return "Error while running command '{0}': {1}".format(self.cmd,
                                                               self.error)


class TestCaseError(APIException):
    """
    Raised when something goes wrong and test can not be completed.
    """


class CLITimeout(APITimeout):
    '''
    Raised when some action timeouts.
    '''
    pass


class CLIError(APICommandError):
    '''
    Raised when EOF reached with cli engine (connection lost)
    '''
    pass


class UnsupportedCLIEngine(APIException):
    '''
    Raised when trying to use unsupported cli engine
    '''
    pass


class CLICommandFailure(APIException):
    '''
    Raised when cli command returns error
    '''

    def __init__(self, message, err=None):
        self.status = None
        self.reason = None
        self.detail = None
        # in case of api error
        if isinstance(err, tuple):
            self.status = err.status
            self.reason = err.reason
            self.detail = err.detail
        elif err:
            message = " ".join([str(message), str(err)])
        super(CLICommandFailure, self).__init__(message)


class CLITracebackError(APIException):
    '''
    Raised when it is internal error in cli engine
    '''
    _error_start = "Traceback (most recent call last):"

    def __init__(self, error):
        self.before_error, self.error = error.split(self._error_start)
        self.prepare_traceback_message()

    def __str__(self):
        before_traceback = "{0}".format(self.before_error)
        traceback_msg = \
            "Traceback found in RHEVM/oVirt CLI output: {0}".format(self.error)
        return "Output before traceback: {0}\nTraceback:\n{1}".\
            format(before_traceback, traceback_msg)

    def prepare_traceback_message(self):
        self.error = self.error.replace('File', '\nFile')


class CLIAutoCompletionFailure(APIException):
    '''
    Raised when there is some autocompletion related error
    '''
    pass
