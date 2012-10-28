#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2012 Red Hat, Inc.
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

import art.test_handler.settings as settings
from utilities.postgresConnection import Postgresql
from utilities import errors
from datetime import datetime, timedelta, date
from dateutil import tz
import re
from logging import getLogger
from art.core_api import is_action
from configobj import ConfigObj

logger = getLogger('db_utils')

HISTORY_DB_NAME = 'ovirt_engine_history'

DAILY = 'daily'
HOURLY = 'hourly'
SAMPLES = 'samples'

HOUR_INTERVAL = 'h'
DAY_INTERVAL = 'd'
MONTH_INTERVAL = 'm'

MAX_SAMPLES = 48 * 60 # 48 hours once a minute
MAX_HOURS = 60 * 24   # 2 months once an hour
MAX_DAYS = 2 * 365    # 2 years once a day

class EntityIsNotFoundInDBError(errors.GeneralException):
    message = 'Entity of this type is not found in the configuration table.'

class WrongTimeIntervalFormatError(errors.GeneralException):
    message = 'Wrong time interval format.'

class WrongTimeIntervalTypeError(errors.GeneralException):
    message = 'Wrong time interval type.'
    message += 'Can be one of the following: {0}, {1}, {2}'.format(
            HOUR_INTERVAL, DAY_INTERVAL, MONTH_INTERVAL)

class WrongTimeFormatError(errors.GeneralException):
    message = 'wrong start date format: Year-Month-Day [Hour:[Minutes]] [] - optional'

