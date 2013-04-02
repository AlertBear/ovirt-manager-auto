def setup(app):
    from art.core_api.external_api import TestRunnerWrapper
    wrapper = TestRunnerWrapper('10.10.10.10', standalone=True)
