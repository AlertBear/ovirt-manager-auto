
import time
import logging
from contextlib import contextmanager
from art.test_handler.settings import initPlmanager


@contextmanager
def measure_time(): # should be some appropiate params
    '''
    Context manager to log request response time
    '''
    plmanager = initPlmanager()
    plmanager.time_measurement.on_start_measure()
    try:
        st = time.clock()
        yield
    finally:
        responseTime = time.clock() - st
        plmanager.time_measurement.on_stop_measure(responseTime)
        logging.debug("Request response time: %0.3f" % (responseTime))

