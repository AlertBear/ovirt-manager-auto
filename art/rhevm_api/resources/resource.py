import logging


class Resource(object):
    """
    Common base for any kind of resource across rhevm tests
    """
    class LoggerAdapter(logging.LoggerAdapter):
        pass

    @property
    def logger(self):
        logger = logging.getLogger(self.__class__.__name__)
        return self.LoggerAdapter(logger, self)
