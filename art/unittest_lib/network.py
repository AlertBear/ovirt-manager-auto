#!/usr/bin/env python

# Copyright (C) 2013 Red Hat, Inc.
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

logger = logging.getLogger(__name__)
DEAFULT_HOST_NICS_NUM = 4
TIMEOUT = 60
SLEEP = 1


def skipBOND(case_list, host_nics):
    '''
    Description: Check if host can run BOND test (host have 4 interfaces)
    if not skip the test (only for unittest)
    **Author**: myakove
    **Parameters**:
       * *case_list* - list of class names from unittest test.
       * *host_nics* - List of interfaces on the host (use config.HOST_NICS)
    '''
    if len(host_nics) < DEAFULT_HOST_NICS_NUM:
        for case in case_list:
            case.__test__ = False
            logger.info("%s is skipped, host cannot run BOND test case" % case)


def WaitForFuncStatus(result=True, timeout=TIMEOUT, sleep=SLEEP, func=None,
                      *args, **kwargs):
    '''
    Description: Get function and run it for given time util success or
                 timeout.
    **Author**: myakove
    **Parameters**:
        * *result* - Expected result from func (True or False)
        * *timeout* - timeout for running the loop
        * *sleep* - Time to sleep between retries
        * *func* - function (*args and **kwargs are from function)
    Example (calling updateNic function)::
        WaitForFuncStatus(result=True, timeout=60, sleep=1,
                          func=updateNic, positive=True,
                          vm=config.VM_NAME[0], nic="vnic3",
                          network=config.VLAN_NETWORKS[1],
                          plugged='false')
    '''
    time_out = timeout
    while timeout > 0:
        if func(*args, **kwargs) == result:
            return True
        timeout -= sleep
        time.sleep(sleep)
    logger.error("(%s) return incorrect status after %s seconds" %
                (func.__name__, time_out))
    return False
