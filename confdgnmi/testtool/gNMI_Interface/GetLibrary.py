from __future__ import annotations
from dataclasses import dataclass
import json
from typing import Dict, List, Optional
from robot.api.logger import trace
from CapabilitiesLibrary import CapabilitiesLibrary
from confd_gnmi_common import _make_string_path, datatype_str_to_int, encoding_str_to_int


@dataclass
class GetRequestParameters:
    """ Placeholder for all the parameters of GetRequest.\n
        Its contents to be state-fully set by the calls to `set_..._to()` methods. """
    prefix: str = None
    paths: List[str] = None
    type: int = 0  # TODO - which one to use?
    encoding: int = None
    use_models: List[dict] = None

    @staticmethod
    def new():
        """ Returns new instance of GetRequest parameters' placeholder. """
        return GetRequestParameters()

    def to_kwargs(self, default_encoding: Optional[int]):
        return {
            'prefix': self.prefix,
            'paths': [] if self.paths is None else self.paths,
            'get_type': self.type,
            'encoding': self.encoding if self.encoding is not None
                        else default_encoding if default_encoding is not None
                        else None
        }


@dataclass
class UpdatePayload:
    path: str
    value: Dict[str, object]

    @staticmethod
    def from_obj(updateObj):
        path = _make_string_path(updateObj.path, xpath=True)
        value = json.loads(updateObj.val.json_ietf_val)
        return UpdatePayload(path=path, value=value)


class GetLibrary(CapabilitiesLibrary):
    """ ROBOT test suite library for servicing the gNMI GetRequest tests.\n
        Uses internal state to manage request parameters and response data. """
    ROBOT_LIBRARY_SCOPE = 'SUITE'

    default_encoding: Optional[str]
    params: GetRequestParameters

    def __init__(self, default_encoding: str = None) -> None:
        super().__init__()
        self.default_encoding = encoding_str_to_int(default_encoding) if default_encoding is not None else None
        self.params = GetRequestParameters.new()

    def get_last_updates_count(self):
        """ Return total number of updates in last response payload,
            or 0 if none OK response has been received. """
        if self.last_response is None:
            return 0
        # trace(self.last_response)
        return sum(len(n.update) for n in self.last_response.notification)

    def supported_models_should_include(self, model_name: str) -> bool:
        # TODO - rewrite to more efficient any()...
        models = self.get_supported_model_names()
        assert model_name in models, f'CapabilityResponse does NOT include \"{model_name}\"'

    def get_supported_model_names(self):
        """ Return list of all the models supported by device/server.\n
            This is retrieved from the `CapabilityRequest`'s supported_models property. """
        response = self._client.get_capabilities()
        return [model.name for model in response.supported_models]

    def cleanup_getrequest_parameters(self):
        """ Clear all parameters of following `GetRequest` to be empty. """
        self.params = GetRequestParameters.new()

    def prefix_set_to(self, prefix: str):
        """ Set the `prefix` parameter of the next `GetRequest` to specified value. """
        self.params.prefix = prefix
        trace(f"next GetRequest prefix set to: {prefix}")

    def encoding_set_to(self, encoding: str):
        """ Set the `Encoding` parameter of the next `GetRequest` to specified value. """
        self.params.encoding = encoding_str_to_int(encoding, no_error=True)
        trace(f"next GetRequest encoding set to: {self.params.encoding} (input: {encoding})")

    def datatype_set_to(self, data_type: str):
        """ Set the `DataType` parameter of the next `GetRequest` to specified value. """
        self.params.type = datatype_str_to_int(data_type, no_error=True)
        trace(f"next GetRequest encoding set to: {self.params.type} (input: {data_type})")

    def paths_include(self, path: str):
        """ Add a path parameter into collected array for next `GetRequest`. """
        params = self.params
        if params.paths is None:
            params.paths = []
        params.paths.append(path)
        trace(f"next GetRequest paths extended with: {path}")

    def dispatch_get_request(self):
        """ Dispatch the GetRequest towards server and store the received response.\n
            Parameters of the request are set according to previously set values. """
        self.cleanup_last_request_results()
        try:
            kwargs = self.params.to_kwargs(self.default_encoding)
            # TODO - client should trace/log all request params!
            trace(f"Dispatching GetRequest with parameters: {kwargs}")
            self.last_response = self._client.get_public(**kwargs)
        except Exception as ex:
            self.last_exception = ex
        trace(f"Last exception: {self.last_exception}")
        trace(f"Last response: {self.last_response}")

    def get_last_flattened_updates(self) -> List[List[UpdatePayload]]:
        if self.last_response is None:
            return None
        notifications = self.last_response.notification
        updates = []
        for n in notifications:
            for update in n.update:
                trace(update)
                updates.append(UpdatePayload.from_obj(update))
        return updates

    def _updates_include(self, text: str) -> bool:
        updates = self.get_last_flattened_updates()
        if updates is None:
            return False
        trace(updates)
        return any(text in update.value for update in updates)

    def check_last_updates_include(self, text: str) -> bool:
        assert self._updates_include(text), f'Wanted text \"{text}\" not found in any of updates'

    def check_last_updates_not_include(self, text: str) -> bool:
        assert not self._updates_include(text), f'Unwanted text \"{text}\" found in some of updates'
