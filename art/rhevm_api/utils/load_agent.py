#!/usr/bin/env python

from abc import ABCMeta, abstractmethod
import logging
import sys

from utilities import enum, errors
from utilities.jobs import Job, JobsSet


# module-level logger
logger = logging.getLogger('load_agent')

# all relevant types of system load
eLoadType = enum.Enum(CPU='CPU',
                      MEM='MEM',
                      IO='IO',
                      NET='NET')


class LoadAgent(object):
    """
    Class designed for system load management.
    """
    def __init__(self, machine, nameVM=None, skip_alive_check=True):
        """
        Description: Init. 
        Author: pnovotny
        Date: 2011-07-04
        Parameters:
            * machine - instance of utitlities.machine.Machine()
              Machine on which system load will ran.
            * nameVM - name of machine
        """
        if skip_alive_check and not machine.isAlive(5):
            raise IOError("Host %s is not responding to ping request!" % machine.host)
        self.__machine = machine
        self.__loadGenerators = {}
        self.__name = nameVM

    @property
    def nameVM(self):
        return self.__name

    @property
    def generators(self):
        return self.__loadGenerators

    def addLoadGenerator(self, loadType, **kwargs):
        """
        Description: Create load generator controller instance of given type 
          and store it in private dictionary.
        Author: pnovotny
        Date: 2011-07-04
        Parameters:
            * loadType - type of load generator, see 'eLoadType' attributes
            * kwargs - dictionary parameters which are passed to generator instance
        Return: True/False
        """
        if loadType not in self.__loadGenerators.keys():
            loadGenerator = LoadGeneratorFactory.createLoadGenerator(loadType, self.__machine, **kwargs)
            self.__loadGenerators[loadType] = loadGenerator
            return True
        logger.warn('Load generator for %s is already loaded in the agent, ignoring.'
                    % loadType)
        return False

    def removeLoadGenerator(self, loadType):
        """
        Remove load generator controller instance from private dictionary, 
          resulting the load generator is automatically stopped and uninstalled. 
          CAUTION! If you set 'stopLG' parameter to False in <addLoadGenerator>
          call, you have to stop & uninstall the load generator manually 
          via <dispatch> method before running this action! 
          Otherwise you will just loose the link how to control the generator 
          which can be still running.
        Author: pnovotny
        Parameters:
            * loadType - type of load generator, see 'eLoadType' attributes
        Return: True/False
        """
        try:
            logger.debug('deleting %s load gen...' % loadType)
            del(self.__loadGenerators[loadType])
            return True
        except KeyError:
            logger.error("'%s' load generator is not present in this agent." % loadType)
        return False

    def dispatch(self, loadType):
        """
        Description: Dispatcher. Returns load generator instance of given type.
        Author: pnovotny
        Date: 2011-07-04
        Parameters:
            * loadType - type of load generator, see 'eLoadType' attributes
        Return: load generator instance or throws error 
        Throws: LoadGeneratorNotPresentError(loadType)
        """
        try:
            return self.__loadGenerators[loadType]
        except KeyError:
            raise LoadGeneratorNotPresentError(loadType)


class LoadGeneratorFactory(object):
    """
    Factory for load generator controller instances.
    """
    @staticmethod
    def createLoadGenerator(loadType, machine, **kwargs):
        """
        Description: Factory method
        Author: pnovotny
        Date: 2011-07-04
        Parameters:
            * loadType - type of load generator, see 'eLoadType' attributes
            * machine - machine.Machine instance
            * kwargs - keyword arguments passed to the load gen. constructor
        Return: load generator instance of the given type
        """
        if loadType == eLoadType.CPU:
            return CPULoadController(machine, **kwargs)
        elif loadType == eLoadType.MEM:
            return MemLoadController(machine, **kwargs)
        elif loadType == eLoadType.IO:
            return IOLoadController(machine, **kwargs)
        elif loadType == eLoadType.NET:
            return NetLoadController(machine, **kwargs)
        else:
            raise WrongLoadTypeError(loadType)


