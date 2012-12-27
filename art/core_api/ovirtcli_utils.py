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
from functools import wraps
from sys import exit
from abc import ABCMeta, abstractmethod
from time import strftime
from art.rhevm_api.data_struct.data_structures import *
from art.rhevm_api.data_struct.data_structures import ClassesMapping
from art.core_api.rest_utils import RestUtil
from art.core_api.apis_exceptions import CLIError, CLITimeout,\
            CLICommandFailure, UnsupportedCLIEngine
from art.core_api import validator
from utilities.utils import createCommandLineOptionFromDict

cliInit = False
addlock = threading.Lock()

ILLEGAL_XML_CHARS = u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]'
CONTROL_CHARS = u'[\n\r]'
RHEVM_SHELL = 'rhevm-shell'
TMP_FILE = '/tmp/cli_output.tmp'


def threadSafeRun(func):
    """
    This closure will be used as decorator while calling API methods
    """
    @wraps(func)
    def apifunc(*args, **kwargs):
        with addlock:
            return func(*args, **kwargs)
    return apifunc


class CliConnection(object):
    __metaclass__ = ABCMeta

    def __init__(self, command, prompt, timeout, logFile=None):
        self._prompt = prompt
        self.cliConnection = pe.spawn(command, timeout=timeout)
        self.cliConnection.setecho(False)
        timestamp = strftime('%Y%m%d_%H%M%S')
        if logFile:
            self.cliLog = logFile
        else:
            self.cliLog = "/tmp/cli_log_%s.log" % timestamp
        self.cliConnection.logfile = open(self.cliLog, 'w')
        self._expectDict = {}
        self._illegalXMLCharsRE = re.compile(ILLEGAL_XML_CHARS)
        self._controlCharsRE = re.compile(CONTROL_CHARS)

    @abstractmethod
    def login(self, *args, **kwargs):
        """
        Virtual function that should be implemented by child class.
        Reason: Login may differ between different CLI engines
        """

    @property
    def expectDict(self):
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
        with open(TMP_FILE) as f:
            return f.read()

    def sendCmd(self, cmd, timeout):
        """
        This method sends command
        Input:
        cmd - command to run
        timeout - specific timeout in [sec] for this command run
        Output: string with data from child process
        """
        if not timeout:
            timeout = self.cliConnection.timeout

        expectList = self. expectDict.keys()
        expectList.insert(0, self._prompt)
        output = []

        self.cliConnection.sendline(cmd)
        try:
            i = self.cliConnection.expect(expectList, timeout)
            while i != 0:
                sendButton = self.expectDict[expectList[i]]
                self.cliConnection.sendline(sendButton)
                output.append(self.cliConnection.before)

                # WA for trash in buffer (END issue)
                try:
                    i = self.cliConnection.expect(self._prompt,
                                              timeout=0.001)
                except pe.TIMEOUT:
                    i = self.cliConnection.expect(expectList,
                                              timeout)

            output.append(self.cliConnection.before)
        except pe.TIMEOUT as e:
            raise CLITimeout(e)
        except pe.EOF as e:
            raise CLIError(cmd, e)

        # flushing the buffer
        self.cliConnection.expect([self._prompt, pe.TIMEOUT], timeout=0.1)
        if type(self.cliConnection.before) == str:
            output.append(self.cliConnection.before)

        return "\n".join(output)

    def commandRun(self, cmd, timeout=''):
        """
        Wrapper that runs command and returns validated output
        Input:
         - cmd - command to run
         - timeout - timeout in [sec]. If timeout parameter is
           not set default timeout used
        """
        return self.outputValidator(self.sendCmd(cmd, timeout))

    @abstractmethod
    def outputValidator(self, output):
        """
        Virtual function that should be implemented by child class.
        Reason:  Output validation may differ between different CLI engines
        """

    def outputCleaner(self, output):
        """
        this method cleans output for special characters and align it to UTF8
        """
        if type(output) == list:
            output = ' '.join(output)
        output = self.escapeControlChars(output)
        return self.escapeXMLIllegalChars(output)

    def escapeControlChars(self, val, replacement=''):
        return self._controlCharsRE.sub(replacement, val)

    def escapeXMLIllegalChars(self, val, replacement=''):
        return self._illegalXMLCharsRE.sub(replacement, val).decode('utf-8')


