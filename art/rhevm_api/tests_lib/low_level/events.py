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

import logging
import time

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.core_api import apis_utils
from art.core_api.apis_exceptions import APITimeout
from art.core_api.validator import compareCollectionSize
from art.rhevm_api.utils.test_utils import get_api

logger = logging.getLogger("art.ll_lib.events")

ELEMENT = 'event'
COLLECTION = 'events'
util = get_api(ELEMENT, COLLECTION)

DEF_TIMEOUT = 120
DEF_SLEEP = 5
SAMPLER_TIMEOUT = 210
MAX_EVENTS = 100


def get_max_event_id(query="", max_events=MAX_EVENTS):
    """
    Function get id of last event or id of last given event under query

    Args:
        query (str): query of event
        max_events (int): Max number of events to get from query

    Returns:
        int or None:  If query is empty, return id of last event,
        if query not empty return id of last event with given query,
        if no events founded return None
    """
    logger.info("Getting MAX event ID")
    events = util.query(constraint=query, max=max_events)
    if not events:
        logger.warning("Event ID not found")
        return None
    return max(int(event.get_id()) for event in events)


def search_for_recent_event(
    positive, win_start_query, query, expected_count=1, max_events=MAX_EVENTS
):
    """
    Checks the count of events specified by query, sentineled by
    win_start_query.

    Expected count is the count of such events on the listing page, that have
    their id greater that the event specified by win_start_query. If
    win_start_query matches more events, the first one is taken in account.

    Args:
        positive (bool): Expected result
        win_start_query (str): Event text and type to start from
        query (str): Event text and type to query
        expected_count (int): Expected events to find
        max_events (int): Max number of events to get from query

    Examples:
        search_for_recent_event(
            True, win_start_query='DataCenterRest1 type=950',
            query='DatacenterRest2 type=950',expected_count=1
        )

        this will expect one occurence of event of type 950 with description
        containing string "DataCenterRest1".

    Returns:
        bool: True if expected_count == number of found events, False otherwise
    """
    expected_count = int(expected_count)

    # Pick the event with maximum id, matching the win_start_query.
    win_start_event_id = get_max_event_id(
        query=win_start_query, max_events=max_events
    )
    if win_start_event_id is None:
        util.logger.error(
            "Couln\'t find the event that marks the matching-window start, "
            "win_start_query=%s", win_start_query
        )
        return False

    # Query for events matching `query`, with id bigger than window start one.
    found_ev = util.query(query, event_id=str(win_start_event_id))
    util.logger.info('Searching for events with id > %s,', win_start_event_id)
    status = compareCollectionSize(found_ev, expected_count, util.logger)

    return positive == status


def search_for_recent_event_from_event_id(
    positive, win_start_event_id, query, expected_count=1
):
    """
    Checks the count of events specified by query from win_start_event_id.

    Expected count is the count of such events on the listing page, that have
    their id greater that specified by win_start_event_id.

    Args:
        positive (bool): Expected result
        win_start_event_id (str): Event ID to start from
        query (str): Event text and type to query
        expected_count (int): Expected events to find

    Examples:
        search_for_recent_event_from_event_id(
            True, win_start_event_id=event_id,
            query='Started to check for available updates',expected_count=1
        )

        this will expect one occurrence of event with description
        containing string "Started to check for available updates".

    Returns:
        bool: True if expected_count == number of found events, False otherwise
    """
    expected_count = int(expected_count)

    # Query for events matching `query`, with id bigger than window start one.
    found_ev = util.query(query, event_id=str(win_start_event_id))
    util.logger.info('Searching for events with id > %s,', win_start_event_id)
    status = compareCollectionSize(found_ev, expected_count, util.logger)

    return positive == status


