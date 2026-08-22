from __future__ import annotations

import asyncio
import json
import os

from app.clients.iotlab import IoTLabClient


async def main() -> None:

    from dotenv import load_dotenv

    load_dotenv()
    username = os.environ.get(
        "IOTLAB_USERNAME"
    )
    password = os.environ.get(
        "IOTLAB_PASSWORD"
    )

    if not username or not password:
        raise RuntimeError(
            "Set IOTLAB_USERNAME and "
            "IOTLAB_PASSWORD before running "
            "this script."
        )

    client = IoTLabClient(
        base_url=os.environ.get(
            "IOTLAB_BASE_URL",
            "https://www.iot-lab.info/api",
        ),
        username=username,
        password=password,
    )

    response = await client.get_nodes()
    nodes = client.extract_items(response)

    print(f"Node count: {len(nodes)}")

    if not nodes:
        print("No nodes returned.")
        return

    print()
    print("First node keys:")
    print(sorted(nodes[0].keys()))

    print()
    print("First node:")
    print(
        json.dumps(
            nodes[0],
            indent=2,
            ensure_ascii=False,
        )
    )

    sites = sorted(
        {
            str(node["site"])
            for node in nodes
            if node.get("site")
        }
    )

    architectures = sorted(
        {
            str(node["archi"])
            for node in nodes
            if node.get("archi")
        }
    )

    states = sorted(
        {
            str(node["state"])
            for node in nodes
            if node.get("state")
        }
    )

    print()
    print(f"Sites ({len(sites)}):")
    print(sites)

    print()
    print(
        f"Architectures "
        f"({len(architectures)}):"
    )
    print(architectures)

    print()
    print(f"States ({len(states)}):")
    print(states)


if __name__ == "__main__":
    asyncio.run(main())