class RhevmCli(CliConnection):
    """
    CLI connection implementation for rhevm-shell
    """
    # rhevm shell specific configs
    _query_id_re = 'id(\s+):'
    _id_extract_re = 'id(\\s+):(\\s+)(\S*)'
    _status_extract_re = '.*: (\w+).*'
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
    _specialCliPrompt = {'\r\n:': ' ', '7m\(END\)': 'q'}

    def __init__(self, logger, uri, user, userDomain, password,
                 secure, sslKeyFile, sslCertFile, sslCaFile, logFile,
                 **kwargs):
        """
        Input:
         - logger - logger reference
         - uri, user, userDomain, password - REST API Parameters
         - additional parameters to CLI could be passed via kwargs
        """
        self.logger = logger
        self.prepareConnectionCommand(uri, user, userDomain,
            secure, sslKeyFile, sslCertFile, sslCaFile, additionalArgs=kwargs)
        super(RhevmCli, self).__init__(self._connectionCommand,
                            prompt=self._rhevmPrompt,
                            timeout=self._rhevmTimeout,
                            logFile=logFile)
        self.logger.debug("CLI logfile: %s" % self.cliLog)
        self.login(password)
        # updating parent dictionary for cli work
        self.expectDict = self._specialCliPrompt

    @threadSafeRun
    def cliCmdRunner(self, apiCmd, apiCmdName):
        self.logger.debug("%s cli command is: %s", apiCmdName, apiCmd)
        errAndDebug = self.commandRun(apiCmd)
        out = self.readTmpFile()
        self.logger.debug("%s cli command Debug and Error output: %s",
                              apiCmdName, errAndDebug)
        self.logger.debug("%s cli command output: %s", apiCmdName, out)
        return out

    def login(self, password):
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
                secure, sslKeyFile, sslCertFile, sslCaFile, additionalArgs):
        cliConnect = []

        userWithDomain = '{0}@{1}'.format(user, userDomain)

        # mandatory data
        cliConnect.append('{0} -c -l "{1}" -u "{2}"'.\
                    format(RHEVM_SHELL, uri, userWithDomain))
        # ssl stuff
        if secure:
            cliConnect.append('-K {0} -C {1} -A {2}'.\
                    format(sslKeyFile, sslCertFile, sslCaFile))
        else:
            cliConnect.append('-I')
        # optional params
        for key in additionalArgs.keys():
            cliConnect.append(str(additionalArgs[key]))

        self._connectionCommand = ' '.join(cliConnect)
        self.logger.debug('Connect: %s' % self._connectionCommand)

    def outputValidator(self, output):
        # looking for error - to change to more generic map style
        errorStatusMsg = re.search(self._errorStatusMsgSearch,
                                   output, flags=re.DOTALL)
        errorParametersMsg = re.search(self._errorParametersMsgSearch,
                                   output, flags=re.DOTALL)
        errorSyntaxMsg = re.search(self._errorSyntaxMsgSearch,
                                   output, flags=re.DOTALL)
        debugMsg = re.search(self._debugMsg, output, flags=re.DOTALL)
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
            raise CLICommandFailure('Wrong parameters:',
                            self.outputCleaner(errorParametersMsg.group(0)))
        elif errorSyntaxMsg:
            raise CLICommandFailure('Wrong syntax:',
                            self.outputCleaner(errorSyntaxMsg.group(0)))

        return self.outputCleaner(output)