class ILoadController(object):
    """
    Interface with several abstract methods common for all load generators.
    """
    __metaclass__ = ABCMeta

    def __init__(self, machine, stopLG=True, **kwargs):
        """
        Description: Constructor. 
          State flags 'isInsalled', 'isRunning' are also set. 
        Author: pnovotny
        Date: 2011-07-04
        Parameters:
            * machine - machine.Machine instance
            * stopLG - automatically stop & uninstall load generator just
                before the load controller instance is destroyed. True by default. 
                Useful when you forgot to do it manually or your script crashes.
            * kwargs - initial load generator arguments
              - port - mandatory for all load generators
              - permanent - CPU load; optional
              - allocationSize - MEM load
              - extra - NET load; optional (clients only)
        """
        self.machine = machine
        self.stopLG = stopLG
        self.params = kwargs

        self.isInstalled = False
        self.isRunning = False

    def __del__(self):
        """
        Description: Do cleanup actions before getting destroyed.
        Author: pnovotny
        Date: 2011-07-04
        """
        if self.stopLG:
            self._cleanup()

    @abstractmethod
    def _cleanup(self):
        """
        Description: Abstract method for cleanup actions.
          In most cases it means stopping and uninstalling the load generator.
        Author: pnovotny
        Date: 2011-07-04
        """
        raise NotImplementedError("Abstract method.")

    @abstractmethod
    def start(self):
        """
        Description: Start system load (abstract method).
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        raise NotImplementedError("Abstract method.")

    @abstractmethod
    def stop(self):
        """
        Description: Stop system load (abstract method).
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        raise NotImplementedError("Abstract method.")

    @abstractmethod
    def kill(self):
        """
        Description: Kill load generator (i.e. stop and uninstall it) 
          (abstract method)
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        return True

    def changeParam(self):
        """
        Description: Change load generator parameter.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        pass


class CPULoadController(ILoadController):
    """
    CPU load generator controller.
    """

    def __installLoadGenerator(self):
        """
        Description: Trigger load gen. installation and set proper proper state flags.
        Author: pnovotny
        Date: 2011-07-04
        """
        self.isInstalled = self.isRunning = \
            self.machine.installCpuLoadGenerator(port=self.params['port'])

    def start(self):
        """
        Description: Start to generate system load.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('CPU:starting...')
        if not self.isInstalled:
            self.__installLoadGenerator()
        if not self.isRunning:
            self.isRunning = \
                self.machine.toggleCpuLoadGenerator('start',
                                                    permanent=self.params.get('permanent', False))
        return self.isRunning

    def stop(self):
        """
        Description: Stop system load generation.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('CPU:stopping...')
        if self.isRunning:
            return self.kill()

    def kill(self):
        """
        Description: Cancel system load generation and uninstall the generator.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('CPU:killing...')
        if self.isInstalled:
            self.isInstalled = self.isRunning = \
                not self.machine.toggleCpuLoadGenerator('kill')
            logger.debug('CPU killed: %s' % (not self.isInstalled))
        return not self.isInstalled


    def changeParam(self, param, value):
        """
        Description: Change CPU load generator parameter.
        Author: pnovotny
        Date: 2011-07-04
        Parameters:
            * param - parameter name
            * value - parameter value
          - example: changeParam('load', 90)
          - see: Machine.toggleCpuLoadGenerator() options for more
        Return: True/False
        """
        kwarg = {param: value}
        logger.debug('CPU:changeParam(%s)...' % kwarg)
        return self.machine.toggleCpuLoadGenerator(param, **kwarg)

    # private methods

    def _cleanup(self):
        """
        Description: Cleanup actions - stopping and uninstalling the load generator.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('CPU:cleanup...')
        return self.kill()


class MemLoadController(ILoadController):
    """
    Memory load generator controller.
    """

    def __validateParams(self):
        """
        Description: Validate input parameters and values.
        Author: pnovotny
        Date: 2011-07-04
        Return: None or throws error 
        Throws: errors.WrongParameterError
        """
        try:
            assert self.params['port']
            assert self.params['allocationSize']
        except KeyError as ex:
            raise errors.WrongParameterError(ex)

    def __installLoadGenerator(self):
        """
        Description: Trigger load gen. installation and set proper state flags.
        Author: pnovotny
        Date: 2011-07-04
        """
        self.__validateParams()
        self.isInstalled = self.isRunning = \
            self.machine.installMemoryLoadGenerator(port=self.params['port'],
                                                    allocationSize=self.params['allocationSize'])

    def start(self):
        """
        Description: Start to generate system load.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('MEM:starting...')
        if not self.isInstalled:
            self.__installLoadGenerator()
        if not self.isRunning:
            self.isRunning = self.machine.toggleMemoryLoadGenerator('start')
        return self.isRunning

    def stop(self):
        """
        Description: Stop system load generation.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('MEM:stopping...')
        if self.isRunning:
            self.isRunning = not self.machine.toggleMemoryLoadGenerator('stop')
        return self.isRunning

    def kill(self):
        """
        Description: Cancel system load generation and uninstall the generator.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('MEM:killing...')
        if self.isInstalled:
            self.isInstalled = self.isRunning = \
                not self.machine.toggleMemoryLoadGenerator('kill')
        return not self.isInstalled

    def changeParam(self, param, value=None):
        """
        Description: Change or get memory load generator parameter.
        Author: pnovotny
        Date: 2011-07-04
        Parameters:
            * param - parameter name
            * value - parameter value; optional for some parameters
          - example: changeParam('isAlive')
          - see: Machine.toggleMemoryLoadGenerator() options for more
        Return: True/False
        """
        if value:
            kwarg = {param: value}
            logger.debug('MEM:changeParam(%s)...' % kwarg)
            return self.machine.toggleMemoryLoadGenerator(param, **kwarg)
        logger.debug('MEM:changeParam(%s)...' % param)
        return self.machine.toggleMemoryLoadGenerator(param)


    # private methods

    def _cleanup(self):
        """
        Description: Cleanup actions - stopping and uninstalling the load generator.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('MEM:cleanup...')
        return self.kill()


