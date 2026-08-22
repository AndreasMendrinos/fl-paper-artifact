import argparse
import csv
import json
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt


def load_jsonl(path: Path) -> list[dict]:
    records = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if line:
                records.append(json.loads(line))

    return records


def build_rows(records: list[dict]) -> list[dict]:
    counters = {}
    rows = []

    for record in records:
        request = record.get("request", {})
        result = record.get("result", {})

        # Νέα structured μορφή broker
        command = record.get("command")

        # Εναλλακτικά, μπορεί να βρίσκεται μέσα στο request
        if command is None:
            command = request.get("command")

        # Συμβατότητα με παλιότερα broker records
        if command is None:
            if result.get("training_time_seconds") is not None:
                command = "train"
            elif result.get("evaluation_time_seconds") is not None:
                command = "evaluate"

        if command not in {"train", "evaluate"}:
            continue

        node_id = record.get(
            "node_id",
            result.get("node_id", "unknown"),
        )

        # Ξεχωριστή αρίθμηση γύρων ανά node και command
        counter_key = (node_id, command)
        counters[counter_key] = counters.get(counter_key, 0) + 1
        round_number = counters[counter_key]

        dataset = result.get("dataset", {})

        result_weights = result.get("weights")
        request_weights = request.get("weights")

        weight = None

        if result_weights:
            weight = result_weights[0]
        elif request_weights:
            weight = request_weights[0]

        rows.append(
            {
                "round": round_number,
                "command": command,
                "node_id": node_id,
                "loss": result.get("loss"),
                "initial_loss": result.get("initial_loss"),
                "loss_improvement": result.get("loss_improvement"),
                "weight": weight,
                "bias": result.get(
                    "bias",
                    request.get("bias"),
                ),
                "num_examples": result.get("num_examples"),
                "training_time_seconds": result.get(
                    "training_time_seconds"
                ),
                "evaluation_time_seconds": result.get(
                    "evaluation_time_seconds"
                ),
                "max_rss_kb": result.get("max_rss_kb"),
                "queue_wait_seconds": record.get(
                    "queue_wait_seconds"
                ),
                "execution_total_seconds": record.get(
                    "execution_total_seconds"
                ),
                "broker_total_seconds": record.get(
                    "broker_total_seconds"
                ),
                "dataset_seed": dataset.get("dataset_seed"),
                "x_min": dataset.get("x_min"),
                "x_max": dataset.get("x_max"),
                "x_mean": dataset.get("x_mean"),
                "x_std": dataset.get("x_std"),
                "noise_std": dataset.get("noise_std"),
                "node_variant": dataset.get("node_variant"),
            }
        )

    return rows


def write_csv(rows: list[dict], output_path: Path) -> None:
    if not rows:
        raise RuntimeError("No train/evaluate records found")

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)


def save_plot(
    x,
    values,
    xlabel,
    ylabel,
    title,
    path,
    label=None,
):
    plt.figure(figsize=(8, 5))

    plt.plot(
        x,
        values,
        marker="o",
        label=label,
    )

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, alpha=0.3)

    if label:
        plt.legend()

    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()


def plot_loss(rows: list[dict], plots_dir: Path) -> None:
    train = [
        row for row in rows
        if row["command"] == "train"
    ]

    evaluate = [
        row for row in rows
        if row["command"] == "evaluate"
    ]

    plt.figure(figsize=(8, 5))

    if train:
        plt.plot(
            [row["round"] for row in train],
            [row["loss"] for row in train],
            marker="o",
            label="Train loss",
        )

    if evaluate:
        plt.plot(
            [row["round"] for row in evaluate],
            [row["loss"] for row in evaluate],
            marker="o",
            label="Evaluation loss",
        )

    plt.xlabel("Federated round")
    plt.ylabel("Mean squared error")
    plt.title("IoT-LAB A8 model convergence")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        plots_dir / "loss_by_round.png",
        dpi=300,
    )
    plt.close()


