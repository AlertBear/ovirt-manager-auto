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
import pexpect as pe
import re
import threading
import subprocess
from functools import wraps
from sys import exit
from abc import ABCMeta, abstractmethod
from time import strftime, sleep
from art.rhevm_api.data_struct.data_structures import *
from art.rhevm_api.data_struct.data_structures import ClassesMapping
from art.core_api.rest_utils import RestUtil
from art.core_api.apis_exceptions import CLIError, CLITimeout,\
    CLICommandFailure, UnsupportedCLIEngine, CLITracebackError,\
    CLIAutoCompletionFailure
from art.core_api import validator
from utilities.utils import createCommandLineOptionFromDict

cliInit = False
addlock = threading.Lock()

ILLEGAL_XML_CHARS = u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]'
CONTROL_CHARS = u'[\n\r]'
RHEVM_SHELL = 'rhevm-shell'
OVIRT_SHELL = 'ovirt-shell'
TMP_FILE = '/tmp/cli_output.tmp'
IP_FORMAT = '^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
ADD_WAIVER = []
UPDATE_WAIVER = []
REMOVE_WAIVER = []
ACTION_WAIVER = []
COMPLEX_TO_BASE_CLASSES_DICT = {'HostNIC': 'nic'}
MAX_TIMEOUT_FOR_FILE_READ = 10
POLLING_TIMEOUT_FOR_FILE_READ = 0.5


def threadSafeRun(func):
    """
    Description: This closure will be used as decorator for critical section
    Author: imeerovi
    Parameters:
        *  func - function that runs critical section code
    Returns: returns apifunc wrapper for func
    """
    @wraps(func)
    def apifunc(*args, **kwargs):
        """
        Description: this code will run when func will be called
        Author: imeerovi
        Parameters:
            *  *args, **kwargs - parameters that should be passed to func
        Returns: result of func run
        """
        with addlock:
            return func(*args, **kwargs)
    return apifunc


class QueryResult(object):
    """
    Description: This class contains query result data
    Author: imeerovi
    Parameters:
        * dataDict - dictionary with query result data
    """
    def __init__(self, dataDict):
        for key, val in dataDict.iteritems():
            setattr(self, key, val)


