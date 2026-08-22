import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import os


HOST = "0.0.0.0"
PORT = 8081

RESULTS_DIR = Path(
    os.environ.get(
        "IOT_RESULTS_DIR",
        str(Path.home() / "fl-thesis" / "logs" / "iot_broker"),
    )
)

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class TaskState:
    task_id: str
    node_id: str
    payload: dict[str, Any]
    status: str = "pending"
    result: dict[str, Any] | None = None
    created_at: float = field(default_factory=time.time)
    claimed_at: float | None = None
    completed_at: float | None = None



TASKS: dict[str, TaskState] = {}
LOCK = threading.Lock()


def create_task(node_id: str, payload: dict[str, Any]) -> str:
    task_id = str(uuid.uuid4())

    task = TaskState(
        task_id=task_id,
        node_id=node_id,
        payload=payload,
    )

    with LOCK:
        TASKS[task_id] = task

    return task_id


def wait_for_result(
    task_id: str,
    timeout: float = 180.0,
    poll_interval: float = 0.25,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        with LOCK:
            task = TASKS.get(task_id)

            if task is None:
                raise KeyError(f"Unknown task: {task_id}")

            if task.status == "completed" and task.result is not None:
                return task.result

        time.sleep(poll_interval)

    raise TimeoutError(f"Timed out waiting for task {task_id}")


class BrokerHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        if not raw_body:
            return {}

        return json.loads(raw_body.decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")

        if parsed.path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "iot-task-broker",
                },
            )
            return

        # GET /tasks/next/<node_id>
        if len(parts) == 3 and parts[:2] == ["tasks", "next"]:
            node_id = parts[2]

            with LOCK:
                pending = next(
                    (
                        task
                        for task in TASKS.values()
                        if task.node_id == node_id
                        and task.status == "pending"
                    ),
                    None,
                )

                if pending is None:
                    self._send_json(204, {})
                    return

                pending.status = "running"
                pending.claimed_at = time.time()

                response = {
                    "task_id": pending.task_id,
                    **pending.payload,
                }

            self._send_json(200, response)
            return

        # GET /tasks/<task_id>
        if len(parts) == 2 and parts[0] == "tasks":
            task_id = parts[1]

            with LOCK:
                task = TASKS.get(task_id)

                if task is None:
                    self._send_json(
                        404,
                        {"error": "unknown_task"},
                    )
                    return

                response = {
                    "task_id": task.task_id,
                    "node_id": task.node_id,
                    "status": task.status,
                    "created_at": task.created_at,
                    "claimed_at": task.claimed_at,
                    "completed_at": task.completed_at,
                }

                if task.status == "completed":
                    response["result"] = task.result

            self._send_json(200, response)
            return


        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")

        # Temporary testing endpoint:
        # POST /tasks
        if parsed.path == "/tasks":
            payload = self._read_json()
            node_id = str(payload.pop("node_id"))

            task_id = create_task(node_id, payload)

            self._send_json(
                201,
                {
                    "task_id": task_id,
                    "status": "pending",
                },
            )
            return

        # POST /tasks/<task_id>/result
        if (
            len(parts) == 3
            and parts[0] == "tasks"
            and parts[2] == "result"
        ):
            task_id = parts[1]
            result = self._read_json()

            with LOCK:
                task = TASKS.get(task_id)

                if task is None:
                    self._send_json(
                        404,
                        {"error": "unknown_task"},
                    )
                    return

                if task.status == "completed":
                    self._send_json(
                        409,
                        {
                            "error": "task_already_completed",
                            "task_id": task_id,
                        },
                    )
                    return

                task.status = "completed"
                task.result = result
                task.completed_at = time.time()

            output_file = RESULTS_DIR / "results.jsonl"


            with output_file.open("a", encoding="utf-8") as file:
                file.write(
                    json.dumps(
                        {
                            "task_id": task_id,
                            "node_id": task.node_id,
                            "result": result,
                        }
                    )
                    + "\n"
                )

            record = {
                "task_id": task_id,
                "node_id": task.node_id,
                "command": task.payload.get("command"),
                "status": task.status,
                "created_at": task.created_at,
                "claimed_at": task.claimed_at,
                "completed_at": task.completed_at,
                "queue_wait_seconds": (
                    task.claimed_at - task.created_at
                    if task.claimed_at is not None
                    else None
                ),
                "execution_total_seconds": (
                    task.completed_at - task.claimed_at
                    if (
                        task.completed_at is not None
                        and task.claimed_at is not None
                    )
                    else None
                ),
                "broker_total_seconds": (
                    task.completed_at - task.created_at
                    if task.completed_at is not None
                    else None
                ),
                "request": task.payload,
                "result": result,
            }

            with output_file.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record) + "\n")


            self._send_json(
                200,
                {
                    "task_id": task_id,
                    "status": "completed",
                },
            )
            return

        self._send_json(404, {"error": "not_found"})

    def log_message(self, message_format: str, *args: Any) -> None:
        logging.info(
            "%s - %s",
            self.client_address[0],
            message_format % args,
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    server = ThreadingHTTPServer((HOST, PORT), BrokerHandler)

    logging.info("IoT task broker listening on %s:%d", HOST, PORT)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Stopping IoT task broker")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
