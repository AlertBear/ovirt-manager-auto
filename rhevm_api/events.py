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

from rhevm_api.test_utils import get_api
from utils.validator import compareCollectionSize

ELEMENT = 'event'
COLLECTION = 'events'
util = get_api(ELEMENT, COLLECTION)

DEF_TIMEOUT = 120
DEF_SLEEP = 5


def _getMaxEventId(query):
    events = util.query(query)
    if not events:
        return None
    return max(int(event.get_id()) for event in events)


def searchForRecentEvent(positive, win_start_query, query, expected_count=1):
    """
    Checks the count of events specified by query, sentineled by win_start_query.

    Expected count is the count of such events on the listing page, that have 
    their id greater that the event specified by win_start_query. If 
    win_start_query matches more events, the first one is taken in account.

    Example use:
    
    searchForRecentEvent(true, win_start_query='DataCenterRest1 type=950',
        query='DatacenterRest2 type=950',expected_count=1)

    this will expect one occurence of event of type 950 with description 
    containing string "DataCenterRest1".
    
    Author: jhenner
    """
    expected_count = int(expected_count)

    # Pick the event with maximum id, matching the win_start_query.
    win_start_event_id = _getMaxEventId(win_start_query)
    if win_start_event_id is None:
        util.logger.error('Couln\'t find the event that marks the ' \
                     'matching-window start, win_start_query="%s"',
                     win_start_query)
        return False

    # Query for events matching `query`, with id bigger than window start one.
    found_ev = util.query(query, event_id = str(win_start_event_id))
    util.logger.info('Searching for events with id > %s,', win_start_event_id)
    status = compareCollectionSize(found_ev, expected_count, util.logger)
    
    return positive == status


def waitForEvent(query, start_id=None, win_start_query=None,
    timeout=DEF_TIMEOUT, sleep=DEF_SLEEP):
    '''
    Wait until there is an event matching query with id greater than start_id.

    Parameters:
     * query       - query specifying the event to wait for.
     * start_id    - All the returned events will have id greater than start_id.
     * win_start_query - A query for the event which id should be used for
                         start_id.
     * timeout     - Duration of polling for the event to appear in seconds.
     * sleep       - Interval between the poll requests in seconds.
    '''
    if win_start_query:
        start_id = _getMaxEventId(win_start_query)
    if start_id is None:
        start_id = _getMaxEventId('')

    util.waitForQuery(query, str(start_id), timeout, sleep)
    return True

