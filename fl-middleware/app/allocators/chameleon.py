from app.allocators.base import ProviderAllocator
from app.models.resource import NormalizedResource
from app.clients.chameleon_allocation import (
    ChameleonAllocationClient,
)
from app.models.provider import ProviderId
from chi.exception import ResourceError

class ChameleonAllocator(ProviderAllocator):
    """Build Chameleon reservation actions."""
    def __init__(
        self,
        client: ChameleonAllocationClient | None = None,
        *,
        key_name: str | None = None,
        image_name: str = "CC-Ubuntu22.04",
        network_name: str = "sharednet1",
        ssh_username: str = "cc",
    ) -> None:
        self._client = client

        self._key_name = key_name
        self._image_name = image_name
        self._network_name = network_name
        self._ssh_username = ssh_username

        self._deployments: dict[
            str,
            dict[str, object],
        ] = {}

    async def reserve(
        self,
        resource: NormalizedResource,
        *,
        duration_minutes: int,
    ) -> dict[str, object]:
        if resource.provider != ProviderId.CHAMELEON:
            raise ValueError(
                "ChameleonAllocator received a "
                "non-Chameleon resource."
            )

        if self._client is None:
            return {
                "provider": "chameleon",
                "resource_id": resource.id,
                "site": resource.site,
                "node": resource.name,
                "duration_minutes": duration_minutes,
                "status": "planned",
                "reservation_type": "lease",
            }
        
        native_data = resource.source.native_data

        if not isinstance(native_data, dict):
            raise ValueError(
                "Chameleon resource does not contain "
                "native reservation metadata."
        )

        node_name = native_data.get("node_name")
        node_type = resource.native_resource_type

        fallback_used = False

        if node_type is None:
            raise ValueError(
                "Chameleon resource does not expose "
                "a reservable node type."
            )

        result = self._client.create_lease(
            node_name=None,
            node_type=str(node_type),
            duration_minutes=duration_minutes,
        )
        print("CHAMELEON: lease created", flush=True)
        lease_id = str(result["id"])

        lease = self._client.wait_for_lease_active(
            lease_id,
        )
        print("CHAMELEON: lease ACTIVE", flush=True)
        node_reservations = lease.get(
            "node_reservations",
            [],
        )

        if not node_reservations:
            raise RuntimeError(
                "Chameleon lease became ACTIVE "
                "without a node reservation."
            )

        node_reservation_id = str(
            node_reservations[0]["id"]
        )

        if not self._key_name:
            raise RuntimeError(
                "No Chameleon SSH key name "
                "has been configured."
            )

        instance = self._client.create_instance(
            reservation_id=node_reservation_id,
            server_name="fl-middleware-node",
            key_name=self._key_name,
            image_name=self._image_name,
            network_name=self._network_name,
        )
        print("CHAMELEON: instance created", flush=True)
        instance_id = str(
            instance["id"]
        )

        instance = (
            self._client.wait_for_instance_active(
                instance_id,
            )
        )
        print("CHAMELEON: instance ACTIVE", flush=True)
        floating = (
            self._client.allocate_floating_ip()
        )

        floating_ip = str(
            floating["address"]
        )

        floating_ip_created = bool(
            floating["created"]
        )

        self._client.associate_floating_ip(
            instance_id=instance_id,
            floating_ip=floating_ip,
        )

        self._client.wait_for_ssh(
            host=floating_ip,
        )
        print(
            f"CHAMELEON: SSH ready at {floating_ip}",
            flush=True,
        )
        deployment = {
            "lease_id": lease_id,
            "node_reservation_id": (
                node_reservation_id
            ),
            "instance_id": instance_id,
            "floating_ip": floating_ip,
            "floating_ip_created": (
                floating_ip_created
            ),
            "ssh_username": self._ssh_username,
        }

        self._deployments[
            lease_id
        ] = deployment

        return {
            "provider": "chameleon",
            "resource_id": resource.id,
            "site": resource.site,
            "node": resource.name,
            "duration_minutes": duration_minutes,

            "status": "ready",

            "reservation_id": lease_id,
            "reservation_type": "lease",

            "fallback_used": fallback_used,
            "requested_node_name": node_name,
            "requested_node_type": node_type,

            "connection": {
                "protocol": "ssh",
                "host": floating_ip,
                "port": 22,
                "username": self._ssh_username,
            },

            "deployment": deployment,

            "native_data": {
                "lease": lease,
                "instance": instance,
            },
        }
        


    async def get_reservation(
        self,
        *,
        site: str,
        reservation_id: str,
    ) -> dict[str, object]:
        if self._client is None:
            return {
                "provider": "chameleon",
                "site": site,
                "reservation_id": reservation_id,
                "status": "planned",
            }

        result = self._client.get_lease(
            reservation_id
        )

        deployment = self._deployments.get(
            reservation_id
        )

        assigned_resources: list[str] = []
        connection = None

        if deployment is not None:
            instance_id = deployment.get(
                "instance_id"
            )
            floating_ip = deployment.get(
                "floating_ip"
            )

            if instance_id:
                assigned_resources.append(
                    str(instance_id)
                )

            if floating_ip:
                connection = {
                    "protocol": "ssh",
                    "host": str(floating_ip),
                    "port": 22,
                    "username": self._ssh_username,
                }

        return {
            "provider": "chameleon",
            "site": site,
            "reservation_id": reservation_id,
            "status": (
                "ready"
                if deployment is not None
                else str(
                    result.get(
                        "status",
                        "unknown",
                    )
                )
            ),
            "assigned_resources": assigned_resources,
            "connection": connection,
            "deployment": deployment,
            "native_data": result,
        }

    async def release(
        self,
        *,
        site: str,
        reservation_id: str,
    ) -> dict[str, object]:
        if self._client is None:
            return {
                "provider": "chameleon",
                "site": site,
                "reservation_id": reservation_id,
                "status": "planned-release",
            }

        deployment = self._deployments.get(
            reservation_id
        )

        cleanup_errors: list[str] = []

        if deployment is not None:
            instance_id = deployment.get(
                "instance_id"
            )

            floating_ip = deployment.get(
                "floating_ip"
            )

            floating_ip_created = bool(
                deployment.get(
                    "floating_ip_created",
                    False,
                )
            )

            if (
                instance_id is not None
                and floating_ip is not None
            ):
                try:
                    self._client.detach_floating_ip(
                        instance_id=str(instance_id),
                        floating_ip=str(floating_ip),
                    )
                except Exception as exc:
                    cleanup_errors.append(
                        f"floating-ip detach: {exc}"
                    )

            if instance_id is not None:
                try:
                    self._client.delete_instance(
                        str(instance_id)
                    )
                except Exception as exc:
                    cleanup_errors.append(
                        f"instance delete: {exc}"
                    )

            if (
                floating_ip is not None
                and floating_ip_created
            ):
                try:
                    self._client.deallocate_floating_ip(
                        str(floating_ip)
                    )
                except Exception as exc:
                    cleanup_errors.append(
                        f"floating-ip release: {exc}"
                    )
        try:
            self._client.delete_lease(
                reservation_id
            )
        except Exception as exc:
            cleanup_errors.append(
                f"lease delete: {exc}"
            )

        return {
            "provider": "chameleon",
            "site": site,
            "reservation_id": reservation_id,
            "status": (
                "released"
                if not cleanup_errors
                else "released-with-errors"
            ),
            "cleanup_errors": cleanup_errors,
        }