class CliConnection(object):
    """
    Description: Base class with basic cli functionality
    Author: imeerovi
    Parameters:
        * command - connection command
        * prompt - expected prompt
        * timeout - maximum timeout for waiting for prompt
        * logFile - file for cli log
    """
    _defaultLogFile = "/tmp/cli_log_%s.log"
    __metaclass__ = ABCMeta

    def __init__(self, command, prompt, timeout, logFile=None):
        self._prompt = prompt
        self.cliConnection = pe.spawn(command, timeout=timeout)
        self.cliConnection.setecho(False)
        timestamp = strftime('%Y%m%d_%H%M%S')
        if logFile:
            self.cliLog = logFile
        else:
            self.cliLog = self._defaultLogFile % timestamp
        self.cliConnection.logfile = open(self.cliLog, 'w')
        self._expectDict = {}
        self._illegalXMLCharsRE = re.compile(ILLEGAL_XML_CHARS)
        self._controlCharsRE = re.compile(CONTROL_CHARS)

    @abstractmethod
    def login(self, *args, **kwargs):
        """
        Description: Virtual method that should be implemented by child class.
                     Reason: Login may differ between different CLI engines
        Author: imeerovi
        """

    @property
    def expectDict(self):
        """
        Description: expectDict property is dictionary of prompt: action pairs
        Author: imeerovi
        """
        return self._expectDict

    @expectDict.setter
    def expectDict(self, regexButtonDict):
        if not hasattr(self, '_expectDict'):
            self._expectDict = {}
        self._expectDict.update(regexButtonDict)

    @expectDict.deleter
    def expectDict(self):
        del(self._expectDict)

    def readTmpFile(self):
        """
        Description: This method checks if write finished to TMP_FILE and than
                     reads it
        Author: imeerovi
        Parameters:
        Returns: string with data from TMP_FILE
        """
        timeout = MAX_TIMEOUT_FOR_FILE_READ
        size = 0
        new_size = 0

        while new_size == 0 or new_size != size:
            size = new_size
            sleep(POLLING_TIMEOUT_FOR_FILE_READ)
            timeout -= POLLING_TIMEOUT_FOR_FILE_READ
            if timeout == 0:
                raise CLICommandFailure("Read of cli command output from file"
                                        " failed due to timeout in writing/"
                                        "flushing of this file.\n"
                                        "It can also happen if cli doesn't "
                                        "return any stdout (in case of error")
            new_size = int(subprocess.Popen(["wc", "-c", TMP_FILE],
                                            stdout=subprocess.PIPE).
                           communicate()[0].split()[0])

        with open(TMP_FILE) as f:
            return f.read()

    def sendCmd(self, cmd, timeout):
        """
        Description: This method sends command to cli
        Author: imeerovi
        Parameters:
            * cmd - command to run
            * timeout - specific timeout in [sec] for this command run
        Returns: string with data from child process
        """
        if not timeout:
            timeout = self.cliConnection.timeout

        expectList = self.expectDict.keys()
        expectList.insert(0, self._prompt)
        output = []

        # cleaning the buffer
        self.cliConnection.buffer = ''
        self.cliConnection.sendline(cmd)
        try:
            i = self.cliConnection.expect(expectList, timeout)
            while i != 0:
                sendButton = self.expectDict[expectList[i]]
                self.cliConnection.sendline(sendButton)
                output.append(self.cliConnection.before)

                # WA for trash in buffer (END issue)
                try:
                    i = self.cliConnection.expect(self._prompt, timeout=0.1)
                except pe.TIMEOUT:
                    i = self.cliConnection.expect(expectList, timeout)

            output.append(self.cliConnection.before)
        except pe.TIMEOUT as e:
            raise CLITimeout(e)
        except pe.EOF as e:
            raise CLIError(cmd, e)

        # flushing the buffer
        self.cliConnection.expect([self._prompt, pe.TIMEOUT], timeout=0.1)
        if type(self.cliConnection.before) == str:
            output.append(self.cliConnection.before)
        # cleaning the buffer
        self.cliConnection.buffer = ''

        return "\n".join(output)

    def commandRun(self, cmd, timeout=''):
        """
        Description: Wrapper that runs command and returns validated output
        Author: imeerovi
        Parameters:
            * cmd - command to run
            * timeout - timeout in [sec]. If timeout parameter is
              not set default timeout used
        Returns: validated output
        """
        return self.outputValidator(self.sendCmd(cmd, timeout))

    @abstractmethod
    def outputValidator(self, output):
        """
        Description: Virtual method that should be implemented by child class.
                     Reason: Output validation may differ between different
                     CLI engines
        Author: imeerovi
        Parameters:
            * output - output of cli command run
        Returns: validated output
        """

    def outputCleaner(self, output):
        """
        Description: cleans special characters from output and align it to UTF8
        Author: imeerovi
        Parameters:
            * output - output of cli command run
        Returns: UTF8 alligned output
        """
        if type(output) == list:
            output = ' '.join(output)
        output = self.escapeControlChars(output)
        return self.escapeXMLIllegalChars(output).lstrip()

    def escapeControlChars(self, val, replacement=''):
        """
        Description: replaces control characters in given string
        Author: imeerovi
        Parameters:
            * val - string to work on
            * replacement - replacement string
        Returns: string with replaced control characters
        """
        return self._controlCharsRE.sub(replacement, val)

    def escapeXMLIllegalChars(self, val, replacement=''):
        """
        Description: replaces UTF8 illegal characters in given string
        Author: imeerovi
        Parameters:
            * val - string to work on
            * replacement - replacement string
        Returns: string with replaced illegal characters decoded with UTF8
        """
        return self._illegalXMLCharsRE.sub(replacement, val).decode('utf-8')


