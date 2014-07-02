from art.rhevm_api.utils import load_agent
from art.rhevm_api.utils.test_utils import lookingForIpAdressByEntityName, split
from art.rhevm_api.tests_lib.low_level.vms import waitForIP
from utilities.jobs import Job, JobsSet
from utilities.utils import isValidIp
from utilities.machine import Machine
import time
import logging
from art.core_api import is_action

logger = logging.getLogger('guest')

@is_action()
def runLoadOnGuests(positive, targetVMs, osType, username, password, loadType,
                   duration, port, load=None, allocationSize=None,
                   protocol=None, clientVMs=None, extra=None, groupAgent=None):
    """
    Run system load of given type on VMs for specific amount of time.
    Parameters:
      * targetVMs - string contains VM names or IP addresses comma-separated
      * osType - VM's OS type: 'linux' or 'windows'
      * username - SSH or WMI username
      * password - SSH or WMI password
      * loadType - type of system load: 'CPU', 'MEM', 'IO', 'NET'
      * duration - load duration in seconds; if is set to zero,
          system load is not explicitly stopped at the end of the function
      * port - load deamon listen port
      * load - percentage of CPU load: 0-100; CPU only
      * allocationSize - initial memory allocation in MB or percenttage amount
          of physical memory 'xx%' NOTE: there is problem with '%', so please
          use 'P' instaed ('xxP'); MEM only
      * protocol  - network protocol: 'tcp' or 'udp'; NET only
      * clientVMs - VMs which will act as a network clients; NET only
          use coma-seperated VM names or IPs
      * extra - command-line arguments passed to 'iperf' (NET)
          or iozone (IO) utility; use coma-separated values like '-a, -b, -c'
      * groupAgent - LoadAgentGroup object, you can use it to append another
                     generators to same object
    Return: tuple True - success / False - failure,
                  and a dict with an agent instance
    """
    if groupAgent is None:
        groupAgent = load_agent.LoadAgentGroup()
    targetVMs = [x.strip() for x in split(targetVMs)]
    count = len(targetVMs)
    jobs = []
    for targetVM in targetVMs:
        args = (positive, targetVM, osType, username, password, loadType, 0,
                port, load, allocationSize, protocol, clientVMs, extra, False)
        jobs.append(Job(runLoadOnGuest, args=args))
    js = JobsSet()
    js.addJobs(jobs)
    js.start()
    js.join()
    for job in jobs:
        if job.result:
            res, agent = job.result
            if res:
                groupAgent.addLoadAgent(agent['load_agent'])
                continue
        count -= 1
        logger.error("failed to add LoadAgent: %s", job)
    if duration:
        if count == len(targetVMs):
            time.sleep(duration)
        for targetVM in targetVMs:
            groupAgent.kill(loadType, targetVM)
            if not groupAgent.removeLoadGenerator(loadType, targetVM):
                logger.error("Removing %s load generator from %s failed", \
                        loadType, targetVM)
    return count == len(targetVMs), {'group_agent': groupAgent}