class HistoryDB(object):

    TABLES = {
        'config'     : 'history_configuration',
        'host': {
            'config' : 'host_configuration',
            DAILY    : 'host_daily_history',
            HOURLY   : 'host_hourly_history',
            SAMPLES  : 'host_samples_history',
        },
        'host_interface': {
            'config' : 'host_interface_configuration',
            DAILY    : 'host_interface_daily_history',
            HOURLY   : 'host_interface_hourly_history',
            SAMPLES  : 'host_interface_samples_history',
        },
        'vm': {
            'config' : 'vm_configuration',
            DAILY    : 'vm_daily_history',
            HOURLY   : 'vm_hourly_history',
            SAMPLES  : 'vm_samples_history',
        },
        'vm_interface': {
            'config' : 'vm_interface_configuration',
            DAILY    : 'vm_interface_daily_history',
            HOURLY   : 'vm_interface_hourly_history',
            SAMPLES  : 'vm_interface_samples_history',
        },
    }
    DATETIME_COL = 'history_datetime'

    def __init__(self):
        conf = ConfigObj(settings.opts.get('conf'))
        host = conf.get('REST_CONNECTION').get('host')
        params = conf.get('PARAMETERS')
        user = params.get('history_db_user', 'postgres')
        passw = params.get('history_db_passw', None)
        dbname = params.get('history_db_name', HISTORY_DB_NAME)
        self._dbConn = Postgresql(host=host, user=user, passwd=passw,
                             dbname=dbname)

    def __enter__(self):
        self._dbConn.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._dbConn.close()

    def __insert(self, table, columns, values):
        '''
        Run SQL insert statement.
        '''
        adjVals = []
        for val in values:
            if isinstance(val, str):
                adjVals.append('\'%s\'' % val)
            else:
                adjVals.append(str(val))
        sql = 'INSERT INTO {0} ({1}) VALUES ({2});'.format(table,
                ','.join(columns), ','.join(adjVals))
        return self._dbConn.execute(sql)

    def __update(self, table, propPattern, propValue, columns, values):
        '''
        Run SQL update statement.
        '''
        if isinstance(columns, list):
            updateList = ['{0}=\'{1}\''.format(columns[i], values[i]) for i in range (0,
                len(columns))]
            updateStr = ','.join(updateList)
        else:
            updateStr = '{0}=\'{1}\''.format(columns, values)
        sql = 'UPDATE {0} SET {1} WHERE {2} = \'{3}\''.format(table, updateStr,
                                            propPattern, propValue)
        return self._dbConn.execute(sql)

    def __getEntityId(self, entity, name):
        '''
        Get entity Id by name.
        '''

        if re.match('^host', entity):
            baseEntity = 'host'
        elif re.match('^vm', entity):
            baseEntity = 'vm'
        table = self.TABLES[baseEntity]['config']
        sql = 'SELECT DISTINCT {0}_id FROM {1} WHERE {2}_name = \'{3}\' AND delete_date IS NULL'.format(
            baseEntity, table, baseEntity, name)
        out = self._dbConn.query(sql)
        if not out:
            raise EntityIsNotFoundInDBError(baseEntity, name, table)
        entId = out[-1][0]
        if entity == 'host' or entity == 'vm':
            return entId
        table = self.TABLES[entity]['config']
        sql = 'SELECT DISTINCT {0}_id FROM {1} WHERE {2}_id = \'{3}\' AND delete_date IS NULL'.format(
            entity, table, baseEntity, entId)
        out = self._dbConn.query(sql)
        if not out:
            raise EntityIsNotFoundInDBError(entity, entId, table)
        return out[-1][0]

    def __calculateRecordsCount(self, interval, type):
        interval_patt = re.compile('(\d+)(\w)', re.I)
        m = interval_patt.search(interval)
        if not m:
            raise WrongTimeIntervalFormatError(interval)
        interval_val = int(m.group(1))
        interval_type = m.group(2).lower()
        if interval_type not in (HOUR_INTERVAL, DAY_INTERVAL, MONTH_INTERVAL):
            raise WrongTimeIntervalTypeError(interval_type)
        if type == SAMPLES:
            if interval_type == HOUR_INTERVAL:
                interval_val *= 60
            elif interval_type == DAY_INTERVAL:
                interval_val *= 60 * 24
            elif interval_type == MONTH_INTERVAL:
               interval_val = MAX_SAMPLES
            if interval_val > MAX_SAMPLES:
                interval_val = MAX_SAMPLES
        elif type == HOURLY:
            if interval_type == DAY_INTERVAL:
                interval_val *= 24
            elif interval_type == MONTH_INTERVAL:
                interval_val *= 30 * 24
            if interval_val > MAX_HOURS:
                interval_val = MAX_HOURS
        elif type == DAILY:
            if interval_type == HOUR_INTERVAL:
                interval_val /= 24
            elif interval_type == MONTH_INTERVAL:
                interval_val *= 30
            if interval_val > MAX_DAYS:
                interval_val = MAX_DAYS
        return interval_val

    def __getStartTime(self, type, start_time=None):
        if not start_time:
            if type == DAILY:
                return date.today()
            return datetime.now(tz.tzlocal()) #hourly
        res = re.match('(\d{4})-(\d{2})-(\d{2})( \d{2}:\d{2})?$', start_time) #validate start_time structure
        if not res:
            raise WrongTimeFormatError(start_time)
        start_time = "%s-%s-%s %s" % res.groups('00:00')
        return datetime.strptime(start_time, "%Y-%m-%d %H:%M")

    def __getTimestamp(self, type, startTime, cnt):
        if type == SAMPLES:
            start = startTime - timedelta(minutes=cnt)
        elif type == HOURLY:
            start = startTime - timedelta(hours=cnt)
        elif type == DAILY:
            start = startTime - timedelta(days=cnt)
        return start.isoformat().replace('T', ' ')

    def __updateHistoryConfiguration(self, start, end):
        sql = 'SELECT var_datetime from %s where var_name=\'firstSync\';' % \
                self.TABLES['config']
        out = self._dbConn.query(sql)
        if start < out[0][0].isoformat():
            self.__update(self.TABLES['config'], 'var_name', 'firstSync',
                            'var_datetime', start)
        self.__update(self.TABLES['config'], 'var_name', 'lastDayAggr',
                        'var_datetime', end)
        self.__update(self.TABLES['config'], 'var_name', 'lastHourAggr',
                        'var_datetime', end)

    def fillTable(self, entity, name, type, properties, values, interval, start_time):
        '''
        Insert data to DB table
        '''

        try:
            table = self.TABLES[entity][type]
        except KeyError:
            logger.error(
                'Table with %s data for %s is not supported.' %
                (entity, type))
            return False
        try:
            entityId = self.__getEntityId(entity, name)
            recordCnt = self.__calculateRecordsCount(interval, type)
            startTime = self.__getStartTime(type, start_time)
            entityStatus = 1
            props = [self.DATETIME_COL, '%s_id' % entity]
            if entity == 'host' or entity == 'vm':
                props.append('%s_status' % entity)
            for prop in properties.split(','):
                props.append(prop)
            for ind in range (0, recordCnt):
                tstamp = self.__getTimestamp(type, startTime, ind)
                vals = [tstamp, entityId]
                if entity == 'host' or entity == 'vm':
                    vals.append(entityStatus)
                for val in values.split(','):
                    vals.append(int(val))
                self.__insert(table, props, vals)
            self.__updateHistoryConfiguration(tstamp, startTime.isoformat())
            logger.info('%d records inserted to %s table' % (recordCnt, table))
        except Exception:
            logger.exception('Failed to insert data to the table %s' % table)
            return False
        return True


@is_action()
def forgeHistoryData(entity, name, type, properties, values, interval, start_time=None):
    '''
    Insert fake data to DB table
    Parameters:
        - entity - type of entity(host, vm, host_interface, vm_interface)
        - name - entity name
        - type - history type (hourly, daily, samples)
        - properties - property names (comma separated)
        - values - property values (comma separated)
        - interval - time interval (Nh - N hours, Nd - N days, Nm - N month)
        - start_time - optional parameter to determine when to start filling the DB backward.
             syntx: 'YYYY-MM-DD[ HH:[mm]]', where time is optional and hours in 24 hours format
    Return:
        True/False
    '''

    with HistoryDB() as dbh:
        rc = dbh.fillTable(entity, name, type, properties, values, interval, start_time)
        return rc

