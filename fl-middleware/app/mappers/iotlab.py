from typing import Any

from app.mappers.base import ResourceMapper
from app.models.provider import ProviderId
from app.models.resource import (
    AvailabilityConfidence,
    AvailabilityInfo,
    AvailabilityState,
    HardwareInfo,
    NetworkInfo,
    NormalizedResource,
    ResourceSource,
    ResourceType,
    RuntimeInfo,
    ResourceAvailability,
)


class IoTLabMapper(ResourceMapper[dict[str, Any]]):
    """Map IoT-LAB node records to normalized middleware resources."""

    BOARD_PROFILES: dict[str, dict[str, object]] = {
        "a8": {
            "architecture": "armv7l",
            "cpu_model": "ARM Cortex-A8",
            "cpu_cores": 1,
            "memory_mb": 244,
            "python_version": "3.8.11",
            "numpy": True,
            "pytorch": False,
            "flower_native": False,
            "proxy_required": True,
        },
        "m3": {
            "architecture": "arm",
            "cpu_model": "ARM Cortex-M3",
            "cpu_cores": 1,
            "memory_mb": None,
            "python_version": None,
            "numpy": False,
            "pytorch": False,
            "flower_native": False,
            "proxy_required": True,
        },
    }


    STATE_MAPPING = {
        "alive": AvailabilityState.AVAILABLE,
        "available": AvailabilityState.AVAILABLE,
        "free": AvailabilityState.AVAILABLE,

        "busy": AvailabilityState.UNAVAILABLE,
        "dead": AvailabilityState.UNAVAILABLE,
        "unavailable": AvailabilityState.UNAVAILABLE,

        "suspected": AvailabilityState.UNKNOWN,
        "unknown": AvailabilityState.UNKNOWN,
    }

    def map_resource(
        self,
        native_resource: dict[str, Any],
        *,
        context: dict[str, Any] | None = None,
    ) -> NormalizedResource:
        #network_address = self._required_string(
         #   native_resource,
          #  "network_address",
        #)
        name=self._optional_string(
            native_resource.get("network_address")
        ) or f"{native_resource_type}-{native_id}"
        #site = str(native_resource.get("site") or "unknown")
        architecture_description = str(
            native_resource.get("archi") or "unknown"
        )
        native_id = self._required_string(
            native_resource,
            "uid",
        )

        site = self._required_string(
            native_resource,
            "site",
        )

        resource_id = (
            f"iotlab:{site}:{native_id}"
        )

        board = architecture_description.split(":", maxsplit=1)[0]
        board_profile = self.BOARD_PROFILES.get(board, {})

        #node_name = network_address.split(".", maxsplit=1)[0]
        node_name = name.split(".", maxsplit=1)[0]
        native_state = str(
            native_resource.get("state") or "unknown"
        ).casefold()

        availability_state = self.STATE_MAPPING.get(
            native_state,
            AvailabilityState.UNKNOWN,
        )
        capabilities: list[str] = []

        if self._as_bool(
            native_resource.get("power_consumption")
        ):
            capabilities.append(
                "power-consumption-monitoring"
            )

        if self._as_bool(
            native_resource.get("power_control")
        ):
            capabilities.append("power-control")

        if self._as_bool(
            native_resource.get("radio_sniffing")
        ):
            capabilities.append("radio-sniffing")

        if self._as_bool(
            native_resource.get("mobile")
        ):
            capabilities.append("mobile")

        if self._as_bool(
            native_resource.get("camera")
        ):
            capabilities.append("camera")
        return NormalizedResource(
            #id=f"iotlab:{site}:{node_name}",
            id=resource_id,
            provider=ProviderId.IOTLAB,
            #name=network_address,
            name=name,
            site=site,
            location=self._location_for_site(site),
            resource_type=ResourceType.IOT_DEVICE,
            native_resource_type=self._optional_string(
                native_resource.get("archi")
            ),
            hardware=HardwareInfo(
                architecture=self._optional_string(
                    board_profile.get("architecture")
                ),
                cpu_model=self._optional_string(
                    board_profile.get("cpu_model")
                ),
                cpu_cores=self._optional_int(
                    board_profile.get("cpu_cores")
                ),
                memory_mb=self._optional_int(
                    board_profile.get("memory_mb")
                ),
                gpu_count=0,
            ),
            network=NetworkInfo(
                public_ipv4=None,
                public_ipv6=None,
                outbound_http=None,
                bandwidth_mbps=None,
            ),
            runtime=RuntimeInfo(
                python_version=self._optional_string(
                    board_profile.get("python_version")
                ),
                numpy=self._optional_bool(
                    board_profile.get("numpy")
                ),
                pytorch=self._optional_bool(
                    board_profile.get("pytorch")
                ),
                flower_native=self._optional_bool(
                    board_profile.get("flower_native")
                ),
                proxy_required=self._optional_bool(
                    board_profile.get("proxy_required")
                ),
            ),
            #availability=self._map_availability(
             #   native_node.get("state")
            #),
            availability=ResourceAvailability(
                state=self._map_availability(
                    native_resource.get("state")
                )
),
            capabilities=capabilities,
            labels={
                "architecture": (
                    self._optional_string(
                        native_resource.get("archi")
                    )
                    or "unknown"
                ),
                "mobility-type": (
                    self._optional_string(
                        native_resource.get(
                            "mobility_type"
                        )
                    )
                    or "unknown"
                ),
                "native-state": (
                    self._optional_string(
                        native_resource.get("state")
                    )
                    or "unknown"
                ),
                "network-address": (
                    self._optional_string(
                        native_resource.get(
                            "network_address"
                        )
                    )
                    or "unknown"
                ),
            },
            source=ResourceSource(
                adapter="iotlab-adapter",
                native_id=native_id,
                native_data=native_resource,
            ),
        )

    @staticmethod
    def _required_string(
        record: dict[str, Any],
        key: str,
    ) -> str:
        value = record.get(key)

        if value is None or not str(value).strip():
            raise ValueError(
                f"IoT-LAB record is missing required field '{key}'."
            )

        return str(value)

    @staticmethod
    def _radio_chip(architecture: str) -> str:
        parts = architecture.split(":", maxsplit=1)
        return parts[1] if len(parts) == 2 else "unknown"

    @staticmethod
    def _location_for_site(site: str) -> str | None:
        locations = {
            "grenoble": "Grenoble, France",
            "lille": "Lille, France",
            "saclay": "Saclay, France",
            "strasbourg": "Strasbourg, France",
            "lyon": "Lyon, France",
        }

        return locations.get(site.casefold())

    @staticmethod
    def _optional_string(value: object) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return int(value) if value is not None else None

    @staticmethod
    def _optional_bool(value: object) -> bool | None:
        return bool(value) if value is not None else None
    
    @staticmethod
    def _map_availability(
        native_state: Any,
    ) -> AvailabilityState:
        if native_state is None:
            return AvailabilityState.UNKNOWN

        normalized_state = (
            str(native_state).strip().casefold()
        )

        if normalized_state == "alive":
            return AvailabilityState.AVAILABLE

        if normalized_state in {
            "busy",
            "dead",
        }:
            return AvailabilityState.UNAVAILABLE

        return AvailabilityState.UNKNOWN

    @staticmethod
    def _as_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, int):
            return value != 0

        if isinstance(value, str):
            return value.strip().casefold() in {
                "1",
                "true",
                "yes",
            }

        return False

