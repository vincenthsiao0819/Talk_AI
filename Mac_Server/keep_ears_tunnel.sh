#!/bin/bash
while true; do
    sshpass -p 6611 ssh -o StrictHostKeyChecking=no -N -R 5005:127.0.0.1:5005 magic@192.168.50.204
    sleep 5
done
