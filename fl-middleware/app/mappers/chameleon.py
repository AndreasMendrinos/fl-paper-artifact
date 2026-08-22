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



class ChameleonMapper(ResourceMapper[dict[str, Any]]):
    """Map Chameleon hardware inventory nodes."""

    def map_resource(
        self,
        native_resource: dict[str, Any],
        *,
        context: dict[str, Any] | None = None,
    ) -> NormalizedResource:
        context = context or {}

        include_native_data = bool(
            context.get("include_native_data", False)
        )

        node_id = self._required_string(native_resource, "uid")
        site = str(context.get("site_uid") or "unknown")
        site_location = self._optional_string(
            context.get("site_location")
        )
        inventory_version = self._optional_string(
            context.get("inventory_version")
        )

        architecture_data = self._dict_value(
            native_resource.get("architecture")
        )

        processor = self._extract_processor(
            native_resource
        )
        memory = self._dict_value(
            native_resource.get("main_memory")
        )

        storage_devices = self._dict_list(
            native_resource.get("storage_devices")
        )
        network_adapters = self._dict_list(
            native_resource.get("network_adapters")
        )
        gpu_devices = self._dict_list(
            native_resource.get("gpu_devices")
        )
        
        cpu_cores = (
            self._first_integer(
                processor,
                "nb_cores",
                "core_count",
                "cores",
            )
            or self._first_integer(
                architecture_data,
                "nb_cores",
                "core_count",
                "cores",
                "smt_size",
            )
        )

        memory_mb = self._bytes_to_mb(
            memory.get("ram_size")
        )

        storage_gb = sum(
            self._bytes_to_gb(device.get("size")) or 0
            for device in storage_devices
        )

        bandwidth_mbps = self._maximum_bandwidth_mbps(
            network_adapters
        )

        gpu_models = [
            str(
                device.get("model")
                or device.get("product_name")
                or "unknown"
            )
            for device in gpu_devices
        ]

        capabilities = [
            "bare-metal",
            "hardware-versioning",
            "native-flower-client",
            "pytorch-training",
        ]

        if gpu_devices:
            capabilities.append("gpu-compute")

        return NormalizedResource(
            id=f"chameleon:{site}:{node_id}",
            provider=ProviderId.CHAMELEON,
            name=node_id,
            site=site,
            location=site_location,
            resource_type=(
                ResourceType.GPU_NODE
                if gpu_devices
                else ResourceType.BARE_METAL
            ),
            #resource_type="bare_metal_node",
            native_resource_type=self._optional_string(
                native_resource.get("node_type")
            ),
            hardware=HardwareInfo(
                architecture=self._optional_string(
                    architecture_data.get("platform_type")
                ),
                cpu_model=self._first_string(
                    processor,
                    "model",
                    "model_name",
                    "product_name",
                ),
                cpu_cores=cpu_cores,
                memory_mb=memory_mb,
                gpu_count=len(gpu_devices),
                gpu_model=(
                    ", ".join(gpu_models)
                    if gpu_models
                    else None
                ),
                storage_gb=storage_gb or None,
            ),
            network=NetworkInfo(
                public_ipv4=None,
                public_ipv6=None,
                outbound_http=None,
                bandwidth_mbps=bandwidth_mbps,
            ),
            runtime=RuntimeInfo(
                python_version=None,
                numpy=None,
                pytorch=True,
                flower_native=True,
                proxy_required=False,
            ),
            #availability=AvailabilityInfo(
             #   state=AvailabilityState.UNKNOWN,
              #  confidence=AvailabilityConfidence.UNKNOWN,
               # source="chameleon-resource-discovery",
            #),
            #availability=ResourceAvailability.UNKNOWN,
            availability=ResourceAvailability(
                state=AvailabilityState.UNKNOWN
            ),
            capabilities=capabilities,
            labels={
                "site-class": str(
                    context.get("site_class") or "unknown"
                ),
                "cluster": str(
                    context.get("cluster_uid") or "unknown"
                ),
                "inventory-kind": "physical-node",
            },
            source=ResourceSource(
                adapter="chameleon-resource-discovery-adapter",
                native_id=node_id,
                inventory_version=inventory_version,
                native_data=(
                    native_resource
                    if include_native_data
                    else None
                ),
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
                f"Chameleon record is missing required field '{key}'."
            )

        return str(value)

    @staticmethod
    def _dict_value(value: object) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _dict_list(value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        return [
            item for item in value
            if isinstance(item, dict)
        ]

    @classmethod
    def _first_dict(cls, value: object) -> dict[str, Any]:
        items = cls._dict_list(value)
        return items[0] if items else {}

    @staticmethod
    def _bytes_to_mb(value: object) -> int | None:
        if value is None:
            return None

        return round(int(value) / (1024**2))

    @staticmethod
    def _bytes_to_gb(value: object) -> float | None:
        if value is None:
            return None

        return round(int(value) / (1024**3), 2)

    @staticmethod
    def _optional_string(value: object) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return int(value) if value is not None else None

    @staticmethod
    def _maximum_bandwidth_mbps(
        adapters: list[dict[str, Any]],
    ) -> float | None:
        rates = [
            float(adapter["rate"]) / 1_000_000
            for adapter in adapters
            if adapter.get("rate") is not None
        ]

        return max(rates) if rates else None
    
    @classmethod
    def _extract_processor(
        cls,
        native_resource: dict[str, Any],
    ) -> dict[str, Any]:
        processor = native_resource.get("processor")

        if isinstance(processor, dict):
            return processor

        processors = cls._dict_list(
            native_resource.get("processors")
        )

        return processors[0] if processors else {}

    @staticmethod
    def _first_integer(
        record: dict[str, Any],
        *keys: str,
    ) -> int | None:
        for key in keys:
            value = record.get(key)

            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue

        return None

    @staticmethod
    def _first_string(
        record: dict[str, Any],
        *keys: str,
    ) -> str | None:
        for key in keys:
            value = record.get(key)

            if value is not None and str(value).strip():
                return str(value)

        return None