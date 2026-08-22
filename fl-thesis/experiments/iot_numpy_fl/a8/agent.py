import json
import resource
import socket
import time
import urllib.error
import urllib.request

import numpy as np

from typing import Dict, Optional, Tuple
import hashlib
import os

BROKER_URL = os.environ.get(
    "BROKER_URL",
    "http://127.0.0.1:8081",
)


NODE_ID = socket.gethostname()

def stable_node_seed(node_id):
    """Return a deterministic seed for each IoT-LAB node."""
    digest = hashlib.sha256(
        node_id.encode("utf-8")
    ).hexdigest()

    return int(digest[:8], 16)

POLL_INTERVAL_SECONDS = 2.0

def create_local_dataset(split):
    """Create a deterministic node-specific local dataset."""

    base_seed = stable_node_seed(NODE_ID)

    if split == "train":
        seed = base_seed
        num_samples = 1000
    elif split == "evaluate":
        seed = base_seed + 100000
        num_samples = 300
    else:
        raise ValueError(
            "Unsupported dataset split: {}".format(split)
        )

    rng = np.random.RandomState(seed)

    # Διαφορετική περιοχή εισόδων ανά node.
    node_variant = base_seed % 3

    if node_variant == 0:
        x_low = 0.0
        x_high = 0.65
    elif node_variant == 1:
        x_low = 0.35
        x_high = 1.0
    else:
        x_low = 0.15
        x_high = 0.85

    x = rng.uniform(
        low=x_low,
        high=x_high,
        size=num_samples,
    ).astype(np.float32)

    # Μικρός, node-specific θόρυβος.
    noise_std = 0.03 + 0.01 * node_variant

    noise = rng.normal(
        loc=0.0,
        scale=noise_std,
        size=num_samples,
    ).astype(np.float32)

    # Κοινό underlying global πρόβλημα.
    y = 2.0 * x + 1.0 + noise

    metadata = {
        "dataset_seed": int(seed),
        "dataset_split": split,
        "num_samples": int(num_samples),
        "x_min": float(x.min()),
        "x_max": float(x.max()),
        "x_mean": float(x.mean()),
        "x_std": float(x.std()),
        "noise_std": float(noise_std),
        "node_variant": int(node_variant),
    }

    return x, y, metadata


def request_json(
    url: str,
    method: str = "GET",
    payload: Optional[Dict] = None,
    timeout: float = 15.0,
) -> Tuple[int, Dict]:
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            body = response.read()

            if not body:
                return response.status, {}

            return response.status, json.loads(body.decode("utf-8"))

    except urllib.error.HTTPError as exc:
        if exc.code == 204:
            return 204, {}

        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"HTTP {exc.code} from {url}: {body}"
        ) from exc


def train_task(task):
    weights = np.asarray(
        task["weights"],
        dtype=np.float32,
    )

    bias = float(task["bias"])

    learning_rate = float(
        task.get("learning_rate", 0.01)
    )

    local_epochs = int(
        task.get("local_epochs", 5)
    )

    x, y, dataset_metadata = create_local_dataset(
        split="train"
    )

    start = time.time()

    initial_predictions = x * weights[0] + bias
    initial_loss = float(
        np.mean((initial_predictions - y) ** 2)
    )

    for _ in range(local_epochs):
        predictions = x * weights[0] + bias
        errors = predictions - y

        gradient_weight = float(
            2.0 * np.mean(errors * x)
        )

        gradient_bias = float(
            2.0 * np.mean(errors)
        )

        if not np.isfinite(gradient_weight):
            raise ValueError(
                "Non-finite weight gradient: {}".format(
                    gradient_weight
                )
            )

        if not np.isfinite(gradient_bias):
            raise ValueError(
                "Non-finite bias gradient: {}".format(
                    gradient_bias
                )
            )

        weights[0] -= learning_rate * gradient_weight
        bias -= learning_rate * gradient_bias

    predictions = x * weights[0] + bias

    final_loss = float(
        np.mean((predictions - y) ** 2)
    )

    if not np.all(np.isfinite(weights)):
        raise ValueError(
            "Training produced non-finite weights"
        )

    if not np.isfinite(bias):
        raise ValueError(
            "Training produced non-finite bias"
        )

    if not np.isfinite(final_loss):
        raise ValueError(
            "Training produced non-finite loss"
        )

    elapsed = time.time() - start

    usage = resource.getrusage(
        resource.RUSAGE_SELF
    )

    return {
        "node_id": NODE_ID,
        "weights": weights.tolist(),
        "bias": float(bias),
        "num_examples": int(len(x)),
        "initial_loss": initial_loss,
        "loss": final_loss,
        "loss_improvement": initial_loss - final_loss,
        "training_time_seconds": elapsed,
        "max_rss_kb": int(usage.ru_maxrss),
        "numpy_version": np.__version__,
        "dataset": dataset_metadata,
    }