class RhevmCli(CliConnection):
    """
    Description: CLI connection implementation for rhevm-shell
    Author: imeerovi
    Parameters:
        * logger - reference to logger
        * uri - rhevm URI
        * user - rhevm username
        * userDomain - rhevm user domain
        * password - rhevm password
        * secure - secure connection boolean
        * sslKeyFile - ssl key file
        * sslCertFile - ssl certificate file
        * sslCaFile - ssl ca file
        * logFile - file for cli log
        * **kwargs - additional parameters to CLI
    """
    # rhevm shell specific configs
    _query_id_re = 'id(\s+):'
    _id_extract_re = 'id(\\s+):(\\s+)(\S*)'
    _status_extract_re = '.*: (\w+).*'
    _tracebackMsgSearch = "Traceback (most recent call last):"
    _rhevmOutputErrorKeys = ['error', 'status', 'reason', 'detail']
    _debugMsg = "send:.*header:.*(\r\r\n\r)"
    _errorStatusMsgSearch = "error:.*status:.*reason:.*detail:.*"
    _errorParametersMsgSearch = "error:.*"
    _errorSyntaxMsgSearch = "\*\*\* Unknown syntax.*"
    _insiderSearch = "status:.*reason:.*detail:.*"
    _eol = '\r\n'
    _rhevmLoginPrompt = "Password:"
    _rhevmPrompt = '\[RHEVM shell \(connected\)\]# '
    _rhevmDisconnectedPrompt = '\[RHEVM shell \(disconnected\)\]# '
    _rhevmTimeout = 900
    _specialCliPrompt = {'\r\n:': ' ', '7m\(END\)': 'q', '--More--': ' '}
    _specialMatrixParamsDict = {'case-sensitive': 'case_sensitive'}
    _cliRootCommands = ['action', 'add', 'list', 'remove', 'show', 'update']
    _cliTrashPattern = "[\[\]\\\?]"
    _command = RHEVM_SHELL

    def __init__(self, logger, uri, user, userDomain, password,
                 secure, sslKeyFile, sslCertFile, sslCaFile, logFile,
                 session_timeout, **kwargs):
        self.logger = logger
        self.prepareConnectionCommand(uri, user, userDomain,
                                      secure, sslKeyFile, sslCertFile,
                                      sslCaFile, session_timeout,
                                      additionalArgs=kwargs)
        super(RhevmCli, self).__init__(self._connectionCommand,
                                       prompt=self._rhevmPrompt,
                                       timeout=self._rhevmTimeout,
                                       logFile=logFile)
        self.logger.debug("CLI logfile: %s" % self.cliLog)
        self.login(password)
        # updating parent dictionary for cli work
        self.expectDict = self._specialCliPrompt
        # getting contexts for auto completion
        self.getAutocompletionContext()

    def convertComplexNameToBaseEntityName(self, entity, cmd):
        """
        Description: This method replaces complex name like hostnic to cli
                     valid name (entity name)
        Author: imeerovi
        Parameters:
            * entity - entity passed to cli command run
            * cmd - cli command
        Returns: cli command with replaced name if entity actually is broker
        """
        entity_name = entity.__class__.__name__
        base_name = \
            COMPLEX_TO_BASE_CLASSES_DICT.get(entity_name, None)
        if base_name:
            return cmd.replace(entity_name.lower(), base_name, 1)
        return cmd

    @threadSafeRun
    def cliCmdRunner(self, apiCmd, apiCmdName):
        """
        Description: This method runs cli command
        Author: imeerovi
        Parameters:
            * apiCmd - command to run
            * apiCmdName - REST API command type
        Returns: CLI output
        """
        self.logger.debug("%s cli command is: %s", apiCmdName, apiCmd)
        errAndDebug = self.commandRun(apiCmd)
        self.logger.debug("%s cli command Debug and Error output: %s",
                          apiCmdName, errAndDebug)
        out = self.readTmpFile()
        self.logger.debug("%s cli command output: %s", apiCmdName, out)
        return out

    def login(self, password):
        """
        Description: implementation of login for rhevm-cli
        Author: imeerovi
        Parameters:
            * password - CLI password
        Returns: nothing, Exception will be raised upon failed login
        """
        self.expectDict = {self._rhevmLoginPrompt: password}
        self.expectDict = {self._rhevmDisconnectedPrompt: "exit"}

        expectList = self. expectDict.keys()
        expectList.insert(0, self._prompt)
        output = []

        try:
            i = self.cliConnection.expect(expectList)
            while i != 0:
                sendButton = self.expectDict[expectList[i]]
                output.append(self.cliConnection.before)
                self.cliConnection.sendline(sendButton)
                i = self.cliConnection.expect(expectList)
            output.append(self.cliConnection.before)
        except pe.TIMEOUT as e:
            self.logger.error('CLI Output %s', ' '.join(output))
            raise CLITimeout(e)
        except pe.EOF as e:
            self.logger.error('CLI Output %s', ' '.join(output))
            raise CLIError(self._connectionCommand, e)

        del self.expectDict

    def prepareConnectionCommand(self, uri, user, userDomain,
                                 secure, sslKeyFile, sslCertFile,
                                 sslCaFile, session_timeout, additionalArgs):
        """
        Description: This method prepares CLI connection command
        Author: imeerovi
        Parameters:
            * uri - rhevm URI
            * user - rhevm username
            * userDomain - rhevm user domain
            * secure - secure connection boolean
            * sslKeyFile - ssl key file
            * sslCertFile - ssl certificate file
            * sslCaFile - ssl ca file
            * additionalArgs - additional parameters to CLI
        Returns: nothing
        """
        cliConnect = []

        userWithDomain = '{0}@{1}'.format(user, userDomain)

        # mandatory data
        cliConnect.append('{0} -c -l "{1}" -u "{2}"'.
                          format(self._command, uri, userWithDomain))
        # ssl stuff
        if secure:
            cliConnect.append('-K {0} -C {1} -A {2}'.
                              format(sslKeyFile, sslCertFile, sslCaFile))
        else:
            cliConnect.append('-I')

        # session timeout
        cliConnect.append('-S {0}'.format(session_timeout))

        # optional params
        for key in additionalArgs.keys():
            cliConnect.append(str(additionalArgs[key]))

        self._connectionCommand = ' '.join(cliConnect)
        self.logger.debug('Connect: %s' % self._connectionCommand)

    def outputValidator(self, output):
        """
        Description: Implementation of outputValidator for rhevm-cli
        Author: imeerovi
        Parameters:
            * output - output of cli command run
        Returns: validated output
        """
        # looking for error - to change to more generic map style
        tracebackMsg = self._tracebackMsgSearch in output
        errorStatusMsg = re.search(self._errorStatusMsgSearch,
                                   output, flags=re.DOTALL)
        errorParametersMsg = re.search(self._errorParametersMsgSearch,
                                       output, flags=re.DOTALL)
        errorSyntaxMsg = re.search(self._errorSyntaxMsgSearch,
                                   output, flags=re.DOTALL)
        debugMsg = re.search(self._debugMsg, output, flags=re.DOTALL)
        if tracebackMsg:
            raise CLITracebackError(self.outputCleaner(output))
        if debugMsg:
            self.logger.debug('Debug output: %s',
                              self.outputCleaner(debugMsg.group(0)))
        if errorStatusMsg:
            data = re.search(self._insiderSearch, errorStatusMsg.group(0),
                             flags=re.DOTALL).group(0).split(self._eol)
            status = self.outputCleaner(data[0])
            reason = self.outputCleaner(data[1])
            detail = self.outputCleaner(data[2:])
            raise CLICommandFailure('Command Failed:', status, reason, detail)
        elif errorParametersMsg:
            raise CLICommandFailure('Wrong parameters:', self.outputCleaner(
                                    errorParametersMsg.group(0)))
        elif errorSyntaxMsg:
            raise CLICommandFailure('Wrong syntax:', self.outputCleaner(
                                    errorSyntaxMsg.group(0)))

        return self.outputCleaner(output)

    @threadSafeRun
    def getAutoCompletionOptions(self, cmd=''):
        """
        Description: This method sends "cmd TAB" and gets
                     autocompletion options
        Author: imeerovi
        Parameters:
            * cmd - command to get autocompletion options
        Returns: autocompletion options list
        """
        timeout = 10

        # why we need 'TAB' 'TAB EOL' ? don't ask, it works
        cmd = "%s %s%s" % (cmd, chr(9), chr(9))

        try:
            output = self.sendCmd(cmd, timeout)
        except pe.TIMEOUT as e:
            raise CLITimeout(e)
        except pe.EOF as e:
            raise CLIError(cmd, e)

        # debug case
        if 'send:' in output:
            ret = output.split('send:')[0].split()
        # non debug case, sometimes we can get error message
        # after autocompletion options
        elif 'error:' in output:
            ret = output.split('error:')[0].split()
        else:
            ret = output.split()

        # cleaning from cli trash
        pattern = re.compile(self._cliTrashPattern)
        ret = filter(lambda x: not pattern.search(x), ret)

        if len(ret):
            return ret
        # case with single autocompletion parameter
        else:
            out = self.sendCmd("help %s" % cmd, 10).split('\n')
            ret = [x.split('--')[1].split(':')[0]
                   for x in filter(lambda x: '[--' in x and '*' not in x, out)]
        return ret

    def validateCommand(self, cmd):
        """
        Description: This method validates add, update or remove
                     command passed to cli vs. autocompletion options
        Author: imeerovi
        Parameters:
            * cmd - command to run
        Returns: validated command
        """
        validated_command = []
        starting_position = 0
        autocompletion_params = []
        # taking care of '', ' ', '  ', ... stuff
        spaces_regex = re.compile("'\s*'")
        spaces = iter(spaces_regex.findall(cmd))
        cmd_params = map(lambda x: spaces.next() if x == 'SPACE' else x,
                         re.sub("'\s*'", 'SPACE', cmd).split())
        params_len = len(cmd_params)
        cmd_type, object_name = cmd_params[:2]
        # getting context
        try:
            context = self.contextDict[cmd_type][object_name]
        except KeyError:
            msg = "First level key {0} or second level key {1} are missing \
in Context dictionary:\n{2}".format(cmd_type, object_name, self.contextDict)
            raise CLIAutoCompletionFailure(msg)

        if len(context[0]) == 0:
            help_cmd = "{0} {1}".format(cmd_type, object_name)
            autocompletion_params += self.getAutoCompletionOptions(help_cmd)
        # now we check if we need to add another context
        # add usecase
        # add <type> [parent identifiers] [command options]
        if cmd_type == 'add':
            if 'identifier' in cmd_params[2]:
                context_key = cmd_params[2].replace('--', '').split('-')[0]
                context_objects = filter(lambda x: context_key in x, context)
                if context_objects:
                    help_cmd = "{0} {1} {2} {3}".format(cmd_type, object_name,
                                                        cmd_params[2],
                                                        cmd_params[3])
                    autocompletion_params += \
                        self.getAutoCompletionOptions(help_cmd)
                else:
                    self.logger.error("Object %s is not found in context %s",
                                      cmd_params[2], context)
                starting_position = 4
            else:
                starting_position = 2
        # update or remove usecases
        # update <type> <id> [parent identifiers] [command options]
        # remove <type> <id> [parent identifiers] [command options]
        elif cmd_type in ['update', 'remove']:
            if params_len > 3 and 'identifier' in cmd_params[3]:
                context_key = cmd_params[3].replace('--', '').split('-')[0]
                context_objects = filter(lambda x: context_key in x, context)
                if context_objects:
                    help_cmd = "{0} {1} {2}".format(cmd_type, object_name,
                                                    cmd_params[3])
                    autocompletion_params += \
                        self.getAutoCompletionOptions(help_cmd)
                else:
                    self.logger.error("Object %s is not found in context %s",
                                      cmd_params[3], context)
                starting_position = 5
            else:
                starting_position = 3
        # action <type> <id> <action> [parent identifiers] [command options]
        elif cmd_type == 'action':
            object_type = cmd_params[1]
            object_name = cmd_params[2]
            action = cmd_params[3]
            if params_len > 4 and 'identifier' in cmd_params[4]:
                context_key = cmd_params[4].replace('--', '').split('-')[0]
                context_objects = filter(lambda x: context_key in x, context)
                if context_objects:
                    help_cmd = "{0} {1} {2} {3} {4}".format(cmd_type,
                                                            object_type,
                                                            object_name,
                                                            action,
                                                            cmd_params[4])
                    autocompletion_params += \
                        self.getAutoCompletionOptions(help_cmd)
                else:
                    self.logger.error("Object %s is not found in context %s",
                                      cmd_params[2], context)
                starting_position = 6
            else:
                starting_position = 4

        # remove all duplicated stuff:
        autocompletion_params = set(autocompletion_params)
        self.logger.debug("Autocompletion options:\n%s", autocompletion_params)

        # lets validate
        validated_command += cmd_params[:starting_position]

        # passing over command and checking it
        while starting_position < params_len:
            needed_param = False
            if cmd_params[starting_position].replace('--', '') in \
                    autocompletion_params:
                validated_command.append(cmd_params[starting_position])
                needed_param = True
            starting_position += 1

            # collections or booleans
            if '=' in cmd_params[starting_position] or \
                    cmd_params[starting_position] in ['true', 'false']:
                if needed_param:
                    validated_command.append(cmd_params[starting_position])
                starting_position += 1
                continue
            # integers
            try:
                int(cmd_params[starting_position], 10)
                if needed_param:
                    validated_command.append(cmd_params[starting_position])
                starting_position += 1
                continue
            except ValueError:
                pass
            # strings
            # situation like '--cpu-id', "'Intel", 'Nehalem', "Family'",
            while not cmd_params[starting_position].endswith("'"):
                if needed_param:
                    validated_command.append(cmd_params[starting_position])
                starting_position += 1
            # string without spaces or end of big string with spaces
            else:
                if needed_param:
                    validated_command.append(cmd_params[starting_position])
                starting_position += 1

        return ' '.join(validated_command)

    def getAutocompletionContext(self):
        """
        Description: This method collects contexts for autocompletion and
                    creates dictionary with these contexts
        Author: imeerovi
        """
        self.contextDict = {}
        for cmd in self._cliRootCommands:
            self.contextDict[cmd] = {}
            self.commandRun('help "%s" > %s' % (cmd, TMP_FILE), 10)
            # getting data
            with open('%s' % TMP_FILE) as f:
                out = f.readlines()
            # filtering and parsing it
            out = filter(lambda x: 'contexts:' in x, out)
            for line in out:
                objectType, context = line.split('(')
                self.contextDict[cmd][objectType.split()[1].strip()] = \
                    eval(context.split(')')[0].split('contexts: ')[1])


