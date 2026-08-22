from collections import OrderedDict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

import time
from dataclasses import dataclass


class Net(nn.Module):
    """Simple MLP for tabular binary classification."""

    def __init__(self):
        super(Net, self).__init__()
        self.fc1 = nn.Linear(30, 16)
        self.fc2 = nn.Linear(16, 8)
        self.fc3 = nn.Linear(8, 2)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)
    
'''
def load_data(partition_id: int, num_partitions: int, batch_size: int):
    """Load Breast Cancer data and return local train/validation loaders for one client."""

    dataset = load_breast_cancer()
    x = dataset.data.astype(np.float32)
    y = dataset.target.astype(np.int64)

    # Keep a centralized test set separate from all client data
    x_train_global, _, y_train_global, _ = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    # Normalize using only global training data
    scaler = StandardScaler()
    x_train_global = scaler.fit_transform(x_train_global).astype(np.float32)

    # Split global training data into client partitions
    x_partitions = np.array_split(x_train_global, num_partitions)
    y_partitions = np.array_split(y_train_global, num_partitions)

    x_client = x_partitions[partition_id]
    y_client = y_partitions[partition_id]

    # Split each client's local data into train and validation
    x_train, x_val, y_train, y_val = train_test_split(
        x_client,
        y_client,
        test_size=0.2,
        random_state=42,
        stratify=y_client,
    )

    trainset = TensorDataset(
        torch.tensor(x_train),
        torch.tensor(y_train),
    )

    valset = TensorDataset(
        torch.tensor(x_val),
        torch.tensor(y_val),
    )

    trainloader = DataLoader(trainset, batch_size=batch_size, shuffle=True)
    valloader = DataLoader(valset, batch_size=batch_size)

    return trainloader, valloader
'''

def create_dirichlet_partitions(
    x,
    y,
    num_partitions: int,
    alpha: float,
    seed: int = 42,
):
    """Create non-IID partitions using Dirichlet label distribution."""

    rng = np.random.default_rng(seed)

    partitions_indices = [[] for _ in range(num_partitions)]
    classes = np.unique(y)

    for cls in classes:
        cls_indices = np.where(y == cls)[0]
        rng.shuffle(cls_indices)

        proportions = rng.dirichlet(
            alpha=np.repeat(alpha, num_partitions)
        )

        split_points = (np.cumsum(proportions)[:-1] * len(cls_indices)).astype(int)
        cls_splits = np.split(cls_indices, split_points)

        for partition_id, split in enumerate(cls_splits):
            partitions_indices[partition_id].extend(split.tolist())

    x_partitions = []
    y_partitions = []

    for indices in partitions_indices:
        indices = np.array(indices)
        rng.shuffle(indices)

        x_partitions.append(x[indices])
        y_partitions.append(y[indices])

    return x_partitions, y_partitions

def get_client_data_distribution(
    num_partitions: int,
    partition_strategy: str = "iid",
    dirichlet_alpha: float = 0.5,
):
    """Return class distribution per client for the current partitioning strategy."""

    dataset = load_breast_cancer()
    x = dataset.data.astype(np.float32)
    y = dataset.target.astype(np.int64)

    x_train_global, _, y_train_global, _ = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    scaler = StandardScaler()
    x_train_global = scaler.fit_transform(x_train_global).astype(np.float32)

    if partition_strategy == "iid":
        y_partitions = np.array_split(y_train_global, num_partitions)

    elif partition_strategy == "dirichlet":
        _, y_partitions = create_dirichlet_partitions(
            x_train_global,
            y_train_global,
            num_partitions=num_partitions,
            alpha=dirichlet_alpha,
        )

    else:
        raise ValueError(f"Unknown partition strategy: {partition_strategy}")

    rows = []

    for client_id, y_client in enumerate(y_partitions):
        unique, counts = np.unique(y_client, return_counts=True)
        count_dict = dict(zip(unique, counts))

        rows.append(
            {
                "client_id": client_id,
                "class_0_count": int(count_dict.get(0, 0)),
                "class_1_count": int(count_dict.get(1, 0)),
                "total_samples": int(len(y_client)),
            }
        )

    return rows


