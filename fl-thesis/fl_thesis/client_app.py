import torch

from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

from fl_thesis.task import Net, load_data
from fl_thesis.task import train as train_fn
from fl_thesis.task import test as test_fn

app = ClientApp()


@app.train()
def train(msg: Message, context: Context):
    """Train the model on local client data."""

    # Load global model parameters sent by the server
    model = Net()
    model.load_state_dict(msg.content["arrays"].to_torch_state_dict())

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Load this client's local dataset partition
    partition_id = context.node_config["partition-id"]
    num_partitions = context.node_config["num-partitions"]
    batch_size = context.run_config["batch-size"]
    partition_strategy = context.run_config.get("partition-strategy", "iid")
    dirichlet_alpha = context.run_config.get("dirichlet-alpha", 0.5)
    
    trainloader, _ = load_data(
        partition_id=partition_id,
        num_partitions=num_partitions,
        batch_size=batch_size,
        partition_strategy=partition_strategy,
        dirichlet_alpha=dirichlet_alpha,
    )
    # Train locally
    train_loss, train_metadata = train_fn(
        net=model,
        trainloader=trainloader,
        epochs=context.run_config["local-epochs"],
        #lr=context.run_config["learning-rate"],
        lr=msg.content["config"]["learning-rate"],
        device=device,
    )

    # Return updated model parameters + training metrics
    model_record = ArrayRecord(model.state_dict())

    metrics = {
        "train_loss": train_loss,
        "num-examples": len(trainloader.dataset),
        "training_time": train_metadata.training_time,
        "converged": int(train_metadata.converged),
    }

    for epoch_name, epoch_loss in train_metadata.training_losses.items():
        metrics[f"train_{epoch_name}_loss"] = epoch_loss

    metric_record = MetricRecord(metrics)

    content = RecordDict(
        {
            "arrays": model_record,
            "metrics": metric_record,
        }
    )

    return Message(content=content, reply_to=msg)


@app.evaluate()
def evaluate(msg: Message, context: Context):
    """Evaluate the model on local client test data."""

    # Load global model parameters sent by the server
    model = Net()
    model.load_state_dict(msg.content["arrays"].to_torch_state_dict())

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Load this client's validation/test data
    partition_id = context.node_config["partition-id"]
    num_partitions = context.node_config["num-partitions"]
    batch_size = context.run_config["batch-size"]
    partition_strategy = context.run_config.get("partition-strategy", "iid")
    dirichlet_alpha = context.run_config.get("dirichlet-alpha", 0.5)
    
    _, valloader = load_data(
        partition_id=partition_id,
        num_partitions=num_partitions,
        batch_size=batch_size,
        partition_strategy=partition_strategy,
        dirichlet_alpha=dirichlet_alpha,
    )

    # Evaluate locally
    eval_loss, eval_acc = test_fn(
        net=model,
        testloader=valloader,
        device=device,
    )

    # Return evaluation metrics
    metrics = {
        "eval_loss": eval_loss,
        "eval_acc": eval_acc,
        "num-examples": len(valloader.dataset),
    }

    metric_record = MetricRecord(metrics)
    content = RecordDict({"metrics": metric_record})

    return Message(content=content, reply_to=msg)
