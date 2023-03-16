from abc import ABC
import logging
from typing import Dict, Optional
from robot.api.logger import trace
from confd_gnmi_client import ConfDgNMIClient


class gNMIRobotLibrary(ABC):

    last_response: Optional[Dict] = None
    last_exception: Optional[Exception] = None

    """ Common gNMI related functionality used across Robot tests and all libraries inheriting. """
    def __init__(self, enable_extra_logs = False) -> None:
        self._client: Optional[ConfDgNMIClient] = None
        if not enable_extra_logs:
            # disable all confg_gnmi_ loggers to not pollute robot logs
            for name in logging.root.manager.loggerDict:
                if name.startswith('confd_gnmi_'):
                    logging.getLogger(name).disabled = True
            # but keep the RPC one...
            logging.getLogger('confd_gnmi_rpc').disabled = False

    def setup_client(self, host, port, username, passwd, insecure):
        """ Initialize new gNMI client instance for dispatching the requests to server. """
        self._client = ConfDgNMIClient(host=host, port=port, insecure=insecure,
                                       username=username, password=passwd)
        trace('gNMI client connection OK')

    def close_client(self):
        """ Close previously initialized gNMI client instance. """
        self._client.close()
        trace('gNMI client connection closed')

    def _assert_condition(self, condition: bool, message: str):
        if not condition:
            trace(f'last response: {self.last_response}')
            trace(f'last exception: {self.last_exception}')
        assert condition, message

    def should_received_ok_response(self):
        """ Verify that last request ended with positive response from server. """
        condition = self.last_response is not None and self.last_exception is None
        message = 'Didn\'t receive expected OK response'
        self._assert_condition(condition, message)

    def should_received_error_response(self):
        """ Verify that last request ended with negative response from server. """
        condition = self.last_response is None and self.last_exception is not None
        message = 'Didn\'t receive expected error response'
        self._assert_condition(condition, message)

    def retrieve_last_response(self):
        """ Return the last received "response" object, or None
            if last gNMI request ended in error/exception. """
        return self.last_response

    def retrieve_last_exception(self):
        """ Return the last received "exception" object, or None
            if last gNMI request ended OK. """
        return self.last_exception

    def cleanup_last_request_results(self):
        """ Reset previously buffered response/exception. """
        self.last_response = None
        self.last_exception = None

    def test_teardown(self):
        """ To be used as robot's "Test teardown" for cleaning up any (sub)class state. """
        self.cleanup_last_request_results()