class IOLoadController(ILoadController):
    """
    IO load generator controller.
    """

    def __installLoadGenerator(self):
        """
        Description: Trigger load gen. installation and set proper state flags.
        Author: pnovotny
        Date: 2011-07-04
        """
        self.isInstalled = self.isRunning = \
            self.machine.installIOLoadGenerator(port=self.params['port'])

    def start(self):
        """
        Description: Start to generate system load.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('IO:starting...')
        if not self.isInstalled:
            self.__installLoadGenerator()
        if self.isRunning:
            logger.debug('IO:calling restart...')
            return self.machine.toggleIOLoadGenerator('restart')
        logger.debug('IO:calling start...')
        self.isRunning = self.machine.toggleIOLoadGenerator('start')
        return self.isRunning

    def stop(self):
        """
        Description: Stop system load generation.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('IO:stopping...')
        if self.isRunning:
            self.isRunning = not self.machine.toggleIOLoadGenerator('stop')
        return self.isRunning

    def kill(self):
        """
        Description: Cancel system load generation and uninstall the generator.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('IO:killing...')
        if self.isInstalled:
            self.isInstalled = self.isRunning = \
                not self.machine.toggleIOLoadGenerator('kill')
        return not self.isInstalled

    # private methods

    def _cleanup(self):
        """
        Description: Cleanup actions - stopping and uninstalling the load generator.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('IO:cleanup...')
        return self.kill()


class NetLoadController(ILoadController):
    """
    Network load generator controller.
    """

    def __validateParams(self):
        """
        Description: Validate input parameters and values.
        Author: pnovotny
        Date: 2011-07-04
        Return: None or throws error 
        Throws: errors.WrongParameterError
        """
        VALID_PROTOCOLS = ['tcp', 'TCP', 'udp', 'UDP']
        try:
            assert self.params['port']
            assert self.params['protocol']
            assert (self.params['protocol'] in VALID_PROTOCOLS), \
                "valid protocols are: %s" % VALID_PROTOCOLS
        except (KeyError, AssertionError) as ex:
            raise errors.WrongParameterError(ex)

    def __installLoadGenerator(self):
        """
        Description: Trigger load gen. installation and set proper state flags.
        Author: pnovotny
        Date: 2011-07-04
        """
        self.__validateParams()
        self.isInstalled = self.machine.installNetworkLoadGenerator()
        self.machine.createNetworkLoadServer(port=self.params['port'],
                                             protocol=self.params['protocol'])

    def start(self, clientMachines=None):
        """
        Description: Start to generate system load.
        Author: pnovotny
        Date: 2011-07-04
        Parameters:
            * clientMachines - list of Machine instances in role of clients
        Return: True/False
        """
        if not clientMachines:
            clientMachines = []
        logger.debug('Net:starting...')
        if not self.isInstalled:
            self.__installLoadGenerator()
        for client in clientMachines:
            self.machine.addClientToNetworkLoadServer(client,
                                                      protocol=self.params['protocol'],
                                                      extra=self.params.get('extra', []))
        self.isRunning = True
        return self.isRunning

    def stop(self):
        """
        Description: Stop system load generation.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('Net:stopping...')
        self.machine.stopNetworkLoadServer()
        self.isRunning = self.isInstalled = False
        return not self.isRunning

    def kill(self):
        """
        Description: Cancel system load generation and uninstall the generator.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('Net:killing...')
        return self.stop()

    # private methods

    def _cleanup(self):
        """
        Description: Cleanup actions - stopping and uninstalling the load generator.
        Author: pnovotny
        Date: 2011-07-04
        Return: True/False
        """
        logger.debug('Net:cleanup...')
        return self.kill()


