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
from sys import exit
from rhevm_api.data_struct.data_structures import *
from rhevm_api.data_struct.data_structures import ClassesMapping
from core_api.rest_utils import RestUtil
from core_api import validator
from utilities.utils import createCommandLineOptionFromDict

cliInit = False

DEF_TIMEOUT = 900 # default timeout
DEF_SLEEP = 10 # default sleep
CLI_PROMPT = '[oVirt shell (connected)]'
CLI_TIMEOUT = 30


class CliUtil(RestUtil):
    '''
    Implements CLI APIs methods
    Some of the methods are just inherited from Rest API
    '''

    def __init__(self, element, collection):
        super(CliUtil, self).__init__(element, collection)
        # no _ in cli
        self.element_name = self.element_name.replace('_','')

        global cliInit
       
        if not cliInit:
            user_with_domain = '{0}@{1}'.format(self.opts['user'],\
                                        self.opts['user_domain'])
            cli_connect = 'ovirt-shell -c -l "{0}" -u "{1}" -p "{2}"'.\
                format(self.opts['uri'], user_with_domain, self.opts['password'])

            try:
                self.logger.debug('Connect: %s' % cli_connect)
                self.cli = pe.spawn(cli_connect, timeout=CLI_TIMEOUT)
                self.cli.expect(CLI_PROMPT)
            except pe.ExceptionPexpect as e:
                self.logger.error('Pexpect Connection Error: %s ' % e.value)
                exit(2)

            cliInit = self.cli
        else:
            self.cli = cliInit


    def __del__(self):
        '''
        Close the cli connection
        '''
        self.cli.close()


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
           * expectedEntity - if there are some expected entity different from sent
           * incrementBy - increment by number of elements
           * async -sycnh or asynch request
        Return: POST response (None on parse error.),
                status (True if POST test succeeded, False otherwise.)
        '''
        addEntity = validator.cli_entity(entity, self.element_name)
        
        createCmd = 'create {0} {1}'.format(self.element_name,
            validator.cli_entity(entity, self.element_name))

        if collection:
            ownerId, ownerName, entityName = \
                            self._getHrefData(collection)

            if ownerId and ownerName: # adding to some element collection
                createCmd = "create {0} --{1}-identifier '{2}' {3}".format(\
                                                            self.element_name,
                                                            ownerId.rstrip('s'),
                                                            entityName,
                                                            addEntity)

        self.logger.debug("CREATE cli command is: %s" % createCmd)

        collHref = collection
        collection = self.getCollection(collHref)
        initialCollectionSize = len(collection)

        response = None
        try:
            self.cli.sendline(createCmd)
            self.cli.expect('id(\s+):')

            # refresh collection
            collection = self.getCollection(collHref)

            if entity.name:
                response = self.find(entity.name,
                            collection=collection, absLink=False)
              
            if not async and not validator.compareCollectionSize(collection,
                                        initialCollectionSize + incrementBy,
                                        self.logger):
                    return None, False

            self.logger.info("New entity was added successfully")
            expEntity = entity if not expectedEntity else expectedEntity

            if response and not validator.compareElements(expEntity,
                  response, self.logger, self.element_name):
                return None, False
             
        except pe.ExceptionPexpect as e:
            if positive and self.cli.buffer.find('error'):
                errorMsg = "Failed to create a new element, details: {0}"
                self.logger.error(errorMsg.format(e))
                return None, False
            else:
                if not validator.compareCollectionSize(collection,
                                            initialCollectionSize,
                                            self.logger):
                    return None, False

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

        updateBody = validator.cli_entity(newEntity, self.element_name)
        defaultColl = True
        collHref, collection = None, None

        updateCmd = 'update {0} {1} {2}'.format(self.element_name,
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
            defaultColl = False

        self.logger.debug("UPDATE cli command is: %s" % updateCmd)

        response = None
        try:
            if positive:
                self.cli.sendline(updateCmd)
                self.cli.expect('id(\s+):')
                self.logger.info(self.element_name + " was updated")

                if collHref:
                    collection = self.get(collHref, listOnly=True)
                    
                response = self.find(origEntity.id, 'id', absLink=defaultColl,
                                                        collection=collection)

                if not validator.compareElements(newEntity, response,
                                    self.logger, self.element_name):
                    return None, False

        except pe.ExceptionPexpect as e:
            if positive:
                errorMsg = "Failed to update an element, details: {0}"
                self.logger.error(errorMsg.format(e))
                return None, False
 
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
            addBody = validator.cli_entity(body, self.element_name)

        deleteCmd = 'delete {0} {1} {2}'.format(self.element_name,
                                            entity.name, addBody)

        ownerId, ownerName, entityName = \
                                self._getHrefData(entity.href)

        if ownerId and ownerName and entityName:
            deleteCmd = "delete {0} '{1}' --{2}-identifier '{3}' {4}".\
                format(entityName, entity.id, ownerName, ownerId, addBody)

        self.logger.debug("DELETE cli command is: %s" % deleteCmd)
            
        try:
            self.cli.sendline(deleteCmd)
            # waiting for error because nothing is returned for success
            self.cli.expect('error')
            if positive:
                errorMsg = "Failed to delete an element, details: {0}"
                self.logger.error(errorMsg.format(self.cli))
                return False
            
        except pe.TIMEOUT:
            self.logger.info("Entity '%s' was deleted successfully" % entity.id)
        except pe.ExceptionPexpect as e:
            self.logger.error('Pexpect Error: %s ' % e.value)
      
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
    
        if event_id is not None:
            params['from'] = event_id

        queryCmd = 'list {0} --query "{1}" {2}'.format(self.collection_name,
                constraint, " ".join(createCommandLineOptionFromDict(params)))

        self.logger.debug("SEARCH cli command is: %s" % queryCmd)

        results = []
        try:
            self.cli.sendline(queryCmd)
            self.cli.expect(['id(\s+):', pe.EOF])
            match = self.cli.match
            results = match.groups()
        except pe.TIMEOUT:
            self.logger.warn("No match found for query: '%s' " % queryCmd)
        except pe.ExceptionPexpect as e:
            self.logger.error('Pexpect Error: %s ' % e.value)

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
                                    validator.cli_entity(act, 'action'))

        ownerId, ownerName, entityName = \
                            self._getHrefData(entity.href)

        if ownerId and ownerName and entityName:
            addParams = ''
            for p in params:
                if ClassesMapping.get(p, None):
                    addParams += " --{0}-id '{1}'".format(p, params[p].id)
               
            actionCmd = "action {0} '{1}' {2} --{3}-identifier '{4}' {5}".\
                                format(entityName, entity.id, action,
                                        ownerName, ownerId, addParams)

        self.logger.debug("ACTION cli command is: %s" % actionCmd)
        
        try:
            self.cli.sendline(actionCmd)
            expectOut = 'status-state'
            if action == 'iscsidiscover':
                expectOut = 'iscsi_target'
            self.cli.expect(expectOut, timeout=300)
        except pe.ExceptionPexpect as e:
            if positive:
                errorMsg = "Failed to run an action, details: {0}"
                self.logger.error(errorMsg.format(e))
                return False

            return True

        actionStateMatch = re.match('.*: (\w+).*', self.cli.buffer)
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
  