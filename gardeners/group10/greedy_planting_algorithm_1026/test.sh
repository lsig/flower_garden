#!/bin/bash

# Test script for Greedy Planting Algorithm
# Usage: ./test.sh
# Control: Set GUI_ON, CONFIG, and TURNS below

cd "$(dirname "$0")/../../.."

# Configuration
CONFIG="gardeners/group10/config/test.json"  # Path to nursery JSON
TURNS=100                                     # Simulation turns (optional, uses config.yaml max T if not set)
GUI_ON=false                                  # Set to true to enable GUI visualization

# Run test
if [ "$GUI_ON" = true ]; then
    uv run python gardeners/group10/greedy_planting_algorithm_1026/test_runner.py \
        --config "$CONFIG" \
        --turns "$TURNS" \
        --gui
else
    uv run python gardeners/group10/greedy_planting_algorithm_1026/test_runner.py \
        --config "$CONFIG" \
        --turns "$TURNS"
fi