class LoadAgentGroup(object):
    """
    Description: Wrapper for LoadAgent
    Author: lbednar
    """

    def __init__(self):
        self.__agents = []

    def addLoadAgent(self, agent):
        """
        Description: Adds another LoadAgent
        """
        def myclean():
            return True
        for item in self.__agents:
            if item is agent:
                break
            if item.nameVM == agent.nameVM:
                item.generators.update(agent.generators)
                agent._cleanup = myclean
                break
        else:
            self.__agents.append(agent)

    def removeLoadGenerator(self, loadType, nameVM=None):
        """
        Description: Removes load generator
        """
        for agent in self.filter(loadType, nameVM):
            agent.removeLoadGenerator(loadType)
            if not agent.generators:
                self.__agents.remove(agent)

    def start(self, loadType, nameVM=None, **kwargs):
        """
        Description: Starts all of load generators which match with loadType
                     and nameVM
        Parameters:
         * loadType - type of load generator
         * nameVM - name of VM
        """
        return self.__commandOverGenerators(loadType, nameVM, 'start', **kwargs)

    def stop(self, loadType, nameVM=None, **kwargs):
        """
        Description: Stops all of load generators which match with loadType
                     and nameVM
        Parameters:
         * loadType - type of load generator
         * nameVM - name of VM
        """
        return self.__commandOverGenerators(loadType, nameVM, 'stop', **kwargs)

    def kill(self, loadType, nameVM=None, **kwargs):
        """
        Description: Kills all of load generators which match with loadType
                     and nameVM
        Parameters:
         * loadType - type of load generator
         * nameVM - name of VM
        """
        return self.__commandOverGenerators(loadType, nameVM, 'kill', **kwargs)

    def __commandOverGenerators(self, loadType, nameVM, cmd, **kwargs):
        jobs = []
        for agent in self.filter(loadType, nameVM):
            jobs.append(Job(getattr(agent.dispatch(loadType), cmd), kwargs=kwargs))
        if jobs:
            jobSet = JobsSet()
            jobSet.addJobs(jobs)
            jobSet.start()
            jobSet.join()
            return all((x.result for x in jobs))
        return True

    def filter(self, loadType, nameVM):
        for agent in self.__agents:
            if loadType in agent.generators.keys():
                if nameVM is None or nameVM == agent.nameVM:
                    yield agent

# Exceptions & errors


class WrongLoadTypeError(errors.GeneralException):
    """
    This error is risen when invalid type of load generator is provided.
    """
    message = "invalid load generator type provided"


class LoadGeneratorNotPresentError(errors.GeneralException):
    """
    This error is risen when load gen. instance is not present in LoadAgent dictionary.
    """
    message = "load generator is not present"


def main():
    """
    Main function with example usage.
    Run for debug purposes only! 
    """
    import time
    from utilities.machine import Machine

    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.DEBUG)

    machine = Machine('<IP>', '<user>', '<pass>').util('linux|windows')
    agent = LoadAgent(machine)
    # test execution flags
    runTestCPU = False
    runTestMEM = False
    runTestIO = False
    runTestNET = False

    if runTestCPU:
        # CPU
        agent.addLoadGenerator(eLoadType.CPU, port=5555)
        agent.dispatch(eLoadType.CPU).start()
        time.sleep(10)
        agent.dispatch(eLoadType.CPU).changeParam('load', 90)
        time.sleep(10)
        agent.dispatch(eLoadType.CPU).stop()
        agent.removeLoadGenerator(eLoadType.CPU)
    if runTestMEM:
        # memory
        agent.addLoadGenerator(eLoadType.MEM, port=6666, allocationSize=500)
        agent.dispatch(eLoadType.MEM).start()
        time.sleep(20)
        agent.dispatch(eLoadType.MEM).stop()
        agent.removeLoadGenerator(eLoadType.MEM)
    if runTestIO:
        # IO
        agent.addLoadGenerator(eLoadType.IO, port=7777)
        agent.dispatch(eLoadType.IO).start()
        time.sleep(15)
        agent.dispatch(eLoadType.IO).stop()
        agent.removeLoadGenerator(eLoadType.IO)
    if runTestNET:
        # network
        agent.addLoadGenerator(eLoadType.NET, port=8888, protocol='tcp')
        # or
        #agent.addLoadGenerator(eLoadType.NET, port=8888, protocol='udp', extra=['-b', '100M', '-d'])
        m_client = Machine('<IP>', '<user>', '<pass>').util('linux|windows')
        agent.dispatch(eLoadType.NET).start([m_client])
        time.sleep(10)
        agent.dispatch(eLoadType.NET).stop()
        agent.removeLoadGenerator(eLoadType.NET)


if __name__ == "__main__":
    main()
