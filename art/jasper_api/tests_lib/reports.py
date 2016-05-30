#!/usr/bin/env python

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


from art.core_api.rest_utils import RestUtil
from art.test_handler.settings import opts
from StringIO import StringIO
from lxml import etree
from tempfile import NamedTemporaryFile
from configobj import ConfigObj
from copy import deepcopy
import logging

logger=logging.getLogger('rhevm_reports')

reportsObj = None


class ExecutiveReports():
    type = 'Executive'
    activeVmsByOs = 'active_vms_by_os_br18'
    clusterCapacity = 'cluster_capacity_vs_usage_br19'
    hostsBreakDown = 'host_os_break_down_BR22'
    hostsSummary = 'summary_of_host_usage_resources_br17'

class InventoryReports():
    type = 'Inventory'
    hosts = 'Hosts_Inventory'
    storagDomains = 'Storage_Domain_Report_BR21'
    VMs = 'VM_Inventory'

class ServiceLevelReports():
    type = 'Service_level'

class ServiceLevelHostReports(ServiceLevelReports):
    subType = 'Hosts'
    clusterQualityHosts = 'cluster_quality_of_service_hosts_br6'
    clusterUptime = 'cluster_uptime_br7'
    singleHostUptime = 'single_host_uptime_br8'
    top10Hosts = 'top_10_downtime_hosts_br7b'

class ServiceLevelVMReports(ServiceLevelReports):
    subType = 'VMs'
    clusterQualityVMs = 'cluster_quality_of_service_vms_br13'
    VMsUptime = 'virtual_servers_uptime_br14'

class TrendReports():
    type = 'Trend'

class TrendHostReports(TrendReports):
    subType = 'Hosts'
    least5utilized = 'five_least_utilized_hosts_br5'
    most5utilized = 'Five_most_utilized_hosts_over_time'
    multipleResource = 'multiple_hosts_resource_usage_br3'
    singleResource = 'single_host_resource_br2a'
    singleResourceDow = 'single_host_resource_usage_dow_br2b'
    singleResourceHod = 'single_host_resource_usage_hour_of_day_br2c'

class TrendVMReports(TrendReports):
    subType = 'Virtual_machines'
    least5utilized = 'five_least_utilized_vms_Over_Time_BR12'
    most5utilized = 'five_most_utilized_vms_over_time_br11'
    multipleResource = 'multiple_vms_resource_usage_over_time_br16'
    singleResourceDow = 'single_vm_resources_days_week_BR10B'
    singleResourceHod = 'single_vm_resources_hour_of_day_BR10c'
    singleResource = 'single_vm_resources_over_time_BR10A'


class JasperReports(object):
    '''
    Implements methods for Jasper Report services using REST API.
    '''
    def __init__(self):
        '''
        Constructor
        Reads Jasper Server connection parameters from configuration file
        and creates standalone instance of RestUtil to perform http requests.
        '''
        conf = ConfigObj(opts['conf'])
        try:
            user = conf['JASPER_REST_CONNECTION']['user']
            password = conf['JASPER_REST_CONNECTION']['password']
            entry_point = conf['JASPER_REST_CONNECTION']['entry_point']
            self.__base_uri = '{0}://{1}:{2}/{3}/'.format(opts['scheme'],
                            opts['host'], opts['port'], entry_point)
        except Exception as ex:
            logger.error('Jasperserver is not configured: %s' % ex)
            raise
        localOpts = deepcopy(opts)
        localOpts['user'] = user
        localOpts['password'] = password
        localOpts['uri'] = self.__base_uri
        localOpts['standalone'] = True
        localOpts['user_domain'] = None
        self._reportUtil = RestUtil('Reports', 'report', opts=localOpts)

    def __createURL(self, path):
        return '%s%s' % (self.__base_uri, path)

    def _getResourceDescriptor(self, path, report):
        '''
        Get report resource descriptor required when running a report.
        Parameters:
            - path - report relative path
            - report - report name
        Return:
            Resource descriptor as XML string.
        '''
        uri = self.__createURL('resources/Reports/{0}'.format(path))
        resp = self._reportUtil.get(uri, noParse=True)
        rd = self._parse(resp, 'name', report)
        return rd

    def _parse(self, response, key, value):
        '''
        Parse response and search for element by key.
        Parameters:
            - response - http response
            - key - search attribute
            - value - element name
        Return:
            Element as XML string.
        '''
        xml = StringIO(response)
        tree = etree.parse(xml)
        for item in list(tree.getroot()):
            if item.get(key) == value:
                return etree.tostring(item)

    def _getReportId(self, response):
        '''
        Get report UUID provided by response of report execution.
        Parameters:
            - response - report response
        Return:
            Report UUID/None if not found
        '''
        xml = StringIO(response['body'])
        tree = etree.parse(xml)
        root = tree.getroot()
        item = root.find('uuid')
        if item is not None:
            return item.text
        return None

    def runReport(self, path, report):
        '''
        Runs report by name and store the report results.
        Parameters:
            - path - report relative path
            - report - report name
        Return:

        '''
        rd = self._getResourceDescriptor(path, report)
        uri = self.__createURL('report/{0}/{1}'.format(path, report))
        resp = self._reportUtil.api.PUT(uri, rd)
        uuid = self._getReportId(resp)
        return self.getReportResult(uuid, report)

    def getReportResult(self, uuid, report):
        '''
        Download report output from Jasper Server and save it in pdf format
        on the local host.
        Parameters:
            - uuid - report UUID
            - report - report name
        Return:
            File pathname/None if failed
        '''
        uri = self.__createURL('{0}/{1}?file=report'.format('report/', uuid))
        resp = self._reportUtil.get(uri, noParse=True, validate=False)
        # TODO: response validation
        fname = None
        try:
            with NamedTemporaryFile(delete=False, prefix=report,
                suffix='.pdf') as tmp:
                    tmp.write(resp)
                    fname = tmp.name
        except Exception as ex:
            logger.error('Failed to store report output: %s' % report)
        return fname

    def regenerateReport(self, report):
        pass


