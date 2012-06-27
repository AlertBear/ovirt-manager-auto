class TcmsEntryWrapper(object):
    """
        Set of wrappers for TCMS records.
        Author: mbenenso
        Parameters: none
        Return: none
    """
    def __init__(self, objectInfo):
        for key, value in objectInfo.iteritems():
            setattr(self, key, str(value).lower())


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