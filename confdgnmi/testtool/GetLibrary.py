from __future__ import annotations
from dataclasses import dataclass

import typing as t

from gnmi_proto_helpers import datatype_str_to_int, encoding_int_to_str, encoding_str_to_int
# from robot.api.logger import info
from robot_gnmi_client import GNMIClient


@dataclass
class GetRequestParameters:
    """ Placeholder for all the parameters of GetRequest.\n
        Its contents to be state-fully set by the calls to `set_..._to()` methods. """
    prefix: str = None
    paths: list[str] = None
    get_type: str = None
    encoding: int = None

    def to_kwargs(self):
        return {
            'prefix': self.prefix,
            'paths': [] if self.paths is None else self.paths,
            'get_type': self.get_type,
            'encoding': self.encoding
        }


def new_empty_params():
    """ Returns new instance of GetRequest parameters' placeholder. """
    return GetRequestParameters()


class GetLibrary(GNMIClient):
    """ ROBOT test suite library for servicing the gNMI GetRequest tests.\n
        Uses internal state to manage request parameters and response data. """
    ROBOT_LIBRARY_SCOPE = 'SUITE'

    params: GetRequestParameters
    last_get_response: t.Optional[dict]  # TODO - make proper type
    last_get_exception: t.Optional[Exception]

    def __init__(self) -> None:
        super().__init__()
        self.params = new_empty_params()

    def get_library_greeting(self):
        """ A sanity check that this library is working with the robot \"backend\". """
        return 'hello'

    def get_supported_encodings(self):
        """ Return list of all the encodings claimed to be supported by server.\n
            This is retrieved from the `CapabilityRequest`'s supported_encodings property. """
        response = self._client.get_capabilities()
        return [encoding_int_to_str(encoding) for encoding in response.supported_encodings]

    def get_unsupported_encodings(self):
        """ Return list of encodings that are NOT reported as supported by server.\n
            Created as a complement of all the possible encodings'
            to the `self.get_supported_encodings()` list. """
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
        """ Add a path parameter into collected array for next `GetRequest`. """
        params = self.params
        if params.paths is None:
            params.paths = []
        params.paths += path

    def dispatch_get_request(self):
        """ Dispatch the GetRequest towards server and store the received response.\n
            Parameters of the request are set according to previously set placeholder values
            (see `set_..._to()` methods). """
        self.last_get_response = None
        self.last_get_exception = None
        try:
            self.last_get_response = self._client.get_todo(**self.params.to_kwargs())
        except Exception as ex:
            self.last_get_exception = ex
            return

    def should_receive_ok_response(self):
        """ Verify that last `GetRequest` ended with positive response from server. """
        assert self.last_get_response is not None and self.last_get_exception is None

    def should_receive_error_response(self):
        """ Verify that last `GetRequest` ended with negative response from server. """
        assert self.last_get_response is None and self.last_get_exception is not None