def getReports():
    global reportsObj
    if not reportsObj:
        reportsObj = JasperReports()
    return reportsObj


def _runReport(path, report):
    robj = getReports()
    res = robj.runReport(path, report)
    logger.info('%s report saved in the file %s' % (report, res))
    return True if res else False


def reportActiveVmsByOs():
    '''
    The report contains comparative measurements number of running
    virtual machines and OS usage in for a selected cluster
    and a selected virtual machine's type within the requested period.
    '''
    rep = ExecutiveReports()
    return _runReport(rep.type, rep.activeVmsByOs)


def reportClusterCapacityVsUsage():
    '''
    This report contains charts displaying hosts resources usage measurements
    (CPU core, physical Memory) and charts displaying virtual machines
    resources usage measurements (virtual machines total vCPU,
    Virtual Memory size) for a selected cluster.
    '''
    rep = ExecutiveReports()
    return _runReport(rep.type, rep.clusterCapacity)


def reportHostOsBreakDown():
    '''
    This report contains a table and a chart displaying the number of hosts
    for each OS version for a selected cluster within a requested period.
    '''
    rep = ExecutiveReports()
    return _runReport(rep.type, rep.hostsBreakDown)


def reportSummaryHostUsageResources():
    '''
    The report contains a scattered chart of CPU and memory usage data
    within a requested period and for a selected cluster.
    '''
    rep = ExecutiveReports()
    return _runReport(rep.type, rep.hostsSummary)


def reportHostsInventory():
    '''
    This report displays a list of all hosts of the selected data center
    and cluster.
    '''
    rep = InventoryReports()
    return _runReport(rep.type, rep.hosts)


def reportStorageDomain():
    '''
    This report displays daily used disk size versus available disk size data
    for the selected datacenter and storage domain within a requested period.
    '''
    rep = InventoryReports()
    return _runReport(rep.type, rep.storagDomains)


def reportVMInventory():
    '''
    This report displays a list of all virtual machines of the selected
    data center and cluster.
    '''
    rep = InventoryReports()
    return _runReport(rep.type, rep.VMs)


def reportClusterQualityOfServiceHosts():
    '''
    This report contains a chart displaying the time hosts have performed
    above a selected threshold (Host-hours) and a table of total time
    each host was performing above the CPU or the Memory threshold.
    '''
    rep = ServiceLevelHostReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.clusterQualityHosts,
    )


def reportClusterUptime():
    '''
    This report contains chart displaying the weighted average uptime of hosts
    within a selected cluster for a requested period and a table of history data
    displaying the down time and the maintenance time each time of each host.
    '''
    rep = ServiceLevelHostReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.clusterUptime,
    )


def reportSingleHostUptime():
    '''
    This report contains one gauge displaying the weighted average uptime
    of a single selected host for a requested period.
    '''
    rep = ServiceLevelHostReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.singleHostUptime,
    )


