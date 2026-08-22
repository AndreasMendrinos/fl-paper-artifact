import numpy as np

from flwr.app import ArrayRecord, ConfigRecord, Context
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg


app = ServerApp()


@app.main()
def main(grid: Grid, context: Context) -> None:
    num_rounds = int(
        context.run_config.get("num-server-rounds", 3)
    )
    learning_rate = float(
        context.run_config.get("learning-rate", 0.01)
    )
    local_epochs = int(
        context.run_config.get("local-epochs", 5)
    )

    # Array 0: weight
    # Array 1: bias
    initial_arrays = ArrayRecord(
        [
            np.asarray([0.0], dtype=np.float32),
            np.asarray([0.0], dtype=np.float32),
        ]
    )

    strategy = FedAvg(
        fraction_train=1.0,
        fraction_evaluate=1.0,
        min_train_nodes=1,
        min_evaluate_nodes=1,
        min_available_nodes=1,
    )

    result = strategy.start(
        grid=grid,
        initial_arrays=initial_arrays,
        train_config=ConfigRecord(
            {
                "learning-rate": learning_rate,
                "local-epochs": local_epochs,
            }
        ),
        num_rounds=num_rounds,
    )

    final_arrays = result.arrays.to_numpy_ndarrays()

    print("Final weight:", float(final_arrays[0].reshape(-1)[0]))
    print("Final bias:", float(final_arrays[1].reshape(-1)[0]))
    print("Final result:", result)