GRID5000_MOCK_RESPONSE: dict[str, object] = {
    "site_uid": "grenoble",
    "cluster_uid": "dahu",
    "items": [
        {
            "uid": "dahu-1",
            "architecture": {
                "platform_type": "x86_64",
                "smt_size": 2,
            },
            "processor": {
                "model": "Intel Xeon Gold 6130",
                "nb_cores": 16,
            },
            "nodeset": "dahu",
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
                    "network_address": "dahu-1.grenoble.grid5000.fr",
                    "enabled": True,
                    "management": False,
                }
            ],
            "supported_job_types": {
                "deploy": True,
                "besteffort": True,
            },
            "gpu_devices": [],
        }
    ],
}