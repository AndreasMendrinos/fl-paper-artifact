import numpy as np

from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

from iot_fl.broker_client import (
    run_remote_evaluation,
    run_remote_training,
)

app = ClientApp()


def extract_parameters(message: Message) -> tuple[float, float]:
    arrays = message.content["arrays"].to_numpy_ndarrays()

    if len(arrays) != 2:
        raise ValueError(
            f"Expected two model arrays, received {len(arrays)}"
        )

    weight = float(arrays[0].reshape(-1)[0])
    bias = float(arrays[1].reshape(-1)[0])

    return weight, bias


@app.train()
def train(message: Message, context: Context) -> Message:
    global_weight, global_bias = extract_parameters(message)

    config = message.content["config"]

    learning_rate = float(
        config.get("learning-rate", 0.01)
    )
    local_epochs = int(
        config.get("local-epochs", 5)
    )

    broker_url = str(
        context.node_config.get(
            "broker-url",
            "http://127.0.0.1:8081",
        )
    )
    iot_node_id = str(
        context.node_config.get(
            "iot-node-id",
            "node-a8-103",
        )
    )

    result = run_remote_training(
        broker_url=broker_url,
        node_id=iot_node_id,
        weights=[global_weight],
        bias=global_bias,
        learning_rate=learning_rate,
        local_epochs=local_epochs,
    )

    updated_arrays = ArrayRecord(
        [
            np.asarray(
                result["weights"],
                dtype=np.float32,
            ),
            np.asarray(
                [result["bias"]],
                dtype=np.float32,
            ),
        ]
    )

    # MetricRecord δέχεται αριθμητικές τιμές, όχι strings.
    metrics = MetricRecord(
        {
            "num-examples": int(result["num_examples"]),
            "train-loss": float(result["loss"]),
            "training-time-seconds": float(
                result["training_time_seconds"]
            ),
            "max-rss-kb": int(result["max_rss_kb"]),
            "is-iot-proxy": 1,
        }
    )

    return Message(
        content=RecordDict(
            {
                "arrays": updated_arrays,
                "metrics": metrics,
            }
        ),
        reply_to=message,
    )


@app.evaluate()
def evaluate(message: Message, context: Context) -> Message:
    weight, bias = extract_parameters(message)

    broker_url = str(
        context.node_config.get(
            "broker-url",
            "http://127.0.0.1:8081",
        )
    )
    iot_node_id = str(
        context.node_config.get(
            "iot-node-id",
            "node-a8-103",
        )
    )

    result = run_remote_evaluation(
        broker_url=broker_url,
        node_id=iot_node_id,
        weights=[weight],
        bias=bias,
    )

    metrics = MetricRecord(
        {
            "num-examples": int(result["num_examples"]),
            "eval-loss": float(result["loss"]),
            "evaluation-time-seconds": float(
                result["evaluation_time_seconds"]
            ),
            "max-rss-kb": int(result["max_rss_kb"]),
            "is-iot-proxy": 1,
        }
    )

    return Message(
        content=RecordDict(
            {
                "metrics": metrics,
            }
        ),
        reply_to=message,
    )