CHAMELEON_MOCK_RESPONSE: dict[str, object] = {
    "version": "mock-chameleon-v1",
    "site": {
        "uid": "tacc",
        "name": "CHI@TACC",
        "location": "Austin, Texas, USA",
        "site_class": "baremetal",
    },
    "items": [
        {
            "uid": "mock-node-tacc-001",
            "status": None,
            "node_type": "compute",
            "architecture": {
                "platform_type": "x86_64",
                "smt_size": 2,
            },
            "processors": [
                {
                    "model": "Intel Xeon Gold",
                    "nb_cores": 16,
                    "nb_threads": 32,
                }
            ],
            "main_memory": {
                "ram_size": 137438953472,
            },
            "storage_devices": [
                {
                    "size": 480000000000,
                    "storage": "SSD",
                }
            ],
            "network_adapters": [
                {
                    "rate": 10000000000,
                    "interface": "Ethernet",
                }
            ],
            "gpu_devices": [],
        }
    ],
}