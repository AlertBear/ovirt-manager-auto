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

from utils.data_structures import Template, Cluster, CPU, CpuTopology,\
                                    StorageDomain, VM, NIC
from utils.test_utils import get_api
import time
import re
from utils.validator import compareCollectionSize

CREATE_TEMPLATE_TIMEOUT = 900
ELEMENT = 'template'
COLLECTION = 'templates'
util = get_api(ELEMENT, COLLECTION)
sdUtil = get_api('storage_domain', 'storagedomains')
clUtil = get_api('cluster', 'clusters')
vmUtil = get_api('vm', 'vms')
nicUtil = get_api('nic', 'nics')

def _prepareTemplateObject(**kwargs):

    templ = Template()

    name = kwargs.pop('name', None)
    if name:
        templ.set_name(name)

    description = kwargs.pop('description', None)
    if description:
        templ.set_description(description)

    memory = kwargs.pop('name', None)
    if memory:
        templ.set_memory(memory)

    type = kwargs.pop('type', None)
    if type:
        templ.set_type(type)

    cluster = kwargs.pop('cluster', None)
    if type:
        cl = clUtil.find(cluster)
        templ.set_cluster(Cluster(id=cl.get_id()))

    cpu_socket = kwargs.pop('cpu_socket', None)
    cpu_cores = kwargs.pop('cpu_cores', None)

    if cpu_socket or cpu_cores:
        templ.set_cpu(CPU(topology=CpuTopology(sockets=cpu_socket, cores=cpu_cores)))

    vm = kwargs.pop('vm', None)
    if vm:
        vmObj = vmUtil.find(vm)
        templ.set_vm(VM(id=vmObj.get_id()))

    boot = kwargs.pop('boot', None)
    if boot:
        templ.set_os(Boot(dev=boot))

    storagedomain = kwargs.pop('storagedomain', None)
    if storagedomain:
        sd = sdUtil.find(storagedomain)
        templ.set_storagedomain(StorageDomain(id=sd.get_id()))

    return templ
    

def createTemplate(positive, wait=True, timeout=CREATE_TEMPLATE_TIMEOUT, **kwargs):
    '''
    Description: add new template
    Author: edolinin
    Parameters:
       * vm - name of vm for template generation
       * name - template name
       * description - template description
       * cluster - template cluster
       * memory - template memory size
       * cpu_socket - number of cpu sockets
       * cpu_cores - number of cpu cores
       * boot - template boot device
       * type - template type
       * wait - wait untill end of creation of template (true) or exit without waiting (false)
       * storagedomain - name of storagedomain
    Return: status (True if template was added properly, False otherwise)
    '''

    templ = _prepareTemplateObject(**kwargs)
    templ, status = util.create(templ, positive)
    if wait and status and positive:
        status = util.waitForElemStatus(templ, 'OK', timeout)

    return status


def updateTemplate(positive, template, **kwargs):
    '''
    Description: update existed template
    Author: edolinin
    Parameters:
       * template - name of template that should be updated
       * name - new template name
       * description - new template description
       * cluster - new template cluster
       * memory - new template memory size
       * cpu_socket - new number of cpu sockets
       * cpu_cores - new number of cpu cores
       * boot - new template boot device
       * type - new template type
    Return: status (True if template was updated properly, False otherwise)
    '''

    templObj = util.find(template)
    templNew = _prepareTemplateObject(**kwargs)
    templObj, status = util.update(templObj, templNew, positive)

    time.sleep(40)

    return status


def removeTemplate(positive, template, wait=True, sleepTime=10, timeout=60):
    '''
    Description: remove existed template
    Author: edolinin
    Parameters:
       * template - name of template that should be removed
       * wait - When true :wait until end of action ,When False return without wait
       * sleepTime - How much time wait between validation
       * timeout - maximun waiting time
    Return: status (True if template was removed properly, False otherwise)
    '''
    templObj = util.find(template)
    status = util.delete(templObj, positive)
    
    if status and positive and wait:
        handleTimeout = 0
        while handleTimeout <= timeout:
            if not validateTemplate(positive, template):
                # Add a delay, required as a workaround, for actual template removal
                time.sleep(30)
                return True
            time.sleep(sleepTime)
            handleTimeout += sleepTime
        return False
    elif status and positive and not wait:
        return True
    elif status and not positive:
        return True

    return False


def removeTemplates(positive, templates):
    # TODO: Doc
    jobs = [Job(target=removeTemplate, args=(True, tmpl)) for tmpl in split(templates)]
    js = JobsSet()
    js.addJobs(jobs)
    js.start()
    js.join()

    status = True
    for job in jobs:
        status &= job.result
        if not job.result:
            util.logger.error('Removing template %s failed', job.args[1])
    return status


def searchForTemplate(positive, query_key, query_val, key_name):
    '''
    Description: search for a data center by desired property
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in data center object equivalent to query_key
    Return: status (True if expected number of data centers equal to
                    found by search, False otherwise)
    '''

    expected_count = 0
    templates = util.get(absLink=False)

    for templ in templates:
        tProperty = getattr(templ, key_name)
        if re.match(r'(.*)\*$',query_val):
            if re.match(r'^' + query_val, tProperty):
                expected_count = expected_count + 1
        else:
            if tProperty == query_val:
                expected_count = expected_count + 1

    contsraint = "{0}={1}".format(query_key, query_val)
    query_templs = util.query(contsraint)
    status = compareCollectionSize(query_templs, expected_count, util.logger)

    return status


