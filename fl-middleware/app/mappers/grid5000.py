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
    ResourceAvailability
)


class Grid5000Mapper(ResourceMapper[dict[str, Any]]):
    """Map Grid'5000 reference API node records."""

    def map_resource(
        self,
        native_resource: dict[str, Any],
        *,
        context: dict[str, Any] | None = None,
    ) -> NormalizedResource:
        context = context or {}

        node_id = self._required_string(native_resource, "uid")
        site = str(context.get("site_uid") or "unknown")
        cluster = str(
            context.get("cluster_uid")
            or native_resource.get("nodeset")
            or "unknown"
        )
        
        architecture = self._dictionary(
            native_resource.get("architecture")
        )
        processor = self._processor(native_resource)
        memory = self._dictionary(
            native_resource.get("main_memory")
        )

        network_adapters = self._dictionary_list(
            native_resource.get("network_adapters")
        )
        storage_devices = self._dictionary_list(
            native_resource.get("storage_devices")
        )
        gpu_devices = self._dictionary_list(
            native_resource.get("gpu_devices")
        )

        storage_gb = sum(
            self._bytes_to_gb(device.get("size")) or 0
            for device in storage_devices
        )

        capabilities = [
            "bare-metal",
            "native-flower-client",
            "high-bandwidth",
        ]

        supported_job_types = self._dictionary(
            native_resource.get("supported_job_types")
        )
        
        queues = supported_job_types.get("queues")

        normalized_queues = (
            [
                str(queue).strip()
                for queue in queues
                if str(queue).strip()
            ]
            if isinstance(queues, list)
            else []
        )

        if supported_job_types.get("deploy") is True:
            capabilities.append("bare-metal-deployment")

        if gpu_devices:
            capabilities.append("gpu-compute")
        
        reservation_queue: str | None = None

        if "default" in normalized_queues:
            reservation_queue = "default"
        elif "abaca" in normalized_queues:
            reservation_queue = "abaca"
        elif normalized_queues:
            reservation_queue = normalized_queues[0]

        return NormalizedResource(
            id=f"grid5000:{site}:{node_id}",
            provider=ProviderId.GRID5000,
            name=node_id,
            site=site,
            location=self._location_for_site(site),
            resource_type=(
                ResourceType.GPU_NODE
                if gpu_devices
                else ResourceType.BARE_METAL
            ),
            native_resource_type=self._optional_string(
                native_resource.get("model")
                or native_resource.get("type")
            ),
            hardware=HardwareInfo(
                architecture=self._optional_string(
                    architecture.get("platform_type")
                ),
                cpu_model=self._optional_string(
                    processor.get("model")
                ),
                cpu_cores = (
                    self._optional_int(
                        architecture.get("nb_cores")
                    )
                    or
                    self._optional_int(
                        processor.get("nb_cores")
                    )
                ),
                memory_mb=self._bytes_to_mb(
                    memory.get("ram_size")
                ),
                gpu_count=len(gpu_devices),
                gpu_model=self._gpu_models(gpu_devices),
                storage_gb=storage_gb or None,
            ),
            network=NetworkInfo(
                public_ipv4=False,
                public_ipv6=True,
                outbound_http=True,
                bandwidth_mbps=self._maximum_bandwidth_mbps(
                    network_adapters
                ),
            ),
            runtime=RuntimeInfo(
                python_version=None,
                numpy=None,
                pytorch=None,
                flower_native=True,
                proxy_required=False,
            ),
            
            availability=ResourceAvailability(
                state=AvailabilityState.UNKNOWN
            ),
            capabilities=capabilities,
            
            labels={
                "cluster": cluster,
                "scheduler": "oar",
                **(
                    {"queue": reservation_queue}
                    if reservation_queue is not None
                    else {}
                ),
            },
            source=ResourceSource(
                adapter="grid5000-reference-api-adapter",
                native_id=node_id,
                inventory_version=self._optional_string(
                    context.get("inventory_version")
                ),
                #native_data=native_resource,
                native_data=(
                    native_resource
                    if context.get("include_native_data") is True
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
                f"Grid'5000 record is missing required field '{key}'."
            )

        return str(value)

    @classmethod
    def _processor(
        cls,
        native_resource: dict[str, Any],
    ) -> dict[str, Any]:
        processor = native_resource.get("processor")

        if isinstance(processor, dict):
            return processor

        processors = cls._dictionary_list(
            native_resource.get("processors")
        )

        return processors[0] if processors else {}

    @staticmethod
    def _dictionary(value: object) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _dictionary_list(value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        return [
            item
            for item in value
            if isinstance(item, dict)
        ]

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
    def _maximum_bandwidth_mbps(
        adapters: list[dict[str, Any]],
    ) -> float | None:
        rates = [
            float(adapter["rate"]) / 1_000_000
            for adapter in adapters
            if (
                adapter.get("enabled", True)
                and adapter.get("management") is not True
                and adapter.get("rate") is not None
            )
        ]

        return max(rates) if rates else None

    @staticmethod
    def _gpu_models(
        devices: list[dict[str, Any]],
    ) -> str | None:
        if not devices:
            return None

        models = [
            str(
                device.get("model")
                or device.get("product_name")
                or "unknown"
            )
            for device in devices
        ]

        return ", ".join(models)

    @staticmethod
    def _optional_string(value: object) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return int(value) if value is not None else None

    @staticmethod
    def _location_for_site(site: str) -> str | None:
        locations = {
            "grenoble": "Grenoble, France",
            "lyon": "Lyon, France",
            "lille": "Lille, France",
            "nancy": "Nancy, France",
            "nantes": "Nantes, France",
            "rennes": "Rennes, France",
            "sophia": "Sophia Antipolis, France",
            "toulouse": "Toulouse, France",
        }
        locations = {
            "bordeaux": "Bordeaux, France",
            "grenoble": "Grenoble, France",
            "lille": "Lille, France",
            "louvain": "Louvain-la-Neuve, Belgium",
            "luxembourg": "Luxembourg, Luxembourg",
            "lyon": "Lyon, France",
            "nancy": "Nancy, France",
            "nantes": "Nantes, France",
            "rennes": "Rennes, France",
            "sophia": "Sophia Antipolis, France",
            "strasbourg": "Strasbourg, France",
            "toulouse": "Toulouse, France",
        }

        normalized_site = site.strip().casefold()
        return locations.get(site.casefold())