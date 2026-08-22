"""pytorchexample: A Flower / PyTorch app."""

#import torch
from flwr.app import ArrayRecord, ConfigRecord, Context, MetricRecord
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg

from fl_thesis.task import Net, load_centralized_dataset, test

from datetime import datetime
from pathlib import Path
import csv
import json

from fl_thesis.task import get_client_data_distribution

app = ServerApp()
server_metrics = []
client_train_metrics = []
client_eval_metrics = []

@app.main()
def main(grid: Grid, context: Context) -> None:
    """Main entry point for the ServerApp."""
    print("SERVER MAIN STARTED", flush=True)
    import torch
    # Read run config
    num_rounds: int = context.run_config["num-server-rounds"]
    learning_rate: float = context.run_config["learning-rate"]
    fraction_train: float = context.run_config["fraction-train"]
    fraction_evaluate: float = context.run_config["fraction-evaluate"]

    # Initialize global model
    global_model = Net()
    arrays = ArrayRecord(global_model.state_dict())

    # Initialize strategy
    strategy = FedAvg(
        fraction_train=fraction_train,
        fraction_evaluate=fraction_evaluate,
    )

    # Create output directory for this run
    current_time = datetime.now()
    run_dir = current_time.strftime("%Y-%m-%d/%H-%M-%S")
    save_path = Path.cwd() / "outputs" / run_dir
    save_path.mkdir(parents=True, exist_ok=True)

    # Start federated training
    result = strategy.start(
        grid=grid,
        initial_arrays=arrays,
        train_config=ConfigRecord({"learning-rate": learning_rate}),
        num_rounds=num_rounds,
        evaluate_fn=global_evaluate,
    )

    # Save final model
    final_model_path = save_path / "final_model.pt"
    state_dict = result.arrays.to_torch_state_dict()
    torch.save(state_dict, final_model_path)
    print(f"\nFinal model saved to: {final_model_path}")

    # Save run config
    run_config_path = save_path / "run_config.json"

    with open(run_config_path, "w") as f:
        json.dump(dict(context.run_config), f, indent=4)

    # Save server-side metrics
    server_metrics_path = save_path / "server_metrics.csv"

    with open(server_metrics_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["round", "loss", "accuracy"],
        )
        writer.writeheader()
        writer.writerows(server_metrics)

    print(f"Run config saved to: {run_config_path}")
    print(f"Server metrics saved to: {server_metrics_path}")


    # Save client data distribution
    partition_strategy = context.run_config.get("partition-strategy", "iid")
    dirichlet_alpha = context.run_config.get("dirichlet-alpha", 0.5)
    num_clients = context.run_config.get("num-clients", 2)

    distribution_rows = get_client_data_distribution(
        num_partitions=num_clients,
        partition_strategy=partition_strategy,
        dirichlet_alpha=dirichlet_alpha,
    )

    distribution_path = save_path / "client_data_distribution.csv"

    with open(distribution_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "client_id",
                "class_0_count",
                "class_1_count",
                "total_samples",
            ],
        )
        writer.writeheader()
        writer.writerows(distribution_rows)

    print(f"Client data distribution saved to: {distribution_path}")


    # Save aggregated client-side train metrics
    client_train_metrics_path = save_path / "client_train_metrics.csv"

    # Collect all metric keys that appear across rounds
    train_metric_keys = set()

    for _, metrics in result.train_metrics_clientapp.items():
        train_metric_keys.update(metrics.keys())

    fieldnames = ["round"] + sorted(train_metric_keys)

    with open(client_train_metrics_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for rnd, metrics in result.train_metrics_clientapp.items():
            row = {"round": rnd}
            for key in train_metric_keys:
                row[key] = metrics.get(key, None)
            writer.writerow(row)

    print(f"Client train metrics saved to: {client_train_metrics_path}")


    # Save aggregated client-side evaluation metrics
    client_eval_metrics_path = save_path / "client_eval_metrics.csv"

    eval_metric_keys = set()

    for _, metrics in result.evaluate_metrics_clientapp.items():
        eval_metric_keys.update(metrics.keys())

    fieldnames = ["round"] + sorted(eval_metric_keys)

    with open(client_eval_metrics_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for rnd, metrics in result.evaluate_metrics_clientapp.items():
            row = {"round": rnd}
            for key in eval_metric_keys:
                row[key] = metrics.get(key, None)
            writer.writerow(row)

    print(f"Client eval metrics saved to: {client_eval_metrics_path}")



def global_evaluate(server_round: int, arrays: ArrayRecord) -> MetricRecord:
    """Evaluate model on centralized test data."""
    import torch
    # Load global model
    model = Net()
    model.load_state_dict(arrays.to_torch_state_dict())

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Load centralized test set
    test_dataloader = load_centralized_dataset()

    # Evaluate global model
    test_loss, test_acc = test(model, test_dataloader, device)

    server_metrics.append(
        {
            "round": server_round,
            "loss": test_loss,
            "accuracy": test_acc,
        }
    )
    # Return evaluation metrics
    return MetricRecord(
        {
            "accuracy": test_acc,
            "loss": test_loss,
        }
    )