def addTemplateNic(positive, template, name, network='rhevm',interface=None):
    '''
    Description: add nic to template
    Author: atal
    Parameters:
       * template - name of template that we add the nic to
       * name - name of nic
       * network - network that nic depends on
       * interface - nic type. available types: virtio, rtl8139 and e1000 (for 2.2 also rtl8139_virtio)
    Return: status (True if nic was added properly, False otherwise)
    '''
    templObj = util.find(template)
    clusterObj = clUtil.find(templObj.get_cluster().get_id(), 'id')

    nic = NIC(name=name, interface=interface)
    clusterNet = util.getElemFromElemColl(clusterObj, network, 'networks', 'network')
    nic.set_network(clusterNet)

    templateNics = util.getElemFromLink(templObj, link_name='nics', attr='nic', get_href=True)
    nic, status = nicUtil.create(nic, positive, collection=templateNics)

    return  status


def updateTemplateNic(positive, template, nic, name=None, network=None, interface=None):
    '''
    Description: update an existing nic
    Author: atal
    Parameters:
       * template - name of template that we update the nic
       * nic - nic name that should be updated
       * name - new nic name
       * network - network that nic depends on
       * interface - nic type. available types: virtio, rtl8139 and e1000 (for 2.2 also rtl8139_virtio)
    Return: status (True if nic was updated properly, False otherwise)
    '''
    templObj = util.find(template)
    clusterObj = clUtil.find(templObj.get_cluster().get_id(), 'id')
    nicObj = util.getElemFromElemColl(templObj, nic, 'nics', 'nic')

    nicNew = NIC()
    if name:
        nicNew.set_name(name)
    if interface:
        nicNew.set_interface(interface)
    if network:
        clusterNet = util.getElemFromElemColl(clusterObj, network, 'networks', 'network')
        nicNew.set_network(clusterNet)

    nic, status = util.update(nicObj, nicNew, positive)

    return status


def removeTemplateNic(positive, template, nic):
    '''
    Description: remove nic from template
    Author: atal
    Parameters:
       * template - template where nic should be removed
       * nic - nic name that should be removed
    Return: status (True if nic was removed properly, False otherwise)
    '''
    templObj = util.find(template)
    nicObj = util.getElemFromElemColl(templObj, nic, 'nics', 'nic')
    return util.delete(nicObj,positive)


def removeTemplateFromExportDomain(positive, template, datacenter, export_storagedomain):
    '''
    Description: removes a template from export domain
    Author: istein
    Parameters:
       * template - template name
       * datacenter - name of data center
       * export_storagedomain - storage domain where to remove vm from
    Return: status (True if template was removed properly, False otherwise)
    '''
    expStorDomObj = sdUtil.find(export_storagedomain)
    templObj = util.getElemFromElemColl(expStorDomObj, template)
    status = util.delete(templObj, positive)
    time.sleep(30)
    return status


def validateTemplate(positive, template):
    '''
    Description: Validate template if exist
    Author: egerman
    Parameters:
       * template - template name
    Return: status (True if template exist, False otherwise)
    '''
    templates = util.get(absLink=False)
    templates = filter(lambda x: x.name.lower() == template.lower(), templates)
    return bool(templates) == positive


def getTemplateId(positive, template):
    '''
    Description: Get template id
    Author: egerman
    Parameters:
       * template - template name
    Return: True and template id or False and None
    '''
    try:
        templObj = util.find(template)
    except EntityNotFound:
        return False, {'templateId' : None}
    return True, {'templateId' : templObj.get_id()}


def exportTemplate(positive, template, storagedomain, exclusive='false'):
    '''
    Description: export template
    Author: edolinin
    Parameters:
       * template - name of template that should be exported
       * storagedomain - name of export storage domain where to export to
       * exclusive - 'true' if overwrite already existed templates with the same
                       name, 'false' otherwise ('false' by default)
    Return: status (True if template was exported properly, False otherwise)
    '''

    templObj = util.find(template)
 
    sd = StorageDomain(name=storagedomain)
    actionParams = dict(storage_domain=sd, exclusive=exclusive)
    
    return util.syncAction(templObj, "export", positive, **actionParams)



def importTemplate(positive, template, export_storagedomain,
                            import_storagedomain, cluster):
    '''
    Description: import template
    Author: edolinin
    Parameters:
       * template - name of template that should be imported
       * datacenter - data center to use
       * export_storagedomain - storage domain where to export the template from
       * import_storagedomain - storage domain where to import the template to
    Return: status (True if template was imported properly, False otherwise)
    '''

    expStorDomObj = sdUtil.find(export_storagedomain)
    templObj = util.getElemFromElemColl(expStorDomObj, template)

    sd = StorageDomain(name=import_storagedomain)
    cl = Cluster(name=cluster)

    actionParams = dict(storage_domain=sd, cluster=cl)

    status = util.syncAction(templObj, "import", positive, **actionParams)
    time.sleep(30)

    return status