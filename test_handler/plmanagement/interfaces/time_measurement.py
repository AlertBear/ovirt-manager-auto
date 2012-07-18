
from test_handler.plmanagement import Interface


class ITimeMeasurement(Interface):
    def on_start_measure(self): # needs add some parameter
        """Called when measure of something starts """

    def on_stop_measure(self, elapsed_time):
        """Called when measure of something stops """