def plot_parameters(
    rows: list[dict],
    plots_dir: Path,
) -> None:
    train = [
        row for row in rows
        if row["command"] == "train"
    ]

    plt.figure(figsize=(8, 5))

    plt.plot(
        [row["round"] for row in train],
        [row["weight"] for row in train],
        marker="o",
        label="Weight",
    )

    plt.plot(
        [row["round"] for row in train],
        [row["bias"] for row in train],
        marker="o",
        label="Bias",
    )

    plt.axhline(
        y=2.0,
        linestyle="--",
        label="Target weight",
    )

    plt.axhline(
        y=1.0,
        linestyle="--",
        label="Target bias",
    )

    plt.xlabel("Federated round")
    plt.ylabel("Parameter value")
    plt.title("Global model parameter evolution")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        plots_dir / "parameters_by_round.png",
        dpi=300,
    )
    plt.close()


def build_summary(rows: list[dict]) -> dict:
    train = [
        row for row in rows
        if row["command"] == "train"
    ]

    evaluate = [
        row for row in rows
        if row["command"] == "evaluate"
    ]

    training_times = [
        row["training_time_seconds"]
        for row in train
        if row["training_time_seconds"] is not None
    ]

    memory_values = [
        row["max_rss_kb"]
        for row in train
        if row["max_rss_kb"] is not None
    ]

    overheads = [
        row["broker_total_seconds"]
        for row in train
        if row["broker_total_seconds"] is not None
    ]

    return {
        "num_train_rounds": len(train),
        "num_evaluate_rounds": len(evaluate),
        "initial_train_loss": (
            train[0]["loss"] if train else None
        ),
        "final_train_loss": (
            train[-1]["loss"] if train else None
        ),
        "final_evaluate_loss": (
            evaluate[-1]["loss"]
            if evaluate
            else None
        ),
        "final_weight": (
            train[-1]["weight"] if train else None
        ),
        "final_bias": (
            train[-1]["bias"] if train else None
        ),
        "mean_training_time_seconds": (
            mean(training_times)
            if training_times
            else None
        ),
        "mean_max_rss_kb": (
            mean(memory_values)
            if memory_values
            else None
        ),
        "mean_broker_total_seconds": (
            mean(overheads)
            if overheads
            else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    metrics_dir = args.run_dir / "metrics"
    plots_dir = args.run_dir / "plots"

    plots_dir.mkdir(parents=True, exist_ok=True)

    results_file = metrics_dir / "results.jsonl"

    records = load_jsonl(results_file)
    rows = build_rows(records)

    write_csv(
        rows,
        metrics_dir / "round_metrics.csv",
    )

    summary = build_summary(rows)

    with (
        metrics_dir / "summary.json"
    ).open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    plot_loss(rows, plots_dir)
    plot_parameters(rows, plots_dir)

    train = [
        row for row in rows
        if row["command"] == "train"
    ]

    save_plot(
        [row["round"] for row in train],
        [
            row["training_time_seconds"] * 1000
            for row in train
        ],
        "Federated round",
        "Training time (ms)",
        "IoT-LAB A8 local training time",
        plots_dir / "training_time_by_round.png",
    )

    save_plot(
        [row["round"] for row in train],
        [
            row["max_rss_kb"] / 1024
            for row in train
        ],
        "Federated round",
        "Peak memory (MB)",
        "IoT-LAB A8 memory usage",
        plots_dir / "memory_by_round.png",
    )

    save_plot(
        [row["round"] for row in train],
        [
            row["broker_total_seconds"]
            for row in train
        ],
        "Federated round",
        "End-to-end duration (s)",
        "A8 task end-to-end latency",
        plots_dir / "end_to_end_latency_by_round.png",
    )

    print("Analysis completed")
    print("CSV:", metrics_dir / "round_metrics.csv")
    print("Summary:", metrics_dir / "summary.json")
    print("Plots:", plots_dir)


if __name__ == "__main__":
    main()
