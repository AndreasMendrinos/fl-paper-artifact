from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from app.models.resource import NormalizedResource


NativeResource = TypeVar("NativeResource")


class ResourceMapper(ABC, Generic[NativeResource]):
    """Convert provider-specific data into the common resource model."""

    @abstractmethod
    def map_resource(
        self,
        native_resource: NativeResource,
        *,
        context: dict[str, Any] | None = None,
    ) -> NormalizedResource:
        """Map one native provider resource."""

    def map_resources(
        self,
        native_resources: list[NativeResource],
        *,
        context: dict[str, Any] | None = None,
    ) -> list[NormalizedResource]:
        """Map a collection of native provider resources."""

        return [
            self.map_resource(
                native_resource,
                context=context,
            )
            for native_resource in native_resources
        ]