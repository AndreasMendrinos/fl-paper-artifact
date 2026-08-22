import asyncio

from app.clients.chameleon import ChameleonClient


async def main() -> None:
    client = ChameleonClient(
        base_url="https://api.chameleoncloud.org",
        timeout_seconds=30,
    )

    sites_response = await client.get_sites()

    print("Sites:", sites_response.get("total"))
    print("Version:", sites_response.get("version"))

    for site in sites_response.get("items", []):
        print(
            site.get("uid"),
            "-",
            site.get("name"),
            "-",
            site.get("site_class"),
        )

    tacc_response = await client.discover_site(
        site_id="tacc",
        cluster_id="chameleon",
    )

    print()
    print("TACC version:", tacc_response.get("version"))
    print("TACC nodes:", len(tacc_response.get("items", [])))

    if tacc_response.get("items"):
        first_node = tacc_response["items"][0]

        print("First node UID:", first_node.get("uid"))
        print("First node keys:", sorted(first_node.keys()))

    baremetal_sites = await client.discover_site_ids(
        allowed_site_classes={"baremetal"}
    )

    print()
    print("Automatically selected bare-metal sites:")
    for site_id in baremetal_sites:
        print("-", site_id)

    nodes = await client.get_nodes(
        site_id="tacc",
        cluster_id="chameleon",
    )

    node_items = client.extract_items(nodes)

    distinct_types = sorted(
        {
            str(node["type"])
            for node in node_items
            if node.get("type") is not None
        }
    )

    distinct_node_types = sorted(
        {
            str(node["node_type"])
            for node in node_items
            if node.get("node_type") is not None
        }
    )

    distinct_job_types = sorted(
        {
            str(job_type)
            for node in node_items
            for job_type in (
                node.get("supported_job_types") or []
            )
        }
    )

    print()
    print("Distinct type values:")
    for value in distinct_types:
        print("-", value)

    print()
    print("Distinct node_type values:")
    for value in distinct_node_types:
        print("-", value)

    print()
    print("Distinct supported_job_types:")
    for value in distinct_job_types:
        print("-", value)

    print()
    print("Clusters by site:")

    for site_id in baremetal_sites:
        try:
            cluster_response = await client.get_clusters(
                site_id
            )

            cluster_items = client.extract_items(
                cluster_response
            )

            print()
            print(f"Site: {site_id}")
            print(f"Cluster count: {len(cluster_items)}")

            if cluster_items:
                print(
                    "First cluster keys:",
                    sorted(cluster_items[0].keys()),
                )

            cluster_ids = await client.discover_cluster_ids(
                site_id=site_id
            )

            print("Cluster IDs:", cluster_ids)

        except Exception as exc:
            print(f"Site {site_id}: ERROR: {exc}")


if __name__ == "__main__":
    asyncio.run(main())