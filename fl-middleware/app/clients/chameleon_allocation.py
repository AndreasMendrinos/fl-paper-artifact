from __future__ import annotations

import openstack
from datetime import timedelta
import time

from chi import network, server
from chi import context, lease

class ChameleonAllocationClient:
    """Authenticated client for Chameleon allocation operations."""

    def __init__(
        self,
        *,
        auth_url: str,
        application_credential_id: str,
        application_credential_secret: str,
        region_name: str,
        interface: str = "public",
    ) -> None:

        self._auth_url = auth_url
        self._application_credential_id = (
            application_credential_id
        )
        self._application_credential_secret = (
            application_credential_secret
        )
        self._region_name = region_name
        self._interface = interface

        self._connection = openstack.connection.Connection(
            auth_type="v3applicationcredential",
            auth_url=auth_url,
            application_credential_id=(
                application_credential_id
            ),
            application_credential_secret=(
                application_credential_secret
            ),
            region_name=region_name,
            interface=interface,
        )

    def authorize(self) -> str:
        return self._connection.authorize()
    
    def _configure_chi(self) -> None:
        context.reset()

        context.set(
            "auth_type",
            "v3applicationcredential",
        )
        context.set(
            "auth_url",
            self._auth_url,
        )
        context.set(
            "application_credential_id",
            self._application_credential_id,
        )
        context.set(
            "application_credential_secret",
            self._application_credential_secret,
        )
        context.set(
            "region_name",
            self._region_name,
        )
        #context.use_site(self._region_name)

    def create_lease(
        self,
        *,
        node_name: str | None,
        node_type: str | None,
        duration_minutes: int,
    ) -> dict[str, object]:
        if duration_minutes < 1:
            raise ValueError(
                "duration_minutes must be >= 1."
            )

        self._configure_chi()

        reservation = lease.Lease(
            name="fl-middleware-allocation",
            duration=timedelta(
                minutes=duration_minutes
            ),
        )
        '''
        reservation.add_node_reservation(
            node_name=node_name,
            amount=1,
        )
        '''
        if node_name is not None:
            reservation.add_node_reservation(
                node_name=node_name,
                amount=1,
            )
        elif node_type is not None:
            reservation.add_node_reservation(
                node_type=node_type,
                amount=1,
            )
        else:
            reservation.add_node_reservation(
                amount=1,
            )

        reservation.submit(
            wait_for_active=False,
        )

        return {
            "id": reservation.id,
            "status": reservation.status,
            "name": reservation.name,
            "node_reservations": (
                reservation.node_reservations
            ),
            "start_date": reservation.start_date,
            "end_date": reservation.end_date,
        }

    def get_lease(
        self,
        lease_id: str,
    ) -> dict[str, object]:
        self._configure_chi()

        item = lease.get_lease(lease_id)

        return {
            "id": item.id,
            "name": item.name,
            "status": item.status,
            "node_reservations": (
                item.node_reservations
            ),
            "start_date": item.start_date,
            "end_date": item.end_date,
        }
    
    def delete_lease(
        self,
        lease_id: str,
    ) -> None:
        self._configure_chi()

        item = lease.get_lease(lease_id)
        item.delete()

    def wait_for_lease_active(
        self,
        lease_id: str,
        *,
        timeout_seconds: int = 300,
        poll_seconds: int = 5,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            result = self.get_lease(lease_id)

            status = str(
                result.get("status", "")
            ).upper()

            if status == "ACTIVE":
                return result

            if status in {
                "ERROR",
                "TERMINATED",
                "DELETED",
            }:
                raise RuntimeError(
                    "Chameleon lease entered "
                    f"terminal state: {status}"
                )

            time.sleep(poll_seconds)

        raise TimeoutError(
            "Timed out waiting for Chameleon "
            "lease to become ACTIVE."
        )

    def create_instance(
        self,
        *,
        reservation_id: str,
        server_name: str = "fl-middleware-node",
        key_name: str,
        image_name: str = "CC-Ubuntu22.04",
        network_name: str = "sharednet1",
    ) -> dict[str, Any]:
        self._configure_chi()

        instance = server.create_server(
            server_name=server_name,
            reservation_id=reservation_id,
            key_name=key_name,
            image_name=image_name,
            flavor_name="baremetal",
            network_name=network_name,
        )

        return {
            "id": str(instance.id),
            "name": str(instance.name),
            "status": str(instance.status),
        }

    def wait_for_instance_active(
        self,
        instance_id: str,
        *,
        timeout_seconds: int = 1200,
    ) -> dict[str, Any]:
        self._configure_chi()

        server.wait_for_active(
            instance_id,
            timeout=timeout_seconds,
        )

        instance = server.show_server(
            instance_id
        )

        return {
            "id": str(instance.id),
            "name": str(instance.name),
            "status": str(instance.status),
        }

    def allocate_floating_ip(
        self,
    ) -> dict[str, Any]:
        self._configure_chi()

        floating_ip, created = (
            network.get_or_create_floating_ip()
        )

        return {
            "address": str(
                floating_ip["floating_ip_address"]
            ),
            "created": bool(created),
        }

    def associate_floating_ip(
        self,
        *,
        instance_id: str,
        floating_ip: str,
    ) -> None:
        self._configure_chi()

        server.associate_floating_ip(
            instance_id,
            floating_ip,
        )

    def wait_for_ssh(
        self,
        *,
        host: str,
        timeout_seconds: int = 1200,
    ) -> None:
        self._configure_chi()

        server.wait_for_tcp(
            host,
            22,
            timeout=timeout_seconds,
        )

    def delete_instance(
        self,
        instance_id: str,
    ) -> None:
        self._configure_chi()

        server.delete_server(
            instance_id
        )


    def detach_floating_ip(
        self,
        *,
        instance_id: str,
        floating_ip: str,
    ) -> None:
        self._configure_chi()

        server.detach_floating_ip(
            instance_id,
            floating_ip,
        )


    def deallocate_floating_ip(
        self,
        floating_ip: str,
    ) -> None:
        self._configure_chi()

        network.deallocate_floating_ip(
            floating_ip
        )