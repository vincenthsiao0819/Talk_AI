#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FLAG_FILE="$DIR/mute.flag"

echo "Setting mute.flag..."
touch "$FLAG_FILE"

echo "Killing start_ears.bat and ears.py on Windows..."
# Terminate the infinite loop batch script
sshpass -p 6611 ssh -o StrictHostKeyChecking=no magic@192.168.50.204 "wmic process where \"CommandLine like '%start_ears%'\" call terminate" >/dev/null 2>&1
# Terminate the Python script
sshpass -p 6611 ssh -o StrictHostKeyChecking=no magic@192.168.50.204 "wmic process where \"CommandLine like '%ears.py%'\" call terminate" >/dev/null 2>&1

echo "Microphone muted successfully."
