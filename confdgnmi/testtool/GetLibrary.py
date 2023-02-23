from __future__ import annotations

import typing as t

from attr import dataclass

from gnmi_proto_helpers import datatype_str_to_int, encoding_int_to_str, encoding_str_to_int
from robot.api.logger import info
from confd_gnmi_client import ConfDgNMIClient


@dataclass
class GetRequestParameters:
    """ Placeholder for al the parameters of GetRequest.\n
        Its contents to be statefully set by the calls to `set_..._to()` methods. """
    prefix: str = None
    paths: list[str] = None
    get_type: str = None
    encoding: int = None


def new_empty_params():
    """ Returns new instance of GetRequest parameters' placeholder. """
    return GetRequestParameters()


class GetLibrary:
    """ ROBOT test suite library for servicing the gNMI GetRequest tests.\n
        Uses internal state to manage request parameters and response data. """
    ROBOT_LIBRARY_SCOPE = 'SUITE'

    params: GetRequestParameters
    response: t.Optional[dict]  # TODO - make proper type

    def __init__(self) -> None:
        self._client: t.Optional[ConfDgNMIClient] = None
        self.params = new_empty_params()

    def get_library_greeting(self):
        """ A sanity check that this library is working with the robot \"backend\". """
        return 'hello'

    def setup_client(self, ip, username, passwd, insecure):
        """ Initialize new gNMI client instance for dispatching the requests to server. """
        self._client = ConfDgNMIClient(*ip.split(':'), insecure=insecure,
                                       username=username, password=passwd)

    def close_client(self):
        """ Close previously initialized gNMI client instance. """
        self._client.close()

    def get_supported_encodings(self):
        """ Return list of all the encodings claimed to be supported by server.\n
            This is retrieved from the `CapabilityRequest`'s supported_encodings property. """
        response = self._client.get_capabilities()
        return [encoding_int_to_str(encoding) for encoding in response.supported_encodings]

    def get_unsupported_encodings(self):
        """ Return list of encodings that are NOT reported as supported by server.\n
            Created as all the possible encodings' completent
            to `self.get_supported_encodings()` list. """
        ALL_ENCODINGS = ['JSON', 'BYTES', 'PROTO', 'ASCII', 'JSON_IETFS']
        supported = self.get_supported_encodings()
        return [encoding for encoding in ALL_ENCODINGS if encoding not in supported]

    def clear_getrequest_parameters(self):
        """ Clear all parameters of following `GetRequest` to be empty. """
        self.params = new_empty_params()

    def set_prefix_to(self, prefix: str):
        """ Set the `prefix` parameter of the next `GetRequest` to specified value. """
        self.params.prefix = prefix

    def set_encoding_to(self, encoding: str):
        """ Set the `Encoding` parameter of the next `GetRequest` to specified value. """
        self.params.encoding = encoding_str_to_int(encoding)

    def set_datatype_to(self, data_type: str):
        """ Set the `DataType` parameter of the next `GetRequest` to specified value. """
        self.params.get_type = datatype_str_to_int(data_type)

    def add_path_parameter(self, path: str):
        params = self.params
        if params.paths is None:
            params.paths = []
        params.paths += path

    def dispatch_get_request(self):
        """ Dispatch the GetRequest towards server and store the received response.\n
            Parameters of the request are set according to previously set placeholder values
            (see `set_..._to()` methods). """
        params = self.params
        info(params)
        self.response = None
        response = self._client.get_todo(params.prefix, params.paths,
                                    params.get_type, params.encoding)
        self.response = response

    def check_received_ok_response(self):
        """ Verify that last `GetRequest` ended with positive response from server. """
        # TODO - check the response object - "ok" or error?
        assert self.response is not None

    def check_received_error_response(self):
        """ Verify that last `GetRequest` ended with negative response from server. """
        assert self.response is None
