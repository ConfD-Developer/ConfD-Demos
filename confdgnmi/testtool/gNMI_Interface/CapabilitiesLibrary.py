from __future__ import annotations
from dataclasses import dataclass
from typing import List
from confd_gnmi_common import encoding_int_to_str

from gNMIRobotLibrary import gNMIRobotLibrary


@dataclass
class CapabilitiesData:
    model_names: List[str]
    encodings: List[str]


def empty_capabilities_data():
    return CapabilitiesData([], [])


class CapabilitiesLibrary(gNMIRobotLibrary):
    ROBOT_LIBRARY_SCOPE = 'SUITE'

    def __init__(self) -> None:
        super().__init__()
        self._capabilities_data = empty_capabilities_data()

    def cleanup_capabilities(self) -> None:
        """ Reset previously (if applicable) loaded ``CapabilityResponse`` data. """
        self._capabilities_data = empty_capabilities_data()

    def get_capabilities_from_device(self) -> None:
        """ Dispatch ``CapabilityRequest`` to a target device and retrieve list of
            supported encodings and model names. """
        self.cleanup_last_request_results()
        self.cleanup_capabilities()
        try:
            response = self._client.get_capabilities()
            self._capabilities_data = CapabilitiesData(
                model_names = [m.name for m in response.supported_models],
                encodings = [encoding_int_to_str(e) for e in response.supported_encodings]
            )
            self.last_response = response
        except Exception as ex:
            self.last_exception = ex

    def list_supported_encodings(self) -> List[str]:
        """ Return list of all the *encodings* advertised as supported by server. """
        return self._capabilities_data.encodings

    def list_supported_model_names(self) -> List[str]:
        """ Return list of all the *model names* advertised as supported by server. """
        return self._capabilities_data.model_names

    def list_unsupported_encodings(self):
        """ Return list of encodings that are NOT reported as supported by server.\n
            Created as a complement of all the possible encodings'
            to the `self.get_supported_encodings()` list. """
        ALL_ENCODINGS = ['JSON', 'BYTES', 'PROTO', 'ASCII', 'JSON_IETF']
        supported = self.list_supported_encodings()
        unsupported = [encoding for encoding in ALL_ENCODINGS if encoding not in supported]
        return unsupported
