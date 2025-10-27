#!/bin/bash

# Test script for Beam Search Planting Algorithm

# Configuration
CONFIG="gardeners/group10/config/test.json"
GUI_ON=false  # Set to true to enable GUI

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --gui)
            GUI_ON=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: bash test.sh [--gui]"
            exit 1
            ;;
    esac
done

# Run the test
if [ "$GUI_ON" = true ]; then
    echo "Running with GUI..."
    uv run python gardeners/group10/beam_search_planting_1026/test_runner.py --config "$CONFIG"
else
    echo "Running without GUI..."
    uv run python gardeners/group10/beam_search_planting_1026/test_runner.py --config "$CONFIG"
fi