def wait_for_event(
    query, start_id=None, win_start_query=None, timeout=DEF_TIMEOUT,
    sleep=DEF_SLEEP, max_events=MAX_EVENTS
):
    """
    Wait until there is an event matching query with id greater than start_id

    Args:
        query (str): query specifying the event to wait for
        start_id (str): All the returned events will have id greater than
            start_id
        win_start_query (str): A query for the event which id
            should be used for start_id
        timeout (int): Duration of polling for the event to appear in
            seconds
        sleep (int): Interval between the poll requests in seconds
        max_events (int): Max number of events to get from query

    Returns:
        bool: True, if found event in give timeout, else False
    """
    if win_start_query:
        start_id = get_max_event_id(
            query=win_start_query, max_events=max_events
        )
    if start_id is None:
        start_id = get_max_event_id(max_events=max_events)
    sampler = apis_utils.TimeoutingSampler(
        timeout, sleep, get_events_after_some_event, start_id
    )
    try:
        for events in sampler:
            for event in events:
                if query in event.get_description():
                    return True
    except APITimeout:
        return False


def get_events_after_some_event(event_id, max_events=MAX_EVENTS):
    """
    Return all events after specific event id

    Args:
        event_id (str): event id
        max_events (int): Max number of events to get from query

    Returns:
        list: list of event instances
    """
    events_list = util.query(constraint="", max=max_events)
    return filter(lambda x: int(x.get_id()) > int(event_id), events_list)


def find_event(
    last_event, event_code, content, matches, timeout=SAMPLER_TIMEOUT,
    max_events=MAX_EVENTS
):
    """
    Find one event or more in RHEVM event log by event code and keywords in
    event description. Search for the event only from last event ID.

    Args:
        last_event (Event): Event object to search from
        event_code (int): Event code to search for
        content (str): content to search in description
        matches (int): Number of matches to find in events
        timeout (int): Timeout to exit if number of events not found
        max_events (int): Max number of events to get from query

    Returns:
        bool: True if number of given matches events found otherwise False
    """
    start_time = time.time()
    found_events = list()
    last_event_id = int(last_event.get_id())
    logger.info("Last event ID: %s", last_event_id)
    while matches > 0:
        if timeout < time.time() - start_time:
            logger.error("Not all events with code %s are found", event_code)
            return False

        # Get all events again, we may have new events
        events = get_all_events_from_specific_event_id(
            code=event_code, start_event_id=last_event_id,
            max_events=max_events
        )
        # Filter events that already found
        events = [
            v for v in events if int(v.get_id()) not in found_events
            ]

        for event in events:
            event_id = int(event.get_id())
            event_description = event.get_description()
            if content in event_description and event_id > last_event_id:
                logger.info(
                    "Event found: [%s] %s", event_id, event_description
                )
                matches -= 1
                found_events.append(event_id)
    return True


def get_last_event(code, max_events=MAX_EVENTS):
    """
    Get last event ID by event code

    Args:
        code (int): Event code
        max_events (int): Max number of events to get from query

    Returns:
        Event: Event object if event found else dummy Event object
    """
    logger.info("Get last event with event code %s", code)
    all_events = get_all_events_by_event_code(code=code, max_events=max_events)
    if all_events:
        # The last event is the first on the events list
        return all_events[0]

    else:
        logger.warning(
            "Event with code %s was not found. Creating dummy Event with ID 1",
            code
        )
        event_obj = apis_utils.data_st.Event()
        event_obj.set_id("1")
        event_obj.set_description("Dummy object (get_last_event())")
        return event_obj


def get_all_events_from_specific_event_id(
    code, start_event_id, max_events=MAX_EVENTS
):
    """
    Get all events since start_event_id

    Args:
        code (int): Event code to query
        start_event_id (int): Start event ID to get events from
        max_events (int): Max number of events to get from query

    Returns:
        list: List of events objects
    """
    all_events = get_all_events_by_event_code(code=code, max_events=max_events)
    logger.info("Filter events with event ID > %s", start_event_id)
    return [i for i in all_events if int(i.id) > int(start_event_id)]


def get_all_events_by_event_code(code, max_events=MAX_EVENTS):
    """
    Get all events that match given event code

    Args:
        code (int): Event code to query events
        max_events (int): Max number of events to get from query

    Returns:
        list: All events with matching event code
    """
    query = "type={0}".format(code)
    logger.info("Get all events with code %s", code)
    return ll_hosts.EVENT_API.query(constraint=query, max=max_events)
