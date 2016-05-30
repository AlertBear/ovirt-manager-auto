import time
import logging
from contextlib import contextmanager


logger = logging.getLogger('core_api')


@contextmanager
def measure_time(method_name):
    '''
    Context manager to log request response time
    '''
    from art.test_handler.settings import initPlmanager
    plmanager = initPlmanager()
    plmanager.time_measurement.on_start_measure()
    try:
        st = time.clock()
        yield
    finally:
        responseTime = time.clock() - st
        plmanager.time_measurement.on_stop_measure(method_name, responseTime)
        logger.debug(
            "Request %s response time: %0.3f", method_name, responseTime,
        )
