#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FLAG_FILE="$DIR/mute.flag"

echo "Removing mute.flag..."
rm -f "$FLAG_FILE"

echo "Starting Ears on Windows via Scheduled Task..."
# Run the scheduled task which starts the batch script again
sshpass -p 6611 ssh -o StrictHostKeyChecking=no magic@192.168.50.204 "schtasks /run /tn \"RunEars\"" >/dev/null 2>&1

echo "Microphone unmuted successfully."
