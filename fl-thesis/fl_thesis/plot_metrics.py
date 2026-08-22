from pathlib import Path
import argparse

import pandas as pd
import matplotlib.pyplot as plt

def plot_client_distribution(run_dir: Path):
    distribution_path = run_dir / "client_data_distribution.csv"
    plots_dir = run_dir / "plots"
    plots_dir.mkdir(exist_ok=True)

    df = pd.read_csv(distribution_path)

    plt.figure()
    plt.bar(df["client_id"], df["class_0_count"], label="Class 0")
    plt.bar(
        df["client_id"],
        df["class_1_count"],
        bottom=df["class_0_count"],
        label="Class 1",
    )

    plt.xlabel("Client ID")
    plt.ylabel("Number of samples")
    plt.title("Client Data Distribution")
    plt.legend()
    plt.grid(axis="y")
    plt.savefig(plots_dir / "client_data_distribution.png", bbox_inches="tight")
    plt.close()



def plot_metrics(run_dir: Path):
    metrics_path = run_dir / "server_metrics.csv"
    plots_dir = run_dir / "plots"
    plots_dir.mkdir(exist_ok=True)

    df = pd.read_csv(metrics_path)

    # Accuracy plot
    plt.figure()
    plt.plot(df["round"], df["accuracy"], marker="o")
    plt.xlabel("Round")
    plt.ylabel("Accuracy")
    plt.title("Server-side Accuracy per Round")
    plt.grid(True)
    plt.savefig(plots_dir / "server_accuracy.png", bbox_inches="tight")
    plt.close()

    # Loss plot
    plt.figure()
    plt.plot(df["round"], df["loss"], marker="o")
    plt.xlabel("Round")
    plt.ylabel("Loss")
    plt.title("Server-side Loss per Round")
    plt.grid(True)
    plt.savefig(plots_dir / "server_loss.png", bbox_inches="tight")
    plt.close()

    client_train_path = run_dir / "client_train_metrics.csv"

    if client_train_path.exists():
        train_df = pd.read_csv(client_train_path)

        if "train_loss" in train_df.columns:
            plt.figure()
            plt.plot(train_df["round"], train_df["train_loss"], marker="o")
            plt.xlabel("Round")
            plt.ylabel("Train loss")
            plt.title("Aggregated Client Train Loss per Round")
            plt.grid(True)
            plt.savefig(plots_dir / "client_train_loss.png", bbox_inches="tight")
            plt.close()

        if "training_time" in train_df.columns:
            plt.figure()
            plt.plot(train_df["round"], train_df["training_time"], marker="o")
            plt.xlabel("Round")
            plt.ylabel("Training time (seconds)")
            plt.title("Aggregated Client Training Time per Round")
            plt.grid(True)
            plt.savefig(plots_dir / "client_training_time.png", bbox_inches="tight")
            plt.close()

    client_eval_path = run_dir / "client_eval_metrics.csv"

    if client_eval_path.exists():
        eval_df = pd.read_csv(client_eval_path)

        if "eval_acc" in eval_df.columns:
            plt.figure()
            plt.plot(eval_df["round"], eval_df["eval_acc"], marker="o")
            plt.xlabel("Round")
            plt.ylabel("Evaluation accuracy")
            plt.title("Aggregated Client Evaluation Accuracy per Round")
            plt.grid(True)
            plt.savefig(plots_dir / "client_eval_accuracy.png", bbox_inches="tight")
            plt.close()

        if "eval_loss" in eval_df.columns:
            plt.figure()
            plt.plot(eval_df["round"], eval_df["eval_loss"], marker="o")
            plt.xlabel("Round")
            plt.ylabel("Evaluation loss")
            plt.title("Aggregated Client Evaluation Loss per Round")
            plt.grid(True)
            plt.savefig(plots_dir / "client_eval_loss.png", bbox_inches="tight")
            plt.close()


    if (run_dir / "client_data_distribution.csv").exists():
        plot_client_distribution(run_dir)

    print(f"Plots saved to: {plots_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Path to a run directory containing server_metrics.csv",
    )
    args = parser.parse_args()

    plot_metrics(Path(args.run_dir))