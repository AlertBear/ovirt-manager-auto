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

from utils.data_structures import Host
from utils.apis_utils import get_api

ELEMENT = 'host'
COLLECTION = 'hosts'
util = get_api(ELEMENT, COLLECTION)


def activateHost(positive, host, wait=False):
    '''
    Description: activate host (set status to UP)
    Author: edolinin
    Parameters:
       * host - name of a host to be activated
    Return: status (True if host was activated properly, False otherwise)
    '''
    hostObj = util.find(host)

    status = util.syncAction(hostObj, "activate", positive)
    
    if status and wait and positive:
        testHostStatus = util.waitForElemStatus(hostObj, "up", 30)
    else:
        testHostStatus = True

    return status and testHostStatus