def reportTop10DowntimeHosts():
    '''
    This report contains a chart displaying the uptime, maintenance time
    and the down time for the bottom 10 hosts sorted by weighted uptime.
    '''
    rep = ServiceLevelHostReports()
    return _runReport('{0}/{1}'.format(rep.type, rep.subType), rep.top10Hosts)


def reportClusterQualityOfServiceVms():
    '''
    This report contains a chart displaying the time virtual machines
    have performed above a selected threshold and a table of total time
    each virtual machine was performing above the CPU or the memory threshold.
    '''
    rep = ServiceLevelVMReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.clusterQualityVMs,
    )


def reportVirtualServersUptime():
    '''
    This report contains one gauge displaying the weighted average uptime
    of high availability virtual servers within a selected cluster
    for a requested period and a table of history data displaying
    the total down time (in hours) of each virtual machine.
    '''
    rep = ServiceLevelVMReports()
    return _runReport('{0}/{1}'.format(rep.type, rep.subType), rep.VMsUptime)


def report5leastUtilizedHosts():
    '''
    This report contains two charts displaying weighted average daily peak
    of CPU and memory usage for the bottom five busiest hosts
    of a selected cluster and within a given period.
    '''
    rep = TrendHostReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.least5utilized,
    )


def report5mostUtilizedHosts():
    '''
    This report contains two charts displaying weighted average daily peak
    of CPU and memory usage for the top five busiest hosts
    of a selected cluster and within a given period.
    '''
    rep = TrendHostReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.most5utilized,
    )


def reportMultipleHostsResourceUsage():
    '''
    This report contains charts displaying daily peak of CPU and memory usage
    for up to 5 selected hosts within a requested period.
    '''
    rep = TrendHostReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.multipleResource,
    )


def reportSingleHostResources():
    '''
    This report contains charts displaying resources usage measurements
    (Number of Virtual Machines, CPU, Memory, Network Tx/Rx)
    for a selected host over the selected period.
    '''
    rep = TrendHostReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.singleResource,
    )


def reportSingleHostResourceUsageDayOfWeek():
    '''
    This report contains charts displaying resources usage measurements
    (Number of Virtual Machines, CPU, Memory, Network Tx/Rx)
    for a selected host by the days of the week.
    '''
    rep = TrendHostReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.singleResourceDow,
    )


def reportSingleHostResourceUsageHourOfDay():
    '''
    This report contains charts displaying resources usage measurements
    (Number of Virtual Machines, CPU, Memory, Network Tx/Rx)
    for a selected host by hours of day.
    '''
    rep = TrendHostReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.singleResourceHod,
    )


def report5leastUtilizedVMs():
    '''
    This report contains charts displaying weighted average daily peak
    of CPU and memory usage for the bottom five busiest virtual machines
    of a selected cluster and within a given period month.
    '''
    rep = TrendVMReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.least5utilized,
    )


def report5mostUtilizedVMs():
    '''
    This report contains charts displaying weighted average daily peak
    of CPU and memory usage for the bottom five busiest virtual machines
    of a selected cluster and within a given period month.
    '''
    rep = TrendVMReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.most5utilized,
    )


def reportMultipleVMsResourceUsage():
    '''
    This report contains charts displaying weighted average daily peak
    of CPU and memory usage for the bottom five busiest virtual machines
    of a selected cluster and within a given period month.
    '''
    rep = TrendVMReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.multipleResource,
    )


def reportSingleVMResourceUsageDayOfWeek():
    '''
    This report contains charts displaying resources usage measurements
    (CPU, Memory, Network Tx/Rx, Disk IO rates) for a selected virtual machine
    by days of week.
    '''
    rep = TrendVMReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.singleResourceDow,
    )


def reportSingleVMResourceUsageHourOfDay():
    '''
    This report contains charts displaying resources usage measurements
    (CPU, Memory, Network Tx/Rx, Disk IO rates) for a selected virtual machine
    by hours of day.
    '''
    rep = TrendVMReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.singleResourceHod,
    )


def reportSingleVMResources():
    '''
    This report contains charts displaying resources usage measurements
    (CPU, Memory, Network Tx/Rx, Disk IO rates) for a selected virtual machine
    over the selected time.
    '''
    rep = TrendVMReports()
    return _runReport(
        '{0}/{1}'.format(rep.type, rep.subType), rep.singleResource,
    )
