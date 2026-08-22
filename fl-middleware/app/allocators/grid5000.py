from app.allocators.base import ProviderAllocator
from app.models.resource import NormalizedResource
from app.clients.grid5000 import Grid5000Client
from app.models.provider import ProviderId

class Grid5000Allocator(ProviderAllocator):
    """Build Grid'5000 reservation actions."""
    """Reserve Grid'5000 resources."""

    def __init__(
        self,
        client: Grid5000Client | None = None,
    ) -> None:
        self._client = client

    async def reserve(
        self,
        resource: NormalizedResource,
        *,
        duration_minutes: int,
    ) -> dict[str, object]:
        if resource.provider != ProviderId.GRID5000:
            raise ValueError(
                "Grid5000Allocator received a "
                "non-Grid'5000 resource."
            )

        # Keep existing dry-run behavior when
        # no live client has been configured.
        if self._client is None:
            return {
                "provider": "grid5000",
                "resource_id": resource.id,
                "site": resource.site,
                "node": resource.name,
                "duration_minutes": duration_minutes,
                "status": "planned",
            }

        queue = resource.labels.get("queue")

        result = await self._client.create_job(
            site_id=resource.site,
            node_name=resource.name,
            duration_minutes=duration_minutes,
            queue=queue,
        )

        reservation_id = result.get("uid")
        state = result.get("state")

        return {
            "provider": "grid5000",
            "resource_id": resource.id,
            "site": resource.site,
            "node": resource.name,
            "duration_minutes": duration_minutes,
            "status": (
                str(state)
                if state is not None
                else "submitted"
            ),
            "reservation_id": (
                str(reservation_id)
                if reservation_id is not None
                else None
            ),
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
                "provider": "grid5000",
                "site": site,
                "reservation_id": reservation_id,
                "status": "planned",
            }

        job = await self._client.get_job(
            site_id=site,
            job_id=reservation_id,
        )

        state = str(
            job.get("state", "unknown")
        )

        assigned_nodes = job.get(
            "assigned_nodes",
            [],
        )

        if not isinstance(assigned_nodes, list):
            assigned_nodes = []

        connection = None

        if assigned_nodes:
            node = str(assigned_nodes[0])

            connection = {
                "node": node,
                "frontend": (
                    f"{site}.grid5000.fr"
                ),
                "recommended_command": (
                    f"OAR_JOB_ID={reservation_id} "
                    f"oarsh {node}"
                ),
                "ssh_command": (
                    f"ssh {node}"
                ),
            }

        return {
            "provider": "grid5000",
            "site": site,
            "reservation_id": reservation_id,
            "status": state,
            "assigned_resources": [
                str(node)
                for node in assigned_nodes
            ],
            "connection": connection,
            "native_data": job,
        }


    async def release(
        self,
        *,
        site: str,
        reservation_id: str,
    ) -> dict[str, object]:
        if self._client is None:
            return {
                "provider": "grid5000",
                "site": site,
                "reservation_id": reservation_id,
                "status": "planned-release",
            }

        await self._client.delete_job(
            site_id=site,
            job_id=reservation_id,
        )

        return {
            "provider": "grid5000",
            "site": site,
            "reservation_id": reservation_id,
            "status": "released",
        }
