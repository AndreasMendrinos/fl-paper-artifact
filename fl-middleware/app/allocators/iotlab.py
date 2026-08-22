from app.allocators.base import ProviderAllocator
from app.models.resource import NormalizedResource
from app.clients.iotlab import IoTLabClient
from app.models.provider import ProviderId




class IoTLabAllocator(ProviderAllocator):
    """Build IoT-LAB experiment reservation actions."""
    def __init__(
        self,
        client: IoTLabClient | None = None,
    ) -> None:
        self._client = client

    async def reserve(
        self,
        resource: NormalizedResource,
        *,
        duration_minutes: int,
    ) -> dict[str, object]:
        if resource.provider != ProviderId.IOTLAB:
            raise ValueError(
                "IoTLabAllocator received a non-IoT-LAB resource."
            )

        if self._client is None:
            return {
                "provider": "iotlab",
                "resource_id": resource.id,
                "site": resource.site,
                "node": resource.name,
                "duration_minutes": duration_minutes,
                "status": "planned",
                "reservation_type": "experiment",
            }

        architecture = resource.labels.get("architecture")

        if not architecture:
            raise ValueError(
                "IoT-LAB resource does not expose architecture metadata."
            )

        result = await self._client.create_experiment(
            site=resource.site,
            architecture=architecture,
            count=1,
            duration_minutes=duration_minutes,
        )

        experiment_id = result.get("id")

        return {
            "provider": "iotlab",
            "resource_id": resource.id,
            "site": resource.site,
            "node": resource.name,
            "duration_minutes": duration_minutes,
            "status": "submitted",
            "reservation_id": (
                str(experiment_id)
                if experiment_id is not None
                else None
            ),
            "reservation_type": "experiment",
            "native_data": result,
        }

    async def get_reservation(
        self,
        *,
        site: str,
        reservation_id: str,
    ) -> dict[str, object]:
        if self._client is None:
            return {
                "provider": "iotlab",
                "site": site,
                "reservation_id": reservation_id,
                "status": "planned",
            }

        experiment = await self._client.get_experiment(
            reservation_id
        )

        state = str(
            experiment.get("state", "unknown")
        )

        assigned_resources: list[str] = []

        if state.lower() in {
            "running",
            "launching",
            "waiting",
        }:
            nodes_payload = (
                await self._client.get_experiment_nodes(
                    reservation_id
                )
            )

            for node in self._client.extract_items(
                nodes_payload
            ):
                address = node.get("network_address")

                if address:
                    assigned_resources.append(
                        str(address)
                    )

        connection = None

        if assigned_resources:
            connection = {
                "frontend": (
                    f"{site}.iot-lab.info"
                ),
                "nodes": assigned_resources,
            }

        return {
            "provider": "iotlab",
            "site": site,
            "reservation_id": reservation_id,
            "status": state,
            "assigned_resources": assigned_resources,
            "connection": connection,
            "native_data": experiment,
        }

    async def release(
        self,
        *,
        site: str,
        reservation_id: str,
    ) -> dict[str, object]:
        if self._client is None:
            return {
                "provider": "iotlab",
                "site": site,
                "reservation_id": reservation_id,
                "status": "planned-release",
            }

        result = await self._client.delete_experiment(
            reservation_id
        )

        return {
            "provider": "iotlab",
            "site": site,
            "reservation_id": reservation_id,
            "status": "released",
            "native_data": result,
        }

