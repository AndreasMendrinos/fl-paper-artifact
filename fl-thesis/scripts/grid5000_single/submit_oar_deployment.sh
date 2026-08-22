#!/bin/bash


set -euo pipefail

PROJECT_DIR="$HOME/fl-thesis"
SCRIPT_DIR="$PROJECT_DIR/scripts/grid5000"

NUM_PARTITIONS=2
RUN_CONFIG="num-server-rounds=10 num-clients=2 local-epochs=5 learning-rate=0.01 batch-size=16 partition-strategy='dirichlet' dirichlet-alpha=0.5"

RUN_ID="g5k_${OAR_JOB_ID}_$(date +%Y%m%d_%H%M%S)"
RUN_DIR="$PROJECT_DIR/logs/$RUN_ID"
mkdir -p "$RUN_DIR"

NODES=($(uniq "$OAR_NODEFILE"))

SUPERLINK_NODE="${NODES[0]}"
SUPERNODE_0="${NODES[1]}"
SUPERNODE_1="${NODES[2]}"

echo "Run directory: $RUN_DIR"
echo "OAR job id: $OAR_JOB_ID"
echo "SuperLink node: $SUPERLINK_NODE"
echo "SuperNode 0: $SUPERNODE_0"
echo "SuperNode 1: $SUPERNODE_1"

cleanup() {
    echo "Cleaning up Flower processes..."

    pkill -f flower-superlink || true

    oarsh "$SUPERNODE_0" "pkill -f flower-supernode || true" || true
    oarsh "$SUPERNODE_1" "pkill -f flower-supernode || true" || true

    echo "Cleanup done."
}

trap cleanup EXIT

echo "Starting SuperLink..."
bash "$SCRIPT_DIR/launch_superlink.sh" "$RUN_DIR" &

sleep 8

echo "Starting SuperNodes..."

oarsh "$SUPERNODE_0" "bash $SCRIPT_DIR/launch_supernode.sh $SUPERLINK_NODE 0 $NUM_PARTITIONS $RUN_DIR" &

oarsh "$SUPERNODE_1" "bash $SCRIPT_DIR/launch_supernode.sh $SUPERLINK_NODE 1 $NUM_PARTITIONS $RUN_DIR" &

sleep 10

echo "Starting Flower run..."

bash "$SCRIPT_DIR/run_flwr_app.sh" "$SUPERLINK_NODE" "$RUN_DIR" "$RUN_CONFIG"

echo "Flower deployment finished."
echo "Logs saved in: $RUN_DIR"
