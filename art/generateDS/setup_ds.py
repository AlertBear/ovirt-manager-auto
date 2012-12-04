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

import os
from abc import ABCMeta, abstractmethod
import logging
from subprocess  import Popen, PIPE

logger = logging.getLogger('setup_ds')


class GenerateDataStructures(object):

    __metaclass__ = ABCMeta

    def __init__(self, opts, repo_path):
        self._repo_path = repo_path
        self._opts = opts
        self._set_xsd_path()

    @abstractmethod
    def _set_xsd_path(self):
        """
        We need to get path to right api
        """

    def __call__(self, conf):
        self._download_xsd()
        self._generate_ds()

    def _download_xsd(self):
        from art.core_api.http import HTTPProxy
        proxy = HTTPProxy(self._opts)
        res = proxy.GET('/api?schema')
        if res['status'] > 300:
            raise Exception("Failed to download schema: %s " % res['reason'])

        with open(self._xsd_path, 'w') as fh:
            fh.write(res['body'])
        logger.info("Downloaded XSD scheme: %s", self._xsd_path)

    def _generate_ds(self):
        ds_exec = os.path.join(self._repo_path, 'generateDS', 'generateDS.py')
        cmd = ['python', ds_exec, '-f', '-o', self._ds_path, \
                '--member-specs=dict', self._xsd_path]

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode:
            raise Exception(err)
        logger.info("Generated data structures: %s", self._ds_path)
