from app.models.allocation import (
    ResourceAllocation,
    ResourceRequirements,
)
from app.models.resource import NormalizedResource
from app.services.inventory import InventoryService

class ResourceMatchingService:
    """Match normalized resources against user requirements."""

    def __init__(
        self,
        inventory_service: InventoryService,
    ) -> None:
        self._inventory = inventory_service

    def allocate(
        self,
        requirements: ResourceRequirements,
    ) -> ResourceAllocation:

        candidates = self._inventory.list_resources(
            provider=requirements.provider,
            site=requirements.site,
            available=requirements.available,
            resource_type=(
                requirements.resource_type.value
                if requirements.resource_type
                else None
            ),
        )

        candidates = [
            resource
            for resource in candidates
            if self._matches(resource, requirements)
        ]

        candidates = self._rank_candidates(
            candidates,
            requirements,
        )

        selected = candidates[:requirements.count]

        if len(selected) >= requirements.count:
            status = "satisfied"
            message = None
        elif selected:
            status = "partial"
            message = (
                f"Requested {requirements.count} resources, "
                f"but only {len(selected)} matched."
            )
        else:
            status = "unsatisfied"
            message = "No resources matched the requirements."

        return ResourceAllocation(
            status=status,
            requested_count=requirements.count,
            matched_count=len(selected),
            resources=selected,
            message=message,
        )

    
    @staticmethod
    def _matches(
        resource: NormalizedResource,
        requirements: ResourceRequirements,
    ) -> bool:
        if requirements.architecture is not None:
            architecture = resource.hardware.architecture

            if architecture is None:
                return False

            if (
                architecture.casefold()
                != requirements.architecture.casefold()
            ):
                return False

        if requirements.native_resource_type is not None:
            native_resource_type = resource.native_resource_type

            if native_resource_type is None:
                return False

            if (
                native_resource_type.casefold()
                != requirements.native_resource_type.casefold()
            ):
                return False

        if requirements.min_cpu_cores is not None:
            cpu_cores = resource.hardware.cpu_cores

            if (
                cpu_cores is None
                or cpu_cores < requirements.min_cpu_cores
            ):
                return False

        if requirements.min_memory_mb is not None:
            memory_mb = resource.hardware.memory_mb

            if (
                memory_mb is None
                or memory_mb < requirements.min_memory_mb
            ):
                return False

        if requirements.min_gpu_count is not None:
            gpu_count = resource.hardware.gpu_count

            if (
                gpu_count is None
                or gpu_count < requirements.min_gpu_count
            ):
                return False

        if requirements.requires_ipv4 is not None:
            if (
                resource.network.public_ipv4
                is not requirements.requires_ipv4
            ):
                return False

        if requirements.requires_ipv6 is not None:
            if (
                resource.network.public_ipv6
                is not requirements.requires_ipv6
            ):
                return False

        if requirements.requires_outbound_http is not None:
            if (
                resource.network.outbound_http
                is not requirements.requires_outbound_http
            ):
                return False

        if requirements.python_version is not None:
            if (
                resource.runtime.python_version
                != requirements.python_version
            ):
                return False

        if requirements.capabilities:
            resource_capabilities = {
                capability.casefold()
                for capability in resource.capabilities
            }

            required_capabilities = {
                capability.casefold()
                for capability in requirements.capabilities
            }

            if not required_capabilities.issubset(
                resource_capabilities
            ):
                return False

        return True

    def _rank_candidates(
        self,
        candidates: list[NormalizedResource],
        requirements: ResourceRequirements,
    ) -> list[NormalizedResource]:
        """
        Rank matching resources using a simple best-fit policy.

        Resources that satisfy the requested constraints with
        the least excess capacity are preferred.
        """

        def score(
            resource: NormalizedResource,
        ) -> tuple[int, int, int, str]:

            cpu_excess = 0
            memory_excess = 0
            gpu_excess = 0

            if requirements.min_cpu_cores is not None:
                cpu_cores = resource.hardware.cpu_cores

                if cpu_cores is not None:
                    cpu_excess = (
                        cpu_cores
                        - requirements.min_cpu_cores
                    )

            if requirements.min_memory_mb is not None:
                memory_mb = resource.hardware.memory_mb

                if memory_mb is not None:
                    memory_excess = (
                        memory_mb
                        - requirements.min_memory_mb
                    )

            if requirements.min_gpu_count is not None:
                gpu_count = resource.hardware.gpu_count

                if gpu_count is not None:
                    gpu_excess = (
                        gpu_count
                        - requirements.min_gpu_count
                    )

            return (
                cpu_excess,
                memory_excess,
                gpu_excess,
                resource.id,
            )

        return sorted(
            candidates,
            key=score,
        )