#!/bin/bash

virtualenv env --download --clear -p python3.7
source env/bin/activate
python --version

pip install -r requirements.txt
deactivate