def load_data(partition_id: int, num_partitions: int, batch_size: int, partition_strategy: str = "iid", dirichlet_alpha: float = 0.5):
    """Load Breast Cancer data and return local train/validation loaders for one client."""

    dataset = load_breast_cancer()
    x = dataset.data.astype(np.float32)
    y = dataset.target.astype(np.int64)

    # Keep a centralized test set separate from all client data
    x_train_global, _, y_train_global, _ = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    # Normalize using only global training data
    scaler = StandardScaler()
    x_train_global = scaler.fit_transform(x_train_global).astype(np.float32)

    # Split global training data into client partitions
    #x_partitions = np.array_split(x_train_global, num_partitions)
    #y_partitions = np.array_split(y_train_global, num_partitions)

    if partition_strategy == "iid":
        x_partitions = np.array_split(x_train_global, num_partitions)
        y_partitions = np.array_split(y_train_global, num_partitions)

    elif partition_strategy == "dirichlet":
        x_partitions, y_partitions = create_dirichlet_partitions(
            x_train_global,
            y_train_global,
            num_partitions=num_partitions,
            alpha=dirichlet_alpha,
        )

    else:
        raise ValueError(f"Unknown partition strategy: {partition_strategy}")

    x_client = x_partitions[partition_id]
    y_client = y_partitions[partition_id]

    # Split each client's local data into train and validation
    x_train, x_val, y_train, y_val = train_test_split(
        x_client,
        y_client,
        test_size=0.2,
        random_state=42,
        stratify=y_client,
    )

    trainset = TensorDataset(
        torch.tensor(x_train),
        torch.tensor(y_train),
    )

    valset = TensorDataset(
        torch.tensor(x_val),
        torch.tensor(y_val),
    )

    trainloader = DataLoader(trainset, batch_size=batch_size, shuffle=True)
    valloader = DataLoader(valset, batch_size=batch_size)

    return trainloader, valloader



def load_centralized_dataset(batch_size: int = 128):
    dataset = load_breast_cancer()
    x = dataset.data.astype(np.float32)
    y = dataset.target.astype(np.int64)

    x_train, x_test, _, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    scaler = StandardScaler()
    scaler.fit(x_train)
    x_test = scaler.transform(x_test).astype(np.float32)

    testset = TensorDataset(
        torch.tensor(x_test),
        torch.tensor(y_test),
    )

    return DataLoader(testset, batch_size=batch_size)


def train(net, trainloader, epochs: int, lr: float, device: str):
    """Train the model on the local client training set."""

    start_time = time.time()

    net.to(device)
    criterion = torch.nn.CrossEntropyLoss().to(device)
    optimizer = torch.optim.SGD(net.parameters(), lr=lr, momentum=0.9)
    net.train()

    running_loss = 0.0
    training_losses = {}

    for epoch in range(epochs):
        epoch_loss = 0.0

        for features, labels in trainloader:
            features = features.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = net(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            epoch_loss += loss.item()

        epoch_loss = epoch_loss / len(trainloader)
        training_losses[f"epoch_{epoch + 1}"] = epoch_loss

    avg_trainloss = running_loss / (epochs * len(trainloader))
    training_time = time.time() - start_time

    metadata = TrainProcessMetadata(
        training_time=training_time,
        converged=avg_trainloss < 0.1,
        training_losses=training_losses,
    )

    return avg_trainloss, metadata


def test(net, testloader, device: str):
    """Evaluate the model on a test set."""

    net.to(device)
    criterion = torch.nn.CrossEntropyLoss().to(device)

    correct = 0
    loss = 0.0

    net.eval()
    with torch.no_grad():
        for features, labels in testloader:
            features = features.to(device)
            labels = labels.to(device)

            outputs = net(features)
            loss += criterion(outputs, labels).item()
            predicted = torch.max(outputs.data, 1)[1]
            correct += (predicted == labels).sum().item()

    accuracy = correct / len(testloader.dataset)
    loss = loss / len(testloader)

    return loss, accuracy


@dataclass
class TrainProcessMetadata:
    """Metadata about the training process."""

    training_time: float
    converged: bool
    training_losses: dict[str, float]  # e.g. { "epoch_1": 0.5, "epoch_2": 0.3 }