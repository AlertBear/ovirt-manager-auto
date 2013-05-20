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

import logging
logger = logging.getLogger(__name__)
DEAFULT_HOST_NICS_NUM = 4


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
