#!/bin/bash

export DRONEROOT="task_tracker_drone"

screen -S tt_drone -X quit

cd ${DRONEROOT}
virtualenv env --download --clear -p python3.7
source env/bin/activate
python --version
pip install -r requirements.txt
deactivate

echo "starting drone"
screen -S tt_drone -d -m bash -c "source env/bin/activate && python src/drone.py 'https://tt.simon987.net' 'tt_drone'"
sleep 1
screen -list
