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

"""
A module containing the functions for loading the configuration
and preparing the environment for the tests.
"""
import os
import sys
import threading
import traceback
import time
import gc
import logging
import yaml
import collections
from jinja2 import Environment, FileSystemLoader


ART_CONFIG = {}
opts = {}
GE = {}

""" A options global for all REST tests. """
RC_RANGE = [2, 9]

# garbage collector interval in seconds
GC_INTERVAL = 600


def set_cmd_line_params_in_dict(cmd_line):

    cmd_line_args = {}

    vars_to_be_treated_as_list = ['engines', 'storages']

    for param in cmd_line:
        try:
            key, value = param.split('=', 1)
        except ValueError:
            raise Exception("Expected '=' sign somewhere in '%s'." % param)
        section, var = key.split('.')
        if var in vars_to_be_treated_as_list:
            value = value.split(',')
        update_dict(cmd_line_args, {section: {var: value}})

    return cmd_line_args


def update_dict(master, update):
    for k, v in update.iteritems():
        if isinstance(v, collections.Mapping):
            r = update_dict(master.get(k, {}), v)
            master[k] = r
        else:
            master[k] = update[k]

    return master


def get_ge_yaml(cmd_line_params):
    ge_yaml = cmd_line_params.get('RUN').get('golden_environment')

    assert os.path.exists(ge_yaml)

    return ge_yaml


def generate_ge_description(ge_yaml):
    env = Environment(loader=FileSystemLoader('/'))

    runtime_yaml = 'runtime.yaml'
    template = env.get_template(ge_yaml)
    with open(ge_yaml, 'r') as f:
        context = yaml.load(f)

    rendered_yaml = template.render(context)

    with open(runtime_yaml, 'w') as f:
        f.write(rendered_yaml)

    with open(runtime_yaml, 'r') as f:
        return yaml.load(f)

    return None


def get_vds_n_passwords():

    vds_passwords = []
    vds = []

    for host in GE['hosts']:
        vds_passwords.append(host.get('password'))
        vds.append(host.get('address'))

    return vds, vds_passwords


def create_runtime_config(path_to_defaults, art_define_args):

    # global opts
    global ART_CONFIG
    global GE

    with open(path_to_defaults, 'r') as fh:
        defaults = yaml.load(fh)

    context = {}
    update_dict(context, defaults)

    cmd_line = set_cmd_line_params_in_dict(art_define_args)
    ge_yaml = get_ge_yaml(cmd_line)

    update_dict(context, cmd_line)

    ART_CONFIG.update(context)
    GE.update(generate_ge_description(ge_yaml))

    ART_CONFIG['DEFAULT']['PRODUCT'] = GE['product']
    ART_CONFIG['DEFAULT']['VERSION'] = GE['version']
    ART_CONFIG['REST_CONNECTION']['host'] = GE['engine']['fqdn']
    ART_CONFIG['REST_CONNECTION']['uri'] = (
        ART_CONFIG['REST_CONNECTION']['uri'] % ART_CONFIG['REST_CONNECTION']
    )
    if not ART_CONFIG['REST_CONNECTION']['urisuffix']:
        ART_CONFIG['REST_CONNECTION']['uri'] = (
            ART_CONFIG['REST_CONNECTION']['uri'].replace('None', '')
        )

    vds, vds_paswords = get_vds_n_passwords()

    ART_CONFIG['PARAMETERS']['vds'] = vds
    ART_CONFIG['PARAMETERS']['vds_password'] = vds_paswords


def dump_stacks(signal, frame):
    """
    In case of ART get stuck we can run kill sig command and get the
    stack traceback of each thread.
    like:
        kill -SIGUSR1 <ART PID>

    __author__ : khakimi
    :param signal: the signal number
    :type signal: int
    :param frame: the interrupted stack frame
    :type frame: frame object
    """
    id2name = dict((th.ident, th.name) for th in threading.enumerate())
    for threadId, stack in sys._current_frames().items():
        print("\nThread: {0}({1})".format(id2name[threadId], threadId))
        traceback.print_stack(f=stack)


def stuck_handler():
    """
    Check MainThread every 4 minutes if stuck.
    """
    mt = threading.current_thread().ident
    t = threading.Thread(target=stuck_check, args=(mt,))
    t.daemon = True
    t.start()


def stuck_check(main_thread):
    t = [None for i in range(5)]
    logger = logging.getLogger("stuck_handler")
    while True:
        time.sleep(240)
        t.pop(0)
        try:
            tmp = sys._current_frames()[main_thread]
        except Exception as ex:
            logger.warning(
                "sys._current_frames failed with exception: %s\n", ex
            )
            break
        t.append(traceback.format_stack(f=tmp))
        if not [x for x in t if t[0] != x]:
            logger.warn(
                "There is possiblity that MainThread is stucked. "
                "Check debug log to see traceback where it is stucked on."
            )
            logger.debug(''.join(t[-1]))


class MonitorGC(object):

    logger = logging.getLogger('art_monitor_gc')

    def __init__(self, interval=GC_INTERVAL):
        self.interval = interval
        self.thread = threading.Thread(target=self.run, name='monitor_gc')
        self.thread.daemon = True
        self.thread.start()

    def run(self):
        self.logger.info("monitor Garbage Collector started")
        saved_flags = gc.get_debug()
        gc.set_debug(0)
        try:
            while True:
                time.sleep(GC_INTERVAL)
                self.collect_gc()
        finally:
            gc.set_debug(saved_flags)
            self.logger.debug("monitor GC stopped")

    def collect_gc(self):
        try:
            collected = gc.collect()
            self.logger.debug("Collected %d objects from GC", collected)
            # Copy garbage so it is not modified while iterate over it.
            uncollectable = gc.garbage[:]
            if uncollectable:
                uncollectable = [
                    self.saferepr(obj) for obj in uncollectable
                    ]
                self.logger.warning(
                    "Found %d uncollectable objects: %s",
                    len(uncollectable), uncollectable
                )
        except Exception as exc:
            self.logger.exception("Error checking GC: %s", exc)

    def saferepr(self, obj):
        """
        Some objects from standard library fail in repr because of buggy
        __repr__ implementation. Try the builtin repr() and if it fails,
        warn and fallback to simple repr.
        """
        try:
            return repr(obj)
        except Exception as e:
            simple_repr = "<%s at 0x%x>" % (type(obj), id(obj))
            self.logger.warning("repr() failed for %s: %s", simple_repr, e)
            return simple_repr
