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

import os
import re
from concurrent.futures import ThreadPoolExecutor

LOAD_SCRIPT_DIR = "/tmp"
LOAD_SCRIPT_NAME = "load_host.sh"

logger = logging.getLogger(__name__)


def get_list_of_online_cpus_on_resource(resource):
    """
    Return number of online cpus on resource

    Args:
        resource (VDS): resource

    Returns:
        list: online cpu's on resource
    """
    online_cpus_l = []
    command = ['lscpu']
    rc, out, _ = resource.run_command(command)
    if rc:
        return online_cpus_l
    online_cpus = re.search(r'On-line CPU\(s\) list:\s+(\S+)', out).group(1)
    online_cpus = online_cpus.split(',')
    for cpus in online_cpus:
        if '-' in cpus:
            t_cpus = cpus.split('-')
            online_cpus_l.extend(xrange(int(t_cpus[0]), int(t_cpus[1]) + 1))
        else:
            online_cpus_l.append(int(cpus))
    return online_cpus_l


def load_resource_cpu(resource, load):
    """
    Load resource CPU

    Args:
        resource (VDS): resource
        load (int): load resource to given value

    Returns:
        bool: True, if load succeed, otherwise False
    """
    logger.info("Get number of online CPU's from resource %s", resource)
    num_of_cpus = len(get_list_of_online_cpus_on_resource(resource))
    if not num_of_cpus:
        logger.error(
            "Failed to get number of online CPU's from resource %s",
            resource
        )
        return False
    logger.info(
        "Number of online CPU's on resource %s: %d", resource, num_of_cpus
    )
    num_of_cpus /= 100 / load
    logger.info(
        "Create CPU load script on resource %s", resource
    )
    script_body = (
        "#!/bin/bash\n"
        "for i in `seq 1 %d`;\n"
        "do while :\n"
        " do :\n"
        " done &\n"
        " done" %
        num_of_cpus
    )
    script_path = os.path.join(LOAD_SCRIPT_DIR, LOAD_SCRIPT_NAME)
    resource.fs.create_script(script_body, script_path)
    cmd = [
        "sh", script_path, "&>", "/tmp/OUT1", "&", "echo", "$!"
    ]
    logger.info(
        "Run CPU load script '%s' on resource %s", script_path, resource
    )
    rc = resource.run_command(cmd)[0]
    if rc:
        return False
    return True


def load_resources_cpu(resources, load):
    """
    Load resources CPU

    Args:
        resources (list): VDS resources
        load (int): load resource to given value

    Returns:
        bool: True, if load succeed on all resources, otherwise False
    """
    results = []
    with ThreadPoolExecutor(max_workers=len(resources)) as executor:
        for resource in resources:
            results.append(executor.submit(load_resource_cpu, resource, load))
    for result in results:
        if not result.result():
            return False
    return True


def stop_cpu_load_on_resource(resource):
    """
    Stop CPU load on resource
    Args:
        resource (VDS): resource

    Returns:
        bool: True, if loading stopped, otherwise False
    """
    cmd = [
        "kill", "$(pidof", "sh", "%s)" % os.path.join(
            LOAD_SCRIPT_DIR, LOAD_SCRIPT_NAME
        )
    ]
    logger.info("Stop CPU loading on resource %s", resource)
    rc = resource.executor().run_cmd(cmd)[0]
    if rc:
        logger.error("Failed to stop CPU loading on host %s", resource)
        return False
    return True


def stop_cpu_load_on_resources(resources):
    """
    Stop CPU load on resources
    Args:
        resources (list): VDS resources

    Returns:
        bool: True, if loading stopped on all hosts, otherwise False
    """
    results = []
    with ThreadPoolExecutor(max_workers=len(resources)) as executor:
        for resource in resources:
            results.append(
                executor.submit(stop_cpu_load_on_resource, resource)
            )
    for result in results:
        if not result.result():
            return False
    return True