@lookingForIpAdressByEntityName('vms', 'targetVM', 'targetVM')
@is_action()
def runLoadOnGuest(positive, targetVM, osType, username, password, loadType,
                   duration, port, load=None, allocationSize=None,
                   protocol=None, clientVMs=None, extra=None, stopLG=True):
    """
    Run system load of given type on VM for specific amount of time.
    Author: pnovotny
    Parameters:
      * targetVM - VM name or IP address
      * osType - VM's OS type: 'linux' or 'windows'
      * username - SSH or STAF username
      * password - SSH or STAF password
      * loadType - type of system load: 'CPU', 'MEM', 'IO', 'NET'
      * duration - load duration in seconds; if is set to zero,
          system load is not explicitly stopped at the end of the function
      * port - load deamon listen port
      * load - percentage of CPU load: 0-100; CPU only
      * allocationSize - initial memory allocation in MB; MEM only
      * protocol  - network protocol: 'tcp' or 'udp'; NET only
      * clientVMs - VMs which will act as a network clients; NET only
          use coma-seperated VM names or IPs
      * extra - command-line arguments passed to 'iperf' (NET)
          or iozone (IO) utility; use coma-separated values like '-a, -b, -c'
      * stopLG  - whether to automatically stop & uninstall LG on guest machine
    Return: tuple True - success / False - failure,
                  and a dict with an agent instance
    """
    initParams = {'port': port, 'stopLG': stopLG}
    startParams = {}
    eLoadType = load_agent.eLoadType

    assert duration >= 0, \
            "System load duration must be a positive number or zero."
    if loadType == eLoadType.CPU:
        MIN_CPU_LOAD = 0
        MAX_CPU_LOAD = 100
        assert MIN_CPU_LOAD <= load <= MAX_CPU_LOAD, "CPU load percentage 0-100 is required."
    elif loadType == eLoadType.MEM:
        assert allocationSize > 0, "Positive memory allocation size is required."
        if isinstance(allocationSize, basestring) and allocationSize.endswith('P'):
        # TODO: This is workaround due to #717, when it will be fixed we can
        # remove this condition
            allocationSize = allocationSize[:-1] + '%'
        initParams['allocationSize'] = allocationSize
    elif loadType == eLoadType.NET:
        assert protocol in ['tcp', 'udp'], "Network protocol 'tcp' or 'udp' is required."
        clientVMList = map(lambda x: x.strip(), clientVMs.split(','))
        assert clientVMList, "Coma-separated client VM names or IPs are required."
        clientIPs = []
        for clientVM in clientVMList:
            clientIP = clientVM if isValidIp(clientVM) \
                        else waitForIP(clientVM)[1]['ip']
            clientIPs.append(clientIP)
        initParams['protocol'] = protocol
        startParams['clientMachines'] = []
        for clientIP in clientIPs:
            assert isValidIp(clientIP), "Invalid IPv4 address: %s" % clientIP
            machine = Machine(clientIP, username, password).util(osType)
            startParams['clientMachines'].append(machine)
    if loadType in [eLoadType.IO, eLoadType.NET] and extra:
        extra = map(lambda x: x.strip(), extra.split(','))
        initParams['extra'] = extra

    vmIPAddress = targetVM if isValidIp(targetVM) \
        else waitForIP(targetVM)[1]['ip']
    machine = Machine(vmIPAddress, username, password).util(osType)
    agent = load_agent.LoadAgent(machine, targetVM)
    if not agent.addLoadGenerator(loadType, **initParams):
        logger.error("Adding %s load generator failed" % loadType)
        return False, {}
    if not agent.dispatch(loadType).start(**startParams):
        logger.error("%s load start failed" % loadType)
        return False, {}
    if loadType == eLoadType.CPU and not \
       agent.dispatch(loadType).changeParam('load', load):
        logger.error("%s change load failed" % loadType)
        return False, {}
    if duration:
        time.sleep(duration)
        if not agent.removeLoadGenerator(loadType):
            logger.error("Removing %s load generator failed" % loadType)
            return False, {}
    # return load agent instance to keep the load running
    return True, {'load_agent': agent}


@lookingForIpAdressByEntityName('vms', 'targetVM', 'targetVM')
@is_action()
def stopLoadOnGuest(targetVM, loadType, agent):
    """
    Just stop load generator on machine
    Parameters:
     * targetVM - name of machine, [vms:]nameOfVm
     * loadType - load type
     * agent - load agent
    """
    if isinstance(agent, load_agent.LoadAgent):
        return agent.dispatch(loadType).kill()
    elif isinstance(agent, load_agent.LoadAgentGroup):
        return agent.kill(loadType, targetVM)
    else:
        raise ValueError("unexpected instance of LoadAgent: %s" % agent)


def stopLoadOnGuests(targetVMs, loadTypes, agent):
    """
    Just stop load generators on machines
    Parameters:
     * targetVMs - names of machine (comma separated)
     * loadTypes - load types (comma separated)
     * agent - load agent
    """
    ecode = True
    for target in split(targetVMs):
        target = target.strip()
        for loadtype in split(loadTypes):
            ecode &= stopLoadOnGuest(target, loadtype, agent)
    return ecode


