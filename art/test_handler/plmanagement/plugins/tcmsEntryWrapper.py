class TcmsEntryWrapper(object):
    """
        Set of wrappers for TCMS records.
        Author: mbenenso
        Parameters: none
        Return: none
    """
    encoding = 'utf8'  # FIXME: it is not good
    on_errors = 'replace'

    def __init__(self, objectInfo):
        for key, value in objectInfo.iteritems():
            if not isinstance(value, basestring):
                value = str(value)  # this can produce non-ascii as well

            if not isinstance(value, unicode):
                value = unicode(value, self.encoding, errors=self.on_errors)

            value = value.encode("ascii", self.on_errors)
            setattr(self, key, value.lower())


class TestPlanWrapper(TcmsEntryWrapper):
    def __init__(self, dict):
        TcmsEntryWrapper.__init__(self, dict)

    @property
    def id(self):
        return self.plan_id


class BuildWrapper(TcmsEntryWrapper):
    def __init__(self, dict):
        TcmsEntryWrapper.__init__(self, dict)

    @property
    def id(self):
        return self.build_id


class ProductVersionWrapper(TcmsEntryWrapper):
    def __init__(self, dict):
        TcmsEntryWrapper.__init__(self, dict)

    @property
    def name(self):
        return self.value


class ProductCategoryWrapper(TcmsEntryWrapper):
    def __init__(self, dict):
        TcmsEntryWrapper.__init__(self, dict)


class UserInfoWrapper(TcmsEntryWrapper):
    def __init__(self, dict):
        TcmsEntryWrapper.__init__(self, dict)

    @property
    def name(self):
        return self.email


class TestCaseWrapper(TcmsEntryWrapper):
    def __init__(self, dict):
        TcmsEntryWrapper.__init__(self, dict)

    @property
    def id(self):
        return self.case_id

    @property
    def name(self):
        return self.summary