class OvirtCli(RhevmCli):
    """
    Description: CLI connection implementation for ovirt-shell
    Author: imeerovi
    Parameters:
        * logger - reference to logger
        * uri - ovirt URI
        * user - ovirt username
        * userDomain - ovirt user domain
        * password - ovirt password
        * secure - secure connection boolean
        * sslKeyFile - ssl key file
        * sslCertFile - ssl certificate file
        * sslCaFile - ssl ca file
        * logFile - file for cli log
        * **kwargs - additional parameters to CLI
    """
    _rhevmPrompt = '((\[oVirt shell \(\x1b\[\d;\d\dmconnected\x1b\[\d;m\)\]#' \
        ' )|(\[oVirt shell \(connected\)\]# ))'
    _rhevmDisconnectedPrompt = '((\[oVirt shell \(\x1b\[\d;\d\dmdisconnected' \
        '\x1b\[\d;m\)\]# )|(\[oVirt shell \(disconnected\)\]# ))'
    _command = OVIRT_SHELL
    _errorStatusMsgSearch = "=+ ERROR.*status:.*reason:.*detail:.* (?==+)"
    _errorParametersMsgSearch = "=+ ERROR.* (?==+)"

    def __init__(self, logger, uri, user, userDomain, password,
                 secure, sslKeyFile, sslCertFile, sslCaFile, logFile,
                 session_timeout, **kwargs):
        super(OvirtCli, self).__init__(logger, uri, user, userDomain, password,
                                       secure, sslKeyFile, sslCertFile,
                                       sslCaFile, logFile, session_timeout,
                                       **kwargs)

    def outputValidator(self, output):
        """
        Description: Implementation of outputValidator for ovirt-cli
        Author: imeerovi
        Parameters:
            * output - output of cli command run
        Returns: validated output
        """
        # looking for error - to change to more generic map style
        tracebackMsg = self._tracebackMsgSearch in output
        errorStatusMsg = re.search(self._errorStatusMsgSearch,
                                   output, flags=re.DOTALL)
        errorParametersMsg = re.search(self._errorParametersMsgSearch,
                                       output, flags=re.DOTALL)
        errorSyntaxMsg = re.search(self._errorSyntaxMsgSearch,
                                   output, flags=re.DOTALL)
        debugMsg = re.search(self._debugMsg, output, flags=re.DOTALL)
        if tracebackMsg:
            raise CLITracebackError(self.outputCleaner(output))
        if debugMsg:
            self.logger.debug('Debug output: %s',
                              self.outputCleaner(debugMsg.group(0)))
        if errorStatusMsg:
            data = re.search(self._insiderSearch, errorStatusMsg.group(0),
                             flags=re.DOTALL).group(0).split(self._eol)
            status = self.outputCleaner(data[0])
            reason = self.outputCleaner(data[1])
            detail = self.outputCleaner(data[2:])
            raise CLICommandFailure('Command Failed:', status, reason, detail)
        elif errorParametersMsg:
            reason = errorParametersMsg.group(0).split(self._eol)[1]
            raise CLICommandFailure('Wrong parameters:', self.outputCleaner(
                                    reason))
        elif errorSyntaxMsg:
            raise CLICommandFailure('Wrong syntax:', self.outputCleaner(
                                    errorSyntaxMsg.group(0)))

        return self.outputCleaner(output)


