#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

""" Common functions and wrappers used in all other tests. """

__test__ = False

import logging
import uuid
from art.rhevm_api.tests_lib.low_level import disks

LOGGER = logging.getLogger(__name__)

# For more info about tables check:
# http://www.ovirt.org/Features/Design/Quota
V_QUOTA_GLOBAL = 'quota_global_view'
V_QUOTA_VDS = 'quota_vds_group_view'
V_QUOTA_STORAGE = 'quota_storage_view'
T_QUOTA = 'quota'
T_QUOTA_LIMITATION = 'quota_limitation'


class DB(object):
    """
    Implements basic functionality for quota queries to db.
    """
    def __init__(self, setup):
        """
        Creates connection to db.
        Parameters:
         * setup - instance of linux machine class
        """
        self.setup = setup

    def update_quota(self, quota_name, **kwargs):
        """
        Update quota table.
        Parameters:
         * threshold_vds_group_percentage - vds threshold in %
         * threshold_storage_percentage - storage threshold in %
         * grace_vds_group_percentage - vds grace in %
         * grace_storage_percentage - storage grace in %
        """
        sql = "UPDATE quota SET %s = '%s' WHERE quota_name = '%s'"
        for k, v in kwargs.iteritems():
            self.setup.psql(sql, k, v, quota_name)

    def set_dc_quota_mode(self, dc, mode):
        """
        Set datacenter quota mode.
        Parameters:
         * dc - datacenter to set mode
         * mode - 0, 1 or 2(Disabled, Audit, Enforced)
        """
        sql = ("UPDATE storage_pool "
               "SET quota_enforcement_type = '%s' WHERE name = '%s'")
        self.setup.psql(sql, mode, dc)

    def get_quota_id_by_name(self, quota_name):
        """
        Return quota id by name.
        Parameters:
         * quota_name - name of quota
        Return quota id.
        """
        sql = "select id from %s where quota_name = '%s'"
        return self.setup.psql(sql, T_QUOTA, quota_name)[0][0]

    def get_quota_name_by_id(self, quota_id):
        """
        Return quota name by id.
        Parameters:
         * quota_id - id of quota
        Return quota name.
        """
        sql = "select quota_name from %s where id = '%s'"
        return self.setup.psql(sql, T_QUOTA, quota_id)[0][0]

    def check_quota_exists(self, quota_name):
        """
        Check if quota exists
        Parameters:
         * quota_name - name of quota to check
        return True if quota exists else False
        """
        sql = "SELECT id FROM %s WHERE quota_name = '%s'"
        return len(self.setup.psql(sql, T_QUOTA, quota_name)) == 1

    def check_quota_limits(self, quota_name, **kwargs):
        """
        Check quota limits
        Parameters:
         * quota_name - name of quota to check
         * description - description of quota
         * mem_size_mb - memory limit of quota
         * virtual_cpu - vcpu limit of quota
         * storage_size_gb - storage limit of quota
        return True if quota limits are equal else False
        """
        sql = "SELECT %s FROM %s WHERE quota_id = '%s'"
        return self._check_values(quota_name, T_QUOTA_LIMITATION,
                                  sql, **kwargs)

    def check_global_consumption(self, quota_name, **kwargs):
        """
        Parameters:
         * quota_name - name of quota to check
         * mem_size_mb_usage - value that mem should have
         * virtual_cpu_usage - value that vcput should have
         * storage_size_gb_usage - value that should be consumed by quota
        """
        sql = "SELECT %s FROM %s WHERE quota_id = '%s'"
        return self._check_values(quota_name, V_QUOTA_GLOBAL, sql, **kwargs)

    def check_cluster_consumption(self, quota_name, cluster, **kwargs):
        """
        Check if resources are allocated right.
        Parameters:
         * cluster - name of cluster to check, if None check all clusters
         * quota_name - name of quota to check
         * mem_size_mb_usage - value that mem should have
         * virtual_cpu_usage - value that vcput should have
        """
        sql = "SELECT %s FROM %s WHERE quota_id = '%s'" \
              " AND vds_group_name = '" + cluster + "'"
        return self._check_values(quota_name, V_QUOTA_VDS, sql, **kwargs)

    def check_storage_consumption(self, quota_name, storage, **kwargs):
        """
        Check if resources are allocated right.
        Parameters:
         * storage - name of storage to check, if None check all storages
         * quota_name - name of quota to check
         * storage_size_gb_usage - value that should be consumed by quota
        """
        sql = "SELECT %s FROM %s WHERE quota_id = '%s' AND storage_name = '"\
              + storage + "'"
        return self._check_values(quota_name, V_QUOTA_STORAGE, sql, **kwargs)

    def _check_values(self, quota_name, table, sql, **kwargs):
        quota_id = self.get_quota_id_by_name(quota_name)
        for k, v in kwargs.iteritems():
            d = int(self.setup.psql(sql, k, table, quota_id)[0][0])
            if not int(v) == d:
                LOGGER.warn("%s does not equal to %s, but to %s", k, v, d)
                return False
        return True

    def assign_quota_to_disk(self, quota_name, disk_name):
        """
        Assign quota to disk.
        Parameters:
         * quota_name - name of quota to assign
         * disk_name - disk to be quota assigned
        """
        sql = "UPDATE images SET quota_id = '%s' WHERE image_guid = '%s'"
        q_id = self.get_quota_id_by_name(quota_name)
        disk = disks.DISKS_API.find(disk_name)
        if disk is None:
            LOGGER.info("Disk '%s' was not found.", disk_name)
        self.setup.psql(sql, q_id, disk.get_image_id())

    def create_storage_limits(self, sd_name, quota_name, storage_limit):
        """
        Create quota storage limit for specific storage.
        Parameters:
         * sd_name - name of sd
         * quota_name - name of quota
         * storage_limit - storage limit of quota
        """
        quota_id = self.get_quota_id_by_name(quota_name)
        storage_pool_id = self._get_storage_pool_id(quota_id)
        storage_id = self._get_storage_id(sd_name)
        values = ', '.join(str(val) for val in (storage_pool_id, quota_id,
                                                storage_id, sd_name,
                                                storage_limit, 0))
        sql = "INSERT INTO %s VALUES (%s)"
        self.setup.psql(sql, V_QUOTA_STORAGE, values)

    def _get_storage_pool_id(self, quota_id):
        sql = "SELECT %s FROM %s WHERE quota_id = '%s'"
        return self.setup.psql(sql, 'storage_pool_id',
                               T_QUOTA, quota_id)[0][0]

    def _get_storage_id(self, storage_name):
        sql = "SELECT %s FROM %s WHERE %s = '%s'"
        return self.setup.psql(sql, 'id', 'storage_domains',
                               'storage_name', storage_name)[0][0]

    def create_vds_limits(self, cluster_name, quota_name,
                          mem_limit, vcpu_limit):
        """
        Create quota mem/vcpu limit for specific cluster.
        Parameters:
         * cluster_name - name of cluster
         * quota_name - name of quota
         * mem_limit - memory limit of quota
         * vcpu_limit - vcpu limit of quota
        """
        new_uuid = uuid.uuid4()
        quota_id = self.get_quota_id_by_name(quota_name)
        cluster_id = self._get_vds_group_id(cluster_name)
        values = ', '.join(str(val) for val in (new_uuid, quota_id,
                                                cluster_id, cluster_name,
                                                vcpu_limit, mem_limit, 0))
        sql = "INSERT INTO %s VALUES (%s)"
        self.setup.psql(sql, V_QUOTA_VDS, values)

    def _get_vds_group_id(self, cluster_name):
        sql = "SELECT %s FROM %s WHERE %s = '%s'"
        return self.setup.psql(sql, 'vds_group_id', 'vds',
                               'vds_group_name', cluster_name)
