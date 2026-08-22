import json
import time
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class BrokerError(RuntimeError):
    """Raised when communication with the IoT broker fails."""


def _request_json(
    url: str,
    method: str = "GET",
    payload: Dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    data = None
    headers: Dict[str, str] = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()

            if not body:
                return {}

            return json.loads(body.decode("utf-8"))

    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise BrokerError(
            f"Broker returned HTTP {exc.code}: {body}"
        ) from exc

    except URLError as exc:
        raise BrokerError(
            f"Could not contact broker at {url}: {exc}"
        ) from exc


def submit_task(
    broker_url: str,
    node_id: str,
    payload: Dict[str, Any],
) -> str:
    request_payload = {
        "node_id": node_id,
        **payload,
    }

    response = _request_json(
        f"{broker_url}/tasks",
        method="POST",
        payload=request_payload,
    )

    task_id = response.get("task_id")

    if not task_id:
        raise BrokerError(
            f"Broker did not return task_id: {response}"
        )

    return str(task_id)


def wait_for_task_result(
    broker_url: str,
    task_id: str,
    timeout: float = 180.0,
    poll_interval: float = 0.5,
) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        response = _request_json(
            f"{broker_url}/tasks/{task_id}"
        )

        status = response.get("status")

        if status == "completed":
            result = response.get("result")

            if not isinstance(result, dict):
                raise BrokerError(
                    f"Task {task_id} completed without result"
                )

            if result.get("status") != "success":
                raise BrokerError(
                    f"A8 task failed: {result}"
                )

            return result

        if status not in {"pending", "running"}:
            raise BrokerError(
                f"Unexpected task status: {response}"
            )

        time.sleep(poll_interval)

    raise TimeoutError(
        f"Timed out waiting for A8 task {task_id}"
    )


def run_remote_training(
    broker_url: str,
    node_id: str,
    weights: list[float],
    bias: float,
    learning_rate: float,
    local_epochs: int,
) -> Dict[str, Any]:
    task_id = submit_task(
        broker_url=broker_url,
        node_id=node_id,
        payload={
            "command": "train",
            "weights": weights,
            "bias": bias,
            "learning_rate": learning_rate,
            "local_epochs": local_epochs,
        },
    )

    return wait_for_task_result(
        broker_url=broker_url,
        task_id=task_id,
    )

def run_remote_evaluation(
    broker_url: str,
    node_id: str,
    weights: list[float],
    bias: float,
) -> Dict[str, Any]:
    task_id = submit_task(
        broker_url=broker_url,
        node_id=node_id,
        payload={
            "command": "evaluate",
            "weights": weights,
            "bias": bias,
        },
    )

    return wait_for_task_result(
        broker_url=broker_url,
        task_id=task_id,
    )
