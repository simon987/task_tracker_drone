#!/bin/bash

export DRONEROOT="task_tracker_drone"

screen -S tt_drone -X quit
echo "starting drone"
screen -S tt_drone -d -m bash -c "cd ${DRONEROOT} && source env/bin/activate && python src/drone.py"
sleep 1
screen -list
