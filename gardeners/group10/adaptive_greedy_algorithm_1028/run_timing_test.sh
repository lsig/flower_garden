#!/bin/bash

# Run timing test and capture output
cd /Users/yuanyunchen/Desktop/GitHub/flower_garden-1

OUTPUT_FILE="/tmp/flower_garden_timing_test.txt"

echo "=== Flower Garden Timing Test ===" | tee $OUTPUT_FILE
echo "Start time: $(date)" | tee -a $OUTPUT_FILE
echo "" | tee -a $OUTPUT_FILE

# Run the test - will stop after first group placement is complete
python main.py --gardener g10 --json_path gardeners/group9/config/jack.json --turns 100 2>&1 | tee -a $OUTPUT_FILE

echo "" | tee -a $OUTPUT_FILE
echo "End time: $(date)" | tee -a $OUTPUT_FILE
echo "Output saved to: $OUTPUT_FILE"