class CliUtil(RestUtil):
    '''
    Implements CLI APIs methods
    Some of the methods are just inherited from Rest API
    '''

    def __init__(self, element, collection):
        super(CliUtil, self).__init__(element, collection)
        # no _ in cli
        self.cli_element_name = self.element_name.replace('_', '')

        global cliInit

        if not cliInit:
            try:
                if self.opts['cli_tool'] == RHEVM_SHELL:
                    self.cli = RhevmCli(self.logger,
                            self.opts['uri'],
                            self.opts['user'],
                            self.opts['user_domain'],
                            self.opts['password'],
                            self.opts['secure'],
                            # WA until conf spec implementation in ssl plugin
                            sslKeyFile=self.opts.get('ssl_key_file', None),
                            sslCertFile=self.opts.get('ssl_cert_file', None),
                            sslCaFile=self.opts.get('ssl_ca_file', None),
                            logFile=self.opts['cli_log_file'],
                            optionalParms=self.opts['cli_optional_params'],
                            )
                else:
                    msg = 'Unsupported CLI engine: %s' % self.opts['cli_tool']
                    raise UnsupportedCLIEngine(msg)

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
        createCmd = 'add {0} {1} --expect 201'.format(self.cli_element_name,
            validator.cliEntety(entity, self.element_name))

        if collection:
            ownerId, ownerName, entityName = \
                            self._getHrefData(collection)

            if ownerId and ownerName:  # adding to some element collection
                createCmd = "add {0} --{1}-identifier '{2}' {3} --expect 201".\
                            format(self.cli_element_name, ownerId.rstrip('s'),
                                   entityName, addEntity)
        correlationId = self.getCorrelationId()
        if correlationId:
            createCmd = "%s --correlation_id %s" % (createCmd, correlationId)

        createCmd = "%s > %s" % (createCmd, TMP_FILE)
        collHref = collection
        collection = self.getCollection(collHref)

        response = None
        try:
            out = self.cli.cliCmdRunner(createCmd, 'CREATE')
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

                if response and not validator.compareElements(\
                    expEntity, response, self.logger, self.element_name):
                    return response, False

                self.logger.info("New entity was added successfully")
        return response, True

    def update(self, origEntity, newEntity, positive):
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

        updateCmd = 'update {0} {1} {2}'.format(self.cli_element_name,
                                    origEntity.name, updateBody)

        ownerId, ownerName, entityName = \
                        self._getHrefData(origEntity.href)

        if ownerId and ownerName and entityName:
            updateCmd = \
            "update {0} '{1}' --{2}-identifier '{3}' {4}".\
                    format(entityName, origEntity.id,
                        ownerName, ownerId, updateBody)

            collHref = '/api/{0}s/{1}/{2}s'.format(ownerName,
                                        ownerId, entityName)

        correlationId = self.getCorrelationId()
        if correlationId:
            updateCmd = "%s --correlation_id %s" % (updateCmd, correlationId)

        updateCmd = "%s > %s" % (updateCmd, TMP_FILE)

        response = None
        try:
            out = self.cli.cliCmdRunner(updateCmd, 'UPDATE')
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
                                self.logger, self.element_name):
                    return response, False

        return response, True

    def _getHrefData(self, href):

        entityHrefData = href.split('/')
        actionOwnerId = entityHrefData[-3]
        actionOwnerName = entityHrefData[-4].rstrip('s')
        actionEntityName = entityHrefData[-2].rstrip('s')

        return (actionOwnerId, actionOwnerName, actionEntityName)

    def delete(self, entity, positive,  body=None, **kwargs):
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

        deleteCmd = 'remove {0} "{1}" {2} --expect 201'.format(\
                            self.cli_element_name, entity.name, addBody)

        ownerId, ownerName, entityName = \
                                self._getHrefData(entity.href)

        if ownerId and ownerName and entityName:
            deleteCmd = "remove {0} '{1}' --{2}-identifier '{3}' {4}\
             --expect 201".format(entityName, entity.id, ownerName, ownerId,
                                  addBody)

        correlationId = self.getCorrelationId()
        if correlationId:
            deleteCmd = "%s --correlation_id %s" % (deleteCmd, correlationId)

        deleteCmd = "%s > %s" % (deleteCmd, TMP_FILE)

        try:
            self.cli.cliCmdRunner(deleteCmd, 'DELETE')
        except CLICommandFailure as e:
            errorMsg = "Failed to delete an element, details: {0}"
            self.logger.error(errorMsg.format(e))
            if positive:
                return False

        return True

    def query(self, constraint,  exp_status=None, href=None, event_id=None,
                                                                 **params):
        '''
        Description: run search query
        Author: edolinin
        Parameters:
           * constraint - query for search
        Return: query results
        '''

        if event_id is not None:
            params['from'] = event_id

        queryCmd = 'list {0} --query "{1}" {2}'.format(self.collection_name,
                constraint, " ".join(createCommandLineOptionFromDict(params,
                                                             long_glue=' ')))

        queryCmd = "%s > %s" % (queryCmd, TMP_FILE)

        try:
            out = self.cli.cliCmdRunner(queryCmd, 'SEARCH')
        except CLICommandFailure as e:
            errorMsg = "Failed to perform query, details: {0}"
            self.logger.error(errorMsg.format(e))
            return []

        data = re.findall(self.cli._query_id_re, out)
        if data:
            results = data
        else:
            results = []

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

        ownerId, ownerName, entityName = \
                            self._getHrefData(entity.href)

        if ownerId and ownerName and entityName:
            addParams = ''
            for p in params:
                if ClassesMapping.get(p, None):
                    addParams += " --{0}-id '{1}'".format(p, params[p].id)

            actionCmd = "action {0} '{1}' {2} --{3}-identifier '{4}' {5}".\
                        format(entityName, entity.id, action, ownerName,
                                 ownerId, addParams)

        actionCmd = "%s > %s" % (actionCmd, TMP_FILE)
        try:
            res = self.cli.cliCmdRunner(actionCmd, 'ACTION')
        except CLICommandFailure as e:
            errorMsg = "Failed to perform action, details: {0}"
            self.logger.error(errorMsg.format(e))
            if positive:
                return False

        expectOut = 'status-state'
        if action == 'iscsidiscover':
            expectOut = 'iscsi_target'

        actionStateMatch = re.match(self.cli._status_extract_re, res,
                                    flags=re.DOTALL)
        if not actionStateMatch and positive:
            return False

        actionState = actionStateMatch.group(1)
        if positive and expectOut == 'status-state':
            if not async:
                return validator.compareActionStatus(actionState,
                                        ["complete"], self.logger)
            else:
                return validator.compareActionStatus(actionState,
                            ["pending", "complete"], self.logger)
        else:
            return validator.compareActionStatus(actionState,
                                    ["failed"], self.logger)
