import time
import logging
from contextlib import contextmanager


logger = logging.getLogger('core_api')


@contextmanager
def measure_time(method_name):
    '''
    Context manager to log request response time
    '''
    try:
        st = time.clock()
        yield
    finally:
        response_time = time.clock() - st
        logger.debug(
            "Request %s response time: %0.3f", method_name, response_time,
        )