def evaluate_task(task):
    weights = np.asarray(
        task["weights"],
        dtype=np.float32,
    )

    bias = float(task["bias"])

    x, y, dataset_metadata = create_local_dataset(
        split="evaluate"
    )

    start = time.time()

    predictions = x * weights[0] + bias

    loss = float(
        np.mean((predictions - y) ** 2)
    )

    elapsed = time.time() - start

    usage = resource.getrusage(
        resource.RUSAGE_SELF
    )

    if not np.isfinite(loss):
        raise ValueError(
            "Evaluation produced non-finite loss: {}".format(
                loss
            )
        )

    return {
        "node_id": NODE_ID,
        "num_examples": int(len(x)),
        "loss": loss,
        "evaluation_time_seconds": elapsed,
        "max_rss_kb": int(usage.ru_maxrss),
        "numpy_version": np.__version__,
        "dataset": dataset_metadata,
    }


'''
def evaluate_task(task):
    weights = np.asarray(task["weights"], dtype=np.float32)
    bias = float(task["bias"])

    x = np.linspace(
        0.0,
        1.0,
        1000,
        dtype=np.float32,
    )
    y = 2.0 * x + 1.0

    start = time.time()

    predictions = x * weights[0] + bias
    loss = float(np.mean((predictions - y) ** 2))

    elapsed = time.time() - start
    usage = resource.getrusage(resource.RUSAGE_SELF)

    return {
        "node_id": NODE_ID,
        "num_examples": int(len(x)),
        "loss": loss,
        "evaluation_time_seconds": elapsed,
        "max_rss_kb": int(usage.ru_maxrss),
        "numpy_version": np.__version__,
    }
'''

def process_task(task: dict) -> dict:
    command = task.get("command")

    if command == "train":
        return train_task(task)

    if command == "evaluate":
        return evaluate_task(task)


    raise ValueError(f"Unsupported command: {command}")


def main() -> None:
    print(f"Starting IoT agent for node {NODE_ID}")
    print(f"Broker: {BROKER_URL}")

    while True:
        try:
            status, task = request_json(
                f"{BROKER_URL}/tasks/next/{NODE_ID}",
            )

            if status == 204:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            task_id = task["task_id"]

            print(f"Received task {task_id}")

            try:
                result = process_task(task)
                result["status"] = "success"
            except Exception as exc:
                result = {
                    "node_id": NODE_ID,
                    "status": "error",
                    "error": repr(exc),
                }

            request_json(
                f"{BROKER_URL}/tasks/{task_id}/result",
                method="POST",
                payload=result,
            )

            print(f"Submitted result for task {task_id}")

            try:
                request_json(
                    "{}/tasks/{}/result".format(
                        BROKER_URL,
                        task_id,
                    ),
                    method="POST",
                    payload=result,
                )

                print(
                    "Submitted result for task {}".format(task_id),
                    flush=True,
                )

            except RuntimeError as exc:
                if "HTTP 409" in str(exc):
                    print(
                        "Result already accepted for task {}".format(
                            task_id
                        ),
                        flush=True,
                    )
                else:
                    raise

        except Exception as exc:
            print(f"Agent error: {exc!r}")
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
