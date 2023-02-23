from __future__ import annotations

from dataclasses import dataclass
import typing as t

from robot_gnmi_client import GNMIClient
from gnmi_proto_helpers import encoding_int_to_str


@dataclass
class Capabilities:
    models: t.List[str]
    encodings: t.List[str]


class CapabilityLibrary(GNMIClient):
    "ROBOT test suite library for servicing the gNMI SubscribeRequest tests."
    ROBOT_LIBRARY_SCOPE = 'SUITE'

    def __init__(self) -> None:
        super().__init__()
        self.cleanup_capabilities()

    def cleanup_capabilities(self) -> None:
        self._capas = Capabilities([], [])

    def get_capabilities(self) -> None:
        capas = self._client.get_capabilities()
        self._capas = Capabilities(
            models=[m.name for m in capas.supported_models],
            encodings=[encoding_int_to_str(e) for e in capas.supported_encodings])

    def supported_encodings(self) -> t.List[str]:
        return self._capas.encodings

    def supported_models(self) -> t.List[str]:
        return self._capas.models