class CliUtil(RestUtil):
    """
    Description: Implements CLI APIs methods
                 Some of the methods are just inherited from Rest API
    Author: edolinin
    Parameters:
        * element - data_structures.py style element
        * collection - data_structures.py style collection
    """
    _shells = {RHEVM_SHELL: RhevmCli, OVIRT_SHELL: OvirtCli}

    def __init__(self, element, collection):
        super(CliUtil, self).__init__(element, collection)
        # no _ in cli
        self.cli_element_name = self.element_name.replace('_', '')

        global cliInit

        if not cliInit:
            if self.opts['cli_tool'] not in self._shells:
                msg = 'Unsupported CLI engine: %s' % self.opts['cli_tool']
                raise UnsupportedCLIEngine(msg)
            try:
                self.cli = self._shells[self.opts['cli_tool']](
                    self.logger, self.opts['uri'], self.opts['user'],
                    self.opts['user_domain'], self.opts['password'],
                    self.opts['secure'],
                    sslKeyFile=self.opts.get('ssl_key_file', None),
                    sslCertFile=self.opts.get('ssl_cert_file', None),
                    sslCaFile=self.opts.get('ssl_ca_file', None),
                    logFile=self.opts['cli_log_file'],
                    session_timeout=self.opts['session_timeout'],
                    optionalParms=self.opts['cli_optional_params'])

            except pe.ExceptionPexpect as e:
                self.logger.error('Pexpect Connection Error: %s ' % e.value)
                exit(2)

            cliInit = self.cli
        else:
            self.cli = cliInit

    def getCollection(self, href):

        if not href:
            href = self.links[self.collection_name]

        return self.get(href, listOnly=True)

    def create(self, entity, positive, expectedEntity=None, incrementBy=1,
               async=False, collection=None):
        '''
        Description: creates a new element
        Author: edolinin
        Parameters:
           * entity - entity for post body
           * positive - if positive or negative verification should be done
           * expectedEntity - if there are some expected entity different
             from sent
           * incrementBy - increment by number of elements
           * async -sycnh or asynch request
        Return: POST response (None on parse error.),
                status (True if POST test succeeded, False otherwise.)
        '''
        out = ''
        addEntity = validator.cliEntety(entity, self.element_name)
        createCmd = "add {0} {1} --expect '201-created'".\
            format(self.cli_element_name, addEntity)

        if collection:
            ownerId, ownerName, entityName = \
                self._getHrefData(collection)

            if ownerId and ownerName:  # adding to some element collection
                createCmd = "add {0} --{1}-identifier '{2}' {3} \
--expect '201-created'".format(self.cli_element_name, ownerId.rstrip('s'),
                               entityName, addEntity)
        correlationId = self.getCorrelationId()
        if correlationId:
            createCmd = "%s --correlation_id %s" % (createCmd, correlationId)

        # checking if we have legal entity name
        createCmd = self.cli.convertComplexNameToBaseEntityName(entity,
                                                                createCmd)
        if self.opts['validate_cli_command']:
            # validating command vs cli help
            self.logger.warning('Generated command:\n%s', createCmd)

            if entity.__class__.__name__ in ADD_WAIVER:
                self.logger.warning('Validation skipped for %s',
                                    entity.__class__.__name__)
            else:
                createCmd = self.cli.validateCommand(createCmd)
                self.logger.warning('Actual command after validation:\n%s',
                                    createCmd)

        createCmd = "%s > %s" % (createCmd, TMP_FILE)
        collHref = collection
        collection = self.getCollection(collHref)

        response = None
        try:
            out = self.cli.cliCmdRunner(createCmd, 'CREATE')
        except CLITracebackError as e:
            self.logger.error("%s", e)
            return response, False
        except CLICommandFailure as e:
            errorMsg = "Failed to create a new element, details: {0}"
            self.logger.error(errorMsg.format(e))
            if positive:
                return response, False
        else:
            if positive:
            # refresh collection
                if collHref:
                    collection = self.get(collHref, listOnly=True)
                else:
                    collection = self.getCollection(collHref)
                # looking for id in cli output:
                elemId = re.search(self.cli._id_extract_re, out).group().\
                    split(':')[1].strip()
                response = self.find(elemId, attribute='id',
                                     collection=collection,
                                     absLink=False)

                expEntity = entity if not expectedEntity else expectedEntity

                if response and not validator.compareElements(
                        expEntity, response, self.logger, self.element_name):
                    return response, False

                self.logger.info("New entity was added successfully")
        return response, True

    def update(self, origEntity, newEntity, positive, current=None):
        '''
        Description: update an element
        Author: edolinin
        Parameters:
           * origEntity - original entity
           * newEntity - entity for post body
           * positive - if positive or negative verification should be done
        Return: PUT response, True if PUT test succeeded, False otherwise
        '''

        updateBody = validator.cliEntety(newEntity, self.element_name)
        collHref, collection = None, None

        if origEntity.name and re.match(IP_FORMAT, origEntity.name):
            name = "'%s'" % origEntity.name
        else:
            name = origEntity.name

        updateCmd = "update {0} {1} {2}".format(self.cli_element_name,
                                                name, updateBody)

        ownerId, ownerName, entityName = \
            self._getHrefData(origEntity.href)

        if ownerId and ownerName and entityName:
            updateCmd = "update {0} '{1}' --{2}-identifier '{3}' {4}".\
                format(entityName, origEntity.id, ownerName, ownerId,
                       updateBody)

            collHref = '/api/{0}s/{1}/{2}s'.format(ownerName,
                                                   ownerId, entityName)

        correlationId = self.getCorrelationId()
        if correlationId:
            updateCmd = "%s --correlation_id %s" % (updateCmd, correlationId)

        if current is not None:
            updateCmd = "%s --current %s" % (updateCmd, current)

        # checking if we have legal entity name
        updateCmd = self.cli.convertComplexNameToBaseEntityName(newEntity,
                                                                updateCmd)

        if self.opts['validate_cli_command']:
            # validating command vs cli help
            self.logger.warning('Generated command:\n%s', updateCmd)

            if newEntity.__class__.__name__ in UPDATE_WAIVER:
                self.logger.warning('Validation skipped for %s',
                                    newEntity.__class__.__name__)
            else:
                updateCmd = self.cli.validateCommand(updateCmd)
                self.logger.warning('Actual command after validation:\n%s',
                                    updateCmd)

        updateCmd = "%s > %s" % (updateCmd, TMP_FILE)

        response = None
        try:
            out = self.cli.cliCmdRunner(updateCmd, 'UPDATE')
        except CLITracebackError as e:
            self.logger.error("%s", e)
            return response, False
        except CLICommandFailure as e:
            errorMsg = "Failed to update a new element, details: {0}"
            self.logger.error(errorMsg.format(e))
            if positive:
                return response, False
        else:
            if positive:
                if collHref:
                    collection = self.get(collHref, listOnly=True)
                else:
                    # refresh collection
                    collection = self.getCollection(collHref)
                # looking for id in cli output:
                elemId = re.search(self.cli._id_extract_re, out).group().\
                    split(':')[1].strip()
                response = self.find(elemId, attribute='id',
                                     collection=collection,
                                     absLink=False)

                if not validator.compareElements(newEntity, response,
                                                 self.logger,
                                                 self.element_name):
                    return response, False

        return response, True

    def _getHrefData(self, href):

        entityHrefData = href.split('/')
        actionOwnerId = entityHrefData[-3]
        actionOwnerName = entityHrefData[-4].rstrip('s')
        actionEntityName = entityHrefData[-2].rstrip('s')

        return (actionOwnerId, actionOwnerName, actionEntityName)

    def delete(self, entity, positive, body=None, **kwargs):
        '''
        Description: delete an element
        Author: edolinin
        Parameters:
           * entity - entity to delete
           * positive - if positive or negative verification should be done
        Return: status (True if DELETE test succeeded, False otherwise)
        '''

        addBody = ''
        if body:
            addBody = validator.cliEntety(body, self.element_name)

        deleteCmd = 'remove {0} "{1}" {2} --async false'.format(
            self.cli_element_name, entity.name, addBody)

        ownerId, ownerName, entityName = self._getHrefData(entity.href)

        if ownerId and ownerName and entityName:
            deleteCmd = "remove {0} '{1}' --{2}-identifier '{3}' {4} "\
                "--async false".format(entityName, entity.id, ownerName,
                                       ownerId, addBody)

        correlationId = self.getCorrelationId()
        if correlationId:
            deleteCmd = "%s --correlation_id %s" % (deleteCmd, correlationId)

        # checking if we have legal entity name
        deleteCmd = self.cli.convertComplexNameToBaseEntityName(entity,
                                                                deleteCmd)

        if self.opts['validate_cli_command']:
            # validating command vs cli help
            self.logger.warning('Generated command:\n%s', deleteCmd)

            if entity.__class__.__name__ in REMOVE_WAIVER:
                self.logger.warning('Validation skipped for %s',
                                    entity.__class__.__name__)
            else:
                deleteCmd = self.cli.validateCommand(deleteCmd)
                self.logger.warning('Actual command after validation:\n%s',
                                    deleteCmd)

        deleteCmd = "%s > %s" % (deleteCmd, TMP_FILE)

        try:
            self.cli.cliCmdRunner(deleteCmd, 'DELETE')
        except CLITracebackError as e:
            self.logger.error("%s", e)
            return False
        except CLICommandFailure as e:
            errorMsg = "Failed to delete an element, details: {0}"
            self.logger.error(errorMsg.format(e))
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

        results = []
        tmpResDict = {}

        if event_id is not None:
            params['from'] = event_id

        constraint = re.sub('\'|\"', '', constraint)

        queryCmd = 'list {0} --query "{1}" {2}'.\
            format(self.collection_name, constraint,
                   " ".join(createCommandLineOptionFromDict(params,
                                                            long_glue=' ')))

        queryCmd = "%s > %s" % (queryCmd, TMP_FILE)

        # checking for special cases
        for cliFormatParam, restFormatParam in \
                self.cli._specialMatrixParamsDict.iteritems():
            queryCmd = queryCmd.replace(cliFormatParam, restFormatParam)
        try:
            out = self.cli.cliCmdRunner(queryCmd, 'SEARCH')
        except CLITracebackError as e:
            self.logger.error("%s", e)
            return []
        except CLICommandFailure as e:
            errorMsg = "Failed to perform query, details: {0}"
            self.logger.error(errorMsg.format(e))
            return []

        # splitting  and cleaning output (first and last lines are empty)
        data = out.split('\n')
        data.pop(0)
        data.pop(-1)

        for line in data:
            # dumping entity data (there is empty line between entities)
            if not line:
                results.append(QueryResult(tmpResDict))
                tmpResDict = {}
                continue
            # getting data
            keyAndValue = line.split(':')
            tmpResDict[keyAndValue[0].strip()] = keyAndValue[1].strip()

        self.logger.debug("Response for QUERY request is: %s " % results)

        return results

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
        act = self.makeAction(async, 10, **params)

        actionCmd = "action {0} '{1}' {2} {3}".\
            format(self.element_name.replace('_', ''), entity.id, action,
                   validator.cliEntety(act, 'action'))

        ownerId, ownerName, entityName = self._getHrefData(entity.href)

        if ownerId and ownerName and entityName:
            addParams = ''
            for p in params:
                if ClassesMapping.get(p, None):
                    if params[p] is None:
                        self.logger.error("%s is None", p)
                        self.logger.error("syncAction failed to run")
                        return False
                    if params[p].id is None:
                        addParams += " --{0}-name '{1}'".format(p,
                                                                params[p].name)
                        self.logger.debug("%s.id=None, using %s.name instead",
                                          params[p], params[p])
                    else:
                        addParams += " --{0}-id '{1}'".format(p, params[p].id)

            actionCmd = "action {0} '{1}' {2} --{3}-identifier '{4}' {5}".\
                        format(entityName, entity.id, action, ownerName,
                               ownerId, addParams)

        correlationId = self.getCorrelationId()
        if correlationId:
            actionCmd = "%s --correlation_id %s" % (actionCmd, correlationId)

        if self.opts['validate_cli_command']:
            # validating command vs cli help
            self.logger.warning('Generated command:\n%s', actionCmd)

            if entity.__class__.__name__ in ACTION_WAIVER:
                self.logger.warning('Validation skipped for %s',
                                    entity.__class__.__name__)
            else:
                createCmd = self.cli.validateCommand(actionCmd)
                self.logger.warning('Actual command after validation:\n%s',
                                    createCmd)

        # checking if we have legal entity name
        actionCmd = self.cli.convertComplexNameToBaseEntityName(entity,
                                                                actionCmd)

        actionCmd = "%s > %s" % (actionCmd, TMP_FILE)
        try:
            res = self.cli.cliCmdRunner(actionCmd, 'ACTION')
        except CLITracebackError as e:
            self.logger.error("%s", e)
            return False
        except CLICommandFailure as e:
            if positive:
                errorMsg = "Failed to perform an action, details: {0}"
                self.logger.error(errorMsg.format(e))
                return False
            else:
                return True
        else:
            if not positive:
                errorMsg = "Succeeded to run an action '{0}' for negative test"
                self.logger.error(errorMsg.format(action))
                return False

        actionStateMatch = [i.split(':')[1].strip() for i in res.split('\n')
                            if 'status-state' in i]
        if not actionStateMatch and positive:
            return False

        actionState = actionStateMatch[0]

        if not async:
            return validator.compareActionStatus(actionState,
                                                 ["complete"], self.logger)
        else:
            return validator.compareActionStatus(actionState,
                                                 ["pending", "complete"],
                                                 self.logger)

        return True
